"""The plan the agents keep in the repository: a feature tree with turn budgets and debt.

The agents write it; the coordinator only reads it, so it costs no model calls. It
tells the agents what matters now and lets the user see where the limits went.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path
from typing import Optional

from . import plan_contract

PLAN_FILE = '.sol83/plan.json'
KINDS = plan_contract.KINDS
PRIORITIES = plan_contract.PRIORITIES
STATUSES = plan_contract.STATUSES
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
    'jej teraz. Nowe pomysły też trafiają do planu, nie do kodu. ' + plan_contract.PROMPT_RULES)


TEXTS = {
    'create': {'pl': CREATE, 'en': (
        'There is no project plan yet. In this turn first create the file .sol83/plan.json, then start the '
        'first item. Format: {"architecture": "3-6 sentences: modules and how they connect", "run": "how to run '
        'and test the application, concrete commands", "items": [{"id": "F1", "title": "...", "kind": "feature", '
        '"parent": null, "priority": "must", "status": "todo"}, {"id": "F1.1", "title": "...", "kind": "task", '
        '"parent": "F1", "priority": "must", "status": "todo", "budget": 2}]}. 5-12 features, under them tasks '
        'of 1-3 turns of work; budget is the number of turns. Priority must: without it the goal is not met; '
        'should: clearly better; could: an extra. Do not split too finely: merge a task smaller than half a turn '
        'with its neighbour.')},
    'add_order': {'pl': ('Użytkownik zlecił nową pracę. Dopisz ją do .sol83/plan.json jako nowe pozycje, bez przebudowy '
                         'całego planu (pozycje done zostają done), i w tej samej turze zacznij najważniejszą z nich.'),
                  'en': ('The user ordered new work. Add it to .sol83/plan.json as new items, without rebuilding the whole '
                         'plan (done items stay done), and start the most important of them in this same turn.')},
    'replan': {'pl': REPLAN, 'en': (
        'The user ordered new work. First rebuild .sol83/plan.json: add the new features, connect them with the '
        'existing items and debt, and set priorities again. Done items stay done. Then start the most important '
        'open must item.')},
    'inherited': {'pl': INHERITED, 'en': (
        'The repository has .sol83/plan.json from an earlier project. It is not the plan of this task. In this '
        'turn build the plan anew for the user\'s task above: describe the architecture and how to run it from '
        'the current code, and carry over from the old plan only the items and debt that concern the new task. '
        'Then start the most important must item.')},
    'rules': {'pl': RULES, 'en': (
        'Working with the plan: in every turn you work on one item and name it in a line "WORK: <id>". Update '
        'its status in the plan. Fix at once only what breaks the build or tests or blocks acceptance of the '
        'current item, and what is cheaper than describing (a few lines). Add any other defect to the plan as '
        'debt: kind "debt", parent: the item it concerns, category: bug|ui|perf|refactor|test|docs, note: symptom '
        'and place. Do not fix it now. New ideas also go into the plan, not into the code. '
        + plan_contract.PROMPT_RULES_EN)},
    'problem': {'pl': 'Plan .sol83/plan.json ma błąd: {problem}. Popraw go w tej turze (próba {attempt} z {limit}; potem '
                      'koordynator przywróci ostatni poprawny plan).',
                'en': 'The plan .sol83/plan.json has an error: {problem}. Fix it in this turn (attempt {attempt} of '
                      '{limit}; after that the coordinator restores the last valid plan).'},
    'stale': {'pl': ' Powyżej streszczenie ostatniego poprawnego planu.', 'en': ' Above is a summary of the last valid plan.'},
    'overrun': {'pl': 'Pozycja {item} przekroczyła budżet ({used}/{budget} tur). W tej turze zdecyduj: domknij ją '
                      'minimalnie albo odłóż (status deferred, w note co zostało) i przejdź do następnej pozycji must.',
                'en': 'Item {item} went over its budget ({used}/{budget} turns). In this turn decide: close it minimally '
                      'or defer it (status deferred, what is left in note) and move on to the next must item.'},
    'summary_head': {'pl': 'Plan: {done}/{total} zadań gotowych, dług: {debt} otwartych pozycji. Pełny plan: .sol83/plan.json.',
                     'en': 'Plan: {done}/{total} tasks done, debt: {debt} open items. Full plan: .sol83/plan.json.'},
    'architecture': {'pl': 'Architektura: {text}', 'en': 'Architecture: {text}'},
    'focus': {'pl': 'Priorytet użytkownika: pozycja {item}.', 'en': "The user's priority: item {item}."},
    'item_line': {'pl': '- {id} {title} [{status}, {used}/{budget} tur]', 'en': '- {id} {title} [{status}, {used}/{budget} turns]'},
    'all_must_done': {'pl': 'Wszystkie zadania must są zamknięte: domknij odbiór albo zajmij się should.',
                      'en': 'All must tasks are closed: finish acceptance or move on to should.'},
}


def text(lang: str, key: str, **values) -> str:
    template = TEXTS[key].get(lang) or TEXTS[key]['pl']
    return template.format(**values) if values else template


def read(worktree) -> tuple:
    """(normalized plan or None, problems, corrections) from the file. No file is (None, [], [])."""
    path = Path(worktree) / PLAN_FILE
    if not path.exists():
        return None, [], []
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return None, [f'niepoprawny JSON: {exc}'], []
    plan, problems, corrections = plan_contract.normalize(data)
    return (None if problems else plan), problems, corrections


def load(worktree) -> tuple[Optional[dict], Optional[str]]:
    """The plan as the file has it, normalized, and a problem with it, if any. An invalid plan is
    (None, problem): its statuses must not count for anything. No plan at all is (None, None)."""
    plan, problems, _ = read(worktree)
    return plan, '; '.join(problems[:3]) or None


def validate(data) -> list:
    return plan_contract.normalize(data)[1]


def effective(store, project: dict) -> tuple[Optional[dict], Optional[str]]:
    """The plan the coordinator works with: the file when it is valid, otherwise the last valid
    revision it recorded. A broken update never replaces a good plan."""
    plan, problem = load(project['worktree']) if project.get('worktree') else (None, None)
    if plan is None and problem:
        saved = store.plan_revision(project['id'])
        return (saved['data'] if saved else None), problem
    return plan, problem


def record(store, project_id: str, worktree, turn: Optional[int]) -> dict:
    """After a turn: keep a valid plan as a new revision, count invalid ones, and after too many
    failed repairs put the last valid plan back (the broken file is kept next to it)."""
    plan, problems, corrections = read(worktree)
    if plan is not None:
        revision = store.add_plan_revision(project_id, turn, plan_contract.fingerprint(plan), plan, corrections)
        store.update_meta(project_id, lambda meta: meta.pop('plan_repairs', None))
        return {'state': 'valid', 'revision': revision, 'corrections': corrections}
    if not problems:
        return {'state': 'missing'}
    repairs = store.update_meta(project_id, lambda meta: meta.__setitem__(
        'plan_repairs', meta.get('plan_repairs', 0) + 1) or meta['plan_repairs'])
    saved = store.plan_revision(project_id)
    if repairs < plan_contract.MAX_REPAIRS or not saved:
        return {'state': 'invalid', 'problems': problems, 'repairs': repairs}
    path = Path(worktree) / PLAN_FILE
    broken = path.with_name('plan.invalid.json')
    try:
        broken.write_text(path.read_text())
    except OSError:
        pass
    path.write_text(json.dumps(saved['data'], ensure_ascii=False, indent=2))
    store.update_meta(project_id, lambda meta: meta.pop('plan_repairs', None))
    return {'state': 'restored', 'problems': problems, 'revision': saved['revision']}


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


def summary(plan: dict, turns: list, focus: Optional[str] = None, lang: str = 'pl') -> str:
    """A few lines for the handoff: enough to keep the agents on course, cheap in tokens."""
    all_items = items(plan)
    tasks = [item for item in all_items if item.get('kind') != 'feature']
    done = sum(1 for item in tasks if item.get('status') == 'done')
    spent = spend(turns)
    debt = sum(1 for item in all_items if item.get('kind') == 'debt' and item.get('status') in OPEN)
    lines = [text(lang, 'summary_head', done=done, total=len(tasks), debt=debt)]
    if plan.get('architecture'):
        lines.append(text(lang, 'architecture', text=str(plan['architecture'])[:500]))
    open_must = [item for item in tasks if item.get('priority') == 'must' and item.get('kind') != 'debt'
                 and item.get('status', 'todo') in OPEN]
    if focus:
        lines.append(text(lang, 'focus', item=focus))
    for item in open_must[:4]:
        used = spent.get(item['id'], {}).get('turns', 0)
        lines.append(text(lang, 'item_line', id=item['id'], title=item['title'], status=item.get('status', 'todo'),
                          used=used, budget=budget(item)))
    if not open_must:
        lines.append(text(lang, 'all_must_done'))
    return '\n'.join(lines)


WEIGHTS = {'must': 3, 'should': 2, 'could': 1}


def progress(plan: Optional[dict], out_of_scope: Optional[set] = None) -> Optional[dict]:
    """Functional progress, technical debt and net progress on one explicit basis (spec 12).

    Basis: the scope items of the plan, weighted by priority (must 3, should 2, could 1). A feature
    counts through its tasks; a feature without tasks counts itself. Debt items are weighted the same
    way and measured against the same denominator, so the two can be subtracted:
    net = max(0, functional - debt). Deferred is not done. Each debt item is one item, whoever found it.
    No plan means no estimate. This is a management indicator, not a probability or a time forecast.
    """
    all_items = items(plan)
    if not all_items:
        return None
    out_of_scope = out_of_scope or set()
    parents = {item.get('parent') for item in all_items if item.get('parent')}
    scope = [item for item in all_items if item.get('kind') != 'debt' and item['id'] not in out_of_scope
             and (item.get('kind') != 'feature' or item['id'] not in parents)]
    debt = [item for item in all_items if item.get('kind') == 'debt' and item.get('status', 'todo') in OPEN]
    weight = lambda item: WEIGHTS.get(item.get('priority'), 2)  # noqa: E731
    total = sum(weight(item) for item in scope)
    if not total:
        return None
    done = sum(weight(item) for item in scope if item.get('status') == 'done')
    functional = 100.0 * done / total
    penalty = 100.0 * sum(weight(item) for item in debt) / total
    return {'done_items': sum(1 for item in scope if item.get('status') == 'done'), 'scope_items': len(scope),
            'functional': round(functional, 1), 'debt_penalty': round(penalty, 1),
            'net': round(max(0.0, functional - penalty), 1), 'open_debt': len(debt),
            'deferred_must': sum(1 for item in scope if item.get('priority') == 'must' and item.get('status') == 'deferred'),
            'basis': 'pozycje zakresu z planu, wagi must 3 / should 2 / could 1; dług w tej samej skali'}
