"""Status questions: a model outside the work answers and sorts the message.

The user picks it: a local LLM through Ollama, which costs no subscription, the idle
one of the working models, or a chosen provider. Each runs read-only, so asking never
changes the code or the agents' conversations. When the chosen one cannot answer, the
local model does, and with nothing available the coordinator answers from its records.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from typing import Optional

from . import limits
from . import plan as project_plan
from .gitops import Git
from .messages import Msg, in_language
from .paths import BIN, agent_path
from .scheduler import clock, label
from .store import Store
from .supervisor import Supervisor

ANSWER_TIMEOUT = 240
DIFF_LIMIT = 8000
COORDINATORS = ('local', 'idle', 'claude', 'codex', 'gemini')
DEFAULT_LOCAL_MODEL = 'gemma4:31b'
OLLAMA_TTL = 30
_ollama: dict = {'at': 0.0, 'models': []}


def ollama_url() -> str:
    return os.environ.get('GEMINI_OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')


def local_model(store: Store) -> str:
    return store.text_setting('local_model') or DEFAULT_LOCAL_MODEL


def ollama_ready(model: str) -> bool:
    """Ollama answers and has the model. Cached, because the panel asks every few seconds."""
    if time.time() - _ollama['at'] > OLLAMA_TTL:
        try:
            with urllib.request.urlopen(f'{ollama_url()}/api/tags', timeout=1.5) as response:
                _ollama['models'] = [item['name'] for item in json.load(response).get('models') or []]
        except (OSError, ValueError, KeyError):
            _ollama['models'] = []
        _ollama['at'] = time.time()
    return model in _ollama['models'] or f'{model}:latest' in _ollama['models']


def gemini_ready() -> bool:
    return shutil.which('gemini', path=agent_path()) is not None


def coordinator(store: Store) -> str:
    """The user's choice, else the local model when Ollama has it: it costs no subscription."""
    chosen = store.text_setting('coordinator')
    if chosen in COORDINATORS:
        return chosen
    return 'local' if ollama_ready(local_model(store)) else 'idle'


def coordinator_view(store: Store) -> dict:
    model = local_model(store)
    return {'choice': store.text_setting('coordinator'), 'effective': coordinator(store),
            'local_model': model, 'local_ready': ollama_ready(model), 'gemini_ready': gemini_ready()}


def facts(store: Store, project: dict, lang: str = 'pl') -> str:
    """What the coordinator knows for certain. Costs nothing to produce."""
    project_id = project['id']
    live = store.live(project_id) or {}
    lines = [Msg('facts_project', title=project['title'], status=Msg(f"status_{project['status']}"))]
    if project['status_detail']:
        lines.append((lang == 'en' and project['status_detail_en']) or project['status_detail'])
    if live.get('phase'):
        who = f"{label(live['speaker'])} " if live.get('speaker') else ''
        turn = Msg('facts_turn', turn=live['turn'], total=project['max_turns']) if live.get('turn') else ''
        lines.append(Msg('facts_now', who=who, phase=Msg(f"phase_{live['phase']}"), turn=turn))
        if live.get('until'):
            lines.append(Msg('facts_reason', reason=(lang == 'en' and live.get('reason_en'))
                             or live.get('reason'), until=clock(live['until'])))
    versions = store.versions(project_id)
    if versions:
        latest = versions[0]
        lines.append(Msg('facts_version', number=latest['number'], sha=latest['commit_sha'][:7],
                         summary=(lang == 'en' and latest['verify_summary_en'])
                         or latest['verify_summary']))
    else:
        lines.append(Msg('facts_no_version'))
    if project.get('worktree'):
        try:
            git = Git(project['worktree'])
            lines.append(Msg('facts_dirty', count=len(git.dirty().splitlines())))
            if project.get('base_commit'):
                lines += [Msg('facts_changes'), git.diff(project['base_commit'], limit=DIFF_LIMIT)]
        except Exception:
            pass
    recent = [(lang == 'en' and event['text_en']) or event['text']
              for event in store.events(project_id, 12)
              if event['kind'] in ('turn_end', 'handoff', 'takeover', 'version', 'verify',
                                   'waiting', 'attention', 'done', 'stopped', 'resumed', 'monitor')]
    if recent:
        lines += [Msg('facts_events'), *(f'- {text}' for text in recent[:8])]
    pending = [note for note in store.notes(project_id) if note['status'] == 'pending']
    if pending:
        lines.append(Msg('facts_notes', count=len(pending)))
    return '\n'.join(in_language(line, lang) for line in lines)


def pick_observer(speaker: Optional[str], snapshots: dict, store: Store) -> Optional[str]:
    """Prefer the idle model; among idle ones, whoever has more limit left."""
    ready = [name for name in limits.PROVIDERS
             if limits.availability(snapshots.get(name), store.threshold(name),
                                    store.block(name)).available]
    idle = [name for name in ready if name != speaker] or ready
    if not idle:
        return None
    return max(idle, key=lambda name: limits.remaining(snapshots.get(name)))


def _ask_claude(prompt: str, cwd: str) -> str:
    done = subprocess.run([str(BIN / 'claude'), '-p', prompt, '--output-format', 'json',
                           '--model', 'haiku', '--tools', 'Read,Grep,Glob',
                           '--no-session-persistence'],
                          cwd=cwd, capture_output=True, text=True, timeout=ANSWER_TIMEOUT,
                          stdin=subprocess.DEVNULL,
                          env={**os.environ, 'PATH': agent_path()})
    if done.returncode:
        raise RuntimeError(done.stderr[-300:] or 'claude nie odpowiedział')
    return (json.loads(done.stdout).get('result') or '').strip()


def _ask_codex(prompt: str, cwd: str) -> str:
    done = subprocess.run(['codex', 'exec', '--sandbox', 'read-only', '--ephemeral',
                           '--skip-git-repo-check', '--cd', cwd,
                           '-c', 'model_reasoning_effort="low"', prompt],
                          capture_output=True, text=True, timeout=ANSWER_TIMEOUT,
                          stdin=subprocess.DEVNULL,
                          env={**os.environ, 'PATH': agent_path()})
    if done.returncode:
        raise RuntimeError(done.stderr[-300:] or 'codex nie odpowiedział')
    return done.stdout.strip()


def _ask_gemini(prompt: str, cwd: str) -> str:
    done = subprocess.run(['gemini', '-p', prompt, '--output-format', 'json', '--approval-mode', 'plan'],
                          cwd=cwd, capture_output=True, text=True, timeout=ANSWER_TIMEOUT,
                          stdin=subprocess.DEVNULL, env={**os.environ, 'PATH': agent_path()})
    if done.returncode:
        raise RuntimeError(done.stderr[-300:] or 'gemini nie odpowiedział')
    return (json.loads(done.stdout).get('response') or '').strip()


def _ask_local(prompt: str, model: str) -> str:
    """Ollama's chat API on this machine: no files, only the facts in the prompt."""
    body = json.dumps({'model': model, 'messages': [{'role': 'user', 'content': prompt}],
                       'stream': False, 'options': {'temperature': 0.2}}).encode()
    request = urllib.request.Request(f'{ollama_url()}/api/chat', data=body,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=ANSWER_TIMEOUT) as response:
        return (json.load(response).get('message') or {}).get('content', '').strip()


ASKERS = {'claude': _ask_claude, 'codex': _ask_codex, 'gemini': _ask_gemini}


_QUESTION = re.compile(r'^\s*(co|jak|czy|gdzie|kiedy|ile|dlaczego|kto|który|jaki|what|how|why|when|where|is|are|does|do|can)\b',
                       re.I)
_TYPE = re.compile(r'^\s*TYP\s*:\s*(PYTANIE|ZLECENIE|UWAGA)\s*$', re.M | re.I)
KINDS = {'PYTANIE': 'question', 'ZLECENIE': 'order', 'UWAGA': 'note'}


_INFO = re.compile(r'nie podejmuj|nie r[óo]b|nie pracuj|napisz mi|jak si[ęe] ma|jaki jest stan|raport|status'
                   r'|wynik|podsumuj|tell me|report|don.t (start|work)', re.I)


def guess_kind(text: str) -> str:
    """Without a model at hand: a question or a request for information stays an answer."""
    return 'question' if text.strip().endswith('?') or _QUESTION.match(text) or _INFO.search(text) else 'note'


def _prompt(project: dict, known: str, question: str, lang: str, relation: str, files: bool) -> str:
    where = ('Opieraj się na faktach poniżej i na plikach w bieżącym folderze, w tym .sol83/plan.json.'
             if files else 'Nie masz dostępu do plików: opieraj się tylko na faktach poniżej.')
    return (f'Jesteś obserwatorem projektu. Tylko czytasz: niczego nie zmieniaj. {relation}'
            'Pierwsza linia odpowiedzi to dokładnie jedno z: TYP: PYTANIE, TYP: ZLECENIE, TYP: UWAGA. '
            'PYTANIE: użytkownik chce informacji. ZLECENIE: chce nowej pracy, funkcji albo badania. '
            'UWAGA: poprawka albo wskazówka do bieżącej pracy. W razie wątpliwości wybierz PYTANIE: '
            'prośba o informację, stan, raport, wyniki albo polecenie, by nie podejmować pracy, '
            'jest zawsze PYTANIEM. Zlecenie i uwagę koordynator sam '
            'przekaże modelom, które pracują, więc wtedy napisz tylko krótko, co z tym zrobią. '
            f"Potem odpowiedz krótko {'po angielsku' if lang == 'en' else 'po polsku'}, zwykłym tekstem "
            f'bez Markdown. {where} Jeśli czegoś nie wiesz, powiedz to wprost.\n\n'
            f'Zadanie projektu:\n{project["task"][:3000]}\n\n'
            f'Fakty od koordynatora:\n{known}\n\nWiadomość użytkownika: {question}')


def _plan_facts(project: dict) -> str:
    """The plan summary, for a model that cannot read the files itself."""
    plan, _ = project_plan.load(project['worktree']) if project.get('worktree') else (None, None)
    return f'\n{project_plan.summary(plan, [])}' if plan else ''


def answer(supervisor: Supervisor, project_id: str, question_id: int, question: str,
           lang: str = 'pl', interrupted: bool = False) -> str:
    """One box for everything: the chosen coordinator answers and says whether the message is
    a question, a new work order or a note for the current work. Work goes to the agents."""
    store = supervisor.store
    project = store.project(project_id)
    known = facts(store, project, lang)

    def reply(text: str, author: str, kind: str) -> str:
        store.answer_question(question_id, text, author)
        who = Msg('coordinator') if author == 'koordynator' else label(author)
        store.event(project_id, 'answer', Msg('question_answered', who=who), body=text,
                    agent=None if author == 'koordynator' else author)
        if kind in ('order', 'note'):
            supervisor.add_note(project_id, question, order=kind == 'order')
            if interrupted:
                supervisor.continue_after_interrupt(project_id)
            store.event(project_id, 'routed', Msg('routed_order' if kind == 'order' else 'routed_note'))
        return kind

    live = store.live(project_id) or {}
    worktree = project.get('worktree')
    chosen = coordinator(store)
    problems = []
    for who in dict.fromkeys([chosen, 'local']):
        if who == 'local':
            model = local_model(store)
            if not ollama_ready(model):
                continue
            prompt = _prompt(project, known + _plan_facts(project), question, lang, '', files=False)
            ask = lambda: _ask_local(prompt, model)  # noqa: E731
        else:
            if not worktree:
                continue
            snapshots = supervisor.reader.read()
            observer = (pick_observer(live.get('speaker'), snapshots, store) if who == 'idle'
                        else who if who in limits.PROVIDERS and limits.availability(
                            snapshots.get(who), store.threshold(who), store.block(who)).available
                        else who if who == 'gemini' and gemini_ready() else None)
            if observer is None:
                continue
            active = live.get('speaker')
            relation = (f'{label(active)} właśnie pracuje w tym folderze, więc pliki mogą się zmieniać. '
                        if active and active != observer else '')
            prompt = _prompt(project, known, question, lang, relation, files=True)
            ask = (lambda observer=observer, prompt=prompt: ASKERS[observer](prompt, worktree))  # noqa: E731
            who = observer
        try:
            text = ask()
        except Exception as exc:
            problems.append(f'{label(who)}: {str(exc)[:200]}')
            continue
        match = _TYPE.search(text or '')
        kind = KINDS[match[1].upper()] if match else guess_kind(question)
        body = _TYPE.sub('', text or '').strip()
        return reply(body or known, who if body else 'koordynator', kind)
    note = f"\n\n({'; '.join(problems)})" if problems else ''
    return reply(known + note, 'koordynator', guess_kind(question))
