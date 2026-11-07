# Bezpieczeństwo / Security

## Zgłaszanie podatności / Reporting a vulnerability

Nie zgłaszaj podatności w publicznym zgłoszeniu. Użyj prywatnego zgłoszenia GitHub („Report a vulnerability” w zakładce Security repozytorium), jeśli jest włączone. Kanał kontaktowy autora: do uzupełnienia przez autora.

Please do not report vulnerabilities in a public issue. Use GitHub's private vulnerability reporting (Security tab) if enabled. The author's contact channel: to be filled in by the author.

## Model zagrożeń / Threat model (PL)

Sol-83 uruchamia agentów AI, którzy piszą i wykonują kod na Twoim komputerze. Kod ten może być skutkiem błędu modelu albo wstrzyknięcia poleceń (np. z treści stron, które agent czyta). Dlatego:

- **Agenci** pracują w swoich piaskownicach: Claude Code z ustawieniem sandbox, Codex `workspace-write`, a cały proces Antigravity w piaskownicy systemu.
- **Kod z repozytorium uruchamiany przez koordynatora** (polecenie testów, `.gemini-setup`, RUN) działa w piaskownicy systemu: Seatbelt (`sandbox-exec`) na macOS, bubblewrap na Linuksie. Może zapisywać tylko w folderze projektu i w prywatnym katalogu tymczasowym. Nie może czytać `~/.ssh`, `~/.aws`, `~/.gnupg`, loginów `gh`, `codex`, `claude`, `gemini`, pęku kluczy ani danych przeglądarek. Testy domyślnie nie mają sieci wychodzącej (localhost działa).
- **Bez piaskownicy** taki kod się nie uruchamia, chyba że świadomie włączysz „Uruchamianie bez piaskownicy”.
- **`.gemini-setup`** uruchamia się tylko po akceptacji dokładnej treści (sha256); każda zmiana wymaga nowej akceptacji.
- **Sekrety**: przed każdą wysyłką na GitHub (prywatną i publiczną) skanowane są pliki, treść i historia; wysyłka mimo znalezisk wymaga potwierdzenia tej listy. Odpowiedzi modeli, logi testów i błędy są maskowane przed zapisem. Zmienne z kluczami API nie trafiają do agentów, a Sol-83 odmawia startu z kluczami API.
- **Panel** słucha tylko na 127.0.0.1, sprawdza nagłówek Host (ochrona przed DNS rebinding), Origin i typ treści. Brak uwierzytelnienia: każdy lokalny proces Twojego konta może sterować panelem.
- **Git**: brak force push, resetu, przepisywania historii, zmiany widoczności i ochrony gałęzi. Repozytorium Sol-83 nie jest celem operacji projektów.
- **RUN**: tylko proste polecenia znanych narzędzi, bez powłoki, w piaskownicy z siecią; nigdy `sudo`, `curl | sh`, instalacje wymagające administratora; zatrzymywane są tylko procesy uruchomione przez Sol-83.

Ograniczenia: piaskownica pozwala czytać pliki spoza listy chronionych folderów. `sandbox-exec` jest oznaczony przez Apple jako przestarzały. Wzorce sekretów są heurystyczne. Na Linuksie piaskownica nie była testowana na prawdziwej maszynie.

## Threat model (EN)

Sol-83 runs AI agents that write and execute code on your machine; that code may follow from a model error or a prompt injection. Agents run in their own sandboxes; code from the repository that the coordinator itself runs (tests, `.gemini-setup`, RUN) and the whole Antigravity process run in the OS sandbox (Seatbelt on macOS, bubblewrap on Linux): writes only in the project folder and a private temp folder, no reading of SSH keys, cloud and CLI logins, keychains or browser data, no outbound network for tests by default. Without a sandbox such code does not run unless you explicitly allow it. `.gemini-setup` runs only after you approve its exact content. Every push to GitHub is scanned for secrets; outputs and logs are redacted; API keys never reach the agents. The panel binds to 127.0.0.1 with Host, Origin and content-type checks, but has no authentication against other local processes of your account. Limits: reads outside the protected folders are possible; secret patterns are heuristic; the Linux sandbox is untested on real hardware.
