<p align="center">
  <img src="Assets/logo.jpeg" alt="Sol-83 OpenBeta: Your AI subscriptions. One collaborative team." width="760">
</p>

<p align="center">
  <b>Twoje abonamenty AI. Jeden zgrany zespół.</b><br>
  Claude Code · Codex · Gemini (Antigravity) · lokalny LLM
</p>

<p align="center">
  <a href="README.en.md">English</a> ·
  <a href="docs/pl/INSTALACJA.md">Instalacja</a> ·
  <a href="docs/pl/PRZEWODNIK.md">Przewodnik</a> ·
  <a href="#zrzuty-ekranu">Zrzuty ekranu</a> ·
  <a href="#kawa">Postaw mi kawę ☕</a>
</p>

# Sol-83 (OpenBeta)

Sol-83 to lokalny koordynator, który każe agentom programistycznym pracować na zmianę nad jednym repozytorium: **Claude Code**, **Codex** i opcjonalnie **Gemini przez Antigravity**. Agenci sprawdzają się nawzajem, a gdy jednemu kończy się limit abonamentu, pracę przejmuje drugi. Koordynator to zwykły program, nie model. Zapisuje checkpoint Git po każdej turze, uruchamia testy w piaskownicy i numeruje wersję tylko wtedy, gdy przeszły. Ty dostajesz sprawdzone wersje, pytania tylko wtedy, gdy są naprawdę potrzebne, i panel WWW na `127.0.0.1:8765` po polsku i angielsku.

Korzysta wyłącznie z abonamentów: bez kluczy API i bez płatnego rozszerzenia limitów.

> **Status:** wersja OpenBeta, rozwijana od listopada 2026. Przetestowana na macOS (Apple Silicon). Linux jest obsługiwany w kodzie, ale nie był testowany na prawdziwej maszynie; Windows nie jest obsługiwany. Stan każdej funkcji, z testami i ograniczeniami: [docs/TRACEABILITY.md](docs/TRACEABILITY.md).

<a id="zrzuty-ekranu"></a>
## Jak to wygląda

<p align="center">
  <img src="Assets/sc4.png" alt="Sol-83 w skórce SAKURA: limity abonamentów, karty projektów, plan z postępem netto" width="100%"><br>
  <sub>Skórka SAKURA: limity abonamentów, karty projektów i plan z postępem netto.</sub>
</p>

<table>
  <tr>
    <td width="50%" align="center" valign="top">
      <img src="Assets/sc2.png" alt="Plan projektu w skórce TERMINAL"><br>
      <sub>Plan z priorytetami, budżetem tur i przyciskiem „Zleć” przy każdej pozycji.</sub>
    </td>
    <td width="50%" align="center" valign="top">
      <img src="Assets/sc3.png" alt="Ustawienia modeli i ról w skórce TERMINAL"><br>
      <sub>Ustawienia: migawka bieżącej tury, wiele ról na model, tryb Auto.</sub>
    </td>
  </tr>
</table>

<details>
  <summary><b>Więcej zrzutów</b></summary>
  <p align="center">
    <img src="Assets/sc1.png" alt="Przebieg tur w skórce TERMINAL" width="100%"><br>
    <sub>Przebieg: wyraźne nagłówki tur (wykonawca, model, rodzaj pracy) i odpowiedź lokalnego koordynatora.</sub>
  </p>
  <p align="center">
    <img src="Assets/sc5.png" alt="Interfejs po angielsku w skórce SAKURA" width="100%"><br>
    <sub>Interfejs po angielsku: język strony zmienia się niezależnie od stałego języka projektu.</sub>
  </p>
</details>

## Szybki start

Pełna instalacja od zera, krok po kroku: **[docs/pl/INSTALACJA.md](docs/pl/INSTALACJA.md)**.

```bash
git clone https://github.com/MikeMcqueen83/Sol-83-OpenBeta.git
```

```bash
cd Sol-83-OpenBeta && ./bin/setup && ./sol83 doctor
```

```bash
./sol83 serve
```

Potem otwórz http://127.0.0.1:8765 i kliknij **Nowy projekt**.

## Co działa

- Kilku agentów na zmianę, przejęcie pracy po limicie, Full Power (przegląd tym samym modelem w nowej sesji, najwyżej 5 razy z rzędu).
- Trwała kolejka zleceń: nic nie ginie przy restarcie, podwójnym kliknięciu ani zamykaniu projektu.
- Plan z kontraktem PL/EN, rewizjami i postępem netto (funkcje minus dług), bramki odbioru.
- Tryby wyboru modelu Ręczny / Auto — ekonomiczny / Auto — power z katalogiem modeli. Najwyższe modele tylko ręcznie, z potwierdzeniem.
- Kilka ról na model, zamówienia grafik i tekstów z Twoją akceptacją, pytania i testy ręczne dla Ciebie.
- Stały język projektu (PL lub EN) we wszystkich instrukcjach dla agentów.
- Wersje z testami, RUN (kontrolowane uruchomienie wybranej wersji), Git w kontekście projektu, licencja projektu.
- Panel kont i limitów, tokeny liczone poprawnie dla każdego dostawcy.
- Piaskownica systemu dla kodu z repozytoriów, skan sekretów przed każdą wysyłką.
- Skórki LIGHT, DARK, SAKURA, TERMINAL.

## Dokumentacja

| Temat | PL | EN |
|---|---|---|
| Instalacja od zera | [INSTALACJA](docs/pl/INSTALACJA.md) | [INSTALL](docs/en/INSTALL.md) |
| Przewodnik: projekty, modele, role, Auto, Full Power, limity, wersje, RUN, pytania, treści, język, Git, licencje | [PRZEWODNIK](docs/pl/PRZEWODNIK.md) | [GUIDE](docs/en/GUIDE.md) |
| Dane, kopie, aktualizacje, migracje, powrót | [AKTUALIZACJE](docs/pl/AKTUALIZACJE.md) | [UPDATES](docs/en/UPDATES.md) |
| Bezpieczeństwo | [SECURITY.md](SECURITY.md) | [SECURITY.md](SECURITY.md) |
| Współpraca | [CONTRIBUTING.md](CONTRIBUTING.md) | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Audyt i poprawki | [AUDIT-2026-11-07](docs/AUDIT-2026-11-07.md) | |
| Wymagania i stan wdrożenia | [TRACEABILITY](docs/TRACEABILITY.md) | |
| Zmiany | [CHANGELOG.md](CHANGELOG.md) | [CHANGELOG.md](CHANGELOG.md) |

<a id="kawa"></a>
## ☕ Postaw mi kawę

Sol-83 rozwijam samodzielnie i udostępniam bezpłatnie do użytku niekomercyjnego. Jeśli oszczędził Ci czas albo limity abonamentów, jeśli podoba Ci się sam pomysł, albo po prostu chcesz, żeby kolejne funkcje pojawiały się szybciej, postaw mi kawę. To realnie pomaga w dalszym rozwoju, a każde wsparcie bardzo motywuje. Dziękuję! 🌸

<p align="center">
  <a href="https://buycoffee.to/evvil" target="_blank"><img src="https://buycoffee.to/static/img/share/share-button-dark--en.png" width="406" height="92" style="width: 406px; height: 92px" alt="Buy a coffee for Evvil at buycoffee.to"></a>
</p>

## Licencja

Sol-83 jest udostępniany jako **source-available**, a nie jako open source w rozumieniu OSI. Użycie niekomercyjne przez osoby prywatne jest dozwolone. Użycie komercyjne, w tym przez firmy (także wewnętrzne) oraz włączanie kodu lub jego części do monetyzowanych produktów i usług, wymaga uprzedniej pisemnej zgody autora. Zmiany wnosi się przez fork lub gałąź. Warunki są projektem do weryfikacji prawnej: [LICENSE.md](LICENSE.md). Silnik Duet i inne komponenty zachowują swoje licencje: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Licencja projektów, które tworzysz w Sol-83, jest Twoim wyborem i nie zależy od licencji Sol-83.

Autor: Michał Werpachowski.
