# Mapa wymagań: specyfikacja z 7 listopada 2026

Mapa wymaganie → implementacja → test → wynik → ograniczenia. Specyfikacja: `docs/SPEC-2026-11-07.md`.

Oznaczenia wyniku:
- **zrobione**: działa cały przepływ (zapis, wykonanie, odtworzenie po restarcie, prezentacja, obsługa błędu) i są testy,
- **częściowo**: działa opisana część, reszta jest w kolumnie ograniczeń,
- **nie zrobione**: brak implementacji.

Testy „atrapa” używają skryptowanych CLI z `tests/fakes` (bez prawdziwych modeli). Testy „na żywo” są opisane osobno w sekcji na końcu. Atrapa nie potwierdza działania u prawdziwego dostawcy.

## Etap 1: audyt i poprawki krytyczne

| Wymaganie | Implementacja | Test | Wynik | Ograniczenia |
|---|---|---|---|---|
| Kod agentów (`.gemini-setup`, testy) tylko w piaskownicy | `gemini_app/sandbox.py`, `gitops.run_setup`, `scheduler._verify`, wrapper dla Dueta | `tests/test_security.py`: `Sandbox`, `SetupScript`, `VerifyWrapper`, `NoSandbox` | zrobione (macOS, prawdziwa piaskownica) | Linux (bubblewrap) tylko testy budowy argumentów, bez uruchomienia na Linuksie. Testy mogą czytać pliki poza listą chronionych katalogów. |
| `.gemini-setup` dopiero po akceptacji treści | `Supervisor.approve_setup`, `setup_view`, zakładka Ustawienia | `SetupScript.test_runs_only_after_approval_of_this_content` | zrobione | Akceptacja dotyczy projektu, nie pojedynczego folderu. |
| Gemini bez `--dangerously-skip-permissions` poza piaskownicą | `bin/gemini`: `command`, `sandboxed_command` | `Portability.test_gemini_skips_permissions_only_inside_the_os_sandbox`; na żywo: `agy models` w piaskownicy | zrobione | Pełna tura `agy` w piaskownicy: patrz sekcja „na żywo”. |
| Wzorce sekretów, skan każdej wysyłki | `gemini_app/secretscan.py`, `github.check_secrets`, potwierdzenie listy w UI | `SecretPatterns`, `PushScan` | zrobione | Wzorce heurystyczne: mogą przeoczyć nietypowy format i dawać fałszywe alarmy. |
| Maskowanie sekretów w logach i panelu | `Store.event`, `sandbox.run` | `EngineEnvironment.test_events_are_redacted`, `Sandbox.test_output_is_redacted` | zrobione | Historyczne zdarzenia sprzed migracji nie są przepisywane. |
| Brak kluczy API u agentów | `Supervisor._engine_env` | `EngineEnvironment.test_api_keys_never_reach_the_agents` | zrobione | |
| Działanie poza macOS | `monitor.notify`, `bin/gemini.with_terminal`, `bin/claude.find_binary`, `github._path` | `Portability` | częściowo | Brak testu na prawdziwym Linuksie. |
| Brak starego CLI obok koordynatora | `sol83`: tylko `serve`, `doctor` | `Portability.test_legacy_commands_are_gone` | zrobione | |
| Błędne liczby w adresach API → 400 | `server.py` | (do dopisania w testach serwera) | częściowo | |

## Wymagania specyfikacji

| Punkt | Wymaganie | Implementacja | Test | Wynik | Ograniczenia |
|---|---|---|---|---|---|
| 0.1 | Kopia danych przed migracją | `~/Sol-83-backups/2026-11-07-przed-OpenBeta` | ręczne porównanie liczby plików | zrobione | worktrees jako klon APFS na tym samym dysku |
| 1 | Kolejka zleceń i kończenie projektu | | | nie zrobione | |
| 2 | Zmiana modeli i ról w trakcie | | | nie zrobione | |
| 3 | Walidacja i naprawa planu | | | nie zrobione | |
| 4 | Logowanie i dostępność agentów | | | nie zrobione | |
| 5 | Tokeny i zużycie abonamentów | | | nie zrobione | |
| 6 | Auto: wybór modelu | | | nie zrobione | |
| 7 | Wiele ról dla modelu | | | nie zrobione | |
| 8 | Zamówienia grafik i tekstów | | | nie zrobione | |
| 9 | Stały język projektu | | | nie zrobione | |
| 10 | Panel, nazwy, klucze PRn/rr | | | nie zrobione | |
| 11 | RUN | | | nie zrobione | |
| 12 | Postęp netto i dług | | | nie zrobione | |
| 13 | Porządek interfejsu | | | nie zrobione | |
| 14 | Versions | | | nie zrobione | |
| 15 | Licencja projektu | | | nie zrobione | |
| 16 | Licencja Sol-83 | | | nie zrobione | |
| 17 | Dokumentacja | | | nie zrobione | |
| 18 | Skórki | | | nie zrobione | |
| 19 | Weryfikacja i odbiór | | | nie zrobione | |
| 20 | Katalog modeli | | | nie zrobione | |
| 21 | Pytania i testy ręczne | | | nie zrobione | |
| 22 | Git w kontekście projektu | | | nie zrobione | |

## Wywołania na żywo (prawdziwe CLI)

| Data | Co | Wynik | Zużycie |
|---|---|---|---|
| 2026-11-07 | `agy models` w piaskownicy Seatbelt | lista modeli konta, kod 0 | bez wywołania modelu |
