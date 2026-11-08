"""RUN: start one version of a project from the user's folder, under control (spec point 11).

The run plan is derived once per version (agents' HOW TO RUN, the plan's `run`, the README), with
help from the local LLM when it is there, checked, and stored with the version's commit and a hash
of its manifests; it is not regenerated on every click. Only plain commands of known launchers are
executed, without a shell, in the version's folder, inside the OS sandbox (network allowed, writes
limited to that folder); never `sudo`, never a pipe from the network, never an install that needs an
administrator. Processes are identified by pid and start time, so after a restart Sol-83 knows which
ones are still its own, and it never kills a process it did not start. A second click while a run is
alive returns that run.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional

from . import sandbox
from .gitops import Git

LAUNCHERS = {'python3', 'python', 'node', 'npm', 'npx', 'pnpm', 'yarn', 'bun', 'deno', 'make', 'cargo', 'go',
             'java', 'mvn', 'gradle', 'uv', 'poetry', 'ruby', 'bundle', 'flask', 'uvicorn', 'streamlit', 'php',
             'dotnet', 'swift', 'open', 'xdg-open'}
SETUP_ARGS = {'npm': {'install', 'ci', 'i'}, 'pnpm': {'install', 'i'}, 'yarn': {'install'}, 'bun': {'install'},
              'pip': {'install'}, 'pip3': {'install'}, 'uv': {'sync', 'venv', 'pip'}, 'poetry': {'install'},
              'bundle': {'install'}, 'cargo': {'build', 'fetch'}, 'go': {'build', 'mod'}}
FORBIDDEN = re.compile(r'^(sudo|su|doas|rm|dd|mkfs|chmod|chown|curl|wget|bash|sh|zsh|eval|kill|pkill|killall|'
                       r'launchctl|systemctl|brew|apt|apt-get|dnf|yum|pacman|port)$')
SHELL_CHARS = re.compile(r'[|;&`$<>]')
MANIFESTS = ('package.json', 'package-lock.json', 'requirements.txt', 'pyproject.toml', 'Cargo.toml', 'go.mod',
             'Makefile', 'README.md', 'Gemfile', '.sol83/plan.json')
SOL83_PORT = 8765
PORT_RANGE = range(8800, 8900)
URL = re.compile(r'https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?[^\s"\'<>]*')
LIBRARY_HINTS = re.compile(r'\b(library|biblioteka|package|pakiet|sdk|module only)\b', re.I)
OLLAMA_URL = os.environ.get('GEMINI_OLLAMA_URL', 'http://127.0.0.1:11434')
# A document project (a handbook, a research report) is built once and then read: "open dist/x.html".
# A file path, not part of a web address: "open http://localhost:8000/index.html" is an app, not a document.
DOCUMENT = re.compile(r'(?:^|\b)(?:open|otw[óo]rz|xdg-open)\b[^\n]*?(?:^|(?<=[\s`\'"(]))([\w.-][\w./-]*\.html?)\b', re.I)
TEST_STEP = re.compile(r'\b(unittest|pytest|nose2|tox|jest|vitest|mocha)\b|\b(npm|pnpm|yarn|bun) (run )?test\b'
                       r'|\b(go|cargo|swift|mvn|gradle|dotnet) test\b')
ONE_SHOT_TIMEOUT = 600
# Stored run plans of an older format are derived again (format 2: comments removed, documents, 2026-11-08).
PLAN_FORMAT = 2


class RunError(RuntimeError):
    pass


def manifest_hash(repo: str, commit: str) -> str:
    """What the run plan depends on in this commit: launch-relevant files only."""
    git = Git(repo)
    parts = []
    for name in MANIFESTS:
        if git.ok('cat-file', '-e', f'{commit}:{name}'):
            parts.append(name + ':' + git.run('rev-parse', f'{commit}:{name}'))
    return hashlib.sha256('\n'.join(parts).encode()).hexdigest()[:16]


def strip_comment(line: str) -> str:
    """The command without its trailing shell comment ("python3 build.py   # writes dist/"), quotes respected.
    2026-11-08: RUN passed "#", "writes", ... as arguments and the build exited at once with an error."""
    quote = None
    for index, char in enumerate(line):
        if quote:
            if char == quote:
                quote = None
        elif char in '\'"':
            quote = char
        elif char == '#' and (index == 0 or line[index - 1].isspace()):
            return line[:index].rstrip()
    return line.rstrip()


def _clean(line: str) -> str:
    line = line.strip().lstrip('$').strip()
    line = re.sub(r'^[-*\d.)]+\s+', '', line).strip()
    if line.startswith('`') and line.endswith('`'):
        line = line.strip('`').strip()
    return strip_comment(line)


def _is_command(line: str) -> bool:
    """A line that starts with a program (optionally after VAR=value), not prose like "Open the file in a browser"."""
    words = line.split()
    while words and re.match(r'^[A-Za-z_]\w*=\S*$', words[0]):
        words = words[1:]
    return bool(words) and bool(re.match(r'^[a-z0-9_./-][\w./-]*$', words[0])) and not words[0].endswith('.')


def _commands(text: str) -> list:
    """Command lines from free text: fenced code first, else lines that look like commands. Comments,
    prompt signs and list markers are removed."""
    blocks = re.findall(r'```[\w-]*\n(.*?)```', text or '', re.S)
    lines = '\n'.join(blocks).splitlines() if blocks else (text or '').splitlines()
    found = []
    for raw in lines:
        line = _clean(raw)
        if line and _is_command(line) and not DOCUMENT.match(line):
            found.append(line)
    return found


def document_target(text: str) -> Optional[str]:
    """The HTML file the instructions say to open, if any."""
    match = DOCUMENT.search(text or '')
    return match[1].lstrip('./') if match else None


def terminal_lines(text: Optional[str], folder: str) -> list:
    """Commands to paste into a terminal, exactly as they run: cd into the version's folder first, no
    comments, no prose, in the order the agents gave, and "open" for a document to read."""
    lines = [f'cd {shlex.quote(str(folder))}']
    for line in _commands(text or ''):
        if line.split()[0] == 'cd':
            continue
        if line not in lines:
            lines.append(line)
    target = document_target(text or '')
    if target and not any(line.startswith(('open ', 'xdg-open ')) for line in lines):
        lines.append(f'open {shlex.quote(target)}')
    return lines


def ask_local_terminal(text: str, folder: str, model: Optional[str] = None, timeout: float = 90) -> Optional[list]:
    """The local coordinator rewrites free-form instructions as a clean terminal sequence. Its answer is
    checked line by line (comments and prose are dropped); None when it is not there or says nothing usable."""
    prompt = ('Przepisz instrukcję uruchomienia projektu na polecenia do wklejenia w terminal macOS (zsh). '
              'Wypisz wyłącznie polecenia, po jednym w linii, w kolejności wykonania, bez numeracji, bez komentarzy '
              '(żadnego #), bez opisów i bez bloków ```. Pierwsza linia: cd ' + shlex.quote(str(folder)) + '. '
              'Jeśli trzeba otworzyć plik HTML w przeglądarce, użyj: open <ścieżka>. Instrukcja:\n\n' + (text or '')[:6000])
    body = json.dumps({'model': model or os.environ.get('SOL83_LOCAL_MODEL', 'gemma4:31b'), 'stream': False,
                       'prompt': prompt}).encode()
    try:
        request = urllib.request.Request(OLLAMA_URL + '/api/generate', body, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            answer = json.loads(response.read()).get('response') or ''
    except (OSError, ValueError):
        return None
    answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.S)
    lines = [line for line in (_clean(raw) for raw in answer.splitlines()) if line and _is_command(line)]
    if not lines or not lines[0].startswith('cd '):
        return None
    return lines


def check_step(line: str, folder: Path) -> dict:
    """One command, validated: plain argv, a known launcher or a script inside the folder, no shell."""
    line = strip_comment(line)
    if SHELL_CHARS.search(line.replace('{port}', '')):
        raise RunError(f'polecenie z operatorami powłoki nie jest wykonywane: {line}')
    try:
        argv = shlex.split(line)
    except ValueError as exc:
        raise RunError(f'niepoprawne polecenie: {line} ({exc})')
    if not argv:
        raise RunError('puste polecenie')
    if argv[0] == 'cd':
        return {'kind': 'cd', 'argv': argv}
    head = Path(argv[0]).name
    if FORBIDDEN.match(head):
        raise RunError(f'niedozwolone polecenie: {head}')
    if argv[0].startswith(('./', '../')) or '/' in argv[0]:
        target = (folder / argv[0]).resolve()
        if not target.is_relative_to(folder.resolve()):
            raise RunError(f'skrypt poza folderem wersji: {argv[0]}')
    elif head not in LAUNCHERS and head not in SETUP_ARGS:
        raise RunError(f'nieznany program: {head}; dozwolone są typowe narzędzia uruchomieniowe')
    kind = 'setup' if head in SETUP_ARGS and len(argv) > 1 and argv[1] in SETUP_ARGS[head] else 'start'
    if head in ('pip', 'pip3') and kind == 'setup' and '--user' not in argv and not (folder / '.venv').exists():
        raise RunError('instalacja pip poza wirtualnym środowiskiem projektu nie jest wykonywana automatycznie')
    return {'kind': kind, 'argv': argv}


def ask_local_llm(text: str, timeout: float = 60) -> Optional[list]:
    """The local model turns free-form instructions into command lines. None when it is not there:
    then the stored plan or the manual instruction is used, never a paid model."""
    body = json.dumps({'model': os.environ.get('SOL83_LOCAL_MODEL', 'gemma4:31b'), 'stream': False,
                       'prompt': 'Z poniższej instrukcji wypisz wyłącznie polecenia uruchomienia aplikacji, po jednym '
                                 'w linii, bez komentarzy i bez operatorów powłoki:\n\n' + text[:6000]}).encode()
    try:
        request = urllib.request.Request(OLLAMA_URL + '/api/generate', body, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _commands(json.loads(response.read()).get('response') or '')
    except (OSError, ValueError):
        return None


def derive(text: Optional[str], folder: Path, use_llm: bool = True) -> dict:
    """A checked plan from instructions, or a plan marked unavailable with the reason."""
    if not text or not text.strip():
        return {'available': False, 'reason': 'brak instrukcji uruchomienia w tej wersji', 'steps': []}
    lines = _commands(text)
    source = 'instrukcja'
    if not lines and use_llm:
        lines = ask_local_llm(text) or []
        source = 'lokalny LLM'
    steps, problems = [], []
    for line in lines:
        try:
            steps.append(check_step(line, folder))
        except RunError as exc:
            problems.append(str(exc))
    steps = [step for step in steps if step['kind'] != 'cd']
    target = document_target(text)
    if target:
        # A document: its build steps run once, to the end, then the folder is served and the file opened.
        # Test commands are the coordinator's and the agents' job, not part of opening the document.
        build = [step for step in steps if not TEST_STEP.search(shlex.join(step['argv']))]
        return {'available': True, 'kind': 'document', 'document': target, 'steps': build, 'problems': problems,
                'source': source, 'manual': text[:2000], 'format': PLAN_FORMAT}
    if not any(step['kind'] == 'start' for step in steps):
        library = bool(LIBRARY_HINTS.search(text))
        return {'available': False, 'steps': steps, 'problems': problems, 'source': source,
                'reason': 'to biblioteka albo projekt bez aplikacji do uruchomienia' if library
                else 'nie znaleziono dozwolonego polecenia startu', 'manual': text[:2000]}
    return {'available': True, 'steps': steps, 'problems': problems, 'source': source, 'manual': text[:2000],
            'format': PLAN_FORMAT}


def free_port(taken: set) -> int:
    for port in PORT_RANGE:
        if port == SOL83_PORT or port in taken:
            continue
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                continue
        return port
    raise RunError('brak wolnego portu w zakresie 8800-8899')


def process_start(pid: int) -> Optional[str]:
    out = subprocess.run(['ps', '-o', 'lstart=', '-p', str(pid)], capture_output=True, text=True,
                         env={**os.environ, 'LC_ALL': 'C'}).stdout.strip()
    return out or None


def alive(row: dict) -> bool:
    """Still our process: the pid exists and started when we started it (a reused pid does not count)."""
    return bool(row.get('pid')) and process_start(row['pid']) == row.get('started')


def missing_tools(steps: list) -> list:
    path = os.environ.get('PATH', '')
    return sorted({step['argv'][0] for step in steps if '/' not in step['argv'][0]
                   and not shutil.which(step['argv'][0], path=path)})


def start(store, project_id: str, version: int, folder: Path, plan: dict, log_path: Path) -> dict:
    """Run the plan's setup steps, then start the app in the background. Returns the run record."""
    current = store._row("SELECT * FROM app_runs WHERE project_id=? AND state='running' ORDER BY id DESC LIMIT 1",
                         (project_id,))
    if current and alive(current):
        return {**current, 'duplicate': True}
    if not plan.get('available'):
        raise RunError(plan.get('reason') or 'RUN niedostępny')
    missing = missing_tools(plan['steps'])
    if missing:
        raise RunError('brakuje programów: ' + ', '.join(missing) + '. Zainstaluj je (bez uprawnień administratora, '
                       'np. przez menedżer wersji języka) i spróbuj ponownie.')
    taken = {row['port'] for row in store._rows("SELECT port FROM app_runs WHERE state='running'") if row['port']}
    port = free_port(taken)
    env = {**os.environ, 'PORT': str(port), 'HOST': '127.0.0.1'}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if plan.get('kind') == 'document':
        return _start_document(store, project_id, version, folder, plan, log_path, port, env)
    log = open(log_path, 'ab')
    try:
        for step in plan['steps']:
            if step['kind'] != 'setup':
                continue
            argv = [part.replace('{port}', str(port)) for part in step['argv']]
            done = sandbox.run(argv, folder, network=True, timeout=1800, env=env,
                               write=[p for p in (Path.home() / '.npm', Path.home() / '.cache',
                                                  Path.home() / 'Library/Caches') if p.exists()],
                               allow_unsandboxed=bool(store.setting('allow_unsandboxed', 0)))
            log.write(f'$ {shlex.join(argv)}\n{done.output}\n'.encode())
            if done.returncode:
                raise RunError(f'krok przygotowania nie powiódł się: {shlex.join(argv)} (kod {done.returncode})')
        launch = next(step for step in plan['steps'] if step['kind'] == 'start')
        argv = [part.replace('{port}', str(port)) for part in launch['argv']]
        command = sandbox.wrap(argv, [folder], network=True) if sandbox.backend() else (
            argv if store.setting('allow_unsandboxed', 0) else None)
        if command is None:
            raise RunError(sandbox.NO_SANDBOX)
        log.write(f'$ {shlex.join(argv)}  (port {port})\n'.encode())
        log.flush()
        proc = subprocess.Popen(command, cwd=str(folder), env=env, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
    finally:
        log.close()
    record = {'project_id': project_id, 'version': version, 'pid': proc.pid, 'started': process_start(proc.pid),
              'port': port, 'command': shlex.join(argv), 'folder': str(folder), 'log': str(log_path),
              'state': 'running', 'created_at': time.time()}
    with store._db() as db:
        cursor = db.execute('INSERT INTO app_runs(project_id,version,pid,started,port,command,folder,log,state,created_at) '
                            'VALUES(:project_id,:version,:pid,:started,:port,:command,:folder,:log,:state,:created_at)',
                            record)
        record['id'] = cursor.lastrowid
    return record


def _start_document(store, project_id: str, version: int, folder: Path, plan: dict, log_path: Path,
                    port: int, env: dict) -> dict:
    """Build the document once (each step to its end, in the sandbox), then serve the folder on a free local
    port and point at the file. A separate port keeps the document's scripts away from the panel's origin."""
    with open(log_path, 'ab') as log:
        for step in plan['steps']:
            argv = [part.replace('{port}', str(port)) for part in step['argv']]
            done = sandbox.run(argv, folder, network=True, timeout=ONE_SHOT_TIMEOUT, env=env,
                               allow_unsandboxed=bool(store.setting('allow_unsandboxed', 0)))
            log.write(f'$ {shlex.join(argv)}\n{done.output}\n'.encode())
            if done.returncode:
                raise RunError(f'budowanie dokumentu nie powiodło się: {shlex.join(argv)} (kod {done.returncode}); '
                               f'{(done.output or "").strip().splitlines()[-1][:200] if (done.output or "").strip() else ""}')
        target = folder / plan['document']
        if not target.resolve().is_relative_to(folder.resolve()) or not target.is_file():
            raise RunError(f'po budowaniu brak pliku {plan["document"]} w folderze wersji')
        argv = [sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1']
        command = sandbox.wrap(argv, [folder], network=True) if sandbox.backend() else (
            argv if store.setting('allow_unsandboxed', 0) else None)
        if command is None:
            raise RunError(sandbox.NO_SANDBOX)
        url = f'http://127.0.0.1:{port}/{plan["document"]}'
        log.write(f'$ {shlex.join(argv)}\nDokument: {url}\n'.encode())
        log.flush()
        proc = subprocess.Popen(command, cwd=str(folder), env=env, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
    record = {'project_id': project_id, 'version': version, 'pid': proc.pid, 'started': process_start(proc.pid),
              'port': port, 'command': shlex.join(argv), 'folder': str(folder), 'log': str(log_path),
              'state': 'running', 'created_at': time.time(), 'url': url}
    with store._db() as db:
        cursor = db.execute('INSERT INTO app_runs(project_id,version,pid,started,port,command,folder,log,state,created_at,url) '
                            'VALUES(:project_id,:version,:pid,:started,:port,:command,:folder,:log,:state,:created_at,:url)',
                            record)
        record['id'] = cursor.lastrowid
    return record


def stop(store, run_id: int) -> bool:
    """Stop a run Sol-83 started, and only that: the process group of the recorded, still-matching pid."""
    row = store._row('SELECT * FROM app_runs WHERE id=?', (run_id,))
    if not row:
        return False
    if alive(row):
        try:
            os.killpg(row['pid'], signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    with store._db() as db:
        db.execute("UPDATE app_runs SET state='stopped', stopped_at=? WHERE id=?", (time.time(), run_id))
    return True


def view(store, project_id: str) -> Optional[dict]:
    """The latest run with its real state (checked, not assumed), web address and log tail."""
    row = store._row('SELECT * FROM app_runs WHERE project_id=? ORDER BY id DESC LIMIT 1', (project_id,))
    if not row:
        return None
    if row['state'] == 'running' and not alive(row):
        with store._db() as db:
            db.execute("UPDATE app_runs SET state='ended' WHERE id=?", (row['id'],))
        row['state'] = 'ended'
    tail = ''
    try:
        tail = Path(row['log']).read_text(errors='replace')[-4000:]
    except OSError:
        pass
    urls = URL.findall(tail)
    found = urls[-1].replace('0.0.0.0', '127.0.0.1') if urls else None
    return {**row, 'log_tail': sandbox.secretscan.redact(tail), 'url': row.get('url') or found}
