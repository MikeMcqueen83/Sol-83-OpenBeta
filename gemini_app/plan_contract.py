"""The plan contract shared by the prompt, the parser, the validator, the store and the panel.

Canonical values are technical and do not depend on the interface language. Unambiguous
variants (Polish, English, spelling) are normalized through an explicit map and every
correction is reported; anything unknown is an error, never "done". The coordinator keeps
the last valid plan as a numbered revision, so a broken update from an agent cannot replace it.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Optional

STATUSES = ('todo', 'doing', 'done', 'deferred')
KINDS = ('feature', 'task', 'debt')
PRIORITIES = ('must', 'should', 'could')
MAX_REPAIRS = 3


def _fold(value) -> str:
    # ł has no decomposition in Unicode: map it before stripping diacritics.
    text = unicodedata.normalize('NFKD', str(value).translate(str.maketrans('łŁ', 'lL')))
    text = text.encode('ascii', 'ignore').decode()
    return ' '.join(text.lower().replace('_', ' ').replace('-', ' ').split())


# Explicit maps. Keys are folded (lower case, no diacritics, spaces for _ and -).
STATUS_MAP = {
    **{key: 'todo' for key in ('todo', 'to do', 'open', 'new', 'planned', 'do zrobienia', 'otwarte', 'nowe',
                               'zaplanowane')},
    **{key: 'doing' for key in ('doing', 'in progress', 'wip', 'started', 'w toku', 'w trakcie', 'realizacja',
                                'rozpoczete')},
    **{key: 'done' for key in ('done', 'completed', 'complete', 'finished', 'zrobione', 'gotowe', 'ukonczone',
                               'zakonczone', 'wykonane')},
    **{key: 'deferred' for key in ('deferred', 'postponed', 'later', 'odlozone', 'odroczone', 'pozniej')},
}
KIND_MAP = {**{k: 'feature' for k in ('feature', 'funkcja', 'epic')},
            **{k: 'task' for k in ('task', 'zadanie', 'subtask')},
            **{k: 'debt' for k in ('debt', 'dlug', 'tech debt', 'bug', 'usterka')}}
PRIORITY_MAP = {**{k: 'must' for k in ('must', 'must have', 'musi', 'wymagane', 'krytyczne', 'p0')},
                **{k: 'should' for k in ('should', 'should have', 'powinno', 'p1')},
                **{k: 'could' for k in ('could', 'could have', 'moze', 'opcjonalne', 'nice to have', 'p2')}}
FIELDS = (('status', STATUS_MAP, 'todo'), ('kind', KIND_MAP, 'task'), ('priority', PRIORITY_MAP, 'should'))

PROMPT_RULES = ('Kontrakt planu (.sol83/plan.json): wartości techniczne zawsze po angielsku, niezależnie od '
                'języka projektu. status: todo | doing | done | deferred. kind: feature | task | debt. '
                'priority: must | should | could. id: unikalne, bez spacji. parent i depends_on: tylko istniejące '
                'id. deferred nie oznacza ukończenia: odłożenie pozycji must wymaga decyzji użytkownika. '
                'Przyczynę blokady wpisz w blocked_by, a wynik testów w note, nie w status.')
PROMPT_RULES_EN = ('Plan contract (.sol83/plan.json): technical values are always in English, whatever the '
                   'project language. status: todo | doing | done | deferred. kind: feature | task | debt. '
                   'priority: must | should | could. id: unique, no spaces. parent and depends_on: existing ids '
                   'only. deferred does not mean finished: deferring a must item needs the user\'s decision. Put '
                   'the reason for a block in blocked_by and test results in note, not in status.')


def normalize(data) -> tuple:
    """(plan, problems, corrections). The plan is a normalized copy; problems make it invalid."""
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        return None, ['brak listy items'], []
    plan = json.loads(json.dumps(data))
    problems, corrections, ids = [], [], []
    for item in plan['items']:
        if not isinstance(item, dict) or not str(item.get('id') or '').strip() or not item.get('title'):
            problems.append('pozycja bez id albo title')
            continue
        item['id'] = str(item['id']).strip()
        if ' ' in item['id']:
            problems.append(f"{item['id']}: id ze spacją")
        if item['id'] in ids:
            problems.append(f"powtórzone id {item['id']}")
        ids.append(item['id'])
        for field, mapping, default in FIELDS:
            raw = item.get(field)
            if raw is None or raw == '':
                item[field] = default
                continue
            canonical = mapping.get(_fold(raw))
            if canonical is None:
                problems.append(f"{item['id']}: {field} „{raw}” spoza {'/'.join(sorted(set(mapping.values())))}")
            elif canonical != raw:
                corrections.append(f"{item['id']}: {field} „{raw}” → {canonical}")
                item[field] = canonical
    known = set(ids)
    for item in plan['items']:
        if not isinstance(item, dict) or not item.get('id'):
            continue
        if item.get('parent') and item['parent'] not in known:
            problems.append(f"{item['id']}: nieznany parent {item['parent']}")
        depends = item.get('depends_on') or []
        if not isinstance(depends, list):
            problems.append(f"{item['id']}: depends_on musi być listą")
            continue
        for other in depends:
            if other not in known:
                problems.append(f"{item['id']}: nieznana zależność {other}")
    cycle = _cycle(plan['items'])
    if cycle:
        problems.append('cykl zależności: ' + ' → '.join(cycle))
    return plan, problems, corrections


def _cycle(items: list) -> Optional[list]:
    edges = {item['id']: [*(item.get('depends_on') or []), *([item['parent']] if item.get('parent') else [])]
             for item in items if isinstance(item, dict) and item.get('id')}
    state: dict = {}

    def visit(node, path):
        if state.get(node) == 1:
            return path[path.index(node):] + [node]
        if state.get(node) == 2 or node not in edges:
            return None
        state[node] = 1
        for nxt in edges[node]:
            found = visit(nxt, path + [node])
            if found:
                return found
        state[node] = 2
        return None
    for node in edges:
        found = visit(node, [])
        if found:
            return found
    return None


def fingerprint(plan: dict) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def must_deferred(plan: Optional[dict]) -> list:
    """Must items set to deferred: not finished, and not out of scope without the user's decision."""
    return [item for item in (plan or {}).get('items', []) if isinstance(item, dict)
            and item.get('priority') == 'must' and item.get('status') == 'deferred' and item.get('kind') != 'debt']
