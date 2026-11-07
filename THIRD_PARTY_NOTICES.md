# Komponenty zewnętrzne / Third-party components

| Komponent | Gdzie | Licencja | Uwagi |
|---|---|---|---|
| Duet (volkan/duet) | pobierany przez `bin/setup` do `vendor/duet` (nie jest częścią repozytorium) | MIT, Copyright (c) 2026 Volkan Altan | przypięty commit w `config/upstream.json` |
| Łatka do Duet | `patches/duet-gemini.patch` | zmiany w kodzie na licencji MIT; proponowane udostępnienie na MIT (decyzja autora w LICENSE.md) | dodaje harmonogram tur i trzeciego agenta |
| Teksty licencji standardowych | `gemini_app/data/licenses/` | teksty licencji MIT, Apache-2.0, BSD-3-Clause, MPL-2.0, GPL-3.0, AGPL-3.0 w wersjach z API licencji GitHub | niezmienione; do zapisywania licencji projektów użytkowników |

Narzędzia, z których Sol-83 korzysta, ale których nie rozpowszechnia: Claude Code (Anthropic), Codex CLI (OpenAI), Antigravity CLI (Google), GitHub CLI, Ollama i lokalne modele. Każde z nich ma własne warunki; ich przestrzeganie, w tym zasady automatycznego sterowania i korzystania z abonamentów, leży po stronie użytkownika.

Tekst licencji MIT Duet:

```
MIT License

Copyright (c) 2026 Volkan Altan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
