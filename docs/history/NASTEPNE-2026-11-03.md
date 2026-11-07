# Sol-83: następne zmiany

Zadania zlecone przez użytkownika 2 listopada 2026. Stan po wersjach v0.6.1–v0.6.6 (3 listopada 2026).

## Zrobione

| Wersja | Zmiana |
|---|---|
| v0.6.1 | Folder „Uruchamiaj stąd”: `main` projektu Sol-83 idzie za wersją rekomendowaną, a repozytorium użytkownika dostaje `worktrees/<id>-testy`. Sekcja `JAK URUCHOMIĆ:` w odpowiedzi, potem `run` z planu i README. |
| v0.6.2 | Tryb jednego modelu: opcja „Wyłączony”, poziom wersji „Jeden model”, wyłączony model nie musi być zalogowany. |
| v0.6.3 | Role (Ogólna, Architekt, Implementujący, Tester, Analityk systemowy), rodzaj pracy w turze, kontrola pokrycia, zachowanie przy niedostępnej roli. Wybór wykonawcy dla dowolnej liczby modeli, łatka Duet na trzech agentów. |
| v0.6.4 | Koordynator wiadomości do wyboru, domyślnie lokalny `gemma4:31b` przez Ollamę. Sprawdzone na żywo: około 32 s, poprawne rozpoznanie i odpowiedź. |
| v0.6.5 | Gemini jako trzeci model z rolami, przez Antigravity `agy` (Gemini CLI nie jest już wspierane). Rosnąca blokada po wyczerpaniu limitu, bo Antigravity nie podaje limitów. |
| v0.6.6 | „Cofnij przekazanie”, tokeny na turę w Efektywności. Wiadomość czekająca na turę budzi model czekający na przegląd. |
| v0.6.7 | Adapter Antigravity dopasowany do prawdziwego `agy` 1.4.12: tura, wznowienie, tokeny i generowanie obrazu sprawdzone na żywo. |
| v0.6.8 | Gemini w projektach sprzed niego: domyślnie wyłączony, po włączeniu silnik startuje od nowa z trzema modelami. |
| v0.6.9 | Rola Twórca treści, zamówienia w `.sol83/assets.json` i zakładka Treści z miniaturami i zamówieniem z panelu. |

## Zmiana kierunku względem pierwotnego planu

Pierwotny punkt 4 zakładał Gemini tylko do grafiki. Użytkownik doprecyzował 2 listopada: Gemini ma być równoległym modelem obok Claude i Codexa, a nacisk ma iść na role i koordynację trzech modeli. Grafika i inne treści weszły potem jako rola Twórca treści (v0.6.9): zamówienia realizuje model w swojej turze, a nie koordynator poza nią.

## Do zrobienia

- **Błąd wyczerpania limitu Antigravity** nie został jeszcze zaobserwowany. Dziś rozpoznawane są 429, `RESOURCE_EXHAUSTED` i „quota exceeded”. Przy pierwszym prawdziwym wyczerpaniu warto sprawdzić tekst w `runs/<id>/*/turn-*-gemini.stderr.log`.
- **Logowanie Antigravity.** Sesja jest w pęku kluczy macOS, więc panel sprawdza tylko instalację. Brak logowania wychodzi jako błąd logowania w pierwszej turze.
- **Budżet obrazów na projekt** z pierwotnego planu nie powstał. Limit Antigravity chroni rosnąca blokada po błędzie.
- **Regulamin.** Nie sprawdzono, czy regulamin Antigravity pozwala sterować `agy -p` z zewnętrznego narzędzia. Tryb `-p` jest opisany jako przeznaczony do skryptów i CI.

## Lekcja kosztowa z 2 listopada

Największym konsumentem limitu Claude okazała się jedna bardzo długa sesja koordynująca. Każdy krok czyta całą historię, a 95% zużycia przypadało na kontekst powyżej 150 tys. tokenów. Dlatego:
- agenci dostają świeżą sesję co 6 tur, a tokeny na turę w Efektywności pokazują, czy to dobra liczba,
- prace nad Sol-83 najlepiej prowadzić w krótkich sesjach, zaczynając od README i tego pliku.
