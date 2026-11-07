"""Content orders: graphics, texts, descriptions and story, made by the content creator.

Models that cannot make an image, or should not spend their turn on a story, order it
in the repository's `.sol83/assets.json`. The model with the content creator role takes
the orders in its own turn and marks each one done or failed. The coordinator only
reads the file, and writes into it only the orders the user placed in the panel.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

ASSETS_FILE = '.sol83/assets.json'
TYPES = ('image', 'text')
STATUSES = ('requested', 'done', 'error')
IMAGE_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
               '.webp': 'image/webp'}
PREVIEW_CHARS = 600
RULES = ('Treści, których nie zrobisz sam albo które należą do Twórcy treści (grafiki, ilustracje, '
         'ikony, teksty, opisy, fabuła), zamawiaj w .sol83/assets.json: dopisz do listy items pozycję '
         '{"id": "A1", "type": "image" albo "text", "prompt": "co ma powstać", "path": "ścieżka pliku w '
         'repozytorium", "size": "np. 512x512", "style": "styl", "status": "requested"} i pracuj dalej. '
         'Nie zgłaszaj LGTM, dopóki są zamówienia ze statusem requested.')


def load(worktree) -> list:
    """Orders as a list of dicts with an id; a missing or broken file is no orders."""
    try:
        data = json.loads((Path(worktree) / ASSETS_FILE).read_text())
    except (OSError, ValueError):
        return []
    items = data.get('items') if isinstance(data, dict) else data
    return [item for item in items or [] if isinstance(item, dict) and item.get('id')]


def pending(worktree) -> list:
    return [item for item in load(worktree) if item.get('status', 'requested') == 'requested']


def add(worktree, orders: list) -> None:
    """Append the user's orders. Called between turns, so no agent writes the file meanwhile."""
    path = Path(worktree) / ASSETS_FILE
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        data = {}
    if isinstance(data, list):
        data = {'items': data}
    items = data.setdefault('items', [])
    taken = {item.get('id') for item in items if isinstance(item, dict)}
    for order in orders:
        number = len(taken) + 1
        while f'U{number}' in taken:
            number += 1
        taken.add(f'U{number}')
        items.append({'id': f'U{number}', **order, 'status': 'requested', 'by': 'user'})
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    temp.replace(path)


def summary(orders: list) -> str:
    return '\n'.join(f"- {item['id']} ({item.get('type', 'image')}): {str(item.get('prompt', ''))[:200]} "
                     f"-> {item.get('path', '?')}" + (f", {item['size']}" if item.get('size') else '')
                     + (f", styl: {item['style']}" if item.get('style') else '') for item in orders[:12])


def file_of(worktree, path: str) -> Optional[Path]:
    """The file of an order, only if an order names it and it stays inside the worktree."""
    root = Path(worktree).resolve()
    if path not in {str(item.get('path')) for item in load(worktree)}:
        return None
    target = (root / path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        return None
    return target


def view(worktree) -> list:
    """Orders for the panel, with a short preview of texts and a flag for images."""
    rows = []
    for item in load(worktree):
        target = file_of(worktree, str(item.get('path'))) if item.get('path') else None
        image = bool(target and target.suffix.lower() in IMAGE_TYPES)
        preview = None
        if target and not image and target.stat().st_size < 2_000_000:
            preview = target.read_text(errors='replace')[:PREVIEW_CHARS]
        rows.append({'id': item['id'], 'type': item.get('type', 'image'), 'prompt': item.get('prompt'),
                     'path': item.get('path'), 'size': item.get('size'), 'style': item.get('style'),
                     'status': item.get('status', 'requested'), 'note': item.get('note'), 'by': item.get('by'),
                     'image': image, 'preview': preview})
    return rows
