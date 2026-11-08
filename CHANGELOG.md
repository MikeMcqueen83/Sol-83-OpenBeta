# Changelog

## OpenBeta 0.7.4 — 2026-11-08

Oszczędność limitów i przepływ przy awariach (audyt PR9 i PR15, `docs/AUDYT-TOKENY-2026-11-08.md`).

- Nowa sesja agenta w każdej turze (`GEMINI_ROTATE_AFTER`, domyślnie 1): kontekst niesie pakiet przekazania (zadanie, plan, zmiany od ostatniej tury modelu, skrócone do 4000 znaków) zamiast całej historii. Wcześniej wznawiana sesja czytała historię przy każdym kroku: w PR9 szósta tura sesji Gemini kosztowała 2,6 raza tyle co pierwsza.
- Zasada oszczędnej pracy dla modeli: plik w całości zamiast wielu edycji, testy i budowanie raz na koniec tury, krótkie wyjście poleceń, notatki z wyszukiwania w pliku.
- Rodzaj projektu (wykrywany z zadania albo wybrany): przy dokumencie i researchu modele nie budują zaplecza (testów, linterów, skryptów) i sprawdzają treść oraz źródła.
- Awarie: kolejna próba modelu po nieudanej turze zaczyna nową sesję; błędy liczone osobno dla każdego modelu, z rosnącą przerwą (10, 20, 40… min, do 2 h) i komunikatem po trzech z rzędu; model, który zaakceptował bieżący kod, nie dostaje pustej tury ani wymuszonego przejęcia (PR9: sześć utraconych przeglądów Gemini i pięć pustych tur Claude).

## OpenBeta 0.7.3 — 2026-11-08

- Rzadszy przegląd zmian: drugi model przegląda pracę, gdy zamknie się etap planu (funkcja, której zadania są gotowe), przy dużej zmianie (od 500 linii), przy deklaracji gotowości albo gdy nie ma poprawnego planu, a najpóźniej co 3 tury implementacji (`SOL83_REVIEW_EVERY`). Wcześniej przegląd był po każdej turze: połowa tur w PR9, 76% tokenów w PR14. Ustawienie projektu „Po każdej zmianie” przywraca dawny rytm.

## OpenBeta 0.7.2 — 2026-11-08

Po zgłoszeniu dotyczącym PR13/PR14 i audycie zużycia tokenów (`docs/AUDYT-TOKENY-2026-11-08.md`).

- RUN: komentarze w instrukcjach nie trafiają już jako argumenty (PR14: `build.py '#' writes ...` kończył się od razu błędem); prozatorskie „Open dist/x.html…” nie jest odrzucane jako program.
- RUN dla dokumentów: budowanie do końca, potem folder wersji serwowany na osobnym porcie i link do pliku HTML; stan ostatniego RUN z końcówką logu w karcie „Do testów”.
- Polecenia do terminala: gotowa sekwencja `cd` + polecenia bez komentarzy; lokalny koordynator przepisuje ją w tle, a wynik jest sprawdzany linia po linii.
- Daty przy odnowieniu limitu i końcu przerwy (dzień tygodnia, data, godzina; odliczanie w dniach i godzinach).
- Prośby o testy: domyślnie tylko przy wersji końcowej (ustawienie projektu: końcowa / każda wersja / wcale); modele nie zlecają testów, budowania ani skryptów, a w dokumentach i researchu nie proszą o testy w trakcie pracy.
- Ustawienie projektu „Claude może czytać strony WWW (WebFetch)”; modele nie pytają o dostęp do narzędzi w pytaniach do użytkownika.
- Reguła „modele oceniły kroki jako nieprzybliżające” i sygnał efektywności pomijają ocenę własnego kroku (PR9 zatrzymał się na czterech samoocenach Codexa).

## OpenBeta 0.7.1 — 2026-11-08

Poprawki po zgłoszeniu z 8 listopada (projekty PR10, PR11, PR13, PR14). Szczegóły i dowody: `docs/TRACEABILITY.md`, sekcja „Etap 9”.

- Oczekiwanie na limit: odrzucenie przez Claude niesie godzinę resetu podaną przez dostawcę (`resetsAt`), a nie zgadywane +30 min (8.11: blokada do 03:29 przy resecie o 03:00). Godzina z `claude /usage` (z dokładnością do minuty, zaokrąglona w dół) dostaje minutę zapasu.
- Każda przerwa ma źródło: odczyt, komunikat dostawcy, szacunek, awaria, logowanie. Szacunek jest w panelu oznaczony „(szacunek)”.
- Krótsze i jawne przerwy: limit bez godziny resetu 15 min, podwajane do 2 h (było 30 min do 8 h); chwilowa awaria (rate limit, sieć, przeciążenie) 5 min; inny błąd 10 min; logowanie 60 min.
- „Spróbuj teraz”: zdejmuje przerwę Sol-83 dla dostawcy i budzi czekające projekty, które od razu czytają limity na nowo (panel limitów i belka projektu).
- Komunikat oczekiwania mówi prawdę: który model, dlaczego, do kiedy i czy to szacunek (np. „Pracę „plan” może wykonać tylko Claude, a teraz nie może: Claude: limit 5h 100%, do 03:00. Gemini: nie ma roli do pracy „plan”.”). Czekanie na przegląd pokazuje recenzenta, który wróci najwcześniej, a nie pierwszego w kolejności.
- Lista projektów: sekcja „W toku” z jednoznacznym stanem (słowo i ikona) i powodem oczekiwania, pod nią zwinięte grupy „Wymaga uwagi”, „Zatrzymane”, „Ukończone” z licznikami; rozwinięcie zapamiętane w przeglądarce.
- Pytania i testy: wynik testu dla nowszej wersji rozstrzyga test zapisany przy starszej (wcześniej uznawany za „spóźniony”, przez co rekord zostawał otwarty, a powiadomienie wracało); odpowiedziane trafiają do „Zrobione” z informacją, czy modele już je dostały; zmiana odpowiedzi zastępuje notatkę czekającą w kolejce; „Działa” w karcie wersji nie dubluje wyniku. Naprawa przy starcie poprawia rekordy zostawione przez starą regułę i wycofuje zdublowane notatki.

## OpenBeta 0.7.0 — 2026-11-07

Przebudowa według specyfikacji z 7 listopada 2026 i audytu z 3 listopada 2026. Szczegóły: `docs/TRACEABILITY.md`, `docs/AUDIT-2026-11-07.md`.

- Bezpieczeństwo: piaskownica systemu dla testów, `.gemini-setup` (po akceptacji treści), procesu Antigravity i RUN; skan sekretów każdej wysyłki; maskowanie sekretów; brak kluczy API u agentów; usunięte stare polecenia CLI.
- Dane oddzielone od kodu (`~/Sol-83-data`, `SOL83_HOME`), `sol83 migrate`, `sol83 doctor`.
- Trwała kolejka zleceń, atomowe zamykanie, praca z przerwanych tur wraca do kolejki; scalające zapisy stanu projektu.
- Kontrakt planu (PL/EN), rewizje ostatniego poprawnego planu, ograniczona naprawa; postęp netto i bramki odbioru.
- Panel kont i logowania, klasy błędów, reset podany przez dostawcę; znormalizowane tokeny (przyrosty sesji, poprawka odczytu Codex), udział w oknach limitów.
- Auto — ekonomiczny / power, katalog modeli ze źródłami, najwyższe modele tylko ręcznie z potwierdzeniem.
- Kilka ról na model; pytania, decyzje i testy ręczne; zamówienia treści z akceptacją; stały język projektu; klucze PRn/rr.
- RUN z kontrolowanym runnerem; widok wersji; Git w kontekście projektu; licencja projektu.
- Interfejs: belka akcji, Activity z turami, Pytania i testy, usunięta zakładka Live, skórki LIGHT/DARK/SAKURA/TERMINAL, przesuwany panel boczny.

## 0.6.x — 2026-11-02/03

Wersje sprzed OpenBeta (repozytorium MikeMcqueen83/Sol-83). Opis: `docs/history/`.
