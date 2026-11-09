# Raport końcowy: Sol-83 OpenBeta, 7 listopada 2026

Zakres: specyfikacja `docs/SPEC-2026-11-07.md` (22 punkty) i audyt z 3 listopada 2026. Szczegółowa mapa wymaganie → implementacja → test → wynik → ograniczenia: [TRACEABILITY.md](TRACEABILITY.md). Weryfikacja audytu: [AUDIT-2026-11-07.md](AUDIT-2026-11-07.md).

Repozytorium: prywatne `MikeMcqueen83/Sol-83-OpenBeta`. Widoczności nie zmieniano. Repozytorium `MikeMcqueen83/Sol-83` nie było ruszane.

## 1. Zrealizowane wymagania i miejsce w aplikacji

Żaden punkt nie jest oznaczony jako „zrobione” tylko dlatego, że działa interfejs. „Częściowo” znaczy, że opisana część działa w pełnym przepływie z testami, a reszta jest wymieniona w kolumnie ograniczeń w mapie.

| Punkt | Wynik | Gdzie w aplikacji |
|---|---|---|
| Audyt i poprawki krytyczne | zrobione (macOS) | piaskownica dla testów, `.gemini-setup`, Antigravity i RUN; skan sekretów; `sol83 doctor` |
| 1 Kolejka i zamykanie | częściowo | Przebieg, wiadomości, stan projektu; zamknięcie atomowe |
| 2 Zmiana modeli w trakcie | częściowo | Ustawienia: migawka bieżącej tury obok ustawień następnej |
| 3 Plan | zrobione | zakładka Plan, rewizje, komunikaty w Przebiegu |
| 4 Logowanie i dostępność | częściowo | panel boczny „Konta i logowanie”, „Sprawdź połączenie” |
| 5 Tokeny i limity | częściowo | Efektywność: zużycie według modelu, udział w oknach |
| 6 Auto | częściowo | Ustawienia: tryb wyboru, ostrzeżenie przy modelu najwyższym |
| 7 Role | częściowo | Ustawienia: wiele ról z opisami |
| 8 Zamówienia treści | częściowo | Treści: propozycje, decyzje, presety rozmiaru |
| 9 Język projektu | częściowo | nagłówek projektu (PL/EN), Ustawienia: wybór dla nieustalonych |
| 10 Panel projektów | częściowo | karty z kluczem PRn/rr, wersją, RUN, opisem, statusem, postępem; zmiana nazwy |
| 11 RUN | częściowo | belka akcji i Wersje: RUN, stop, adres, log |
| 12 Postęp netto | częściowo | nagłówek projektu i Plan |
| 13 Interfejs | częściowo | belka akcji, Activity z turami, Pytania i testy, bez Live |
| 14 Versions | częściowo | Wersje: testy, folder lub tag, Finder, kopiowanie ścieżki |
| 15 Licencja projektu | częściowo | Ustawienia: licencja |
| 16 Licencja Sol-83 | częściowo (projekt prawny) | `LICENSE.md`, `THIRD_PARTY_NOTICES.md`, `CONTRIBUTING.md` |
| 17 Dokumentacja | częściowo | README PL/EN, `docs/pl`, `docs/en`, instalacja krok po kroku od zera |
| 18 Skórki | częściowo | wybór w panelu bocznym: LIGHT, DARK, SAKURA, TERMINAL |
| 19 Weryfikacja i odbiór | ten raport | |
| 20 Katalog modeli | częściowo | opisy modeli w Ustawieniach, API katalogu |
| 21 Pytania i testy | częściowo | zakładka Pytania i testy, licznik w belce i na karcie projektu |
| 22 Git projektu | częściowo | Ustawienia: Git projektu, „Wyślij gałąź” |

## 2. Wyniki testów

**Atrapy CLI (bez abonamentów), macOS 26, Python 3.14:** pełny zestaw `python3 -m unittest discover -s tests`. Wynik dla ostatniego commita jest w sekcji 6. Testy uruchamiają prawdziwy silnik Duet i koordynatora na skryptowanych CLI, które mówią formatem prawdziwych narzędzi.

**Prawdziwe mechanizmy systemu (bez modeli):** piaskownica Seatbelt (zapis poza projektem zablokowany, odczyt `~/.ssh` zablokowany, sieć zablokowana, maskowanie), RUN z prawdziwym serwerem HTTP w piaskownicy, Git na tymczasowych repozytoriach z lokalnym bare remote, migracja na kopii prawdziwych danych (9 projektów, 823 zdarzenia, 49 wersji, 14 worktree z tym samym HEAD i stanem).

**Na żywo (prawdziwe CLI i konta), oszczędnie:**

| Co | Wynik | Zużycie |
|---|---|---|
| `agy models` w piaskownicy | lista modeli konta | bez wywołania modelu |
| `claude auth status`, `codex login status`, `codex app-server account/read` i `model/list` | konto, abonament, lista modeli | bez wywołania modelu |
| jedna tura `agy` (gemini-3.8-flash-low) w piaskownicy | plik utworzony w projekcie, poprawna odpowiedź | ok. 16 tys. tokenów wejścia |
| panel na kopii danych w przeglądarce (port 8766, offline) | wszystkie zakładki bez błędów, PL/EN, 4 skórki, przesuwany panel | bez wywołań modeli |

Nie wykonano na żywo: pełnej tury Claude ani Codex po zmianach (limit tygodniowy Codex był w chwili testu wyczerpany do 9 listopada), wyczerpania limitu abonamentu, agenta aktualizacji katalogu, planu RUN z lokalnego LLM, PR przez GitHub, testów na Linuksie.

## 3. Migracja, kopie i powrót

Opis przełączenia i stan po nim: sekcja 6.

**Kopia sprzed jakichkolwiek zmian:** `~/Sol-83-backups/2026-11-07-przed-OpenBeta/`. Zawiera: `data/state` (baza przez kopię SQLite), `data/config`, `data/projects`, `data/runs`, `data/demo`, `data/reports` (pełne kopie), `data/worktrees` (29 GB, klon APFS: chroni przed błędami programu, nie przed awarią dysku), `code-ProjectGemini.bundle` (cała historia starego repozytorium), `vendor/` (Duet z łatką) i `docs/SPEC-2026-11-07.md`.

**Powrót do starej wersji:**
1. Zatrzymaj nowy panel: `pkill -f "sol83 serve"`.
2. Przywróć stary folder z Kosza na miejsce: `/Users/evvil/AplikacjeLokalne/ProjectGemini` (Finder → Kosz → „Odłóż”).
3. Uruchom stary panel z jego folderu: `cd /Users/evvil/AplikacjeLokalne/ProjectGemini && ./sol83 serve`. Używa on własnych danych, a nie `~/Sol-83-data`.
4. Jeśli stary folder nie jest dostępny, odtwórz go z kopii: `git clone ~/Sol-83-backups/2026-11-07-przed-OpenBeta/code-ProjectGemini.bundle ProjectGemini`, a potem skopiuj do niego `data/*` (`cp -cRp`) oraz `vendor`.

Uwaga: worktree, które po migracji wskazują nowe repozytoria, są kopiami. Stary folder ma własne, niezmienione powiązania.

## 4. Ograniczenia i decyzje użytkownika

Decyzje do podjęcia:
1. **Licencja Sol-83**: projekt `LICENSE.md` wymaga weryfikacji prawnej i decyzji: definicja użycia komercyjnego, kanał zgody, zasady wkładu (CLA/DCO), licencja łatki Duet. Do tego czasu obowiązuje zasada „wszelkie prawa zastrzeżone”.
2. **Publikacja**: repozytorium jest prywatne. Zmiana na publiczne to Twoja decyzja, a ochronę gałęzi opisuje `docs/BRANCH_PROTECTION.md`. Uwaga: w historii repozytorium są sztuczne, nieważne tokeny z testów skanera sekretów. Po upublicznieniu skaner GitHub może je zgłosić.
3. **Regulamin dostawców**: sterowanie `agy -p`, `claude -p` i `codex exec` z zewnętrznego narzędzia oraz rotacja abonamentów nie zostały sprawdzone pod kątem warunków usług.
4. **Klasyfikacja Antigravity**: wszystkie warianty Gemini 4 Argon są oznaczone jako najwyższe (tylko ręcznie), bo hierarchii nie da się ustalić ze źródeł dostawcy. Możesz to zmienić decyzją w katalogu.
5. **Projekty z językiem `unknown`**: wybierz język raz w Ustawieniach projektu.

Najważniejsze ograniczenia techniczne (pełna lista w mapie):
- Brak testów UI w przeglądarce w zestawie automatycznym; panel sprawdzony ręcznie na kopii danych.
- Praca lokalnego koordynatora (LLM) nie jest liczona osobno w metrykach.
- Intencja Git z uwagi użytkownika nie jest jeszcze wykonywana automatycznie: wysyłka działa z zapisanym kontekstem i przyciskiem „Wyślij gałąź”.
- Licencji nie da się wybrać w formularzu nowego projektu, tylko w Ustawieniach.
- Piaskownica pozwala czytać pliki spoza chronionych folderów; Linux nietestowany.
- Koordynator nie sprawdza semantycznie, czy odpowiedź na pytanie agenta jest już w załącznikach; wykrywa tylko identyczne pytania.

## 5. Uruchomienie i checklista odbioru

Uruchomienie: `cd /Users/evvil/AplikacjeLokalne/Sol-83-OpenBeta && ./sol83 serve`, a potem http://127.0.0.1:8765. Dane: `~/Sol-83-data`.

Checklista odbioru:
- [ ] Panel otwiera się na 8765; widać 9 przeniesionych projektów z kluczami PR1/26…PR9/26.
- [ ] Otwórz dowolny projekt: Przebieg (tury z nagłówkami), Plan (postęp netto), Wersje (testy, folder lub tag), Efektywność (tokeny, okna).
- [ ] Panel boczny: „Konta i logowanie” → „Sprawdź połączenie” pokazuje konta Claude i Codex.
- [ ] Bezpieczeństwo: piaskownica „sandbox-exec”.
- [ ] Ustawienia projektu: tryb Auto, wiele ról, język, licencja, Git projektu; wybór GPT-6-Astra wymaga potwierdzenia.
- [ ] Nowy mały projekt testowy z poleceniem testów: przechodzi do wersji, „Co sprawdzić” pojawia się w Pytaniach i testach.
- [ ] RUN wersji projektu webowego: adres działa, „Zatrzymaj RUN” zatrzymuje.
- [ ] Przełącz PL/EN i skórki; przeciągnij krawędź panelu bocznego.

## 6. Przełączenie instancji i wynik testów końcowych

**Testy końcowe:** `python3 -m unittest discover -s tests` na commicie `ea28c6f` (kod przełączanej wersji; późniejsze commity zmieniają dokumentację, licencję i rozpoznawanie silników w migracji z osobnym testem): **253 testy, OK**, 510 s, macOS 26, Python 3.14, atrapy CLI.

**Przełączenie, 7 listopada 2026, na polecenie użytkownika:**
1. Silniki starej instancji: brak działających.
2. Migawka bazy w chwili przełączenia: `~/Sol-83-backups/2026-11-07-przed-OpenBeta/data/state/gemini-at-switch.db`.
3. `./sol83 migrate --from /Users/evvil/AplikacjeLokalne/ProjectGemini` → `~/Sol-83-data`: 9/9 projektów, 823/823 zdarzeń, 49/49 wersji, 11/11 zleceń, 13/13 pytań, 14 worktree z tym samym HEAD, 63 pola ścieżek w bazie i 36 plików JSON przepisane, brak starych ścieżek w bazie; raport w `~/Sol-83-data/MIGRATION.json`. Migracja zatrzymała się raz na fałszywym alarmie (własne polecenie powłoki uznane za silnik); poprawione i przetestowane.
4. Stary serwer zatrzymany (`pkill -f "sol83 serve"`), nowy uruchomiony na 8765 z czystym środowiskiem (bez zmiennych sesji Claude Code), odłączony od sesji, log: `~/Sol-83-data/state/server.log`.
5. Sprawdzenie: API zwraca 9 projektów z kluczami PR1/26…PR9/26 i pełnymi szczegółami; panel w przeglądarce bez błędów konsoli; `sol83 doctor` same `[ok]`; piaskownica sandbox-exec.
6. Stary folder `/Users/evvil/AplikacjeLokalne/ProjectGemini` przeniesiony do Kosza (nie usunięty), jako ostatni krok.

Projekty po przełączeniu: 9 projektów, PR1/26–PR9/26 (PR1 zatrzymany z 30 wersjami, PR9 wymaga uwagi). Język odczytany z treści zadań (PR2 i PR5: EN). Projekty, które już pracowały, mają język ustalony na stałe; jeśli PR2 lub PR5 ma pracować po polsku, to jest decyzja do podjęcia (zmiana wymaga ręcznej korekty w bazie albo nowego projektu).
