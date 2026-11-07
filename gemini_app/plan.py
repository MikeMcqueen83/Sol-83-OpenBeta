"""The plan the agents keep in the repository: a feature tree with turn budgets and debt.

The agents write it; the coordinator only reads it, so it costs no model calls. It
tells the agents what matters now and lets the user see where the limits went.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path
from typing import Optional

PLAN_FILE = '.sol83/plan.json'
KINDS = ('feature', 'task', 'debt')
PRIORITIES = ('must', 'should', 'could')
STATUSES = ('todo', 'doing', 'done', 'deferred')
CATEGORIES = ('bug', 'ui', 'perf', 'refactor', 'test', 'docs')
DEFAULT_BUDGET = 2
OPEN = ('todo', 'doing')
WEEK = 'seven_day'
FIVE_HOUR = 'five_hour'

CREATE = (
    'Nie ma jeszcze planu projektu. W tej turze najpierw utwórz plik .sol83/plan.json, potem '
    'zacznij pierwszą pozycję. Format: {"architecture": "3-6 zdań: moduły i jak się łączą", '
    '"run": "jak uruchomić i przetestować aplikację, konkretne polecenia", "items": [{"id": "F1", '
    '"title": "...", "kind": "feature", "parent": null, "priority": "must", "status": "todo"}, '
    '{"id": "F1.1", "title": "...", "kind": "task", "parent": "F1", "priority": "must", '
    '"status": "todo", "budget": 2}]}. 5-12 funkcji (feature), pod nimi zadania (task) na 1-3 '
    'tury pracy; budget to liczba tur. Priorytet must: bez tego cel zadania nie jest spełniony; '
    'should: wyraźnie lepiej; could: dodatek. Nie rozdrabniaj: zadanie mniejsze niż pół tury '
    'połącz z sąsiednim.')
REPLAN = (
    'Użytkownik zlecił nową pracę. Najpierw przebuduj .sol83/plan.json: dopisz nowe funkcje, '
    'połącz je z istniejącymi pozycjami i długiem, ustal priorytety na nowo. Pozycje done '
    'zostają done. Potem zacznij najważniejszą otwartą pozycję must.')
INHERITED = (
    'Repozytorium ma .sol83/plan.json z poprzedniego projektu. To nie jest plan tego zadania. W tej '
    'turze zbuduj plan od nowa pod zadanie użytkownika powyżej: architekturę i sposób uruchomienia '
    'opisz według obecnego kodu, a ze starego planu przenieś tylko pozycje i dług, które dotyczą '
    'nowego zadania. Potem zacznij najważniejszą pozycję must.')
RULES = (
    'Zasady pracy z planem: w każdej turze pracujesz nad jedną pozycją i podajesz ją w linii '
    '„PRACA: <id>”. Aktualizuj jej status w planie. Naprawiasz od razu tylko to, co psuje build '
    'lub testy albo blokuje odbiór bieżącej pozycji, oraz to, co jest tańsze niż opisanie '
    '(kilka wierszy). Każdą inną usterkę dopisz do planu jako dług: kind "debt", parent: pozycja, '
    'której dotyczy, category: bug|ui|perf|refactor|test|docs, note: objaw i miejsce. Nie naprawiaj '
    'jej teraz. Nowe pomysły też trafiają do planu, nie do kodu.')


def load(worktree) -> tuple[Optional[dict], Optional[str]]:
    """The plan and a problem with it, if any. No plan at all is (None, None)."""
    path = Path(worktree) / PLAN_FILE
    if not path.exists():
        return None, None
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return None, f'niepoprawny JSON: {exc}'
    problems = validate(data)
    return data, '; '.join(problems[:3]) or None


def validate(data) -> list:
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        return ['brak listy items']
    problems = []
    ids = set()
    for item in data['items']:
        if not isinstance(item, dict) or not item.get('id') or not item.get('title'):
            problems.append('pozycja bez id albo title')
            continue
        if item['id'] in ids:
            problems.append(f"powtórzone id {item['id']}")
        ids.add(item['id'])
        for field, allowed in (('kind', KINDS), ('priority', PRIORITIES), ('status', STATUSES)):
            if item.get(field, allowed[0]) not in allowed:
                problems.append(f"{item['id']}: {field} spoza {'/'.join(allowed)}")
    for item in data['items']:
        if isinstance(item, dict) and item.get('parent') and item['parent'] not in ids:
            problems.append(f"{item.get('id')}: nieznany parent {item['parent']}")
    return problems


def items(plan: Optional[dict]) -> list:
    return [item for item in (plan or {}).get('items', []) if isinstance(item, dict) and item.get('id')]


def budget(item: dict) -> int:
    try:
        return max(1, int(item.get('budget') or DEFAULT_BUDGET))
    except (TypeError, ValueError):
        return DEFAULT_BUDGET


def spend(turns: list) -> dict:
    """Turns and limit percent per plan item, from the coordinator's turn records."""
    spent = collections.defaultdict(lambda: {'turns': 0, 'week': 0.0, 'five_hour': 0.0, 'agents': set()})
    for turn in turns:
        key = turn.get('item') or ''
        row = spent[key]
        row['turns'] += 1
        cost = turn.get('cost') or {}
        row['week'] += cost.get(WEEK) or 0
        row['five_hour'] += cost.get(FIVE_HOUR) or 0
        row['agents'].add(turn.get('agent'))
    return spent


def rows(plan: Optional[dict], turns: list) -> list:
    """The tree for the panel: every item with what it has cost so far."""
    spent = spend(turns)
    result = []
    for item in items(plan):
        used = spent.get(item['id'], {})
        result.append({'id': item['id'], 'title': item['title'], 'parent': item.get('parent'),
                       'kind': item.get('kind', 'task'), 'priority': item.get('priority', 'should'),
                       'status': item.get('status', 'todo'), 'budget': budget(item),
                       'category': item.get('category'), 'note': item.get('note'),
                       'turns': used.get('turns', 0), 'week': round(used.get('week', 0)),
                       'five_hour': round(used.get('five_hour', 0))})
    return result


def overruns(plan: Optional[dict], turns: list) -> list:
    """Open items that used more turns than their budget."""
    spent = spend(turns)
    return [(item, spent[item['id']]['turns']) for item in items(plan)
            if item.get('kind') != 'feature' and item.get('status', 'todo') in OPEN
            and spent.get(item['id'], {}).get('turns', 0) > budget(item)]


def breakdown(plan: Optional[dict], turns: list) -> dict:
    """Where the limits went: core work, nice-to-have, debt, or nothing in the plan."""
    by_id = {item['id']: item for item in items(plan)}
    shares = collections.Counter()
    for turn in turns:
        week = (turn.get('cost') or {}).get(WEEK) or 0
        item = by_id.get(turn.get('item') or '')
        if not item:
            group = 'unassigned'
        elif item.get('kind') == 'debt':
            group = 'debt'
        else:
            group = item.get('priority', 'should')
        shares[group] += week
    return {group: round(value) for group, value in shares.items()}


def summary(plan: dict, turns: list, focus: Optional[str] = None) -> str:
    """A few lines for the handoff: enough to keep the agents on course, cheap in tokens."""
    all_items = items(plan)
    tasks = [item for item in all_items if item.get('kind') != 'feature']
    done = sum(1 for item in tasks if item.get('status') == 'done')
    spent = spend(turns)
    lines = [f'Plan: {done}/{len(tasks)} zadań gotowych, dług: '
             f"{sum(1 for item in all_items if item.get('kind') == 'debt' and item.get('status') in OPEN)} "
             'otwartych pozycji. Pełny plan: .sol83/plan.json.']
    if plan.get('architecture'):
        lines.append(f"Architektura: {str(plan['architecture'])[:500]}")
    open_must = [item for item in tasks if item.get('priority') == 'must' and item.get('kind') != 'debt'
                 and item.get('status', 'todo') in OPEN]
    if focus:
        lines.append(f'Priorytet użytkownika: pozycja {focus}.')
    for item in open_must[:4]:
        used = spent.get(item['id'], {}).get('turns', 0)
        lines.append(f"- {item['id']} {item['title']} [{item.get('status', 'todo')}, "
                     f"{used}/{budget(item)} tur]")
    if not open_must:
        lines.append('Wszystkie zadania must są zamknięte: domknij odbiór albo zajmij się should.')
    return '\n'.join(lines)
