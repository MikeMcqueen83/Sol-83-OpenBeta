# Instalacja Sol-83 krok po kroku, od zera

Ten przewodnik prowadzi od czystego systemu do pierwszego projektu. Każdy krok ma polecenie do wklejenia w Terminalu i sposób sprawdzenia, że się udał.

**Przetestowano:** macOS 26 (Apple Silicon), Python 3.14, Git 2.55, Claude Code 2.1, Codex CLI 0.166, Antigravity CLI 1.5. **Linux** jest obsługiwany w kodzie (piaskownica bubblewrap, `notify-send`), ale nie był testowany na prawdziwej maszynie. **Windows** nie jest obsługiwany (Sol-83 używa `fcntl`, `ps` i piaskownic systemów uniksowych); można próbować w WSL 2 jak na Linuksie, bez gwarancji.

Czego potrzebujesz poza komputerem:
- abonamentu Claude (Pro, Max lub wyższy) dla Claude Code,
- konta ChatGPT z planem obejmującym Codex,
- opcjonalnie konta Google z Google AI Pro/Ultra dla Gemini przez Antigravity,
- około 2 GB miejsca na Sol-83 i narzędzia, plus miejsce na projekty.

Sol-83 korzysta wyłącznie z abonamentów. Nie wymaga kluczy API i nie używa płatnego rozszerzenia limitów.

---

## Krok 1. Otwórz Terminal

macOS: Finder → Programy → Narzędzia → Terminal (albo Cmd+Spacja, wpisz „Terminal”). Wszystkie polecenia poniżej wklejasz tam i zatwierdzasz Enterem.

## Krok 2. Narzędzia programisty Apple (Git)

```bash
xcode-select --install
```

Otworzy się okno instalatora; zatwierdź. Sprawdzenie:

```bash
git --version
```

Powinna pojawić się wersja, np. `git version 2.55.0`.

Linux (Debian/Ubuntu): `sudo apt install git curl`.

## Krok 3. Homebrew (menedżer pakietów macOS)

Jeśli `brew --version` już działa, pomiń ten krok. Polecenie ze strony https://brew.sh:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Na końcu instalator wypisze dwa polecenia dodające Homebrew do ścieżki: wykonaj je. Sprawdzenie: `brew --version`.

## Krok 4. Python 3 i Node.js

```bash
brew install python node
```

Sprawdzenie:

```bash
python3 --version
```

Potrzebny jest Python 3.9 lub nowszy (Sol-83 testowano na 3.14). Node.js jest potrzebny tylko do instalacji Codex przez npm.

Linux: `sudo apt install python3 nodejs npm bubblewrap` (bubblewrap to piaskownica, bez której Sol-83 nie uruchamia kodu z repozytoriów).

## Krok 5. Claude Code

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Alternatywa: `brew install --cask claude-code`. Otwórz nowe okno Terminala i sprawdź:

```bash
claude --version
```

Zaloguj się kontem z abonamentem: uruchom `claude`, wybierz logowanie przez claude.ai i dokończ w przeglądarce. Potem wyjdź z sesji poleceniem `/exit`. Nie ustawiaj zmiennej `ANTHROPIC_API_KEY`: Sol-83 odmawia pracy, gdy widzi klucz API.

Jeśli masz aplikację Claude na Maca, Sol-83 znajdzie też dołączoną do niej kopię Claude Code. Inną lokalizację wskazuje zmienna `GEMINI_CLAUDE_BIN`.

## Krok 6. Codex CLI

```bash
npm install -g @openai/codex
```

Alternatywa: `brew install --cask codex`. Logowanie: uruchom `codex`, wybierz „Sign in with ChatGPT”, dokończ w przeglądarce, wyjdź. Sprawdzenie:

```bash
codex login status
```

Powinno pojawić się `Logged in using ChatGPT`.

## Krok 7 (opcjonalny). Gemini przez Antigravity

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

To polecenie z dokumentacji Antigravity z listopada 2026; jeśli adres się zmienił, użyj aktualnego ze strony antigravity.google. Pierwsze polecenie otwiera logowanie kontem Google:

```bash
agy -p "test"
```

To jedno krótkie zapytanie zużywa niewielką część limitu Antigravity. Sprawdzenie bez zużycia limitu:

```bash
agy models
```

Nie ustawiaj `GEMINI_API_KEY` ani `GOOGLE_API_KEY`: adapter i tak usuwa je ze środowiska.

## Krok 8 (opcjonalny). GitHub CLI

Potrzebny tylko do publikacji wersji na GitHub i do Pull Requestów.

```bash
brew install gh
```

```bash
gh auth login
```

## Krok 9 (opcjonalny). Lokalny model przez Ollama

Lokalny model odpowiada na pytania o stan projektu bez zużywania abonamentów i pomaga ułożyć plan uruchomienia (RUN). Bez niego Sol-83 działa, a koordynatorem wiadomości może być jeden z modeli abonamentowych.

```bash
brew install ollama
```

```bash
ollama serve
```

W drugim oknie Terminala pobierz model (domyślny `gemma4:31b` zajmuje około 20 GB; mniejszy wskażesz zmienną `SOL83_LOCAL_MODEL`):

```bash
ollama pull gemma4:31b
```

## Krok 10. Pobierz Sol-83

Wybierz folder na kod, np. katalog domowy:

```bash
cd ~
```

```bash
git clone https://github.com/MikeMcqueen83/Sol-83-OpenBeta.git
```

```bash
cd Sol-83-OpenBeta
```

## Krok 11. Silnik Duet

Sol-83 korzysta z silnika Duet (licencja MIT) w przypiętej wersji, z łatką z tego repozytorium:

```bash
./bin/setup
```

Powinno pojawić się `Duet gotowy`.

## Krok 12. Sprawdzenie środowiska

```bash
./sol83 doctor
```

Każdy wiersz powinien mieć `[ok]`. Znaczenie typowych `[!!]`:
- **Piaskownica systemu**: na Linuksie zainstaluj `bubblewrap`,
- **Logowanie Claude i Codex**: wróć do kroku 5 albo 6,
- **Brak kluczy API w środowisku**: usuń wskazane zmienne z `~/.zshrc` lub `~/.bashrc`.

`doctor` nie wywołuje żadnego modelu i nie zużywa limitów.

## Krok 13. Uruchomienie panelu

```bash
./sol83 serve
```

Otwórz w przeglądarce http://127.0.0.1:8765. Panel jest dostępny tylko z tego komputera. Zamknięcie Terminala zatrzymuje panel; pracujące projekty kończą bieżącą turę, a po ponownym `./sol83 serve` koordynator podłącza się do nich.

Dane (projekty, przebiegi, baza) trafiają do `~/Sol-83-data`. Inny folder wskażesz zmienną `SOL83_HOME`, np. `SOL83_HOME=/Volumes/Dane/Sol83 ./sol83 serve`.

## Krok 14. Pierwszy projekt

1. Kliknij **Nowy projekt**.
2. Opisz zadanie i kryteria odbioru (jak ocenić, że jest gotowe). Język strony w chwili tworzenia staje się stałym językiem projektu.
3. Wpisz polecenie testów, np. `python3 -m unittest`. Uruchamia się w piaskownicy, bez sieci.
4. Wybierz modele: ręcznie albo tryb **Auto — ekonomiczny** lub **Auto — power** dla każdego dostawcy.
5. Zostaw role na **Ogólna** albo przydziel role szczegółowe.
6. Zatwierdź. Projekt trafia do kolejki i startuje.

Postęp widać w zakładce **Przebieg**. Pytania agentów i testy do wykonania przez Ciebie są w **Pytania i testy**. Gotowe wersje są w **Wersje**: tam uruchomisz wersję przyciskiem **RUN**, otworzysz jej folder i ocenisz ją.

## Aktualizacja Sol-83

```bash
cd ~/Sol-83-OpenBeta
```

```bash
git pull
```

Jeśli zmienił się silnik Duet (submoduł `vendor/duet`, wersja w `config/upstream.json`), odśwież go:

```bash
rm -rf vendor/duet && ./bin/setup
```

Dane w `~/Sol-83-data` pozostają nietknięte. Przed aktualizacją zrób kopię (patrz `docs/pl/AKTUALIZACJE.md`).

## Odinstalowanie

Zatrzymaj panel (Ctrl+C w jego oknie), a potem przenieś do Kosza folder z kodem i, jeśli nie są już potrzebne, folder danych `~/Sol-83-data`. Repozytoria Twoich projektów, które wskazałeś jako źródło, nie są przez Sol-83 usuwane.
