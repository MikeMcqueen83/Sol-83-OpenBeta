# Audyt zużycia tokenów i przebiegu PR9/26 (8 listopada 2026)

Źródła: `~/Sol-83-data/state/gemini.db` (tabele `events`, `usage`, `interactions`, `notes`, `app_runs`, `run_plans`), `~/Sol-83-data/runs/*/engine.log` i `app-v*.log`. Tylko odczyt danych. Tokeny to przyrosty na turę z tabeli `usage` (od 7.11, OpenBeta). Starsze projekty (PR1–PR9) mają niepełne liczniki: Codex nie zapisywał wtedy tokenów, a dane Claude przed 7.11 są niepewne. Tokeny Antigravity (Gemini) liczą każdy krok agenta osobno, łącznie z ponownym odczytem kontekstu z pamięci podręcznej. Nie są więc porównywalne 1:1 z Claude i nie przekładają się wprost na procent limitu.

## Gdzie idą tokeny

| Projekt | Razem | Podział |
|---|---|---|
| PR14/26 Handbook M.VI&V.TAP | 9,86 mln | przegląd Gemini 7,46 mln (76%), implementacja Claude 1,35 mln (14%), implementacja Gemini 1,05 mln (11%) |
| PR13/26 Handbook AP2 | 4,44 mln | implementacja Gemini 2,42 mln (55%, jedna tura na początku sesji), Claude: implementacja 0,71, plan 0,57, przegląd 0,57 |
| PR11/26 audyt bezpieczeństwa | 5,18 mln | przegląd Claude 1,91 mln (37%), implementacja Gemini 1,64, plan Gemini 1,42 |

Wnioski:

1. **Przegląd po każdej turze implementacji to największa pozycja.** Przeglądów jest prawie tyle samo co tur implementacji: PR9 37/40, PR14 10/8, PR2 6/6. W PR14 jedna tura przeglądu Gemini kosztuje 0,6–1,26 mln tokenów, a tura pisania rozdziału przez Claude 0,18–0,30 mln. Gemini w trybie agenta wykonuje kilkanaście kroków i za każdym razem czyta cały kontekst od nowa.
2. **Pierwsza tura nowej sesji jest droga.** Gemini czyta wtedy całe repozytorium: PR14 tury 3 i 15 po około 1,05 mln, PR13 tura 6 2,42 mln. Nowa sesja zaczyna się co 6 tur (`GEMINI_ROTATE_AFTER`), po zmianie modelu i po restarcie silnika.
3. **Błąd RUN wywołał zbędną wymianę z modelami.** Instrukcja uruchomienia miała komentarz, więc RUN wywoływał `build.py '#' writes ...`, a skrypt kończył się błędem. Użytkownik zgłosił „nie mogę wykonać” (I13, I14), a modele poświęciły część dwóch tur na wyjaśnianie, że `unittest` kończy się po sekundzie. Naprawione w 0.7.2.
4. **Prośby o testy przy każdej wersji projektu researchowego.** PR14 dostał 6 próśb „Co sprawdzić” w 8 minut. Każda kazała uruchomić testy jednostkowe i budowanie, czyli coś, co modele robią same. Kosztuje to głównie czas użytkownika i notatki zwrotne do modeli. Naprawione: domyślnie jedna prośba przy wersji końcowej, a modele mają zakaz zlecania użytkownikowi testów i budowania.
5. **Zgoda bez skutku.** W PR14 (I10) użytkownik odpowiedział „tak, pozwól czytać strony źródłowe”, ale Sol-83 dawał Claude tylko wyszukiwarkę. Model spróbował WebFetch, dostał odmowę i pisał rozdziały z fragmentów wyników wyszukiwania, oznaczając je [Verify]. To zapowiedź poprawek później. Dodano ustawienie projektu „Claude może czytać strony WWW (WebFetch)”. Modele mają nie pytać o dostęp do narzędzi w pytaniach do użytkownika.
6. **Bez wycieków w oczekiwaniu i ponowieniach.** Czekanie na limit nie wywołuje modeli: odczyty limitów są darmowe, a odrzucona tura PR11 o 02:59 nie zużyła tokenów. Ponowień po chwilowych awariach nie było (0 zdarzeń `retry`). Przejęcia po limicie: 12 we wszystkich projektach, każde z zapisem częściowej pracy. Koordynator wiadomości odpowiadał 9 razy lokalnym modelem (bez abonamentu), 3 razy przez Codex, raz przez Claude.
7. **Drobny błąd diagnozy.** Przejęcie w PR14 (tura 14, limit Claude) ma w danych diagnozę `not_logged_in`. Klasyfikacja przyczyny jest poprawna (`limit`), ale diagnoza czyta cały ogon logu i trafia na słowo „/login”. Nie wpływa na decyzje.

## PR9/26 Sol-83 Terminal

79 tur od 6.11 00:59 do 7.11 00:55: Gemini 41 tur, Codex 38. 8 wersji. Projekt wstrzymany z powodem „modele oceniły 4 kolejnych kroków jako nieprzybliżające do celu”.

Ustalenia:

- **Wstrzymanie było błędem reguły.** Tury 75–79 wykonywał sam Codex, bo Gemini był niedostępny, a każda tura oceniała „poprzedni krok”, czyli własny. Wszystkie cztery oceny negatywne pochodziły od tego samego modelu o własnej pracy. Takich samoocen było też w PR4 (3), PR1 (2) i PR10 (1). **Naprawione:** reguła wstrzymania i sygnał w zakładce Efektywność liczą tylko ocenę kroku innego modelu (`scheduler._steps_not_closer`, `monitor.assess`).
- **Cel mierzony różnymi miarami.** Codex podawał CEL x/6, Gemini x/24…28, a na końcu 29/41. Modele liczą różne listy kryteriów, więc ten wskaźnik nie mówi, czy praca się przybliża. Postęp netto z planu jest stabilniejszy.
- **Pętla długu.** Recenzenci dopisywali dług (D1…D21), a tury 37–56 i 65–79 szły głównie na dług, choć pozycje F7–F8 czekały. Pozycje wracały wielokrotnie: F2.2 przez 6 tur, F6.2 przez 5, a cztery oceny „cofnął” oznaczały odwracanie zmian partnera.
- **Rytm przegląd–implementacja 1:1.** Prawie każda zmiana szła do przeglądu, więc połowa z 79 tur to przeglądy.

## Propozycje zmian w logice dla dużych projektów

| # | Zmiana | Szacowany efekt | Stan |
|---|---|---|---|
| 1 | Samoocena nie liczy się do reguły „nie przybliża” | brak fałszywych wstrzymań przy pracy solo | **zrobione (0.7.2)** |
| 2 | Testy użytkownika domyślnie tylko dla wersji końcowej; zakaz zlecania testów i budowania | mniej przerw i notatek zwrotnych | **zrobione (0.7.2)** |
| 3 | WebFetch jako ustawienie projektu | research na źródłach pierwotnych, mniej poprawek [Verify] | **zrobione (0.7.2)** |
| 4 | Przegląd po zakończeniu pozycji planu albo co 2–3 tury implementacji, zamiast po każdej turze (natychmiast tylko przy nieprzechodzących testach albo dużym diffie) | około 30–45% mniej tur; w PR14 przeglądy to 76% tokenów | propozycja |
| 5 | Cel z planu (pozycje must i kryteria odbioru), a deklaracja modeli tylko jako wskazówka | wiarygodny sygnał postępu | propozycja |
| 6 | Budżet długu: zanim pozycje must są gotowe, dług tylko z kategorii bug/test, które blokują | koniec pętli D1…D21 | propozycja |
| 7 | Przegląd przez Gemini (Antigravity) z niższym wysiłkiem albo limitem kroków; drogie przeglądy przez Claude lub Codex | PR14: przegląd Gemini 3–5 razy droższy niż tura Claude | propozycja |
| 8 | Diagnoza błędu z komunikatu błędu, nie z całego ogona logu | poprawne etykiety w danych | propozycja |
