"""Publishing project versions to GitHub through the user's own `gh` login.

Only numbered versions leave the machine, never work in progress, and nothing is
ever force-pushed. Every push, private or public, is scanned for secrets first: a
private repository can be made public later from GitHub's own page.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from typing import Optional

from .gitops import Git, GitError, IDENTITY
from . import secretscan
from .messages import Msg
from .paths import agent_path

MAX_FILE_BYTES = 100_000_000
_NAME = re.compile(r'^[\w.-]+(/[\w.-]+)?$')
_REPO = re.compile(r'^[\w.-]+/[\w.-]+$')
CLONE_TIMEOUT = 900
_GITHUB_URL = re.compile(r'github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$')
TOOL_DIRS = ('/opt/homebrew/bin', '/usr/local/bin', '/usr/bin')


class SecretsFound(RuntimeError):
    """Possible credentials in what would be pushed. `token` confirms exactly this list."""

    def __init__(self, findings: list):
        self.findings = findings
        self.token = hashlib.sha256('\n'.join(findings).encode()).hexdigest()[:16]
        super().__init__(Msg('gh_secrets_ack', items=', '.join(findings[:8])))


def _path() -> str:
    """Where `gh` may live: the agents' PATH plus the usual package-manager folders that exist here."""
    extra = [folder for folder in TOOL_DIRS if os.path.isdir(folder)]
    return os.pathsep.join([agent_path(), *extra])


def _credentials() -> list:
    return ['-c', 'credential.helper=', '-c',
            f"credential.helper=!{shutil.which('gh', path=_path())} auth git-credential"]


def _gh(*args: str, check: bool = True, timeout: float = 60) -> str:
    env = {**os.environ, 'PATH': _path(), 'GH_PROMPT_DISABLED': '1'}
    try:
        done = subprocess.run(['gh', *args], capture_output=True, text=True, errors='replace',
                              timeout=timeout, env=env, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(Msg('gh_failed', detail=str(exc)[:200]))
    if check and done.returncode:
        raise RuntimeError(Msg('gh_failed', detail=(done.stderr or done.stdout).strip()[:300]))
    return done.stdout.strip() if done.returncode == 0 else ''


def status() -> dict:
    """Whether publishing can work, read from `gh` without using any token here."""
    try:
        login = _gh('api', 'user', '--jq', '.login', check=False)
    except RuntimeError:
        return {'ready': False, 'problem': Msg('gh_no_cli'), 'command': 'brew install gh'}
    if not login:
        return {'ready': False, 'problem': Msg('gh_no_login'), 'command': 'gh auth login'}
    return {'ready': True, 'user': login}


def remote_url(repo: str) -> str:
    base = os.environ.get('GEMINI_GITHUB_URL', 'https://github.com')
    return f'{base}/{repo}.git'


def github_origin(git: Git) -> Optional[str]:
    """`owner/name` of the source repository's GitHub origin, if it has one."""
    match = _GITHUB_URL.search(git.run('remote', 'get-url', 'origin', check=False))
    return match[1] if match else None


def find_secrets(git: Git, commit: str) -> list:
    """Files, contents and history entries that look like credentials, in everything a push sends."""
    found = {path for path in git.run('ls-tree', '-r', '--name-only', commit).splitlines()
             if secretscan.secret_file(path)}
    for flags, pattern in ((('-E',), secretscan.TOKEN_ERE), (('-E', '-i'), secretscan.ASSIGNMENT_ERE)):
        found.update(git.run('grep', '-I', '-l', *flags, pattern, commit, check=False)
                     .replace(f'{commit}:', '').splitlines())
    # git's pickaxe -G always compiles extended regular expressions.
    for sha in git.run('log', '--format=%h', '-G', secretscan.TOKEN_ERE, commit, check=False).splitlines():
        found.add(f'commit {sha}')
    return sorted(found)


def check_secrets(git: Git, commit: str, confirmed: str = '') -> list:
    """Raise SecretsFound unless the user confirmed exactly the current findings; return them."""
    findings = find_secrets(git, commit)
    if findings:
        error = SecretsFound(findings)
        if confirmed != error.token:
            raise error
    return findings


def find_oversized(git: Git, commit: str) -> list:
    entries = git.run('ls-tree', '-r', '-l', commit).splitlines()
    return [line.split('\t', 1)[1] for line in entries
            if line.split('\t')[0].split()[3].isdigit()
            and int(line.split('\t')[0].split()[3]) > MAX_FILE_BYTES]


def create_repo(name: str, public: bool, description: str) -> str:
    """Create an empty repository; returns `owner/name`."""
    output = _gh('repo', 'create', name, '--public' if public else '--private',
                 '--description', description[:300])
    match = _GITHUB_URL.search(output.splitlines()[-1]) if output else None
    if not match:
        raise RuntimeError(Msg('gh_failed', detail=output[:200] or name))
    return match[1]


def list_repos(limit: int = 200) -> list:
    return json.loads(_gh('repo', 'list', '--limit', str(limit), '--json',
                          'nameWithOwner,description,isPrivate,pushedAt,url') or '[]')


def ensure_clone(repo: str, path) -> None:
    """One local clone per GitHub repository, refreshed before each new project."""
    if (path / '.git').exists():
        try:
            Git(path).run(*_credentials(), 'fetch', '-q', 'origin')
        except GitError as exc:
            raise RuntimeError(Msg('gh_failed', detail=str(exc)[-300:]))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        _gh('repo', 'clone', repo, str(path), '--', '-q', timeout=CLONE_TIMEOUT)


def visibility_of(repo: str) -> str:
    return json.loads(_gh('repo', 'view', repo, '--json', 'visibility'))['visibility'].lower()


def set_visibility(repo: str, public: bool) -> None:
    _gh('repo', 'edit', repo, '--visibility', 'public' if public else 'private',
        '--accept-visibility-change-consequences')


def push(git: Git, repo: str, commit: str, branch: str, tag: str, remote_tag: str) -> None:
    """Plain push through gh's credentials: a diverged remote fails instead of being overwritten."""
    try:
        git.run(*IDENTITY, *_credentials(), 'push', remote_url(repo), f'{commit}:refs/heads/{branch}',
                f'refs/tags/{tag}:refs/tags/{remote_tag}')
    except GitError as exc:
        raise RuntimeError(Msg('gh_failed', detail=str(exc)[-300:]))


def valid_name(name: str) -> bool:
    return bool(_NAME.match(name))


def valid_repo(repo: str) -> bool:
    return bool(_REPO.match(repo))
