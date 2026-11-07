"""SQLite state shared by the web server and the engine processes."""
from __future__ import annotations

import contextlib
import json
import sqlite3
import time
from typing import Iterable, Optional

from . import secretscan
from .limits import DEFAULT_THRESHOLD, FIVE_HOUR, SEVEN_DAY
from .messages import en
from .paths import STATE

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects(
  id TEXT PRIMARY KEY, title TEXT NOT NULL, task TEXT NOT NULL, status TEXT NOT NULL,
  status_detail TEXT, repo_path TEXT, worktree TEXT, branch TEXT, base_commit TEXT,
  verify_cmd TEXT, max_turns INTEGER, turn_timeout INTEGER, claude_model TEXT, codex_model TEXT,
  claude_reasoning TEXT, codex_reasoning TEXT, status_detail_en TEXT,
  github_repo TEXT, github_url TEXT, github_visibility TEXT, github_version INTEGER,
  github_branch TEXT, github_auto INTEGER DEFAULT 0,
  created_at REAL, updated_at REAL, finished_at REAL,
  stop_requested TEXT, resume_after_stop INTEGER DEFAULT 0, accepted_solo INTEGER DEFAULT 0,
  engine_pid INTEGER, engine_start TEXT, run_dir TEXT, test_version INTEGER,
  meta TEXT DEFAULT '{}', run_version INTEGER, delivered_version INTEGER,
  claude_role TEXT, codex_role TEXT, role_fallback TEXT, gemini_model TEXT, gemini_reasoning TEXT,
  gemini_role TEXT);
CREATE TABLE IF NOT EXISTS live(
  project_id TEXT PRIMARY KEY, phase TEXT, speaker TEXT, turn INTEGER, mode TEXT,
  until REAL, reason TEXT, reason_en TEXT, started_at REAL, updated_at REAL);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY, project_id TEXT, ts REAL, kind TEXT, agent TEXT, text TEXT,
  text_en TEXT, data TEXT, body TEXT);
CREATE TABLE IF NOT EXISTS notes(
  id INTEGER PRIMARY KEY, project_id TEXT, ts REAL, text TEXT, urgent INTEGER, status TEXT,
  delivered_to TEXT, delivered_turn INTEGER, delivered_at REAL, response TEXT, kind TEXT,
  reopened TEXT);
CREATE TABLE IF NOT EXISTS questions(
  id INTEGER PRIMARY KEY, project_id TEXT, ts REAL, question TEXT, answer TEXT,
  answered_by TEXT, status TEXT, answered_at REAL);
CREATE TABLE IF NOT EXISTS versions(
  id INTEGER PRIMARY KEY, project_id TEXT, number INTEGER, tag TEXT, commit_sha TEXT, tree TEXT,
  level TEXT, created_at REAL, turn INTEGER, agent TEXT, summary TEXT, what_to_test TEXT,
  accepted_by TEXT DEFAULT '[]', verify_summary TEXT, verify_summary_en TEXT, user_verdict TEXT,
  user_verdict_at REAL, how_to_run TEXT,
  UNIQUE(project_id, number));
CREATE TABLE IF NOT EXISTS blocks(
  provider TEXT PRIMARY KEY, until REAL, reason TEXT, reason_en TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS usage(
  id INTEGER PRIMARY KEY, project_id TEXT, turn INTEGER, agent TEXT, ts REAL, session_id TEXT, scope TEXT,
  source TEXT, raw TEXT, model_requested TEXT, model_confirmed TEXT,
  input INTEGER, cache_read INTEGER, cache_write INTEGER, output INTEGER, reasoning INTEGER, total INTEGER,
  d_input INTEGER, d_cache_read INTEGER, d_cache_write INTEGER, d_output INTEGER, d_reasoning INTEGER,
  d_total INTEGER, note TEXT, UNIQUE(project_id, turn, agent));
CREATE TABLE IF NOT EXISTS interactions(
  id INTEGER PRIMARY KEY, project_id TEXT, key TEXT, type TEXT, text TEXT, author TEXT, model TEXT, role TEXT,
  local_id TEXT, options TEXT, recommendation TEXT, why TEXT, blocks TEXT, independent TEXT, steps TEXT,
  environment TEXT, minutes REAL, mandatory INTEGER DEFAULT 0, version_number INTEGER, commit_sha TEXT,
  plan_revision INTEGER, item TEXT, order_note INTEGER, created_at REAL, updated_at REAL, state TEXT,
  answers TEXT DEFAULT '[]', lang TEXT);
CREATE TABLE IF NOT EXISTS project_keys(year INTEGER PRIMARY KEY, last INTEGER);
CREATE TABLE IF NOT EXISTS catalog_versions(
  version TEXT PRIMARY KEY, created_at REAL, source TEXT, status TEXT, data TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS plan_revisions(
  project_id TEXT, revision INTEGER, created_at REAL, turn INTEGER, sha TEXT, data TEXT, corrections TEXT,
  PRIMARY KEY(project_id, revision));
"""
# Indexes that need columns added by MIGRATIONS run after them.
INDEXES = """
CREATE UNIQUE INDEX IF NOT EXISTS notes_request ON notes(project_id, request_key) WHERE request_key IS NOT NULL;
"""
PROJECT_FIELDS = {
    'title', 'status', 'status_detail', 'repo_path', 'worktree', 'branch', 'base_commit',
    'verify_cmd', 'finished_at', 'stop_requested', 'resume_after_stop', 'accepted_solo',
    'engine_pid', 'engine_start', 'run_dir', 'test_version', 'max_turns', 'claude_model',
    'codex_model', 'claude_reasoning', 'codex_reasoning', 'status_detail_en', 'github_repo',
    'turn_timeout', 'github_url', 'github_visibility', 'github_version', 'github_branch', 'github_auto',
    'run_version', 'delivered_version', 'claude_role', 'codex_role', 'role_fallback',
    'gemini_model', 'gemini_reasoning', 'gemini_role', 'claude_selection', 'codex_selection', 'gemini_selection',
    'language', 'key', 'license', 'git_context'}
MAX_BODY = 40000
MIGRATIONS = {
    'projects': ('claude_reasoning', 'codex_reasoning', 'status_detail_en', 'github_repo',
                 'github_url', 'github_visibility', 'github_version', 'github_branch',
                 'github_auto', 'run_version', 'delivered_version', 'claude_role', 'codex_role',
                 'role_fallback', 'gemini_model', 'gemini_reasoning', 'gemini_role',
                 'claude_selection', 'codex_selection', 'gemini_selection', 'language', 'key', 'license',
                 'git_context'),
    'live': ('reason_en', 'config'), 'events': ('text_en', 'body'), 'versions': ('verify_summary_en', 'how_to_run'),
    'notes': ('response', 'kind', 'reopened', 'request_key', 'priority', 'done_version', 'done_at', 'ref'),
    'blocks': ('reason_en',)}


def next_key(db, moment: float) -> str:
    year = time.localtime(moment).tm_year
    row = db.execute('SELECT last FROM project_keys WHERE year=?', (year,)).fetchone()
    number = (row['last'] if row else 0) + 1
    db.execute('INSERT OR REPLACE INTO project_keys(year, last) VALUES(?, ?)', (year, number))
    return f'PR{number}/{year % 100:02d}'


class Meta(dict):
    """A project's meta as read, remembering the original so a save writes only what changed."""

    def __init__(self, data):
        super().__init__(data)
        self.original = json.loads(json.dumps(data))


class Store:
    def __init__(self, path=None):
        STATE.mkdir(parents=True, exist_ok=True)
        self.path = str(path or STATE / 'gemini.db')
        with self._db() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript(SCHEMA)
            for table, wanted in MIGRATIONS.items():
                columns = {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}
                for column in wanted:
                    if column not in columns:
                        db.execute(f'ALTER TABLE {table} ADD COLUMN {column}')
            db.executescript(INDEXES)

    @contextlib.contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _rows(self, sql: str, args: Iterable = ()) -> list:
        with self._db() as db:
            return [dict(row) for row in db.execute(sql, tuple(args))]

    def _row(self, sql: str, args: Iterable = ()) -> Optional[dict]:
        rows = self._rows(sql, args)
        return rows[0] if rows else None

    def add_project(self, **fields) -> dict:
        """Insert a project with its display key (PRn/yy) taken in the same transaction: numbering is
        global per year of creation, never reused after a deletion, and safe under concurrent creation."""
        now = time.time()
        fields.update(created_at=now, updated_at=now)
        with self.tx() as db:
            if not fields.get('key'):
                fields['key'] = next_key(db, now)
            names = ','.join(fields)
            marks = ','.join('?' * len(fields))
            db.execute(f'INSERT INTO projects({names}) VALUES({marks})', tuple(fields.values()))
        return self.project(fields['id'])

    def assign_missing_keys(self) -> int:
        """Existing projects without a key get one, in order of creation, in their year."""
        with self.tx() as db:
            rows = db.execute("SELECT id, created_at FROM projects WHERE key IS NULL OR key='' "
                              'ORDER BY created_at').fetchall()
            for row in rows:
                db.execute('UPDATE projects SET key=? WHERE id=?', (next_key(db, row['created_at']), row['id']))
        return len(rows)

    def project(self, project_id: str) -> Optional[dict]:
        return self._row('SELECT * FROM projects WHERE id=?', (project_id,))

    def projects(self, *statuses: str) -> list:
        if statuses:
            marks = ','.join('?' * len(statuses))
            return self._rows(f'SELECT * FROM projects WHERE status IN ({marks}) '
                              'ORDER BY created_at', statuses)
        return self._rows('SELECT * FROM projects ORDER BY created_at DESC')

    def update_project(self, project_id: str, **fields) -> None:
        unknown = set(fields) - PROJECT_FIELDS
        if unknown:
            raise ValueError(f'unknown project fields: {sorted(unknown)}')
        if 'status_detail' in fields:
            fields['status_detail_en'] = en(fields['status_detail'])
        fields['updated_at'] = time.time()
        assignments = ','.join(f'{name}=?' for name in fields)
        with self._db() as db:
            db.execute(f'UPDATE projects SET {assignments} WHERE id=?',
                       (*fields.values(), project_id))

    @contextlib.contextmanager
    def tx(self):
        """An IMMEDIATE transaction: the write lock is taken first, so a read and the write that depends
        on it cannot interleave with the server or an engine process doing the same."""
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
            except BaseException:
                db.execute('ROLLBACK')
                raise
            db.execute('COMMIT')
        finally:
            db.close()

    def meta(self, project_id: str) -> dict:
        row = self.project(project_id)
        return Meta(json.loads((row or {}).get('meta') or '{}'))

    def save_meta(self, project_id: str, meta: dict) -> None:
        """Write back only the keys this copy changed or removed, merged into the current value in one
        transaction. The server and the engine both keep state here: a whole-blob write from a stale
        copy used to drop the other side's changes."""
        if isinstance(meta, Meta):
            original = meta.original
            changed = {key: value for key, value in meta.items()
                       if key not in original or original[key] != value}
            removed = [key for key in original if key not in meta]
        else:
            changed, removed = None, []
        with self.tx() as db:
            row = db.execute('SELECT meta FROM projects WHERE id=?', (project_id,)).fetchone()
            current = json.loads((row['meta'] if row else None) or '{}')
            if changed is None:
                current = dict(meta)
            else:
                current.update(changed)
                for key in removed:
                    current.pop(key, None)
            db.execute('UPDATE projects SET meta=? WHERE id=?', (json.dumps(current), project_id))
        if isinstance(meta, Meta):
            meta.original = json.loads(json.dumps(dict(meta)))

    def update_meta(self, project_id: str, change):
        """Apply `change(meta)` to the current value inside one transaction; returns what it returns."""
        with self.tx() as db:
            row = db.execute('SELECT meta FROM projects WHERE id=?', (project_id,)).fetchone()
            current = json.loads((row['meta'] if row else None) or '{}')
            result = change(current)
            db.execute('UPDATE projects SET meta=? WHERE id=?', (json.dumps(current), project_id))
        return result

    def event(self, project_id: str, kind: str, text: str, agent: Optional[str] = None,
              data: Optional[dict] = None, body: Optional[str] = None) -> None:
        # Agents' replies and tool output can echo a credential: it never reaches the log or the panel.
        body = secretscan.redact(body[:MAX_BODY]) if body else None
        text_en = secretscan.redact(en(text))
        text = secretscan.redact(text) if not isinstance(text, str) or secretscan.has_secret(text) else text
        with self._db() as db:
            db.execute('INSERT INTO events(project_id,ts,kind,agent,text,text_en,data,body) '
                       'VALUES(?,?,?,?,?,?,?,?)',
                       (project_id, time.time(), kind, agent, str(text), text_en,
                        json.dumps(data) if data else None, body))

    def events(self, project_id: str, limit: int = 300) -> list:
        rows = self._rows('SELECT id,project_id,ts,kind,agent,text,text_en,data,'
                          'body IS NOT NULL AS has_body FROM events '
                          'WHERE project_id=? ORDER BY id DESC LIMIT ?', (project_id, limit))
        for row in rows:
            row['data'] = json.loads(row['data']) if row['data'] else None
        return rows

    def event_body(self, project_id: str, event_id: int) -> Optional[str]:
        row = self._row('SELECT body FROM events WHERE project_id=? AND id=?', (project_id, event_id))
        return row['body'] if row else None

    def last_event(self, project_id: str, kind: str) -> Optional[dict]:
        return self._row('SELECT * FROM events WHERE project_id=? AND kind=? '
                         'ORDER BY id DESC LIMIT 1', (project_id, kind))

    def set_live(self, project_id: str, **fields) -> None:
        current = self.live(project_id) or {}
        if 'reason' in fields:
            fields['reason_en'] = en(fields['reason'])
        current.update(fields, project_id=project_id, updated_at=time.time())
        names = ','.join(current)
        marks = ','.join('?' * len(current))
        with self._db() as db:
            db.execute(f'INSERT OR REPLACE INTO live({names}) VALUES({marks})',
                       tuple(current.values()))

    def live(self, project_id: str) -> Optional[dict]:
        return self._row('SELECT * FROM live WHERE project_id=?', (project_id,))

    def delete_project(self, project_id: str) -> None:
        """Every record of a project, in one transaction."""
        with self._db() as db:
            for table in ('live', 'events', 'notes', 'questions', 'versions', 'plan_revisions', 'usage', 'interactions',
                          'projects'):
                column = 'id' if table == 'projects' else 'project_id'
                db.execute(f'DELETE FROM {table} WHERE {column}=?', (project_id,))

    def clear_live(self, project_id: str) -> None:
        with self._db() as db:
            db.execute('DELETE FROM live WHERE project_id=?', (project_id,))

    def add_note(self, project_id: str, text: str, urgent: bool = False, kind: Optional[str] = None) -> int:
        with self._db() as db:
            cursor = db.execute('INSERT INTO notes(project_id,ts,text,urgent,status,kind) VALUES(?,?,?,?,?,?)',
                                (project_id, time.time(), text, int(urgent), 'pending', kind))
            return cursor.lastrowid

    def pending_notes(self, project_id: str) -> list:
        return self._rows("SELECT * FROM notes WHERE project_id=? AND status='pending' ORDER BY id",
                          (project_id,))

    def update_note(self, note_id: int, **fields) -> None:
        assignments = ','.join(f'{name}=?' for name in fields)
        with self._db() as db:
            db.execute(f'UPDATE notes SET {assignments} WHERE id=?', (*fields.values(), note_id))

    def notes(self, project_id: str) -> list:
        return self._rows('SELECT * FROM notes WHERE project_id=? ORDER BY id DESC', (project_id,))

    def take_notes(self, project_id: str, agent: str, turn: int) -> list:
        """Hand pending notes to the agent starting this turn."""
        with self._db() as db:
            rows = [dict(r) for r in db.execute(
                "SELECT * FROM notes WHERE project_id=? AND status='pending' ORDER BY priority DESC, id",
                (project_id,))]
            db.execute("UPDATE notes SET status='delivered',delivered_to=?,delivered_turn=?,"
                       "delivered_at=? WHERE project_id=? AND status='pending'",
                       (agent, turn, time.time(), project_id))
        return rows

    def answer_notes(self, project_id: str, turn: int, response: str) -> bool:
        """Attach the agent's reply to the notes it received this turn: they are answered, not yet done."""
        with self._db() as db:
            cursor = db.execute("UPDATE notes SET response=?, status='answered' WHERE project_id=? "
                                "AND delivered_turn=? AND status='delivered' AND response IS NULL",
                                (secretscan.redact(response[:MAX_BODY]), project_id, turn))
            return cursor.rowcount > 0

    def requeue_notes(self, project_id: str, turn: int) -> None:
        """The turn that received these notes died: give them to the next speaker."""
        with self._db() as db:
            db.execute("UPDATE notes SET status='pending',delivered_to=NULL,delivered_turn=NULL,"
                       "delivered_at=NULL WHERE project_id=? AND delivered_turn=? AND status='delivered'",
                       (project_id, turn))

    def plan_revision(self, project_id: str) -> Optional[dict]:
        row = self._row('SELECT * FROM plan_revisions WHERE project_id=? ORDER BY revision DESC LIMIT 1',
                        (project_id,))
        if row:
            row['data'] = json.loads(row['data'])
            row['corrections'] = json.loads(row['corrections'] or '[]')
        return row

    def add_plan_revision(self, project_id: str, turn: Optional[int], sha: str, data: dict,
                          corrections: list) -> Optional[int]:
        """A new valid plan, numbered; None when it equals the latest one. One transaction."""
        with self._db() as db:
            last = db.execute('SELECT revision, sha FROM plan_revisions WHERE project_id=? ORDER BY revision '
                              'DESC LIMIT 1', (project_id,)).fetchone()
            if last and last['sha'] == sha:
                return None
            revision = (last['revision'] if last else 0) + 1
            db.execute('INSERT INTO plan_revisions(project_id,revision,created_at,turn,sha,data,corrections) '
                       'VALUES(?,?,?,?,?,?,?)', (project_id, revision, time.time(), turn, sha,
                                                 json.dumps(data, ensure_ascii=False), json.dumps(corrections)))
            return revision

    def add_question(self, project_id: str, question: str) -> int:
        with self._db() as db:
            cursor = db.execute('INSERT INTO questions(project_id,ts,question,status) '
                                "VALUES(?,?,?,'pending')", (project_id, time.time(), question))
            return cursor.lastrowid

    def answer_question(self, question_id: int, answer: str, answered_by: str) -> None:
        with self._db() as db:
            db.execute("UPDATE questions SET answer=?,answered_by=?,status='answered',"
                       'answered_at=? WHERE id=?', (answer, answered_by, time.time(), question_id))

    def questions(self, project_id: str) -> list:
        return self._rows('SELECT * FROM questions WHERE project_id=? ORDER BY id DESC LIMIT 30',
                          (project_id,))

    def add_version(self, project_id: str, **fields) -> dict:
        with self._db() as db:
            number = db.execute('SELECT COALESCE(MAX(number),0)+1 FROM versions WHERE project_id=?',
                                (project_id,)).fetchone()[0]
            tag = fields.pop('tag_prefix') + f'/v{number}'
            fields.update(project_id=project_id, number=number, tag=tag, created_at=time.time(),
                          accepted_by=json.dumps(fields.get('accepted_by') or []),
                          verify_summary_en=en(fields.get('verify_summary')))
            names = ','.join(fields)
            marks = ','.join('?' * len(fields))
            db.execute(f'INSERT INTO versions({names}) VALUES({marks})', tuple(fields.values()))
        return self.version(project_id, number)

    def update_version(self, project_id: str, number: int, **fields) -> None:
        if 'accepted_by' in fields:
            fields['accepted_by'] = json.dumps(fields['accepted_by'])
        assignments = ','.join(f'{name}=?' for name in fields)
        with self._db() as db:
            db.execute(f'UPDATE versions SET {assignments} WHERE project_id=? AND number=?',
                       (*fields.values(), project_id, number))

    def version(self, project_id: str, number: int) -> Optional[dict]:
        row = self._row('SELECT * FROM versions WHERE project_id=? AND number=?',
                        (project_id, number))
        if row:
            row['accepted_by'] = json.loads(row['accepted_by'])
        return row

    def versions(self, project_id: str) -> list:
        rows = self._rows('SELECT * FROM versions WHERE project_id=? ORDER BY number DESC',
                          (project_id,))
        for row in rows:
            row['accepted_by'] = json.loads(row['accepted_by'])
        return rows

    def latest_version(self, project_id: str) -> Optional[dict]:
        rows = self.versions(project_id)
        return rows[0] if rows else None

    def set_block(self, provider: str, until: float, reason: str) -> None:
        with self._db() as db:
            db.execute('INSERT OR REPLACE INTO blocks(provider,until,reason,reason_en,created_at) '
                       'VALUES(?,?,?,?,?)', (provider, until, reason, en(reason), time.time()))

    def block(self, provider: str) -> Optional[dict]:
        return self._row('SELECT * FROM blocks WHERE provider=?', (provider,))

    def setting(self, key: str, default: float = DEFAULT_THRESHOLD) -> float:
        row = self._row('SELECT value FROM settings WHERE key=?', (key,))
        return float(row['value']) if row else default

    def full_power(self) -> bool:
        return bool(self.setting('full_power', 0))

    def threshold(self, provider: str) -> dict:
        """Usage per window at which a provider gets no new turn. The 5 h one hands work
        over in time; the weekly one is a reserve for the user and none by default.
        Full Power ignores both."""
        if self.full_power():
            return {FIVE_HOUR: 100.0, SEVEN_DAY: 100.0}
        return {FIVE_HOUR: self.setting(f'threshold_{provider}'),
                SEVEN_DAY: self.setting(f'weekly_{provider}', 100.0)}

    def text_setting(self, key: str) -> Optional[str]:
        row = self._row('SELECT value FROM settings WHERE key=?', (key,))
        return row['value'] if row else None

    def set_setting(self, key: str, value) -> None:
        with self._db() as db:
            db.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)', (key, str(value)))
