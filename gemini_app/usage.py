"""Token usage per turn, normalized across providers without pretending they are comparable.

What each adapter reports (checked on real runs of 1-6 November 2026):
- Claude Code `-p --output-format json`: usage of this invocation, i.e. one turn. Fresh input,
  cache writes and cache reads are separate fields; reasoning ("thinking") is inside output
  and is not reported apart.
- Codex `exec`: one line "tokens used" with the total of the whole session (thread), printed
  with a thousands separator ("192 753"). No input/output split. A resumed session keeps counting.
- Antigravity `agy` (Gemini): `usage` of the whole conversation so far. Cached tokens are a
  separate category, many times larger than fresh input, not part of it.

So cumulative counters are turned into per-turn deltas against the previous reading of the same
session; a smaller value than before means a new or reset counter and is taken as it is.
Missing data stays None ("unavailable"), never 0. The raw record is kept for diagnosis.
"""
from __future__ import annotations

import json
import re
import time
from typing import Optional

FIELDS = ('input', 'cache_read', 'cache_write', 'output', 'reasoning', 'total')
SCOPE = {'claude': 'turn', 'codex': 'session', 'gemini': 'session'}
SOURCE = {'claude': 'Claude Code: usage wyniku tury', 'codex': 'Codex: „tokens used” sesji',
          'gemini': 'Antigravity: usage rozmowy'}
_CODEX_TOTAL = re.compile(r'tokens used\s*:?[ \t]*\n?[ \t]*([0-9](?:[0-9 ,.  ]*[0-9])?)', re.I)


def parse_codex_total(text: str) -> Optional[int]:
    """The last "tokens used" total in Codex's stderr, whatever the thousands separator."""
    found = _CODEX_TOTAL.findall(text or '')
    if not found:
        return None
    digits = re.sub(r'\D', '', found[-1])
    return int(digits) if digits else None


def _int(usage: dict, *keys) -> Optional[int]:
    values = [usage.get(key) for key in keys if isinstance(usage.get(key), (int, float))]
    return int(sum(values)) if values else None


def normalize(agent: str, raw) -> dict:
    """One provider's record in common fields. None means the provider did not report it."""
    record = dict.fromkeys(FIELDS)
    if agent == 'codex':
        record['total'] = raw if isinstance(raw, int) else None
        return record
    if not isinstance(raw, dict):
        return record
    if agent == 'claude':
        record.update(input=_int(raw, 'input_tokens'), cache_write=_int(raw, 'cache_creation_input_tokens'),
                      cache_read=_int(raw, 'cache_read_input_tokens'), output=_int(raw, 'output_tokens'))
    else:
        record.update(input=_int(raw, 'input_tokens', 'prompt_tokens', 'inputTokens', 'promptTokens'),
                      cache_read=_int(raw, 'cached_tokens', 'cache_read_tokens', 'cachedTokens',
                                      'cachedContentTokenCount'),
                      output=_int(raw, 'output_tokens', 'completion_tokens', 'outputTokens', 'candidatesTokens'),
                      reasoning=_int(raw, 'thoughts_tokens', 'thinking_tokens', 'reasoning_tokens',
                                     'thoughtsTokenCount'))
    parts = [record[key] for key in ('input', 'cache_read', 'cache_write', 'output') if record[key] is not None]
    # Total of what the turn processed: fresh input, cache traffic and output. Reasoning tokens are
    # shown on their own and not added: whether a provider already counts them in output is not
    # established for Antigravity, and adding them could count them twice.
    record['total'] = sum(parts) if parts else None
    return record


def delta(current: dict, previous: Optional[dict]) -> tuple:
    """(per-turn values, note). Previous is the last reading of the same session."""
    if previous is None:
        return dict(current), None
    if (current.get('total') or 0) < (previous.get('total') or 0):
        return dict(current), 'licznik zaczął się od nowa'
    out = {}
    for key in FIELDS:
        now, before = current.get(key), previous.get(key)
        out[key] = None if now is None else (now - before if before is not None else now)
    return out, None


def record(store, project_id: str, turn: int, agent: str, raw, session_id: Optional[str],
           model_requested: Optional[str], model_confirmed: Optional[str]) -> Optional[dict]:
    """Store one turn's usage once (a repeated call for the same turn changes nothing)."""
    if raw is None:
        return None
    scope = SCOPE.get(agent, 'turn')
    values = normalize(agent, raw)
    previous = None
    if scope == 'session' and session_id:
        row = store._row('SELECT * FROM usage WHERE project_id=? AND agent=? AND session_id=? AND turn<? '
                         'ORDER BY turn DESC LIMIT 1', (project_id, agent, session_id, turn))
        previous = {key: row[key] for key in FIELDS} if row else None
    per_turn, note = delta(values, previous) if scope == 'session' else (values, None)
    if scope == 'session' and previous is None:
        note = 'pierwszy odczyt tej sesji: może obejmować wcześniejsze tury'
    with store._db() as db:
        db.execute('INSERT OR IGNORE INTO usage(project_id,turn,agent,ts,session_id,scope,source,raw,model_requested,'
                   'model_confirmed,' + ','.join(FIELDS) + ',' + ','.join(f'd_{k}' for k in FIELDS) + ',note) '
                   'VALUES(' + ','.join('?' * (11 + 2 * len(FIELDS))) + ')',
                   (project_id, turn, agent, time.time(), session_id, scope, SOURCE.get(agent),
                    json.dumps(raw), model_requested, model_confirmed,
                    *(values[k] for k in FIELDS), *(per_turn[k] for k in FIELDS), note))
    return {**per_turn, 'note': note, 'scope': scope}


def summary(store, project_id: str) -> dict:
    """Per provider and model: turns with a reading, per-turn sums of what was reported, and which
    categories are measured at all. Categories a provider does not report stay None."""
    rows = store._rows('SELECT * FROM usage WHERE project_id=? ORDER BY turn', (project_id,))
    result: dict = {}
    for row in rows:
        key = f"{row['agent']}|{row['model_confirmed'] or row['model_requested'] or '?'}"
        entry = result.setdefault(key, {'agent': row['agent'], 'model': row['model_confirmed'] or row['model_requested'],
                                        'confirmed': bool(row['model_confirmed']), 'turns': 0, 'source': row['source'],
                                        'scope': row['scope'], **dict.fromkeys(FIELDS), 'notes': 0})
        entry['turns'] += 1
        entry['notes'] += bool(row['note'])
        for field in FIELDS:
            value = row[f'd_{field}']
            if value is not None:
                entry[field] = (entry[field] or 0) + value
    return {'rows': list(result.values()),
            'turns': [{'turn': row['turn'], 'agent': row['agent'], 'total': row['d_total'], 'input': row['d_input'],
                       'output': row['d_output'], 'cache_read': row['d_cache_read'], 'note': row['note']}
                      for row in rows][-12:]}


def windows(turns: list, overlaps: Optional[dict] = None) -> dict:
    """Project usage of each provider's limit windows, from the per-turn movement of the account's
    readings. An estimate: the readings cover the whole account, other work included."""
    result: dict = {}
    for turn in turns:
        cost = turn.get('cost')
        entry = result.setdefault(turn['agent'], {'five_hour': 0.0, 'seven_day': 0.0, 'turns': 0,
                                                  'unmeasured': 0, 'shared': 0})
        entry['turns'] += 1
        if not cost:
            entry['unmeasured'] += 1
            continue
        if turn.get('overlap'):
            entry['shared'] += 1
        entry['five_hour'] += cost.get('five_hour') or 0
        entry['seven_day'] += cost.get('seven_day') or 0
    for entry in result.values():
        entry['five_hour_percent'] = round(entry['five_hour'], 1)
        entry['window_equivalents'] = round(entry['five_hour'] / 100, 2)
        entry['weekly_percent'] = round(entry['seven_day'], 1)
    return result
