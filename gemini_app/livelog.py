"""A read-only window into what the working model is doing right now.

It reads the agents' own session logs, so watching costs nothing. Claude Code writes
one file per session under ~/.claude/projects, Codex one rollout per session.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Optional

TAIL_BYTES = 600_000
CODEX_DAYS = 3
_codex_files: dict = {}


def _claude_root() -> Path:
    return Path(os.environ.get('GEMINI_CLAUDE_PROJECTS') or Path.home() / '.claude/projects')


def _codex_root() -> Path:
    return Path(os.environ.get('GEMINI_CODEX_SESSIONS') or Path.home() / '.codex/sessions')


def _tail(path: Path) -> list:
    with open(path, 'rb') as handle:
        size = handle.seek(0, 2)
        handle.seek(max(0, size - TAIL_BYTES))
        data = handle.read().decode('utf-8', errors='replace')
    rows = []
    for line in data.splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def claude_file(worktree: str) -> Optional[Path]:
    folder = _claude_root() / re.sub(r'[^A-Za-z0-9]', '-', worktree)
    files = sorted(folder.glob('*.jsonl'), key=lambda p: p.stat().st_mtime) if folder.exists() else []
    return files[-1] if files else None


def codex_file(worktree: str) -> Optional[Path]:
    """Newest rollout whose session ran in this folder."""
    cutoff = time.time() - CODEX_DAYS * 86400
    best = None
    for path in _codex_root().glob('*/*/*/*.jsonl'):
        mtime = path.stat().st_mtime
        if mtime < cutoff:
            continue
        cwd = _codex_files.get(str(path))
        if cwd is None:
            with open(path, errors='replace') as handle:
                first = handle.readline()
            try:
                cwd = (json.loads(first).get('payload') or {}).get('cwd', '')
            except ValueError:
                cwd = ''
            _codex_files[str(path)] = cwd
        if cwd == worktree and (best is None or mtime > best[0]):
            best = (mtime, path)
    return best[1] if best else None


def _short(value, limit=160) -> str:
    return re.sub(r'\s+', ' ', str(value)).strip()[:limit]


def claude_entries(path: Path) -> list:
    entries = []
    for row in _tail(path):
        content = (row.get('message') or {}).get('content')
        if row.get('type') != 'assistant' or not isinstance(content, list):
            continue
        for part in content:
            kind = part.get('type')
            if kind == 'thinking' and part.get('thinking'):
                entries.append({'t': row.get('timestamp'), 'type': 'thinking', 'text': _short(part['thinking'], 400)})
            elif kind == 'text' and part.get('text', '').strip():
                entries.append({'t': row.get('timestamp'), 'type': 'text', 'text': _short(part['text'], 400)})
            elif kind == 'tool_use':
                data = part.get('input') or {}
                arg = (data.get('command') or data.get('query') or data.get('file_path')
                       or data.get('url') or data.get('pattern') or data.get('description') or '')
                entries.append({'t': row.get('timestamp'), 'type': 'tool',
                                'text': f"{part.get('name')}: {_short(arg)}"})
    return entries


def codex_entries(path: Path) -> list:
    entries = []
    for row in _tail(path):
        payload = row.get('payload') or {}
        kind = payload.get('type')
        if kind in ('function_call', 'custom_tool_call', 'local_shell_call'):
            arg = payload.get('arguments') or payload.get('input') or payload.get('action') or ''
            try:
                parsed = json.loads(arg) if isinstance(arg, str) else arg
                arg = parsed.get('cmd') or parsed.get('command') or parsed if isinstance(parsed, dict) else parsed
            except ValueError:
                pass
            entries.append({'t': row.get('timestamp'), 'type': 'tool',
                            'text': f"{payload.get('name') or kind}: {_short(arg)}"})
        elif kind == 'agent_reasoning' and payload.get('text'):
            entries.append({'t': row.get('timestamp'), 'type': 'thinking', 'text': _short(payload['text'], 400)})
        elif kind == 'agent_message' and payload.get('message'):
            entries.append({'t': row.get('timestamp'), 'type': 'text', 'text': _short(payload['message'], 400)})
    return entries


def live(worktree: Optional[str], speaker: Optional[str], limit: int = 80) -> dict:
    """The speaker's latest activity; without a speaker, whichever model worked last."""
    if not worktree:
        return {'agent': None, 'items': []}
    found = {'claude': claude_file(worktree), 'codex': codex_file(worktree)}
    agent = speaker if found.get(speaker) else max(
        (name for name in found if found[name]), key=lambda name: found[name].stat().st_mtime, default=None)
    if not agent:
        return {'agent': None, 'items': []}
    reader = claude_entries if agent == 'claude' else codex_entries
    return {'agent': agent, 'items': reader(found[agent])[-limit:]}
