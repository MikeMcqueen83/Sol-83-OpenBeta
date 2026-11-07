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

## Etap 3: odkryte i naprawione błędy

- Stan projektu (`meta`) był zapisywany w całości przez serwer i silnik naraz: zapis ze starej kopii gubił zmiany drugiej strony (np. zlecenie przebudowy planu, zamówienie treści). Teraz zapis scala tylko zmienione klucze w jednej transakcji (`Store.save_meta`, `Store.update_meta`); test `MetaMerge`.
- Polecenie przebudowy planu i pozycja zlecona z planu były zdejmowane ze stanu w chwili budowania promptu: gdy tura padła, polecenie przepadało. Teraz wynikają z zleceń w kolejce, które wracają do niej po przerwanej turze.
- Nowe zlecenie dodane w trakcie ostatniej tury zostawało „pending” w zamkniętym projekcie. Teraz zamknięcie i dodanie są szeregowane w jednej transakcji.

## Wymagania specyfikacji

| Punkt | Wymaganie | Implementacja | Test | Wynik | Ograniczenia |
|---|---|---|---|---|---|
| 0.1 | Kopia danych przed migracją | `~/Sol-83-backups/2026-11-07-przed-OpenBeta` | ręczne porównanie liczby plików | zrobione | worktrees jako klon APFS na tym samym dysku |
| 1 | Kolejka zleceń i kończenie projektu | `gemini_app/orders.py` (trwała kolejka w `notes`: id, czas, kolejność, priorytet, stan pending→delivered→answered→done, klucz idempotencji), `Supervisor.add_note` (zapis przed potwierdzeniem, status czytany w tej samej transakcji), `orders.finish` (zamknięcie atomowe z kolejką i bramkami), `scheduler.after_turn` (spóźniona akceptacja nie zamyka projektu), `orders.requeue_unanswered` (restart), pozycje planu jako `kind=item`, `state_kind` (rodzaj oczekiwania) | `tests/test_queue.py`: `DurableQueue` (duplikat, 8 równoczesnych żądań, zamknięcie z pracą w kolejce, praca tuż po zamknięciu, wyścig zamknięcie/dodanie ×20, przerwana tura, answered→done, pozycje planu); `tests/test_gemini.py`: `QueueFlow` (zlecenie w ostatniej turze, utrata silnika i wznowienie) | częściowo | Panel pokazuje stan kolejki tylko w istniejącym widoku wiadomości; pełny widok kolejki i `state_kind` w UI: etap interfejsu. Zlecenie jest „done” dopiero po zaakceptowanej wersji. |
| 2 | Zmiana modeli i ról w trakcie | migawka konfiguracji tury w `live.config` i w zdarzeniu `turn_start`; `Supervisor.next_config`/`_turn_config`; przegląd w trybie jednego modelu w nowej sesji; limit 5 przeglądów Full Power z komunikatem | `QueueFlow.test_turn_keeps_its_configuration_snapshot`; istniejące testy ról i wyłączania modeli w `tests/test_gemini.py` | częściowo | UI nie pokazuje jeszcze obok siebie konfiguracji bieżącej i oczekującej. Full Power opisany w dokumentacji (etap dokumentacji). |
| 3 | Walidacja i naprawa planu | `gemini_app/plan_contract.py` (kanoniczne wartości, jawne mapy PL/EN z logiem poprawek, nieznane = błąd, id, zależności, cykle, `deferred` ≠ done), `plan.record`/`plan.effective` (rewizje w `plan_revisions`, ostatni poprawny plan, maks. 3 próby naprawy, potem przywrócenie), kontrakt w prompcie | `tests/test_queue.py`: `PlanContract`, `PlanRevisions` | zrobione | Zgodność pozycji z zakresem zlecenia ocenia model, nie walidator. |
| 4 | Logowanie i dostępność agentów | `gemini_app/providers.py`: instalacja, wersja, logowanie; konto i abonament tylko z CLI (`claude auth status`, `codex app-server account/read`); Antigravity: `agy models`; 9 klas błędów z klasą „nieustalona”; czas odczytu i nieaktualność; „Sprawdź połączenie” bez wywołania modelu; reset podany przez dostawcę w treści błędu zamiast zgadywania | `tests/test_usage.py`: `Diagnosis` (prawdziwy komunikat Antigravity z 3.11.2026) | częściowo | Antigravity nie ujawnia konta ani abonamentu: „brak danych”. Zgłoszenie „limit nie starcza na jedno zapytanie”: w logach z 3.11 jedynym błędem był tygodniowy limit konta („Individual quota reached… Resets in 144h”), który odrzuca każde zapytanie aż do resetu, a Sol-83 ponawiał co 30 min z podwajaniem. Brak osobnego „testu zużywającego limit” w UI. |
| 5 | Tokeny i zużycie abonamentów | `gemini_app/usage.py`: wspólny model z surowym rekordem, źródłem i zakresem; przyrosty liczników sesji (Codex, Antigravity); brak danych ≠ 0; okna 5 h i tygodniowe projektu z ekwiwalentem okien, turami bez odczytu i turami wspólnymi z innym projektem; widok Efektywność | `tests/test_usage.py` (prawdziwe sekwencje liczników z 3.11.2026), `test_each_turn_records_its_tokens` | częściowo | Z prawdziwych danych: Codex pisze „tokens used” z separatorem tysięcy w nowej linii, parser zapisywał np. 192 zamiast 192 753; Codex i Antigravity podają sumy sesji, które sumowano jak tury; cache Antigravity nie jest częścią input. Rozumowanie: u Claude w output, u Antigravity relacja nieustalona (pokazywane osobno). Praca lokalnego koordynatora nie jest jeszcze liczona osobno. Historyczne tury nie są przeliczane. |
| 6 | Auto: wybór modelu | `gemini_app/model_catalog.py` (`choose`), `data/model_policy.json` (wersjonowana); tryby Ręczny / Auto — ekonomiczny / Auto — power na dostawcę; najwyższe i niesklasyfikowane modele nigdy w Auto (także nie jako fallback ani eskalacja); ręczny wybór najwyższego wymaga potwierdzenia tego modelu; decyzja z powodem i wersjami w migawce tury; model potwierdzony przez CLI zapisany osobno; zmiana modelu daje nową sesję z przekazaniem stanu | `tests/test_catalog.py`: `AutoPolicy`, `TopModelConfirmation`; `QueueFlow.test_auto_selection_picks_an_allowed_model_and_records_why`, `test_auto_without_an_allowed_model_waits_instead_of_falling_back` | częściowo | Oszczędności niezmierzone (wymagają prawdziwych projektów). Trudność oceniana po niepowodzeniach, nie z treści zadania. Brak modelu dozwolonego: strona czeka z komunikatem, bez osobnego pytania do użytkownika. |
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
| 20 | Katalog modeli | katalog z trzema źródłami (fakty dostawcy ze źródłem i datą, lista modeli konta z CLI, `local_stats` z projektów), wersje w `catalog_versions`, walidacja propozycji (bez dopuszczania najwyższych do Auto, nowe modele bez klasyfikacji, zmiany poziomu czekają na decyzję), cofnięcie, miesięczna aktualizacja w tle z odroczeniem i wyłączeniem, ograniczona liczba prób | `tests/test_catalog.py`: `CatalogUpdates` | częściowo | Prawdziwy przebieg agenta badawczego nie był uruchamiany (koszt limitu). UI nie pokazuje jeszcze decyzji do zatwierdzenia ani porównania wersji. Hierarchia Antigravity nieustalona: Argon bezpiecznie jako najwyższy. |
| 21 | Pytania i testy ręczne | | | nie zrobione | |
| 22 | Git w kontekście projektu | | | nie zrobione | |

## Wywołania na żywo (prawdziwe CLI)

| Data | Co | Wynik | Zużycie |
|---|---|---|---|
| 2026-11-07 | `agy models` w piaskownicy Seatbelt | lista modeli konta, kod 0 | bez wywołania modelu |
| 2026-11-07 | `claude auth status`, `codex login status`, `codex app-server account/read` i `model/list` | konto, abonament, lista modeli | bez wywołania modelu |
| 2026-11-07 | dokumentacja Anthropic „Models overview” | hierarchia Fable / Opus / Sonnet / Haiku do katalogu | strona WWW |
