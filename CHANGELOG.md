# Changelog

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
