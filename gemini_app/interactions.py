"""Questions, decisions and manual tests for the user (spec point 21), as durable project records.

An agent records what it needs in `.sol83/requests.json`; after each turn the coordinator takes new
entries into the store. The user answers in the panel; the answer is saved first and then reaches the
right agent through the project's queue at the next safe turn boundary. A repeated form submission is
idempotent. An answer to a superseded or cancelled record, or a test result for an older version, is
kept in the history and not applied by itself. Restart restores everything: it is all in SQLite.

States: open -> answered -> applied, or deferred, cancelled, superseded. No answer is never consent.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Optional

REQUESTS_FILE = '.sol83/requests.json'
TYPES = ('clarification', 'decision', 'manual_test')
RESULTS = ('works', 'fails', 'partial', 'cannot')
OPEN_STATES = ('open', 'answered')
EVIDENCE = ('declaration', 'attachment', 'automatic', 'emulator', 'device_measurement')


def _key(kind: str, text: str) -> str:
    return hashlib.sha256(f"{kind}|{' '.join(text.lower().split())}".encode()).hexdigest()[:16]


def _row(row: Optional[dict]) -> Optional[dict]:
    if not row:
        return None
    for field in ('options', 'blocks', 'answers', 'steps'):
        row[field] = json.loads(row.get(field) or '[]')
    row['ref'] = f"I{row['id']}"
    return row


def get(store, interaction_id: int) -> Optional[dict]:
    return _row(store._row('SELECT * FROM interactions WHERE id=?', (interaction_id,)))


def listing(store, project_id: str) -> list:
    return [_row(row) for row in store._rows('SELECT * FROM interactions WHERE project_id=? ORDER BY id DESC',
                                             (project_id,))]


def open_items(store, project_id: str) -> list:
    return [_row(row) for row in store._rows("SELECT * FROM interactions WHERE project_id=? AND state IN "
                                             "('open','answered') ORDER BY id", (project_id,))]


def add(store, project_id: str, kind: str, text: str, author: Optional[str] = None, **fields) -> dict:
    """A new record, unless the same open question already exists (then that one is returned)."""
    if kind not in TYPES:
        raise ValueError(kind)
    key = _key(kind, text)
    with store.tx() as db:
        # The same question is not asked again once it exists, answered and applied included; only a
        # superseded one may come back (its context changed).
        found = db.execute("SELECT id FROM interactions WHERE project_id=? AND key=? AND state<>'superseded' "
                           'ORDER BY id DESC', (project_id, key)).fetchone()
        if found:
            return {'id': found['id'], 'created': False}
        now = time.time()
        cursor = db.execute(
            'INSERT INTO interactions(project_id,key,type,text,author,model,role,local_id,options,recommendation,why,'
            'blocks,independent,steps,environment,minutes,mandatory,version_number,commit_sha,plan_revision,item,'
            "order_note,created_at,updated_at,state,answers,lang) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'open','[]',?)",
            (project_id, key, kind, text[:4000], author, fields.get('model'), fields.get('role'), fields.get('local_id'),
             json.dumps(fields.get('options') or []), fields.get('recommendation'), fields.get('why'),
             json.dumps(fields.get('blocks') or []), fields.get('independent'), json.dumps(fields.get('steps') or []),
             fields.get('environment'), fields.get('minutes'), int(bool(fields.get('mandatory'))),
             fields.get('version_number'), fields.get('commit_sha'), fields.get('plan_revision'), fields.get('item'),
             fields.get('order_note'), now, now, fields.get('lang')))
        return {'id': cursor.lastrowid, 'created': True}


def ingest(store, project_id: str, worktree, author: str, context: dict) -> list:
    """Take new entries from `.sol83/requests.json` after a turn. Returns the created records."""
    try:
        data = json.loads((Path(worktree) / REQUESTS_FILE).read_text())
    except (OSError, ValueError):
        return []
    items = data.get('items') if isinstance(data, dict) else data
    created = []
    for item in items or []:
        if not isinstance(item, dict) or item.get('type') not in TYPES or not str(item.get('text') or '').strip():
            continue
        steps = [step for step in item.get('steps') or [] if isinstance(step, dict)]
        added = add(store, project_id, item['type'], str(item['text']).strip(), author,
                    local_id=str(item.get('id') or '')[:40], options=[str(o)[:200] for o in item.get('options') or []][:8],
                    recommendation=str(item.get('recommendation') or '')[:500] or None,
                    why=str(item.get('why') or '')[:1000] or None,
                    blocks=[str(b)[:40] for b in item.get('blocks') or []][:20],
                    independent=str(item.get('independent') or '')[:500] or None, steps=steps[:20],
                    environment=str(item.get('environment') or '')[:500] or None,
                    minutes=item.get('minutes') if isinstance(item.get('minutes'), (int, float)) else None,
                    mandatory=bool(item.get('mandatory')) or item['type'] == 'manual_test' and bool(item.get('blocks')),
                    **context)
        if added['created']:
            created.append(get(store, added['id']))
    return created


def answer(store, interaction_id: int, value: str = '', comment: str = '', request_key: str = '',
           result: Optional[str] = None, evidence: str = 'declaration', version: Optional[int] = None) -> dict:
    """Save the user's answer before anything else happens. Returns {'applied': bool, 'late': bool,
    'duplicate': bool, 'row': record}. A late answer (record no longer open, or a test result for
    another version than the one under test) is kept but not applied."""
    if result is not None and result not in RESULTS:
        raise ValueError(result)
    if evidence not in EVIDENCE:
        raise ValueError(evidence)
    with store.tx() as db:
        row = db.execute('SELECT * FROM interactions WHERE id=?', (interaction_id,)).fetchone()
        if row is None:
            raise LookupError(interaction_id)
        answers = json.loads(row['answers'] or '[]')
        if request_key and any(entry.get('request_key') == request_key for entry in answers):
            return {'applied': False, 'late': False, 'duplicate': True, 'row': None}
        late = row['state'] not in ('open', 'answered', 'deferred') or (
            row['type'] == 'manual_test' and version is not None and row['version_number'] is not None
            and version != row['version_number'])
        answers.append({'ts': time.time(), 'value': value[:4000], 'comment': comment[:4000], 'result': result,
                        'evidence': evidence, 'version': version, 'request_key': request_key or None, 'late': late})
        state = row['state'] if late else 'answered'
        db.execute('UPDATE interactions SET answers=?, state=?, updated_at=? WHERE id=?',
                   (json.dumps(answers, ensure_ascii=False), state, time.time(), interaction_id))
    return {'applied': not late, 'late': late, 'duplicate': False, 'row': get(store, interaction_id)}


def set_state(store, interaction_id: int, state: str) -> None:
    if state not in ('deferred', 'cancelled', 'superseded', 'applied', 'open'):
        raise ValueError(state)
    with store.tx() as db:
        db.execute('UPDATE interactions SET state=?, updated_at=? WHERE id=?', (state, time.time(), interaction_id))


def mark_applied(store, project_id: str, interaction_ids: list) -> None:
    """The turn that received the answers finished: they are now part of the work."""
    for interaction_id in interaction_ids:
        with store.tx() as db:
            db.execute("UPDATE interactions SET state='applied', updated_at=? WHERE id=? AND project_id=? "
                       "AND state='answered'", (time.time(), interaction_id, project_id))


def supersede_version_checks(store, project_id: str, version_number: int) -> None:
    """A new version's "what to check" replaces the open one of an older version."""
    with store.tx() as db:
        db.execute("UPDATE interactions SET state='superseded', updated_at=? WHERE project_id=? AND type='manual_test' "
                   "AND author='version' AND state IN ('open','deferred') AND version_number<?",
                   (time.time(), project_id, version_number))


def blockers(store, project_id: str, latest_version: Optional[int]) -> list:
    """What must be settled before the scope can close: open questions that block work, and mandatory
    tests without a passing result for the current version. Deferring does not remove a gate."""
    found = []
    for row in [_row(r) for r in store._rows("SELECT * FROM interactions WHERE project_id=? AND state IN "
                                             "('open','answered','deferred')", (project_id,))]:
        if row['type'] in ('clarification', 'decision') and row['blocks'] and row['state'] != 'answered':
            found.append(f"question:{row['ref']}")
        if row['type'] == 'manual_test' and row['mandatory']:
            passed = [a for a in row['answers'] if a.get('result') == 'works' and not a.get('late')
                      and (a.get('version') in (None, latest_version))]
            if not passed:
                found.append(f"test:{row['ref']}")
    return found


def prompt_lines(store, project_id: str, lang: str) -> list:
    from . import prompts
    rows = [row for row in open_items(store, project_id) if row['state'] == 'open']
    if not rows:
        return []
    items = '; '.join(f"{row['ref']} ({row['type']}): {row['text'][:160]}" for row in rows[:8])
    blocked = sorted({item for row in rows for item in row['blocks']})
    return ['', prompts.text(lang, 'open_requests', items=items, blocked=', '.join(blocked) or '-')]
