"""Roles: which kind of work each model takes.

Every turn is planning, implementing or reviewing, and with a content creator on also
making ordered content: graphics, texts, story. A general model does all of it, as
before roles existed. The others take only their part, so an expensive model can be
kept for planning and research while a cheaper one does the rest.
"""
from __future__ import annotations

GENERAL = 'general'
CONTENT = 'content'
ROLES = ('general', 'architect', 'implementer', 'tester', 'analyst', 'content')
WORKS = ('plan', 'implement', 'review')
COVERS = {'general': {*WORKS, CONTENT}, 'architect': {'plan'}, 'implementer': {'implement'},
          'tester': {'review'}, 'analyst': {'review'}, 'content': {CONTENT}}
FALLBACKS = ('general', 'wait')
PROMPTS = {
    'general': 'Twoja rola: Ogólna. Robisz każdy rodzaj pracy, gdy przypada Twoja tura.',
    'architect': ('Twoja rola: Architekt. Zajmujesz się planem: architekturą, podziałem na pozycje i '
                  'budżety, przebudową planu po nowym zleceniu oraz researchem. Nie implementuj zadań z '
                  'planu: zrobi to inny model.'),
    'implementer': ('Twoja rola: Implementujący. Realizujesz zadania z planu, jedno na turę. Plan, jego '
                    'przebudowa i przegląd należą do innych ról.'),
    'tester': ('Twoja rola: Tester. Przeglądasz ostatnie zmiany, uruchamiasz testy, dopisujesz brakujące '
               'testy i plan regresji. Nie budujesz nowych funkcji: drobną usterkę popraw, większą opisz '
               'i dopisz do planu jako dług.'),
    'analyst': ('Twoja rola: Analityk systemowy. Szukasz luk względem zadania i kryteriów odbioru: '
                'brakujących przypadków, ryzyk i niespójności. Plan ich łatania dopisujesz do '
                '.sol83/plan.json jako dług (kind "debt"). Nie implementujesz.'),
    'content': ('Twoja rola: Twórca treści. Realizujesz zamówienia z .sol83/assets.json: grafiki '
                '(ilustracje, ikony, tekstury, sprite\'y), teksty, opisy i fabułę. Dla każdej pozycji ze '
                'statusem requested utwórz plik pod jej path, zgodnie z prompt, size i style, a potem ustaw '
                'status done albo error z krótkim powodem w note. Grafikę generuj modelem graficznym '
                '(narzędzie generate_image), a nie rysuj jej skryptem: to jedyny wyjątek od zakazu '
                'subagentów, więc możesz użyć subagenta image-generator. Nie zmieniaj kodu ani planu.'),
}
WORK_LINES = {'plan': 'Praca w tej turze: plan.', 'implement': 'Praca w tej turze: zadanie z planu.',
              'review': 'Praca w tej turze: przegląd ostatnich zmian względem zadania.',
              'content': 'Praca w tej turze: zamówione treści z .sol83/assets.json.'}


def of(project: dict, name: str) -> str:
    value = project.get(f'{name}_role') or GENERAL
    return value if value in ROLES else GENERAL


def covers(role: str, work: str) -> bool:
    return work in COVERS.get(role, COVERS[GENERAL])


def specialized(roles: list) -> bool:
    return any(role != GENERAL for role in roles)


def missing(roles: list, enabled: list) -> list:
    """Kinds of work that no switched-on model takes."""
    return [work for work in WORKS
            if not any(on and covers(role, work) for role, on in zip(roles, enabled))]


def creates_content(roles: list, enabled: list) -> bool:
    """Content work exists only with a content creator on: the others cannot make images."""
    return any(on and role == CONTENT for role, on in zip(roles, enabled))


def reviewers(names: list, roles: list, enabled: list) -> list:
    """Models whose acceptance ends the project."""
    return [name for name, role, on in zip(names, roles, enabled) if on and covers(role, 'review')]
