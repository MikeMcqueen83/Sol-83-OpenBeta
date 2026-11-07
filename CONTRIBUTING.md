# Współpraca / Contributing

**PL.** Zmiany wnosi się przez **fork lub osobną gałąź i Pull Request** do gałęzi `main`. Kod jest udostępniony na warunkach source-available (LICENSE.md, projekt wymagający weryfikacji prawnej); zasady wkładu zewnętrznego (CLA/DCO) ustali autor.

1. Zgłoszenie (issue) przed większą zmianą: opis problemu i proponowanego rozwiązania.
2. Gałąź od aktualnego `main`, jedna sprawa na Pull Request.
3. Testy: `python3 -m unittest discover -s tests` muszą przechodzić; nowe zachowanie ma test (atrapy CLI w `tests/fakes`, bez zużywania abonamentów). Wyniki z prawdziwymi CLI opisz osobno i oznacz.
4. Teksty dla użytkownika w PL i EN (`gemini_app/messages.py`, `gemini_app/prompts.py`, `web/index.html`).
5. Bez sekretów, prywatnych ścieżek i danych w repozytorium.
6. Zmiany bezpieczeństwa (piaskownica, sekrety, Git) z opisem ryzyka w Pull Requeście.

Publiczny kod można pobrać i bez forka; zasada fork/gałąź dotyczy wnoszenia zmian do tego repozytorium, a nie zabezpieczenia przed pobraniem.

**EN.** Contribute through a **fork or a separate branch and a pull request** to `main`. Open an issue before larger changes; keep one topic per pull request; all tests must pass and new behaviour needs a test with the fake CLIs; user-facing texts in PL and EN; no secrets or private paths; describe the risk of security-related changes. The fork/branch rule governs contributions; it does not and cannot prevent downloading public code.
