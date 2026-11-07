"""Roles: which kind of work each model takes. A model can hold several roles at once.

Every turn is planning, implementing or reviewing, and with a content creator on also making
ordered content: graphics, texts, story. The general role does planning, implementation and
review; it does NOT include making content: only the content creator role may carry out a
content order (spec 7 and 8.3). Other models may order content, never make it.

Stored as a comma-separated list in `<side>_role`; an older single value is a list of one, so
existing projects keep their meaning.
"""
from __future__ import annotations

GENERAL = 'general'
CONTENT = 'content'
ROLES = ('general', 'architect', 'implementer', 'tester', 'analyst', 'content')
WORKS = ('plan', 'implement', 'review')
COVERS = {'general': set(WORKS), 'architect': {'plan'}, 'implementer': {'implement'},
          'tester': {'review'}, 'analyst': {'review'}, 'content': {CONTENT}}
FALLBACKS = ('general', 'wait')
PROMPTS = {
    'general': {'pl': 'Twoja rola: Ogólna. Planujesz, implementujesz i przeglądasz, gdy przypada Twoja tura. '
                      'Zamówionych treści nie wykonujesz: to należy do Twórcy treści.',
                'en': 'Your role: General. You plan, implement and review when your turn comes. You do not make '
                      'ordered content: that belongs to the Content creator.'},
    'architect': {'pl': 'Twoja rola: Architekt. Zajmujesz się planem: architekturą, podziałem na pozycje i budżety, '
                        'przebudową planu po nowym zleceniu oraz researchem. Nie implementuj zadań z planu: zrobi to inny model.',
                  'en': 'Your role: Architect. You own the plan: architecture, the split into items and budgets, '
                        'rebuilding the plan after a new request, and research. Do not implement plan tasks: another '
                        'model does that.'},
    'implementer': {'pl': 'Twoja rola: Implementujący. Realizujesz zadania z planu, jedno na turę. Plan, jego przebudowa i '
                          'przegląd należą do innych ról.',
                    'en': 'Your role: Implementer. You carry out plan tasks, one per turn. The plan, rebuilding it and '
                          'review belong to other roles.'},
    'tester': {'pl': 'Twoja rola: Tester. Przeglądasz ostatnie zmiany, uruchamiasz testy, dopisujesz brakujące testy i plan '
                     'regresji. Nie budujesz nowych funkcji: drobną usterkę popraw, większą opisz i dopisz do planu jako dług.',
               'en': 'Your role: Tester. You review the latest changes, run the tests, add missing tests and a '
                     'regression plan. You do not build new features: fix a small defect, describe a larger one and add '
                     'it to the plan as debt.'},
    'analyst': {'pl': 'Twoja rola: Analityk systemowy. Szukasz luk względem zadania i kryteriów odbioru: brakujących przypadków, '
                      'ryzyk i niespójności. Plan ich łatania dopisujesz do .sol83/plan.json jako dług (kind "debt"). Nie implementujesz.',
                'en': 'Your role: System analyst. You look for gaps against the task and the acceptance criteria: missing '
                      'cases, risks and inconsistencies. You add the plan to close them to .sol83/plan.json as debt (kind '
                      '"debt"). You do not implement.'},
    'content': {'pl': 'Twoja rola: Twórca treści. Realizujesz zatwierdzone zamówienia z .sol83/assets.json: grafiki '
                      '(ilustracje, ikony, tekstury, sprite\'y), teksty, opisy i fabułę. Dla każdej pozycji ze statusem '
                      'requested utwórz plik pod jej path, zgodnie z prompt, size i style, a potem ustaw status done albo error '
                      'z krótkim powodem w note. Grafikę generuj modelem graficznym (narzędzie generate_image), a nie rysuj jej '
                      'skryptem: to jedyny wyjątek od zakazu subagentów, więc możesz użyć subagenta image-generator. Nie zmieniaj '
                      'kodu ani planu.',
                'en': 'Your role: Content creator. You carry out the approved orders in .sol83/assets.json: graphics '
                      '(illustrations, icons, textures, sprites), texts, descriptions and story. For every item with '
                      'status requested create the file at its path following prompt, size and style, then set status '
                      'done, or error with a short reason in note. Generate images with an image model (the '
                      'generate_image tool) rather than drawing them with a script: that is the only exception to the '
                      'no-subagents rule, so you may use the image-generator subagent. Do not change code or the plan.'},
}
WORK_LINES = {'plan': {'pl': 'Praca w tej turze: plan.', 'en': 'Work in this turn: the plan.'},
              'implement': {'pl': 'Praca w tej turze: zadanie z planu.', 'en': 'Work in this turn: a task from the plan.'},
              'review': {'pl': 'Praca w tej turze: przegląd ostatnich zmian względem zadania.',
                         'en': 'Work in this turn: review of the latest changes against the task.'},
              'content': {'pl': 'Praca w tej turze: zamówione treści z .sol83/assets.json.',
                          'en': 'Work in this turn: the ordered content from .sol83/assets.json.'}}
# For the panel: what each role does and when it gets a turn.
DESCRIPTIONS = {
    'general': {'pl': 'Plan, implementacja i przegląd. Dostaje turę, gdy nikt z rolą szczegółową nie jest dostępny albo gdy ma najdłuższą przerwę. Nie wykonuje zamówionych treści.',
                'en': 'Planning, implementation and review. Gets a turn when no specialist is available or it has waited longest. Does not make ordered content.'},
    'architect': {'pl': 'Plan, architektura, research. Dostaje turę na początku, po nowym zleceniu i przy przebudowie planu.',
                  'en': 'Plan, architecture, research. Gets the turn at the start, after a new request and when the plan is rebuilt.'},
    'implementer': {'pl': 'Zadania z planu. Dostaje turę, gdy plan jest gotowy i kolejna pozycja czeka na wykonanie.',
                    'en': 'Plan tasks. Gets the turn when the plan is ready and the next item waits to be done.'},
    'tester': {'pl': 'Przegląd zmian i testy. Dostaje turę po każdej zmianie w kodzie.', 'en': 'Review of changes and tests. Gets the turn after every code change.'},
    'analyst': {'pl': 'Luki względem zadania, ryzyka, dług. Dostaje turę przeglądu po zmianach.', 'en': 'Gaps against the task, risks, debt. Gets review turns after changes.'},
    'content': {'pl': 'Grafiki, teksty, fabuła z zatwierdzonych zamówień. Dostaje turę, gdy czeka zatwierdzone zamówienie.',
                'en': 'Graphics, texts, story from approved orders. Gets the turn when an approved order is waiting.'},
}


def parse(value) -> tuple:
    """A role list from storage or input; unknown names are dropped, nothing left means general."""
    if not isinstance(value, str) and value is not None:
        value = ','.join(value)
    names = [part.strip() for part in str(value or '').split(',') if part.strip()]
    found = tuple(sorted({name for name in names if name in ROLES}, key=ROLES.index))
    return found or (GENERAL,)


def valid(value) -> bool:
    names = [part.strip() for part in str(value or '').split(',') if part.strip()]
    return all(name in ROLES for name in names)


def serialize(roles) -> str:
    return ','.join(parse(roles))


def of(project: dict, name: str) -> tuple:
    return parse(project.get(f'{name}_role'))


def covers(roles, work: str) -> bool:
    return any(work in COVERS.get(role, set()) for role in parse(roles))


def is_general(roles) -> bool:
    return set(parse(roles)) == {GENERAL}


def specialized(roles: list) -> bool:
    return any(not is_general(role) for role in roles)


def missing(roles: list, enabled: list) -> list:
    """Kinds of work that no switched-on model takes."""
    return [work for work in WORKS if not any(on and covers(role, work) for role, on in zip(roles, enabled))]


def creates_content(roles: list, enabled: list) -> bool:
    """Content work exists only with a content creator on: the others cannot make it."""
    return any(on and CONTENT in parse(role) for role, on in zip(roles, enabled))


def reviewers(names: list, roles: list, enabled: list) -> list:
    """Models whose acceptance ends the project."""
    return [name for name, role, on in zip(names, roles, enabled) if on and covers(role, 'review')]


def prompt(roles, lang: str) -> str:
    return ' '.join(PROMPTS[role][lang if lang in ('pl', 'en') else 'pl'] for role in parse(roles))


def label(roles, lang: str = 'pl'):
    """The roles as a user-facing text; a Msg in Polish so the English version stays available."""
    from .messages import Msg
    parts = [Msg(f'role_{role}') for role in parse(roles)]
    if len(parts) == 1:
        return parts[0]
    return Msg('roles_joined', text=' + '.join(parts), text_en=' + '.join(part.en() for part in parts))
