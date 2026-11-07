# Rzeczywisty test Duet — 1 listopada 2026

Wynik: **converged**, dwóch różnych providerów i niezależne testy końcowe.

1. Codex naprawił naliczanie rabatu i walidację zakresów.
2. Pierwsza recenzja Claude ujawniła brak zgody na uruchomienie testów. Launcher został poprawiony: udostępnia Claude wskazane przez użytkownika polecenie testowe przez allowedTools.
3. Kontrolowana pauza zakończyła pierwszy przebieg statusem force_stop.
4. Wznowienie zachowało identyfikatory obu rozmów i kod oraz przekazało dodatkową uwagę.
5. Claude uruchomił testy i zaakceptował rozwiązanie; Codex następnie potwierdził wynik. Duet wykonał polecenie kontrolne po obu akceptacjach: 6/6 testów OK.
6. Git potwierdza zmianę wyłącznie calculator.py; testy i instrukcje zachowane.

[Przebieg przed pauzą](/Users/evvil/AplikacjeLokalne/ProjectGemini/runs/20261101-215852/transcript.md)

[Przebieg po wznowieniu](/Users/evvil/AplikacjeLokalne/ProjectGemini/worktrees/1c2d1e16bbf4/.duet/runs/20261101-220004/transcript.md)

[Poprawiony kod](/Users/evvil/AplikacjeLokalne/ProjectGemini/worktrees/1c2d1e16bbf4/calculator.py)

Naprawiono też lokalizację logów przyszłych wznowień: trafiają do ProjectGemini/runs. Kontrola dry-run tej poprawki jest w resume-path-check.log. Kod upstream Duet pozostaje niezmieniony.

Nie sprawdzano rzeczywistego wyczerpania abonamentu. Automatyczne przejęcie po limicie nie jest jeszcze częścią wdrożenia. Wspólna akceptacja w tym teście dotyczy niezmienionej poprawki w worktree; nie wdrożono osobnej bramki wiążącej akceptacje z hashem commitu.
