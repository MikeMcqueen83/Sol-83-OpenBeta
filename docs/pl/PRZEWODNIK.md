# Sol-83: przewodnik użytkownika

Instalacja od zera: [INSTALACJA.md](INSTALACJA.md). Ten dokument opisuje działanie aplikacji w wersji OpenBeta. Ograniczenia i stan każdego wymagania są w [../TRACEABILITY.md](../TRACEABILITY.md).

## 1. Czym jest Sol-83

Sol-83 to lokalny koordynator, który każe kilku agentom programistycznym pracować na zmianę nad jednym repozytorium: Claude Code, Codex i opcjonalnie Gemini przez Antigravity. Koordynator to zwykły program, nie model: wybiera, kto ma turę, zapisuje checkpoint Git po każdej turze, uruchamia testy w piaskownicy i numeruje wersję tylko wtedy, gdy testy przeszły. Korzysta z abonamentów, nie z kluczy API. Gdy jednemu agentowi kończy się limit, pracę przejmuje drugi.

Dla kogo: dla osób, które mają abonamenty co najmniej dwóch narzędzi i chcą, żeby się nawzajem sprawdzały, a do siebie dostawały tylko sprawdzone wersje.

Czego nie robi: nie publikuje niczego bez Twojej decyzji, nie używa płatnych kredytów, nie zgaduje logowania, nie zastępuje Twojego odbioru.

## 2. Projekt, kolejka i tury

Projekt to zadanie, repozytorium i zespół modeli. Każde zlecenie (pierwsze zadanie, uwaga, nowa praca, pozycja planu, odrzucona wersja, odpowiedź na pytanie) trafia do trwałej kolejki **zanim** panel potwierdzi przyjęcie. Ma identyfikator, czas, kolejność i stan: *oczekuje → przekazane do tury → odpowiedziane → zrobione* (zrobione oznacza: jest zaakceptowana wersja powstała po odpowiedzi). Podwójne kliknięcie ani ponowione żądanie nie tworzą drugiego wpisu.

Zamknięcie projektu i dodanie pracy są wykonywane w jednej transakcji bazy: zlecenie przyjęte w trakcie finalizacji zawsze zostaje obsłużone, a spóźniona akceptacja starego stanu nie zamyka projektu z nową pracą. Gdy silnik padnie w trakcie tury (np. restart komputera), przekazana praca wraca do kolejki.

Stan projektu w panelu mówi, na co czeka: na turę, na wykonawcę (inna rola), na limit, na Twoją decyzję lub test, albo że wystąpił błąd. Stan jest podany słowem i ikoną, nie tylko kolorem.

**Lista projektów** w lewym panelu ma na górze sekcję **W toku**: projekty pracujące, czekające na model, przegląd albo limit i te w kolejce, każdy z powodem oczekiwania (model, przyczyna, godzina, ewentualny szacunek) i liczbą pytań lub testów, które czekają na Ciebie. Pod nią są zwarte grupy **Wymaga uwagi**, **Zatrzymane** i **Ukończone** z licznikami. Rozwinięcie grup przeglądarka zapamiętuje; grupa z otwartym projektem jest zawsze rozwinięta.

## 3. Modele, role i tryby wyboru

Dla każdego dostawcy wybierasz model i poziom myślenia albo tryb:
- **Ręczny**: model, który wskażesz,
- **Auto — ekonomiczny**: wystarczający model, eskalacja po kolejnych niepowodzeniach,
- **Auto — power**: mocniejszy model z dozwolonej puli, z kontrolą limitów.

Auto wybiera przed każdą turą według rodzaju pracy, wyników (nieudane testy, kroki oceniane jako nieprzybliżające) i zapasu limitu. Decyzja z powodem, wersją polityki i katalogu trafia do Activity. **Najwyższy model dostawcy** (dziś Claude Fable 5.1, GPT-6-Astra, Gemini 4 Argon) nigdy nie jest wybierany automatycznie, także jako zapas lub eskalacja. Ręczny wybór najwyższego modelu wymaga potwierdzenia tego konkretnego modelu. Model niesklasyfikowany (np. modele Ollama widoczne w Codex) też jest poza Auto. Gdy dozwolonego modelu brak, strona czeka i mówi dlaczego.

Zmiana modelu, poziomu, trybu lub roli obowiązuje od następnej tury; bieżąca tura zachowuje swoją migawkę konfiguracji (widoczną w panelu obok konfiguracji następnej tury). Zmiana modelu daje agentowi nową sesję z przekazaniem stanu.

**Role** (model może mieć kilka): Ogólna (plan, implementacja, przegląd), Architekt (plan), Implementujący, Tester i Analityk (przegląd), Twórca treści (wykonuje zatwierdzone zamówienia grafik i tekstów). Rola Ogólna nie wykonuje zamówionych treści. Po każdej zmianie Sol-83 sprawdza, czy każdy rodzaj pracy ma wykonawcę.

**Jeden model**: gdy pracuje tylko jeden, przegląd odbywa się w nowej sesji, a wersja ma oznaczenie ograniczonej niezależności.

**Full Power**: gdy drugi model czeka na reset limitu, ten sam model robi przegląd i poprawki w nowej sesji, bez pamięci swojej pracy, zamiast czekać. Próg przekazania przestaje obowiązywać, więc to szybko zużywa limity. Najwyżej 5 takich przeglądów z rzędu; potem projekt czeka na drugi model i mówi o tym. Full Power nie omija ograniczeń modeli, uprawnień, płatności ani bramek odbioru i nie jest trybem wyboru modelu (to nie „Auto — power”).

## 4. Katalog modeli

Katalog (`gemini_app/data/model_catalog.seed.json`) zawiera dla każdego modelu: fakty według dostawcy ze źródłem i datą sprawdzenia, poziom (economy, standard, strong, top) i to, czy wolno go używać w Auto. Dostępność na Twoim koncie Sol-83 czyta z CLI, a obserwacje z Twoich projektów zbiera osobno. Te trzy źródła nie są ze sobą mieszane.

Raz w miesiącu (pierwszy raz miesiąc po instalacji) koordynator może zlecić aktualizację katalogu modelowi z dozwolonej puli (Sonnet, przez abonament). Propozycja przechodzi walidację: nie może dopuścić najwyższego modelu do Auto ani zdjąć ograniczeń, nowy model zostaje niesklasyfikowany, a zmiana poziomu czeka na Twoją decyzję. Błąd zostawia poprzedni katalog. Aktualizację można wyłączyć, odroczyć albo cofnąć (`/api/catalog/settings`, `/api/catalog/rollback`).

## 5. Limity, tokeny i porównania

Panel **Konta i logowanie** pokazuje dla każdego CLI: instalację, logowanie, konto i abonament (tylko gdy CLI je podaje: Claude i Codex tak, Antigravity nie), czas odczytu i nieaktualność. **Sprawdź połączenie** nie wywołuje modelu. Błędy są rozróżniane: brak logowania, wygasła sesja, niewłaściwe konto, brak dostępu do modelu, limit abonamentu, ograniczenie częstotliwości, sieć, awaria dostawcy, przyczyna nieustalona. Gdy dostawca podaje czas resetu w komunikacie (Antigravity: „Resets in 144h”), Sol-83 używa go zamiast zgadywać.

**Przerwy po błędach.** Godzinę powrotu modelu Sol-83 bierze najpierw z odczytu limitów albo z komunikatu dostawcy (także z odrzucenia przez Claude, które podaje godzinę resetu). Tylko gdy żadne źródło jej nie podaje, przyjmuje szacunek i pokazuje go w panelu jako „(szacunek)”: wyczerpany limit bez godziny 15 min, potem 30, 60 i najwyżej 120 min; chwilowa awaria (ograniczenie częstotliwości, sieć, przeciążenie) 5 min po dwóch szybkich ponowieniach; inny błąd 10 min; problem z logowaniem 60 min. Przycisk **Spróbuj teraz** (w panelu limitów i na belce czekającego projektu) zdejmuje przerwę od razu, a czekające projekty czytają limity na nowo. Odczyt, który nadal pokazuje wyczerpany limit, dalej wstrzymuje tury: to dane dostawcy.

**Dlaczego projekt czeka.** Opis oczekiwania wymienia każdy włączony model: który może wykonać daną pracę, co go wstrzymuje i do kiedy, oraz które modele nie mają potrzebnej roli. Czekanie na przegląd pokazuje recenzenta, który wróci najwcześniej.

**Tokeny** (zakładka Efektywność) to wartości na turę: przyrost licznika tej samej sesji. Claude podaje turę, a Codex i Antigravity podają sumę całej sesji, więc Sol-83 liczy z niej przyrost. Codex podaje tylko sumę, dlatego wejście i wyjście są „brak danych”, a nie zero. Cache jest pokazywany osobno. Kategorii różnych dostawców nie należy porównywać wprost.

**Udział w limitach**: suma ruchu odczytów limitów konta w czasie tur projektu, osobno dla każdego dostawcy, np. 250% okna 5 h = 2,5 pełnego okna. To szacunek, bo obejmuje też inną pracę na koncie. Tury bez odczytu i tury wspólne z innym projektem są wskazane. To nie jest bieżące saldo.

## 6. Plan, postęp i dług

Agenci prowadzą plan w `.sol83/plan.json`. Kanoniczne statusy to `todo`, `doing`, `done` i `deferred`, niezależnie od języka. Warianty jednoznaczne (np. „zrobione”, „in progress”) są normalizowane z wpisem w logu. Nieznana wartość jest błędem, nigdy „zrobione”. Błędny plan nie zastępuje ostatniego poprawnego: koordynator trzyma numerowane rewizje i po 3 nieudanych naprawach przywraca ostatnią poprawną. Błędna wersja trafia do `.sol83/plan.invalid.json`.

**Postęp netto** = max(0, postęp funkcjonalny − dług w punktach procentowych). Oba liczone są na tej samej podstawie: pozycje zakresu ważone priorytetem (must 3, should 2, could 1). Odłożone nie znaczy zrobione. To wskaźnik zarządczy, nie prawdopodobieństwo sukcesu. **Bramki odbioru** są osobno: odłożona pozycja must, pytanie blokujące bez odpowiedzi, obowiązkowy test bez wyniku „działa” dla bieżącej wersji, brakująca obowiązkowa treść. Wysoki procent nie zamyka projektu z otwartą bramką. Zamknięcie bez bramki wymaga Twojej zapisanej decyzji zakresu.

## 7. Pytania i testy dla Ciebie

Agent zgłasza pytanie, prośbę o decyzję albo test ręczny (np. na telefonie) w `.sol83/requests.json`. Sol-83 zapisuje je jako trwałe rekordy z autorem, modelem, rolą, wersją, uzasadnieniem, opcjami, rekomendacją i tym, co blokują. Odpowiadasz w zakładce **Pytania i testy**. Odpowiedź jest zapisana przed wznowieniem pracy i trafia do agentów przez kolejkę na najbliższej granicy tury. Wynik testu: działa, nie działa, częściowo, nie mogę wykonać. Negatywny wynik tworzy jedno zgłoszenie błędu dla tego testu i wersji.

Brak odpowiedzi nie jest zgodą. Prace zależne czekają, niezależne trwają. Gdy nic nie może się dziać, projekt zatrzymuje się w stanie „oczekiwanie na odpowiedź lub test użytkownika” i wznawia się po Twojej odpowiedzi. Spóźniona odpowiedź (do pytania zastąpionego nowszym albo wynik testu dla starszej wersji niż ta, której test dotyczy) zostaje w historii, ale nie jest stosowana automatycznie. Wynik dla nowszej wersji rozstrzyga test: sprawdzasz to, co jest teraz. Odpowiedziane pytania i testy przechodzą do sekcji **Zrobione** (z informacją, czy modele już je dostały) i nie wracają same; „Zmień odpowiedź” otwiera je ponownie.

„Co sprawdzić w tej wersji” to rekord testu ręcznego tej wersji. Ocena wersji przyciskami Działa / Nie działa zapisuje jego wynik.

## 8. Zamówienia grafik i tekstów

Model bez roli Twórcy treści może zaproponować zamówienie (stan „propozycja”) z uzasadnieniem, blokadami i informacją, czy jest obowiązkowe. Wykona je dopiero Twórca treści po Twojej zgodzie na to konkretne zamówienie. Zgoda nie nadaje stałej roli. Zamówienia składane przez Ciebie w zakładce Treści są zatwierdzone od razu. Duplikaty (ten sam typ i ścieżka) są odrzucane. Rozmiar i styl to wskazówki dla generatora; po wykonaniu panel pokazuje faktyczny rozmiar obrazu. Odrzucenie lub odłożenie obowiązkowego zamówienia nie usuwa go z zakresu.

## 9. Wersje, testy i RUN

Wersja powstaje tylko wtedy, gdy testy koordynatora przeszły (albo, bez polecenia testów, na deklarację agenta, co jest wyraźnie oznaczone). Zakładka **Wersje** pokazuje dla każdej wersji: datę, opis, testy automatyczne, test ręczny, przegląd, commit i tag, rekomendację, faktyczny folder (albo informację, że wersja istnieje tylko jako tag, z przyciskiem przygotowania), „Jak uruchomić” i „Co sprawdzić”.

**RUN** uruchamia wybraną wersję w folderze użytkownika („Uruchamiaj stąd”), nigdy w folderze roboczym agentów. Plan uruchomienia powstaje raz dla wersji (z instrukcji agentów, planu lub README, z pomocą lokalnego modelu, gdy trzeba) i jest zapisany z commitem i skrótem plików manifestu. Runner wykonuje tylko proste polecenia znanych narzędzi, bez powłoki, w piaskownicy: nigdy `sudo`, `curl | sh` ani instalacji wymagających administratora. Dostaje port z zakresu 8800–8899 (nigdy 8765 ani zajęty), rozpoznaje swój proces po czasie startu, nie zabija cudzych procesów, a drugie kliknięcie pokazuje trwające uruchomienie. Dla bibliotek RUN jest niedostępny z wyjaśnieniem. Komentarze w instrukcjach (`polecenie   # opis`) są usuwane przed uruchomieniem.

**Dokumenty i research.** Gdy instrukcja każe otworzyć plik HTML („open dist/handbook.html”), RUN najpierw wykonuje do końca kroki budowania (bez testów: te należą do modeli i koordynatora), potem serwuje folder wersji na wolnym porcie i podaje link do dokumentu. Port inny niż panel oddziela skrypty dokumentu od panelu Sol-83. Gdy proces RUN się zakończy, karta „Do testów” pokazuje ostatnie linie jego logu.

**Polecenia do terminala.** Karta „Do testów” pokazuje gotową sekwencję do wklejenia: `cd` do folderu wersji, potem polecenia bez komentarzy i opisów, w kolejności. Najpierw powstaje ona regułami z instrukcji modeli. Potem lokalny koordynator (Ollama, bez abonamentu) przepisuje ją w tle, a jego wersja zostaje tylko wtedy, gdy każda linia jest poleceniem i nie pojawia się program spoza instrukcji.

**Prośby o testy.** Domyślnie Sol-83 prosi Cię o sprawdzenie raz, przy wersji końcowej. W trakcie pracy wynik sprawdzają modele i testy automatyczne, a modele nie mogą zlecać Ci uruchamiania testów, budowania ani skryptów. W Ustawieniach projektu możesz wybrać „Każda nowa wersja” albo „Nie proś o testy”. Karta „Do testów” działa zawsze. W tym samym miejscu jest przełącznik **Claude może czytać strony WWW (WebFetch)**: dla researchu daje pełną treść stron źródłowych zamiast fragmentów z wyszukiwarki.

## 10. Język projektu

Projekt ma stały język (PL albo EN) ustalony przy tworzeniu według języka strony. Wszystkie instrukcje dla agentów, plan, pytania i podsumowania są w tym języku. Zmiana języka strony zmienia tylko interfejs. Dla starszych projektów język został odczytany z treści zadania; gdy treść tego nie przesądza, panel prosi o jednorazowy wybór.

## 11. Git projektu

Agenci pracują na własnej gałęzi `gemini/<id>` w osobnym folderze roboczym. Twoja gałąź główna nie jest ruszana (wyjątek: repozytorium utworzone przez Sol-83, w którym `main` idzie za rekomendowaną wersją, tylko do przodu). W Ustawieniach zapisujesz kontekst Git projektu: remote, gałąź bazową, sposób dostarczania (lokalnie, push gałęzi, push i PR) oraz osobne zgody na push i PR. Sol-83 czyta faktyczny stan repozytorium przed każdą operacją. Nie robi force push, resetu, stash ani przepisywania historii, nie zmienia ochrony gałęzi ani widoczności. Każda operacja ma rekord: po restarcie lub utraconej odpowiedzi najpierw sprawdzany jest stan zdalny, więc nie powstaje drugi commit ani PR. Repozytorium samego Sol-83 nigdy nie jest celem projektu.

Publikacja wersji na GitHub (karta GitHub) skanuje sekrety przed każdą wysyłką, także prywatną. Wysyłka mimo znalezisk wymaga potwierdzenia tej konkretnej listy.

## 12. Licencja projektu

W Ustawieniach projektu wybierasz licencję standardową (MIT, Apache-2.0, BSD-3-Clause, MPL-2.0, GPL-3.0-only, AGPL-3.0-only: niezmienione teksty), własną (np. source-available) albo żadną. Istniejący plik LICENSE nie jest nadpisywany bez zaznaczenia świadomej decyzji. Wybór nie zmienia licencji zależności ani cudzego kodu. Brak licencji nie oznacza, że każdy może używać kodu dowolnie. Licencja Sol-83 jest niezależna od licencji Twoich projektów.

## 13. Bezpieczeństwo w skrócie

Szczegóły: [../../SECURITY.md](../../SECURITY.md). Agenci pracują w swoich piaskownicach. Kod z repozytorium, który uruchamia sam koordynator (testy, `.gemini-setup`, cały proces Antigravity, RUN), działa w piaskownicy systemu (Seatbelt na macOS, bubblewrap na Linuksie). Ma zapis tylko w folderze projektu, nie może czytać kluczy SSH, loginów CLI ani danych przeglądarek, a testy domyślnie nie mają sieci. `.gemini-setup` uruchamia się dopiero po Twojej akceptacji dokładnej treści. Sekrety są maskowane w zdarzeniach i logach. Panel słucha tylko na 127.0.0.1 i odrzuca żądania z innych stron.

## 14. Dane, kopie, aktualizacje i powrót

Patrz [AKTUALIZACJE.md](AKTUALIZACJE.md).

## 15. Diagnostyka

| Objaw | Co zrobić |
|---|---|
| `doctor`: brak piaskownicy | Linux: zainstaluj `bubblewrap`. Bez piaskownicy testy i RUN się nie uruchomią (świadome obejście: ustawienie `allow_unsandboxed`, niezalecane). |
| Projekt „Wymaga uwagi”, logowanie | Zaloguj ponownie CLI (`claude`, `codex login`, `agy`) i kliknij Wznów. |
| Antigravity: „Individual quota reached… Resets in …” | Tygodniowy limit konta Google: Gemini czeka do podanego resetu; pozostałe modele pracują. |
| Testy przechodzą u Ciebie, a w Sol-83 nie | Testy w piaskownicy nie mają sieci i zapisują tylko w folderze projektu. Włącz sieć dla testów (`test_network`) albo dostosuj testy. |
| `.gemini-setup` się nie wykonał | Otwórz Ustawienia projektu, przeczytaj skrypt i zaakceptuj go. |
| RUN: „nieznany program” lub „brakuje programów” | Doinstaluj wskazane narzędzie (bez uprawnień administratora) albo dopisz instrukcję uruchomienia w README projektu. |
| Panel nie startuje: port zajęty | `./sol83 serve --port 8770`. |

## 16. Architektura i testy

| Moduł | Rola |
|---|---|
| `gemini_app/scheduler.py` | kto ma turę, kontekst tury w języku projektu, wersje, przejęcia |
| `gemini_app/supervisor.py` | cykl życia projektów, kolejka, decyzje użytkownika, RUN, Git, licencje |
| `gemini_app/orders.py` | trwała kolejka i atomowe zamykanie |
| `gemini_app/plan_contract.py`, `plan.py` | kontrakt planu, rewizje, postęp netto |
| `gemini_app/interactions.py` | pytania, decyzje, testy ręczne |
| `gemini_app/model_catalog.py`, `data/` | katalog modeli i polityka Auto |
| `gemini_app/usage.py`, `providers.py`, `limits.py` | tokeny, okna limitów, logowanie |
| `gemini_app/sandbox.py`, `secretscan.py` | piaskownica i sekrety |
| `gemini_app/runner.py`, `gitcontext.py`, `licenses.py` | RUN, Git projektu, licencje |
| `gemini_app/prompts.py` | wszystkie teksty dla agentów PL/EN |
| `gemini_app/migrate.py` | przeniesienie danych starszej instalacji |
| `bin/claude`, `bin/gemini` | adaptery CLI |

Testy nie zużywają abonamentów: silnik i koordynator rozmawiają z atrapami CLI, które mówią formatem prawdziwych narzędzi.

```bash
python3 -m unittest discover -s tests
```
