# Changelog

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
