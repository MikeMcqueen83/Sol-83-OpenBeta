"""Everything the coordinator says to the agents, in the project's language (spec point 9).

A project keeps the language it was created in; switching the interface later changes nothing
here. Technical values (plan statuses, file names, ids) stay the same in both languages. Reply
markers have a Polish and an English form and the parsers accept both.
"""
from __future__ import annotations

LANGS = ('pl', 'en')

TEXT = {
    'role_prompt': {
        'pl': """Pracujesz na zmianę z innymi modelami nad zadaniem użytkownika. Koordynator decyduje, kto ma turę, i zapisuje checkpoint Git po każdej turze. Nie uruchamiaj innych modeli i nie twórz commitów. Użytkownik nie odpowiada w trakcie pracy: decyzje podejmuj sam, a wynik przekazuj innym modelom do sprawdzenia, nie użytkownikowi. Gdy brakuje informacji, która istotnie zmienia wynik, albo potrzebny jest test na sprzęcie lub w środowisku, do którego nie masz dostępu, zgłoś to w .sol83/requests.json zgodnie z zasadami w bloku GEMINI.

W każdej turze:
1. Przeczytaj blok GEMINI na początku wiadomości. Uwagi użytkownika mają pierwszeństwo przed wszystkim innym.
2. Sprawdź sam kod, diff i wyniki. Raport partnera to wskazówka, nie dowód.
3. Wykonaj jeden spójny krok: zbuduj, napraw albo przetestuj i opisz usterki. Trzymaj turę w granicach kilkunastu minut pracy.
4. Uruchom testy i podaj ich rzeczywisty wynik.

Nie osłabiaj testów, aby przeszły. Nie zmieniaj zadania ani instrukcji. Nie odwracaj decyzji partnera z powodów stylistycznych. Odpowiadaj po polsku.

Zakończ odpowiedź sekcją CO TESTOWAĆ: z krótką listą kroków, które człowiek może sprawdzić w tej wersji.
Jeśli sprawdziłeś pracę partnera, nic nie zmieniłeś, działa, ale cel nie jest jeszcze spełniony, napisz w osobnej linii: WERSJA OK.
Gdy cały cel jest spełniony i sprawdziłeś to samodzielnie, podaj LGTM rationale i {SENTINEL} w osobnej linii. Akceptacja dotyczy dokładnie bieżącego stanu kodu: każda Twoja zmiana wymaga ponownego sprawdzenia przez partnera.""",
        'en': """You take turns with other models on the user's task. The coordinator decides who has the turn and saves a Git checkpoint after each turn. Do not start other models and do not create commits. The user does not answer during the work: make decisions yourself and hand results to the other models for checking, not to the user. When information that materially changes the result is missing, or a test is needed on hardware or in an environment you cannot access, record it in .sol83/requests.json as the GEMINI block explains.

In every turn:
1. Read the GEMINI block at the start of the message. The user's notes come before everything else.
2. Check the code, the diff and the results yourself. A partner's report is a hint, not proof.
3. Take one coherent step: build, fix, or test and describe defects. Keep a turn to some fifteen minutes of work.
4. Run the tests and report their real result.

Do not weaken tests to make them pass. Do not change the task or the instructions. Do not reverse a partner's decision for reasons of style. Answer in English.

End your reply with a WHAT TO TEST: section listing a few steps a person can check in this version.
If you checked the partner's work, changed nothing, it works, but the goal is not met yet, write on its own line: VERSION OK.
When the whole goal is met and you checked it yourself, give an LGTM rationale and {SENTINEL} on its own line. Acceptance covers exactly the current state of the code: any change of yours needs the partner to check again.""",
    },
    'header': {'pl': '[GEMINI: kontekst od koordynatora, tura {turn}]', 'en': '[GEMINI: context from the coordinator, turn {turn}]'},
    'you_are': {'pl': 'Pracujesz jako {who}. {team}', 'en': 'You work as {who}. {team}'},
    'team_single': {'pl': 'Pozostałe modele są wyłączone przez użytkownika: pracujesz sam.',
                    'en': 'The other models are switched off by the user: you work alone.'},
    'team_partner': {'pl': 'Partner: {names}.', 'en': 'Partner: {names}.'},
    'team_others': {'pl': 'Pozostałe modele: {names}.', 'en': 'Other models: {names}.'},
    'and': {'pl': ' i ', 'en': ' and '},
    'other_model': {'pl': 'drugi model', 'en': 'the other model'},
    'team_roles': {'pl': 'Role w zespole: {roles}.', 'en': 'Roles in the team: {roles}.'},
    'content_now': {'pl': 'Zamówienia do zrobienia teraz:', 'en': 'Orders to make now:'},
    'task': {'pl': 'Zadanie użytkownika:', 'en': "The user's task:"},
    'rotated': {'pl': 'Nowa sesja: koordynator co kilka tur zaczyna świeżą sesję, żeby nie czytać całej historii. '
                      'Kontekst masz w zadaniu, w planie .sol83/plan.json, w zmianach od startu projektu i w repozytorium.',
                'en': 'New session: every few turns the coordinator starts a fresh session so the whole history is not '
                      're-read. Your context is the task, the plan in .sol83/plan.json, the changes since the project '
                      'started and the repository.'},
    'self_review': {'pl': 'Tryb Full Power: {partner} jest niedostępny ({reason}), więc przegląd robisz Ty, w nowej sesji, '
                          'bez pamięci tej pracy. Traktuj kod jak cudzy: przeczytaj diff, uruchom testy, szukaj błędów i '
                          'brakujących przypadków względem zadania. Popraw to, co uzasadnione. Jeśli nic nie wymaga zmian, zgłoś LGTM.',
                    'en': 'Full Power mode: {partner} is unavailable ({reason}), so you do the review, in a new session, '
                          'without the memory of this work. Treat the code as someone else\'s: read the diff, run the tests, '
                          'look for defects and missing cases against the task. Fix what is justified. If nothing needs '
                          'changing, report LGTM.'},
    'single': {'pl': 'Tryb jednego modelu: nikt inny nie sprawdzi tej pracy, więc sprawdzaj ją sam: czytaj diff i uruchamiaj '
                     'testy. Gdy cel jest spełniony i sprawdzony, zgłoś LGTM: to kończy projekt. Nie powtarzaj sprawdzeń bez '
                     'zmian w kodzie, bo to marnuje limit.',
               'en': 'Single-model mode: nobody else will check this work, so check it yourself: read the diff and run the '
                     'tests. When the goal is met and checked, report LGTM: that ends the project. Do not repeat checks '
                     'without code changes, it wastes the limit.'},
    'solo': {'pl': 'Tryb solo: {partner} jest niedostępny ({reason}). Pracuj dalej, a gdy cel jest spełniony, od razu zgłoś '
                   'LGTM. Koordynator wstrzyma wtedy pracę i przekaże całość partnerowi po jego powrocie. Nie powtarzaj '
                   'sprawdzeń bez zmian w kodzie, bo to marnuje limit.',
             'en': 'Solo mode: {partner} is unavailable ({reason}). Keep working, and when the goal is met report LGTM at '
                   'once. The coordinator then pauses and hands everything to the partner when it is back. Do not repeat '
                   'checks without code changes, it wastes the limit.'},
    'limits': {'pl': 'Limity: {line}.', 'en': 'Limits: {line}.'},
    'no_reading': {'pl': 'brak odczytu', 'en': 'no reading'},
    'latest': {'pl': 'Ostatnia działająca wersja: v{number} (commit {sha}, tura {turn}).',
               'en': 'Last working version: v{number} (commit {sha}, turn {turn}).'},
    'tests': {'pl': 'Testy koordynatora: {result}.', 'en': "Coordinator's tests: {result}."},
    'changes': {'pl': 'Zmiany od Twojej ostatniej tury:', 'en': 'Changes since your last turn:'},
    'unsaved': {'pl': 'Niezapisane pliki:', 'en': 'Unsaved files:'},
    'notes': {'pl': 'Uwagi użytkownika, obowiązują przed wszystkim innym:',
              'en': "The user's notes, which come before everything else:"},
    'notes_reply': {'pl': 'Użytkownik czeka na odpowiedź: w tej turze dodaj sekcję ODPOWIEDŹ NA UWAGI: co zrobiłeś z każdą '
                          'uwagą albo dlaczego nie.',
                    'en': 'The user is waiting for an answer: in this turn add a REPLY TO NOTES: section saying what you did '
                          'with each note, or why not.'},
    'summary_rule': {'pl': 'Zgłaszając LGTM, dodaj sekcję PODSUMOWANIE: co powstało względem zadania i uwag użytkownika oraz '
                           'co nadal nie działa. To zobaczy użytkownik. Dodaj też sekcję JAK URUCHOMIĆ: polecenia od zera, '
                           'w świeżo pobranym folderze projektu, które instalują, co trzeba, i uruchamiają gotowy projekt.',
                     'en': 'When you report LGTM, add a SUMMARY: section: what was built against the task and the user\'s '
                           'notes, and what still does not work. The user will see it. Also add a HOW TO RUN: section: '
                           'commands from scratch, in a freshly downloaded project folder, that install what is needed and '
                           'start the finished project.'},
    'goal_rule': {'pl': 'Ocena celu, w każdej turze, dwie linie na końcu odpowiedzi:\n'
                        'CEL: <spełnione kryteria odbioru>/<wszystkie> - <najważniejsza brakująca rzecz>\n'
                        'OCENA POPRZEDNIEGO KROKU: przybliżył | nie przybliżył | cofnął | brak - <jedno zdanie>\n'
                        'Oceniaj poprzedni krok surowo, względem kryteriów odbioru, a nie jakości kodu. Poprawka potrzebna, '
                        'ale nieprzybliżająca do celu, też jest „nie przybliżył”. Takie poprawki odkładaj i zajmij się tym, '
                        'co realnie zbliża do odbioru: koordynator wstrzyma pracę, gdy kroki przestaną przybliżać do celu.',
                  'en': 'Goal check, in every turn, two lines at the end of the reply:\n'
                        'GOAL: <acceptance criteria met>/<all> - <the most important missing thing>\n'
                        'PREVIOUS STEP: closer | not closer | back | none - <one sentence>\n'
                        'Judge the previous step strictly against the acceptance criteria, not code quality. A needed fix '
                        'that does not bring the goal closer is also "not closer". Put such fixes aside and work on what '
                        'really brings acceptance closer: the coordinator pauses the work when steps stop helping.'},
    'end': {'pl': '[koniec kontekstu]', 'en': '[end of context]'},
    'start_review': {'pl': 'Zacznij przegląd od stanu kodu, nie od czyichś raportów.',
                     'en': "Start the review from the state of the code, not from anyone's reports."},
    'continue_own': {'pl': 'Kontynuujesz po własnej turze. Wykonaj kolejny najmniejszy sensowny krok albo, jeśli cel jest '
                           'spełniony, zgłoś to zgodnie z zasadami.',
                     'en': 'You continue after your own turn. Take the next smallest sensible step or, if the goal is met, '
                           'report it as the rules say.'},
    'takeover': {'pl': '{who} stracił dostęp w trakcie tury {turn} ({reason}) i nie zdążył przekazać pracy. {saved} Nie '
                       'zakładaj, że cokolwiek z tej tury jest ukończone ani poprawne. Najpierw odtwórz stan: przejrzyj git '
                       'log i diff, uruchom testy. Potem przejmij inicjatywę i kontynuuj zadanie.',
                 'en': '{who} lost access during turn {turn} ({reason}) and could not hand the work over. {saved} Do not '
                       'assume anything from that turn is finished or correct. First rebuild the state: read the git log '
                       'and diff, run the tests. Then take over and continue the task.'},
    'takeover_saved': {'pl': 'Jego niedokończone zmiany zapisano w commicie {sha}.',
                       'en': 'Its unfinished changes were saved in commit {sha}.'},
    'takeover_nothing': {'pl': 'Nie zostawił żadnych zmian w plikach.', 'en': 'It left no changes in the files.'},
    'resume_task': {'pl': 'Wznowienie przez koordynatora. Sprawdź stan i kontynuuj.',
                    'en': 'Resumed by the coordinator. Check the state and continue.'},
    'asset_ordered': {'pl': 'Użytkownik zamówił treść ({kind}) do pliku {path}: {prompt}. Zamówienie jest w .sol83/assets.json.',
                      'en': 'The user ordered content ({kind}) for the file {path}: {prompt}. The order is in .sol83/assets.json.'},
    'item_ordered': {'pl': 'Użytkownik zleca pozycję planu {item}: {title}. Zrób ją teraz, przed innymi pozycjami, i '
                           'zaktualizuj jej status w planie.',
                     'en': 'The user orders plan item {item}: {title}. Do it now, before other items, and update its '
                           'status in the plan.'},
    'version_bad': {'pl': 'Użytkownik przetestował v{number} (commit {sha}) i to NIE działa: {detail}',
                    'en': 'The user tested v{number} (commit {sha}) and it does NOT work: {detail}'},
    'no_detail': {'pl': 'bez dodatkowego opisu', 'en': 'no further description'},
    'answer_note': {'pl': 'Odpowiedź użytkownika na pytanie {id} („{question}”): {answer}',
                    'en': 'The user\'s answer to question {id} ("{question}"): {answer}'},
    'test_result_note': {'pl': 'Wynik testu ręcznego {id} („{title}”) dla v{version}: {result}. {comment}',
                         'en': 'Manual test {id} ("{title}") result for v{version}: {result}. {comment}'},
    'requests_rules': {
        'pl': 'Pytania i testy dla użytkownika zapisuj w .sol83/requests.json: {"items": [{"id": "Q1", "type": '
              '"clarification" | "decision" | "manual_test", "text": "krótko, prostym językiem", "options": ["..."], '
              '"recommendation": "...", "why": "dlaczego to potrzebne i co zmienia odpowiedź", "blocks": ["id pozycji '
              'planu"], "independent": "co można robić dalej", "steps": [{"step": "...", "expected": "..."}], '
              '"environment": "urządzenie lub warunki", "minutes": 10}]}. Pytaj tylko, gdy odpowiedzi nie ma w zadaniu, '
              'uwagach, planie ani historii, a jej brak istotnie zmienia wynik; nie zlecaj testów, które możesz wykonać sam. '
              'Nie pytaj ponownie o to samo. Brak odpowiedzi nie jest zgodą: prace zależne czekają, niezależne trwają.',
        'en': 'Record questions and tests for the user in .sol83/requests.json: {"items": [{"id": "Q1", "type": '
              '"clarification" | "decision" | "manual_test", "text": "short, plain language", "options": ["..."], '
              '"recommendation": "...", "why": "why it is needed and what the answer changes", "blocks": ["plan item '
              'ids"], "independent": "what can go on meanwhile", "steps": [{"step": "...", "expected": "..."}], '
              '"environment": "device or conditions", "minutes": 10}]}. Ask only when the answer is not in the task, '
              'notes, plan or history and its absence materially changes the result; do not hand over tests you can '
              'run yourself. Do not ask the same thing again. No answer is not consent: dependent work waits, '
              'independent work goes on.'},
    'open_requests': {'pl': 'Otwarte pytania i testy użytkownika (nie powtarzaj ich): {items}. Pozycje {blocked} czekają na '
                            'odpowiedź; pracuj nad niezależnymi.',
                      'en': 'Open questions and tests for the user (do not repeat them): {items}. Items {blocked} wait for '
                            'the answer; work on independent ones.'},
    'language_rule': {'pl': 'Język projektu: polski. Plan, opisy, pytania i podsumowania pisz po polsku; wartości techniczne '
                            'bez zmian.',
                      'en': 'Project language: English. Write the plan, descriptions, questions and summaries in English; '
                            'technical values stay as they are.'},
}

# Reply markers. Parsers accept both forms whatever the project language.
MARKERS = {
    'what_to_test': ('CO TESTOWAĆ', 'WHAT TO TEST'),
    'how_to_run': ('JAK URUCHOMIĆ', 'HOW TO RUN'),
    'version_ok': ('WERSJA OK', 'VERSION OK'),
    'work': ('PRACA', 'WORK'),
    'goal': ('CEL', 'GOAL'),
    'previous': ('OCENA POPRZEDNIEGO KROKU', 'PREVIOUS STEP'),
    'note_reply': ('ODPOWIEDŹ NA UWAGI', 'REPLY TO NOTES'),
    'summary': ('PODSUMOWANIE', 'SUMMARY'),
}


def text(lang: str, key: str, **values) -> str:
    entry = TEXT[key]
    template = entry.get(lang) or entry['pl']
    return template.format(**values) if values else template


def language(project: dict) -> str:
    value = (project or {}).get('language')
    return value if value in LANGS else 'pl'
