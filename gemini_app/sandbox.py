"""OS sandbox for code the agents wrote and the coordinator runs: test commands, the
project's `.gemini-setup`, and the Antigravity CLI itself.

The agents work inside their own sandboxes, but the coordinator used to run their test
command and setup script with the user's full rights. Everything that executes code from
the repository now goes through `run()`: writes only to the given folders and a private
temp folder, no reading of credential stores, and no outbound network unless the call
asks for it. macOS uses Seatbelt (`sandbox-exec`), Linux uses bubblewrap (`bwrap`).
Without either, nothing runs unless the user explicitly allowed unsandboxed execution.

Usage as a command, for Duet's own verify step: `python3 -m gemini_app.sandbox verify`.
"""
from __future__ import annotations

import dataclasses
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Sequence

from . import secretscan

HOME = Path.home()
# Read-protected for any sandboxed code: logins, keys and browser data.
CREDENTIALS = ('.ssh', '.aws', '.gnupg', '.config/gh', '.config/gcloud', '.netrc', '.git-credentials',
               '.docker/config.json', '.kube', '.npmrc', '.pypirc', '.codex', '.claude', '.claude.json',
               '.gemini', 'Library/Keychains', 'Library/Cookies',
               'Library/Application Support/Claude', 'Library/Application Support/Antigravity',
               'Library/Application Support/Google/Chrome', 'Library/Application Support/Firefox',
               'Library/Safari', '.mozilla', '.config/google-chrome', '.local/share/keyrings')
TIMEOUT_EXIT = 124
REFUSED_EXIT = 126


@dataclasses.dataclass
class Result:
    returncode: int
    output: str
    sandbox: Optional[str]


def backend() -> Optional[str]:
    """The sandbox this machine offers, or None. SOL83_SANDBOX=off is for diagnosis only."""
    if os.environ.get('SOL83_SANDBOX') == 'off':
        return None
    if sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').exists():
        return 'sandbox-exec'
    if sys.platform.startswith('linux') and shutil.which('bwrap'):
        return 'bwrap'
    return None


def _quote(path) -> str:
    return '"' + str(path).replace('\\', '\\\\').replace('"', '\\"') + '"'


def _real(paths: Sequence) -> list:
    """Seatbelt matches resolved paths (/tmp is /private/tmp on macOS)."""
    found = []
    for path in paths:
        if path:
            found += [Path(path), Path(path).resolve()] if Path(path).exists() else [Path(path)]
    return sorted(set(found), key=str)


def seatbelt_profile(write: Sequence, deny_read: Sequence, network: bool) -> str:
    lines = ['(version 1)', '(allow default)', '(deny file-write*)',
             '(allow file-write* (literal "/dev/null") (literal "/dev/zero") (literal "/dev/dtracehelper")'
             ' (regex #"^/dev/tty") (regex #"^/dev/fd/"))']
    if write:
        lines.append('(allow file-write* ' + ' '.join(f'(subpath {_quote(p)})' for p in _real(write)) + ')')
    if deny_read:
        lines.append('(deny file-read* ' + ' '.join(f'(subpath {_quote(p)})' for p in _real(deny_read)) + ')')
    if not network:
        lines += ['(deny network-outbound)', '(allow network-outbound (remote unix-socket))',
                  '(allow network-outbound (remote ip "localhost:*"))']
    return '\n'.join(lines)


def bwrap_args(write: Sequence, deny_read: Sequence, network: bool) -> list:
    args = ['bwrap', '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc', '--die-with-parent']
    for path in write:
        if Path(path).exists():
            args += ['--bind', str(path), str(path)]
    for path in deny_read:
        if Path(path).is_dir():
            args += ['--tmpfs', str(path)]
        elif Path(path).exists():
            args += ['--ro-bind', '/dev/null', str(path)]
    if not network:
        args.append('--unshare-net')
    return args + ['--']


def wrap(command: Sequence, write: Sequence, network: bool = False,
         deny_read: Sequence = (), kind: Optional[str] = None) -> Optional[list]:
    """The command wrapped in the sandbox, or None when there is none. SOL83_SANDBOX_WRITE adds
    writable folders from the server's own environment (the test suite's fake CLIs log there)."""
    kind = kind or backend()
    extra = [p for p in os.environ.get('SOL83_SANDBOX_WRITE', '').split(os.pathsep) if p]
    write = [*write, *extra]
    if kind == 'sandbox-exec':
        return ['/usr/bin/sandbox-exec', '-p', seatbelt_profile(write, deny_read, network), *command]
    if kind == 'bwrap':
        return [*bwrap_args(write, deny_read, network), *command]
    return None


def credential_paths(keep: Sequence = ()) -> list:
    keep = {str(Path(p)) for p in keep}
    return [HOME / rel for rel in CREDENTIALS if str(HOME / rel) not in keep]


def run(command: Sequence, cwd, write: Sequence = (), network: bool = False, timeout: float = 1800,
        env: Optional[dict] = None, deny_read: Sequence = (), allow_unsandboxed: bool = False) -> Result:
    """Run code from the repository with writes limited to `cwd`, `write` and a private temp folder.
    Output is merged and returned with credentials masked."""
    temp = Path(tempfile.mkdtemp(prefix='sol83-sbx-'))
    env = {**(env or os.environ), 'TMPDIR': str(temp)}
    for key in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'OPENAI_API_KEY', 'CODEX_API_KEY',
                'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GH_TOKEN', 'GITHUB_TOKEN'):
        env.pop(key, None)
    kind = backend()
    wrapped = wrap(list(command), [cwd, *write, temp], network,
                   [*credential_paths(), *deny_read], kind)
    try:
        if wrapped is None:
            if not allow_unsandboxed:
                return Result(REFUSED_EXIT, NO_SANDBOX, None)
            wrapped = list(command)
        try:
            done = subprocess.run(wrapped, cwd=str(cwd), env=env, text=True, errors='replace',
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL, timeout=timeout)
            return Result(done.returncode, secretscan.redact(done.stdout), kind)
        except subprocess.TimeoutExpired as exc:
            output = exc.output.decode(errors='replace') if isinstance(exc.output, bytes) else (exc.output or '')
            return Result(TIMEOUT_EXIT, secretscan.redact(output) + f'\nPrzekroczono {timeout:.0f} s.', kind)
        except OSError as exc:
            return Result(REFUSED_EXIT, f'Nie można uruchomić: {exc}', kind)
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def run_shell(command: str, cwd, **options) -> Result:
    return run(['/bin/sh', '-c', command], cwd, **options)


NO_SANDBOX = ('Sol-83 nie uruchamia kodu z repozytorium bez piaskownicy systemu, a ten komputer jej nie ma '
              '(macOS: sandbox-exec, Linux: bwrap z pakietu bubblewrap). Zainstaluj bubblewrap albo świadomie '
              'włącz w ustawieniach „Uruchamianie bez piaskownicy”.')


def verify_command() -> str:
    """What Duet runs on every LGTM: this module, which reads the real command from the store."""
    import shlex
    return f'{shlex.quote(sys.executable)} -m gemini_app.sandbox verify'


def _verify_main() -> int:
    """Duet's verify step. The project's command comes from the store, never from Duet's state."""
    from .store import Store
    project_id = os.environ.get('GEMINI_PROJECT_ID')
    store = Store()
    project = store.project(project_id) if project_id else None
    if not project:
        print('Brak projektu dla polecenia testów.', flush=True)
        return REFUSED_EXIT
    command = project.get('verify_cmd')
    if not command:
        print('Projekt nie ma polecenia testów.', flush=True)
        return 0
    cwd = Path.cwd().resolve()
    allowed = {Path(p).resolve() for p in (project.get('worktree'),) if p}
    if cwd not in allowed:
        print(f'Polecenie testów może działać tylko w folderze projektu, a nie w {cwd}.', flush=True)
        return REFUSED_EXIT
    result = run_shell(command, cwd, network=bool(store.setting('test_network', 0)),
                       allow_unsandboxed=bool(store.setting('allow_unsandboxed', 0)))
    sys.stdout.write(result.output)
    sys.stdout.flush()
    return result.returncode


if __name__ == '__main__':
    if sys.argv[1:] == ['verify']:
        sys.exit(_verify_main())
    sys.exit('Użycie: python3 -m gemini_app.sandbox verify')
