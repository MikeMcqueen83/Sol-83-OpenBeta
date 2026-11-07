"""The durable queue of the user's work for a project: orders, notes, plan items, failed tests.

Every entry is written before the request is acknowledged, has an id, a time, an order and a
state, and is tied to its project. A repeated click or a retransmitted request carries the same
request key and does not create a second entry. Closing a project and adding new work are
serialized in one SQLite transaction, so work that arrives during finalization is never lost.

States: pending (queued) -> delivered (a turn received it) -> answered (that turn finished and
replied) -> done (an accepted version exists after it was answered). Also withdrawn.
"""
from __future__ import annotations

import time
from typing import Optional

KINDS = ('note', 'order', 'item', 'verdict', 'asset', 'answer')
OPEN = ('pending', 'delivered')


def transaction(store):
    return store.tx()


def add(store, project_id: str, text: str, kind: str = 'note', urgent: bool = False,
        request_key: Optional[str] = None, priority: int = 0, ref: Optional[str] = None) -> dict:
    """Record new work. Returns {'id', 'created', 'status'}: `status` is the project's status read in
    the same transaction, so the caller knows whether a finished project must be reopened."""
    if kind not in KINDS:
        raise ValueError(kind)
    with transaction(store) as db:
        project = db.execute('SELECT status FROM projects WHERE id=?', (project_id,)).fetchone()
        if project is None:
            raise LookupError(project_id)
        if request_key:
            found = db.execute('SELECT id FROM notes WHERE project_id=? AND request_key=?',
                               (project_id, request_key)).fetchone()
            if found:
                return {'id': found['id'], 'created': False, 'status': project['status']}
        cursor = db.execute('INSERT INTO notes(project_id,ts,text,urgent,status,kind,request_key,priority,ref) '
                            "VALUES(?,?,?,?,'pending',?,?,?,?)",
                            (project_id, time.time(), text, int(urgent), kind, request_key, priority, ref))
        return {'id': cursor.lastrowid, 'created': True, 'status': project['status']}


def open_work(db, project_id: str) -> int:
    """Work nobody has finished a turn on yet: queued, or handed to a turn still running."""
    return db.execute("SELECT COUNT(*) FROM notes WHERE project_id=? AND status IN ('pending','delivered')",
                      (project_id,)).fetchone()[0]


def open_work_count(store, project_id: str) -> int:
    with store.tx() as db:
        return open_work(db, project_id)


def pending_orders(store, project_id: str) -> list:
    """Queued new work that asks for the plan to be rebuilt."""
    return store._rows("SELECT * FROM notes WHERE project_id=? AND status='pending' AND kind='order'",
                       (project_id,))


def finish(store, project_id: str, blockers: Optional[list] = None) -> str:
    """Close a converged project atomically. Returns 'done', or 'queued' when work arrived meanwhile
    or a gate still blocks: then the project goes back to the queue instead of being closed."""
    with transaction(store) as db:
        waiting = open_work(db, project_id)
        status = 'queued' if waiting or blockers else 'done'
        db.execute('UPDATE projects SET status=?, finished_at=?, stop_requested=NULL, updated_at=? WHERE id=?',
                   (status, time.time() if status == 'done' else None, time.time(), project_id))
        return status


def requeue_unanswered(store, project_id: str) -> int:
    """Work handed to a turn that never finished (engine crash, restart) goes back to the queue."""
    with transaction(store) as db:
        cursor = db.execute("UPDATE notes SET status='pending', delivered_to=NULL, delivered_turn=NULL, "
                            "delivered_at=NULL WHERE project_id=? AND status='delivered' AND response IS NULL",
                            (project_id,))
        return cursor.rowcount


def mark_done(store, project_id: str, version_number: int, version_turn: int) -> int:
    """Answered work becomes done with the first accepted version made after it was answered."""
    with transaction(store) as db:
        cursor = db.execute("UPDATE notes SET status='done', done_version=?, done_at=? WHERE project_id=? "
                            "AND status='answered' AND delivered_turn<=?",
                            (version_number, time.time(), project_id, version_turn))
        return cursor.rowcount


def view(store, project_id: str) -> list:
    """The queue in order, newest last, with a plain state for the panel."""
    return store._rows('SELECT id, ts, text, kind, ref, urgent, status, priority, delivered_to, delivered_turn, '
                       'delivered_at, response IS NOT NULL AS replied, done_version, done_at '
                       'FROM notes WHERE project_id=? ORDER BY priority DESC, id', (project_id,))
