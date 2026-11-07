# Dane, kopie, aktualizacje, migracje i powrót

## Gdzie są dane

Kod Sol-83 i dane są rozdzielone. Dane leżą domyślnie w `~/Sol-83-data`; inny folder wskazuje zmienna `SOL83_HOME` (starsza nazwa `GEMINI_HOME` też działa):

| Folder | Zawartość |
|---|---|
| `state/gemini.db` | baza SQLite: projekty, kolejka, zdarzenia, wersje, pytania, rewizje planu, zużycie, katalog |
| `projects/` | repozytoria utworzone przez Sol-83 i klony z GitHub |
| `worktrees/<id>` | foldery robocze agentów (gałąź `gemini/<id>`) |
| `worktrees/<id>-testy` | folder użytkownika z wybraną wersją („Uruchamiaj stąd”, RUN) |
| `runs/<id>/` | przebiegi silnika, logi tur, logi testów i RUN |
| `config/` | konfiguracje przebiegów |

Repozytoria wskazane przez Ciebie jako źródło zostają tam, gdzie są. Sol-83 dodaje w nich tylko gałąź `gemini/<id>`, tagi wersji i worktree.

## Kopia zapasowa

Zatrzymaj panel (Ctrl+C) i poczekaj, aż projekty skończą tury (albo wstrzymaj je w panelu). Potem skopiuj cały folder danych:

```bash
cp -cRp ~/Sol-83-data ~/Sol-83-backup-$(date +%Y%m%d)
```

Na macOS `cp -c` robi klon APFS: kopia nie zajmuje miejsca, dopóki pliki się nie zmienią. Chroni przed błędami programu i pomyłkami, ale nie przed awarią dysku. Do tego potrzebna jest kopia na innym nośniku, np. Time Machine. Na Linuksie użyj `cp -a`.

## Aktualizacja kodu

```bash
cd <folder z kodem Sol-83>
```

```bash
git pull
```

```bash
rm -rf vendor/duet && ./bin/setup
```

Schemat bazy aktualizuje się sam przy starcie: dochodzą nowe tabele i kolumny, a nic nie jest usuwane. Starsze projekty dostają przy pierwszym starcie klucz (PRn/rr) i język odczytany z treści zadania.

## Migracja ze starszej instalacji

Wersje sprzed OpenBeta trzymały dane obok kodu (`state/`, `projects/`, `runs/`, `worktrees/`, `config/` w folderze aplikacji). Przeniesienie:

```bash
./sol83 migrate --from <stary folder aplikacji> --dry-run
```

```bash
./sol83 migrate --from <stary folder aplikacji>
```

Migracja:
- odmawia, gdy w starej instalacji działają silniki projektów albo gdy folder docelowy nie jest pusty,
- kopiuje dane (klon APFS na macOS), a bazę przez mechanizm kopii SQLite,
- przepisuje ścieżki w bazie, konfiguracjach i stanach przebiegów (teksty historycznych zdarzeń zostają bez zmian),
- naprawia powiązania worktree z repozytoriami (`git worktree repair`),
- porównuje liczbę rekordów i zapisuje raport w `MIGRATION.json`.

Źródło nie jest zmieniane, z jednym wyjątkiem: worktree Twoich repozytoriów spoza folderu danych dostają nowe powiązanie zwrotne. `--trial` pozwala przećwiczyć migrację z kopii bez tej zmiany.

## Powrót do poprzedniego stanu

1. Zatrzymaj panel.
2. Przenieś obecny folder danych na bok, np. `mv ~/Sol-83-data ~/Sol-83-data.odrzucone`.
3. Przywróć kopię: `cp -cRp ~/Sol-83-backup-RRRRMMDD ~/Sol-83-data`.
4. Jeśli wracasz do starszego kodu: `git checkout <tag lub commit>` w folderze z kodem, a potem `rm -rf vendor/duet && ./bin/setup`.
5. Jeśli wracasz do instalacji sprzed OpenBeta (dane obok kodu), uruchom stary kod z jego folderu: używa on własnych danych, a nie `~/Sol-83-data`.

Plan uruchomienia RUN, katalog modeli i rewizje planu są w bazie, więc wracają razem z kopią.
