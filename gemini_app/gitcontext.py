"""Git in the context of one project (spec point 22).

A project has a stable Git context: repository, working folder, optional subfolder in a monorepo,
remote, base and work branch, delivery strategy (local, push to a branch, PR) and the operations the
user allowed. Before any operation the real state is read, never guessed: root, HEAD or detached,
remotes, staged and unstaged changes, a merge or rebase in progress. Editing, commit, push and PR are
separate steps with separate permissions. The user's own changes, staged ones included, are never
committed or stashed: a commit takes exactly the listed paths. No force push, no reset, no history
rewrite. Every operation has an id and a record; after a restart or a lost answer the real local and
remote state is checked before anything is repeated, so no second commit or PR appears.
Sol-83's own repository is never a project target.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

from .paths import BASE

STRATEGIES = ('local', 'push', 'pr')
OPERATIONS = ('commit', 'push', 'pr', 'fetch', 'integrate')
_CREDENTIALS_IN_URL = re.compile(r'(https?://)[^/@\s]+@')
INTENTS = (
    ('pr', r'\b(pull request|PR|otw[oó]rz pr|merge request)\b'),
    ('push', r'\b(wy[sś]lij|wypchnij|push|na github|do remote|na serwer|opublikuj zmiany|send .* to (github|remote)'
             r'|upload)\b'),
    ('pull', r'\b(pobierz najnowsz\w*|pull|fetch|zaktualizuj z remote|ściągnij zmiany|get the latest)\b'),
    ('update', r'\b(zaktualizuj na git|update on git|na gita|w gicie|on git)\b'),
    ('commit', r'\b(commit|zapisz (te )?zmiany w git|zrób commit|save .* in git)\b'),
)


class GitContextError(RuntimeError):
    pass


def classify(text: str) -> str:
    """What a request about Git means: edit only, commit, push, PR, pull, or an unclear "update"."""
    for intent, pattern in INTENTS:
        if re.search(pattern, text or '', re.I):
            return intent
    return 'edit'


def safe_url(url: str) -> str:
    return _CREDENTIALS_IN_URL.sub(r'\1', url or '')


def _git(repo, *args, check=True, timeout=120) -> subprocess.CompletedProcess:
    done = subprocess.run(['git', *args], cwd=str(repo), capture_output=True, text=True, errors='replace',
                          timeout=timeout, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
    if check and done.returncode:
        raise GitContextError(f"git {args[0]}: {safe_url((done.stderr or done.stdout).strip())[:400]}")
    return done


def inspect(path) -> dict:
    """The real state of the repository at `path`."""
    path = Path(path)
    if not path.is_dir():
        return {'exists': False}
    top = _git(path, 'rev-parse', '--show-toplevel', check=False)
    if top.returncode:
        return {'exists': True, 'repository': False}
    root = Path(top.stdout.strip())
    branch = _git(path, 'symbolic-ref', '--short', '-q', 'HEAD', check=False).stdout.strip() or None
    head = _git(path, 'rev-parse', '--verify', '-q', 'HEAD', check=False).stdout.strip() or None
    status = _git(path, 'status', '--porcelain=v1', '--untracked-files=all', check=False).stdout.splitlines()
    git_dir = Path(_git(path, 'rev-parse', '--absolute-git-dir', check=False).stdout.strip())
    remotes = {}
    for line in _git(path, 'remote', '-v', check=False).stdout.splitlines():
        name, url, *_ = line.split()
        remotes[name] = safe_url(url)
    upstream = _git(path, 'rev-parse', '--abbrev-ref', '@{upstream}', check=False).stdout.strip() or None
    ahead = behind = None
    if upstream:
        counts = _git(path, 'rev-list', '--left-right', '--count', f'HEAD...{upstream}', check=False).stdout.split()
        if len(counts) == 2:
            ahead, behind = int(counts[0]), int(counts[1])
    return {'exists': True, 'repository': True, 'root': str(root), 'subdir': str(path.resolve().relative_to(root.resolve()))
            if path.resolve() != root.resolve() else '', 'branch': branch, 'detached': branch is None and head is not None,
            'head': head, 'staged': sum(1 for line in status if line[0] not in ' ?'),
            'unstaged': sum(1 for line in status if len(line) > 1 and line[1] not in ' ?'),
            'untracked': sum(1 for line in status if line.startswith('??')), 'remotes': remotes,
            'upstream': upstream, 'ahead': ahead, 'behind': behind,
            'merging': (git_dir / 'MERGE_HEAD').exists(),
            'rebasing': (git_dir / 'rebase-merge').exists() or (git_dir / 'rebase-apply').exists(),
            'identity': bool(_git(path, 'config', 'user.email', check=False).stdout.strip())}


@contextlib.contextmanager
def repo_lock(repo):
    """Operations on one repository are serialized, across processes too."""
    git_dir = Path(_git(repo, 'rev-parse', '--git-common-dir').stdout.strip())
    git_dir = git_dir if git_dir.is_absolute() else Path(repo) / git_dir
    with open(git_dir / 'sol83.lock', 'w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _not_sol83(repo) -> None:
    root = Path(_git(repo, 'rev-parse', '--show-toplevel').stdout.strip()).resolve()
    if root == BASE.resolve() or BASE.resolve().is_relative_to(root):
        raise GitContextError('to repozytorium samego Sol-83: projekty nie mogą go zmieniać ani publikować')


class GitOps:
    def __init__(self, store):
        self.store = store

    def _record(self, op_key: str) -> Optional[dict]:
        row = self.store._row('SELECT * FROM git_ops WHERE op_key=?', (op_key,))
        if row:
            row['files'] = json.loads(row['files'] or '[]')
        return row

    def _save(self, **fields) -> dict:
        fields['files'] = json.dumps(fields.get('files') or [])
        fields.setdefault('created_at', time.time())
        names = ','.join(fields)
        with self.store._db() as db:
            db.execute(f"INSERT OR REPLACE INTO git_ops({names}) VALUES({','.join('?' * len(fields))})",
                       tuple(fields.values()))
        return self._record(fields['op_key'])

    def commit(self, project_id: str, repo, paths: list, message: str, op_key: str) -> dict:
        """Commit exactly `paths` on the current branch. Other changes of the user, staged or not, stay
        as they are. A repeated request with the same key returns the first result."""
        done = self._record(op_key)
        if done and done['state'] in ('committed', 'nothing'):
            return done
        _not_sol83(repo)
        state = inspect(repo)
        if state['merging'] or state['rebasing']:
            raise GitContextError('w repozytorium trwa merge albo rebase: najpierw trzeba go zakończyć')
        if not state['identity']:
            raise GitContextError('brak tożsamości autora (git config user.name i user.email)')
        if not paths or any(Path(p).is_absolute() or '..' in Path(p).parts for p in paths):
            raise GitContextError('commit wymaga listy plików w repozytorium')
        with repo_lock(repo):
            before = state['head']
            changed = _git(repo, 'status', '--porcelain', '--', *paths).stdout.strip()
            if not changed:
                return self._save(op_key=op_key, project_id=project_id, operation='commit', repo=str(repo),
                                  branch=state['branch'], head_before=before, head_after=before, files=paths,
                                  state='nothing', detail='brak zmian w podanych plikach')
            _git(repo, 'add', '--', *paths)
            _git(repo, 'commit', '-q', '-m', message, '--only', '--', *paths)
            after = _git(repo, 'rev-parse', 'HEAD').stdout.strip()
        return self._save(op_key=op_key, project_id=project_id, operation='commit', repo=str(repo),
                          branch=state['branch'], head_before=before, head_after=after, commit_sha=after,
                          files=paths, state='committed')

    def push(self, project_id: str, repo, remote: str, branch: str, op_key: str) -> dict:
        """Push one branch without force. After a lost answer or a restart the remote is checked first."""
        _not_sol83(repo)
        state = inspect(repo)
        if remote not in state['remotes']:
            raise GitContextError(f'brak remote {remote}: repozytorium ma {", ".join(state["remotes"]) or "żadnego"}')
        local = _git(repo, 'rev-parse', branch).stdout.strip()
        done = self._record(op_key)
        if done and done['state'] in ('pushed',):
            return done
        if self._remote_head(repo, remote, branch) == local:
            return self._save(op_key=op_key, project_id=project_id, operation='push', repo=str(repo), branch=branch,
                              head_after=local, remote=state['remotes'][remote], state='pushed',
                              detail='zdalna gałąź już wskazuje ten commit')
        with repo_lock(repo):
            result = _git(repo, 'push', remote, f'{branch}:refs/heads/{branch}', check=False, timeout=300)
        if result.returncode == 0:
            return self._save(op_key=op_key, project_id=project_id, operation='push', repo=str(repo), branch=branch,
                              head_after=local, remote=state['remotes'][remote], state='pushed')
        text = safe_url(result.stderr)
        if re.search(r'non-fast-forward|rejected|fetch first', text):
            kind = 'remote_ahead'
        elif re.search(r'protected branch|GH006|pre-receive hook declined', text):
            kind = 'protected'
        elif re.search(r'Authentication|could not read Username|Permission denied|403', text):
            kind = 'auth'
        else:
            kind = 'error'
        if kind == 'error' and self._remote_head(repo, remote, branch) == local:
            return self._save(op_key=op_key, project_id=project_id, operation='push', repo=str(repo), branch=branch,
                              head_after=local, remote=state['remotes'][remote], state='pushed',
                              detail='odpowiedź zginęła, ale zdalna gałąź ma ten commit')
        return self._save(op_key=op_key, project_id=project_id, operation='push', repo=str(repo), branch=branch,
                          head_after=local, remote=state['remotes'][remote], state=f'failed_{kind}',
                          detail=f'commit {local[:7]} istnieje lokalnie; wysyłka nie powiodła się: {text.strip()[:300]}')

    def open_pr(self, project_id: str, repo, repository: str, branch: str, base: str, title: str, body: str,
                op_key: str) -> dict:
        """Open a PR through the user's gh login, or return the one that already exists for the branch."""
        from . import github
        done = self._record(op_key)
        if done and done['state'] == 'pr_open':
            return done
        _not_sol83(repo)
        existing = json.loads(github._gh('pr', 'list', '--repo', repository, '--head', branch, '--state', 'open',
                                         '--json', 'url', check=False) or '[]')
        if existing:
            url = existing[0]['url']
        else:
            out = github._gh('pr', 'create', '--repo', repository, '--head', branch, '--base', base,
                             '--title', title[:200], '--body', body[:5000])
            url = out.strip().splitlines()[-1] if out.strip() else None
        return self._save(op_key=op_key, project_id=project_id, operation='pr', repo=str(repo), branch=branch,
                          pr_url=url, state='pr_open' if url else 'failed_pr')

    def _remote_head(self, repo, remote: str, branch: str) -> Optional[str]:
        out = _git(repo, 'ls-remote', remote, f'refs/heads/{branch}', check=False, timeout=60).stdout.split()
        return out[0] if out else None

    def fetch(self, repo, remote: str) -> dict:
        _not_sol83(repo)
        with repo_lock(repo):
            _git(repo, 'fetch', '-q', remote, timeout=300)
        return inspect(repo)

    def integrate(self, repo, upstream: str) -> dict:
        """Bring remote changes in, fast-forward only, and never into a dirty folder."""
        _not_sol83(repo)
        state = inspect(repo)
        if state['staged'] or state['unstaged']:
            raise GitContextError('w folderze są niezapisane zmiany: integracja zatrzymana, by ich nie nadpisać')
        with repo_lock(repo):
            result = _git(repo, 'merge', '--ff-only', '-q', upstream, check=False)
        if result.returncode:
            raise GitContextError('gałęzie się rozjechały: potrzebna decyzja (merge lub rebase), nic nie zmieniono')
        return inspect(repo)
