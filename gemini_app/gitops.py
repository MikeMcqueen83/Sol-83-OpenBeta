"""Git operations behind checkpoints and versions."""
from __future__ import annotations

import dataclasses
import hashlib
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

from . import sandbox
from .messages import Msg
from .paths import BASE

IDENTITY = ('-c', 'user.name=Gemini', '-c', 'user.email=gemini@localhost')
EXCLUDES = BASE / 'gemini_app/checkpoint.gitignore'
START_SUBJECT = 'gemini: start projektu'
LOCK_WAIT_S = float(os.environ.get('GEMINI_LOCK_WAIT', 30))
STALE_LOCK_S = 30
_RUN_HEADING = re.compile(r'^(#{1,6})[ \t]*(uruchomienie|jak uruchomi[ćc]|run|running|usage|getting started'
                          r'|quick ?start|start)\b.*$', re.M | re.I)


class GitError(RuntimeError):
    pass


@dataclasses.dataclass
class Checkpoint:
    head: str
    tree: str
    changed: bool


class Git:
    def __init__(self, cwd):
        self.cwd = str(cwd)

    def run(self, *args: str, check: bool = True) -> str:
        done = subprocess.run(['git', *args], cwd=self.cwd, capture_output=True, text=True,
                              errors='replace', timeout=120)
        if check and done.returncode:
            raise GitError(f"git {' '.join(args)}: {done.stderr.strip() or done.stdout.strip()}")
        return done.stdout.strip()

    def ok(self, *args: str) -> bool:
        return subprocess.run(['git', *args], cwd=self.cwd, capture_output=True,
                              timeout=120).returncode == 0

    def is_repo(self) -> bool:
        return self.run('rev-parse', '--is-inside-work-tree', check=False) == 'true'

    def head(self) -> str:
        return self.run('rev-parse', 'HEAD')

    def tree(self) -> str:
        return self.run('rev-parse', 'HEAD^{tree}')

    def dirty(self) -> str:
        return self.run('status', '--porcelain')

    def _unlock(self) -> None:
        """A stopped agent's tool can hold git's index lock a moment longer, or leave it behind:
        wait for it to go, and remove it only once nothing has touched it for a while."""
        lock = Path(self.run('rev-parse', '--git-path', 'index.lock'))
        lock = lock if lock.is_absolute() else Path(self.cwd) / lock
        deadline = time.monotonic() + LOCK_WAIT_S
        while lock.exists() and time.monotonic() < deadline:
            time.sleep(0.5)
        try:
            if time.time() - lock.stat().st_mtime > STALE_LOCK_S:
                lock.unlink()
        except OSError:
            pass

    def checkpoint(self, message: str) -> Checkpoint:
        """Commit everything an agent left. Build junk stays out, so running
        tests cannot change the tree that both agents accepted."""
        self._unlock()
        self.run('-c', f'core.excludesFile={EXCLUDES}', 'add', '-A')
        changed = bool(self.run('diff', '--cached', '--name-only'))
        if changed:
            self.run(*IDENTITY, 'commit', '--no-verify', '-q', '-m', message)
        return Checkpoint(self.head(), self.tree(), changed)

    def changed_lines(self, a: str, b: str) -> int:
        """Insertions plus deletions between two commits."""
        numbers = [int(word) for word in self.run('diff', '--shortstat', a, b, check=False).split()
                   if word.isdigit()]
        return sum(numbers[1:3])

    def tag(self, name: str, commit: str) -> None:
        self.run(*IDENTITY, 'tag', '-f', name, commit)

    def changes_since(self, commit: str) -> str:
        """Short description of what happened after `commit`, for a handoff."""
        log = self.run('log', '--oneline', '--no-decorate', '-n', '20', f'{commit}..HEAD')
        stat = self.run('diff', '--stat', commit, 'HEAD')
        return '\n'.join(part for part in (log, stat) if part)

    def commits_since(self, commit: str) -> int:
        return int(self.run('rev-list', '--count', f'{commit}..HEAD') or 0)

    def diff(self, base: str, limit: int = 300_000) -> str:
        return self.run('diff', '--stat', '--patch', base, 'HEAD')[:limit]


def create_repo(path: Path) -> str:
    """New project: an empty repository with one commit agents can branch from."""
    path.mkdir(parents=True, exist_ok=True)
    git = Git(path)
    git.run('init', '-q', '-b', 'main')
    git.run(*IDENTITY, 'commit', '-q', '--allow-empty', '-m', START_SUBJECT)
    return git.head()


def add_worktree(repo: str, path: Path, branch: str, start: str = 'HEAD') -> str:
    """A worktree for the agents. The project's `.gemini-setup` does not run here: it is code from
    the repository, so it runs only after the user approved its exact content (see `run_setup`)."""
    git = Git(repo)
    git.run('worktree', 'add', '-q', '-b', branch, str(path), start)
    return Git(path).head()


SETUP_FILE = '.gemini-setup'
SETUP_TIMEOUT = 900


def setup_script(worktree) -> Optional[dict]:
    """The project's setup script as the user must see it before approving: path, content, hash."""
    script = Path(worktree) / SETUP_FILE
    if not script.is_file():
        return None
    data = script.read_bytes()
    return {'path': str(script), 'sha': hashlib.sha256(data).hexdigest(),
            'content': data[:20000].decode(errors='replace'), 'truncated': len(data) > 20000}


def run_setup(worktree: Path, approved_sha: Optional[str], allow_unsandboxed: bool = False) -> str:
    """Run `.gemini-setup` in the sandbox, only when the user approved exactly this content.
    A worktree holds only tracked files, so this is where a project links dependencies and data.
    Returns 'none', 'ran' or 'needs_approval'; a failed script raises GitError."""
    script = setup_script(worktree)
    if not script:
        return 'none'
    if script['sha'] != approved_sha:
        return 'needs_approval'
    caches = [Path.home() / '.cache', Path.home() / 'Library/Caches', Path.home() / '.npm']
    command = [script['path']] if os.access(script['path'], os.X_OK) else ['/bin/sh', script['path']]
    done = sandbox.run(command, worktree, write=[c for c in caches if c.exists()], network=True,
                       timeout=SETUP_TIMEOUT, allow_unsandboxed=allow_unsandboxed)
    if done.returncode:
        raise GitError(f'{SETUP_FILE}: {done.output.strip()[-600:]}')
    return 'ran'


def checkout_test_copy(repo: str, path: Path, tag: str) -> None:
    """Fixed copy of one version: agents never touch this folder."""
    if path.exists():
        Git(path).run('checkout', '-q', '--detach', tag)
    else:
        Git(repo).run('worktree', 'add', '-q', '--detach', str(path), tag)


def deliver(repo: str, tag: str) -> None:
    """Put a version into the repository's own folder: main moves forward to it, an older
    version is checked out detached. Main never moves back and local edits stay."""
    git = Git(repo)
    if git.run('status', '--porcelain', '--untracked-files=no'):
        raise GitError(Msg('deliver_dirty', path=repo))
    if git.ok('merge-base', '--is-ancestor', 'main', tag):
        git.run('checkout', '-q', 'main')
        git.run('merge', '--ff-only', '-q', tag)
    elif git.ok('merge-base', '--is-ancestor', tag, 'main'):
        git.run('checkout', '-q', '--detach', tag)
    else:
        raise GitError(Msg('deliver_diverged', path=repo))


def show(repo: str, tag: str, path: str) -> Optional[str]:
    """A file as it is in one version, or None."""
    git = Git(repo)
    return git.run('show', f'{tag}:{path}') if git.ok('cat-file', '-e', f'{tag}:{path}') else None


def readme_run_section(text: Optional[str]) -> Optional[str]:
    """The README part that says how to start the project."""
    match = _RUN_HEADING.search(text or '')
    if not match:
        return None
    rest = text[match.end():]
    end = re.search(rf'^#{{1,{len(match[1])}}}[ \t]', rest, re.M)
    return (rest[:end.start()] if end else rest).strip()[:2000] or None


def validate_source(path: str) -> Optional[str]:
    """Why this folder cannot be a project source; None when it can."""
    folder = Path(path)
    if not folder.is_absolute():
        return Msg('src_absolute')
    if not folder.is_dir():
        return Msg('src_missing', path=path)
    git = Git(folder)
    if not git.is_repo():
        return Msg('src_no_git')
    if not git.run('rev-parse', '--verify', '-q', 'HEAD', check=False):
        return Msg('src_no_commit')
    if git.dirty():
        return Msg('src_dirty')
    return None
