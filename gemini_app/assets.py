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
STATUSES = ('proposed', 'requested', 'done', 'error', 'rejected', 'deferred')
DECISIONS = {'approve': 'requested', 'reject': 'rejected', 'defer': 'deferred'}
SIZE_PRESETS = ('512x512', '1024x1024', '1920x1080', '1080x1920', '1:1', '16:9', '9:16', '4:3')
IMAGE_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
               '.webp': 'image/webp'}
PREVIEW_CHARS = 600
RULES = ('Treści, których nie zrobisz sam albo które należą do Twórcy treści (grafiki, ilustracje, '
         'ikony, teksty, opisy, fabuła), zamawiaj w .sol83/assets.json: dopisz do listy items pozycję '
         '{"id": "A1", "type": "image" albo "text", "prompt": "co ma powstać", "path": "ścieżka pliku w '
         'repozytorium", "size": "np. 512x512", "style": "styl", "why": "uzasadnienie", "blocks": ["id pozycji '
         'planu"], "mandatory": true|false, "status": "proposed"} i pracuj dalej. Zamówienie wykona Twórca treści '
         'dopiero po zatwierdzeniu przez użytkownika. Nie zgłaszaj LGTM, dopóki obowiązkowe zamówienia nie są gotowe.')
RULES_EN = ('Content you cannot make yourself, or that belongs to the Content creator (graphics, illustrations, '
            'icons, texts, descriptions, story), order in .sol83/assets.json: add an item {"id": "A1", "type": '
            '"image" or "text", "prompt": "what to make", "path": "file path in the repository", "size": "e.g. '
            '512x512", "style": "style", "why": "justification", "blocks": ["plan item ids"], "mandatory": '
            'true|false, "status": "proposed"} and keep working. The Content creator makes it only after the user '
            'approves it. Do not report LGTM while mandatory orders are not done.')


def rules(lang: str) -> str:
    return RULES_EN if lang == 'en' else RULES


def load(worktree) -> list:
    """Orders as a list of dicts with an id; a missing or broken file is no orders."""
    try:
        data = json.loads((Path(worktree) / ASSETS_FILE).read_text())
    except (OSError, ValueError):
        return []
    items = data.get('items') if isinstance(data, dict) else data
    return [item for item in items or [] if isinstance(item, dict) and item.get('id')]


def pending(worktree) -> list:
    """Orders the content creator may make now: approved ones only (status requested)."""
    return [item for item in load(worktree) if item.get('status', 'requested') == 'requested']


def _write(worktree, data: dict) -> None:
    path = Path(worktree) / ASSETS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    temp.replace(path)


def _data(worktree) -> dict:
    try:
        data = json.loads((Path(worktree) / ASSETS_FILE).read_text())
    except (OSError, ValueError):
        return {'items': []}
    return {'items': data} if isinstance(data, list) else data


def review_new(worktree, known: set, author: str) -> list:
    """After a turn: orders a model added become proposals the user decides on. A model never approves
    its own order, and an order for a path and type already ordered is marked as a duplicate."""
    data = _data(worktree)
    created, seen = [], {}
    changed = False
    for item in data.get('items', []):
        if not isinstance(item, dict) or not item.get('id'):
            continue
        signature = (item.get('type', 'image'), str(item.get('path') or ''))
        if item['id'] in known or item.get('by') == 'user':
            seen.setdefault(signature, item['id'])
            continue
        item.setdefault('by', author)
        if signature in seen and item.get('status') not in ('rejected', 'done'):
            item['status'], item['note'] = 'rejected', f'duplikat {seen[signature]}'
        elif item.get('status', 'requested') == 'requested':
            item['status'] = 'proposed'
        seen.setdefault(signature, item['id'])
        created.append(dict(item))
        changed = True
    if changed:
        _write(worktree, data)
    return created


def apply_decisions(worktree, decisions: list) -> None:
    """The user's decisions, written between turns: approve, reject or defer one exact order."""
    data = _data(worktree)
    for decision in decisions:
        for item in data.get('items', []):
            if isinstance(item, dict) and item.get('id') == decision['id']:
                item['status'] = DECISIONS[decision['decision']]
                if decision.get('note'):
                    item['decision_note'] = decision['note'][:500]
    _write(worktree, data)


def missing_mandatory(worktree) -> list:
    """Mandatory content not made yet: the scope cannot close as complete without it or a decision."""
    return [item for item in load(worktree) if item.get('mandatory') and item.get('status') != 'done']


def image_size(path: Path):
    """(width, height) read from a PNG, GIF or JPEG header: the size the generator really produced."""
    try:
        head = path.read_bytes()[:65536]
    except OSError:
        return None
    if head[:8] == b'\x89PNG\r\n\x1a\n' and len(head) >= 24:
        return int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')
    if head[:6] in (b'GIF87a', b'GIF89a'):
        return int.from_bytes(head[6:8], 'little'), int.from_bytes(head[8:10], 'little')
    if head[:2] == b'\xff\xd8':
        index = 2
        while index + 9 < len(head):
            if head[index] != 0xFF:
                index += 1
                continue
            marker = head[index + 1]
            length = int.from_bytes(head[index + 2:index + 4], 'big')
            if marker in (0xC0, 0xC1, 0xC2):
                return int.from_bytes(head[index + 7:index + 9], 'big'), int.from_bytes(head[index + 5:index + 7], 'big')
            index += 2 + length
    return None


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
    # Style and size are passed as plain hints: no executor takes them as parameters. The real size of
    # the result is read from the file afterwards and shown next to the order.
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
        actual = image_size(target) if image else None
        rows.append({'id': item['id'], 'type': item.get('type', 'image'), 'prompt': item.get('prompt'),
                     'path': item.get('path'), 'size': item.get('size'), 'style': item.get('style'),
                     'status': item.get('status', 'requested'), 'note': item.get('note'), 'by': item.get('by'),
                     'why': item.get('why'), 'blocks': item.get('blocks') or [], 'mandatory': bool(item.get('mandatory')),
                     'actual_size': f'{actual[0]}x{actual[1]}' if actual else None,
                     'image': image, 'preview': preview})
    return rows
