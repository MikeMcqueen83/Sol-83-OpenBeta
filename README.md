# Sol-83

Codex, Claude Code i opcjonalnie Gemini przez Antigravity pracują na zmianę nad jednym projektem, sprawdzają się nawzajem i przekazują pracę, gdy któremuś kończy się limit. Dzięki temu oba abonamenty są wykorzystywane razem, a Ty dostajesz tylko sprawdzone wersje. Silnikiem jest przebudowany Duet.

## Start

```bash
cd <folder z kodem Sol-83>
./sol83 serve
```

Dane (projekty, przebiegi, baza) są oddzielone od kodu: domyślnie `~/Sol-83-data`, inny folder wskazuje zmienna `SOL83_HOME`. Starszą instalację, która trzymała dane obok kodu, przenosi `./sol83 migrate --from <stary folder>` (kopia, oryginał zostaje nietknięty). `./sol83 doctor` sprawdza CLI, logowanie, piaskownicę i katalog danych bez wywoływania modeli.

Interfejs: http://127.0.0.1:8765

Serwer można bezpiecznie zamknąć i uruchomić ponownie: pracujące projekty działają dalej, a koordynator podłącza się do nich sam. Po restarcie komputera projekt pokaże status „Wymaga uwagi” i wznowisz go przyciskiem. Praca jest zachowana.

Po świeżym sklonowaniu repozytorium pobierz Duet i nałóż łatkę:

```bash
./bin/setup
```

Logowanie wykonuje się raz:

```bash
./bin/claude auth login
```

```bash
codex login
```

Gemini jest opcjonalny, jako trzeci model. Sol-83 uruchamia go przez Antigravity CLI (`agy`), bo Gemini CLI nie jest już wspierane. Instalacja:

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

Logowanie kontem Google, bez klucza API: pierwsze polecenie otwiera przeglądarkę, a sesja trafia do pęku kluczy macOS.

```bash
agy -p "test"
```

Lista modeli dostępnych dla Twojego konta, którą panel czyta sam:

```bash
agy models
```

Abonament Google AI Pro albo Ultra daje wyższe limity niż darmowe konto. Nie ustawiaj `GEMINI_API_KEY`: adapter i tak usuwa klucze ze środowiska `agy`. Panel pokazuje w limitach, czy Antigravity jest gotowy.

## Co robi panel

- **Nowy projekt:** wklej plik .md albo wpisz zadanie. Podaj polecenie testów, bo tylko na jego podstawie powstają numerowane wersje. Możesz je ustawić albo zmienić później w Ustawieniach: działa od końca bieżącej tury. Puste pole folderu tworzy nowy projekt w `projects/`. Istniejący folder musi być repozytorium Git bez niezapisanych zmian.
- **Model i poziom myślenia:** wybierasz je osobno dla Claude i Codexa, przy zakładaniu projektu i w trakcie pracy. Zmiana obowiązuje od następnej tury. Lista modeli Codexa pochodzi na żywo z Codexa.
- **Tryb jednego modelu:** opcja **Wyłączony** w wyborze modelu. Wyłączony model nie dostaje tur, a zmiana w trakcie pracy działa po bieżącej turze. Projekt kończy akceptacja włączonego modelu i nie czeka na wyłączonego partnera. Wersja zaakceptowana przez jeden model ma osobny poziom „Jeden model”. Przynajmniej jeden model musi zostać włączony, a wyłączony nie musi być zalogowany.
- **Limity:** okno 5 h i tydzień dla obu modeli, z czasem resetu. Oba odczyty nie zużywają limitów.
- **Zakładki projektu:** Przebieg, Plan, Na żywo, Treści (zamówione grafiki i teksty) (ostatnie działania i rozumowanie modelu z jego dziennika sesji, bez kosztów), Wersje, Efektywność (z opisem, jak ją czytać), Ustawienia (modele i GitHub), Zadanie. Karta **Do testów** pokazuje folder „Uruchamiaj stąd” i polecenia uruchomienia.
- **Wiadomości:** patrz niżej.
- **Activity:** pytania, uwagi, odpowiedzi modeli i pełny tekst każdej tury, z możliwością rozwinięcia. Po ukończeniu projektu u góry pojawia się odpowiedź końcowa.
- **Zatrzymaj po turze / Zatrzymaj teraz / Wznów.** Zatrzymanie ma pierwszeństwo: reset limitu nigdy go nie cofa.
- **Usuń projekt** (na dole zakładki Ustawienia, z potwierdzeniem): usuwa projekt na zawsze, bez archiwum. Znikają rekordy, historia, wersje, transkrypty, warsztat agentów `worktrees/<id>`, folder testowy i `runs/<id>`. Repozytorium utworzone przez Sol-83 w `projects/` znika z dysku. Twoje własne repozytorium zostaje: znikają z niego tylko gałąź `gemini/<id>`, tagi wersji i foldery robocze Sol-83. Działający projekt najpierw się zatrzymuje. GitHub zostaje nietknięty.
- **Full Power:** patrz niżej.
- **GitHub:** patrz niżej.
- **PL / EN:** przełącznik języka w lewym górnym rogu. Tłumaczy interfejs, zdarzenia i komunikaty. Odpowiedzi na pytania o status przychodzą w wybranym języku, a raporty agentów zostają w języku, w którym je napisali.

## Co testować: wersje

Agenci pracują na ruchomej gałęzi. Po każdej turze koordynator zapisuje punkt kontrolny i sam uruchamia polecenie testów. Numer wersji powstaje tylko wtedy, gdy testy przejdą. Sam raport modelu nie wystarcza.

| Poziom | Znaczenie |
|---|---|
| Przeszła testy | Koordynator uruchomił testy i przeszły |
| Sprawdzona przez oba modele | Oba modele zaakceptowały dokładnie ten sam stan kodu |
| Przegląd jednego modelu (Full Power) | Ten sam model sprawdził kod w nowej sesji |
| Jeden model | Drugi model jest wyłączony, więc wersję zaakceptował tylko jeden |
| Bez testów | Nie podano polecenia testów, jest tylko deklaracja agenta |

Karta **Do testów** zawsze pokazuje wersję, którą warto sprawdzać, wraz z listą kroków od modelu. To, co jest w toku, jest oznaczone jako stan roboczy. **Działa** zapisuje Twoje potwierdzenie. **Nie działa** odsyła wersję do poprawy z Twoim opisem i wznawia projekt.

**Uruchamiaj stąd.** Karta Do testów i karta odpowiedzi końcowej podają folder z najnowszą wersją rekomendowaną i polecenia uruchomienia od zera, zaczynające się od `cd <folder>`. Polecenia pochodzą z sekcji `JAK URUCHOMIĆ:`, którą model dodaje przy LGTM. Gdy jej brak, z pola `run` planu, a potem z sekcji README o uruchomieniu. Agenci nigdy nie pracują w tym folderze.

- **Projekt utworzony przez Sol-83** (w `projects/`): to folder repozytorium. Jego `main` przesuwa się na każdą nową wersję rekomendowaną (`git merge --ff-only`). Niezapisane zmiany w folderze albo własne commity na `main` wstrzymują przesunięcie, a powód pojawia się raz w Activity.
- **Twoje repozytorium** (podany folder albo klon z GitHuba): `main` zostaje nietknięty. Folderem jest `worktrees/<id>-testy`, który sam przechodzi na każdą nową wersję. Kod jest na gałęzi `gemini/<id>`.
- **Testuj tę wersję** w zakładce Wersje ustawia folder na wybraną wersję do czasu kolejnej nowej. Starsza wersja projektu Sol-83 jest pobierana bez cofania `main`.
- **Nie działa** nie cofa folderu do starszej wersji: zostaje na odrzuconej do czasu nowszej. Nowe funkcje lepiej zlecać w oknie wiadomości, bo „Nie działa” oznacza wersję jako zepsutą.

Repozytorium i warsztat agentów `worktrees/<id>` są na rozwijanej liście „Pozostałe foldery”. Wersje mają tagi `gemini/<id>/v<numer>`.

## Jak działa przekazywanie

Decyzje podejmuje koordynator, a nie modele: model, któremu skończył się limit, nie może już niczego zdecydować. Koordynator czyta oba limity i przed każdą turą wybiera wykonawcę.

- **Oba dostępne:** praca na zmianę. Pierwszą, najdroższą turę dostaje model z większym zapasem.
- **Jeden osiąga próg (domyślnie 95%):** drugi przejmuje pracę na granicy tury i dalej pracuje sam.
- **Limit skończył się w trakcie tury:** częściowa praca trafia do punktu kontrolnego, a partner dostaje polecenie, by najpierw odtworzył stan i niczego nie uznawał za gotowe.
- **Model sam skończył:** czeka na przegląd partnera, nie zużywając limitów. Kolejka przechodzi wtedy do następnego projektu.
- **Oba niedostępne:** czekanie do resetu, bez żadnych prób, potem automatyczne wznowienie.

Projekt kończy się, gdy oba modele zaakceptują ten sam stan kodu, a testy przejdą. Jeśli drugi model długo nie wraca, możesz wybrać **Przyjmij bez przeglądu**. Chwilowe awarie są ponawiane, a problem z logowaniem nie jest mylony z limitem. Po 6 turach bez zmian w kodzie albo przy cyklicznym cofaniu zmian projekt zatrzymuje się i czeka na Ciebie.

System nie przechodzi na płatne API ani dokupione kredyty. Adapter Claude przerywa turę, gdyby zaczęła korzystać z płatnego rozszerzenia limitu.

## Gemini jako trzeci model

W nowym projekcie Gemini ma własny wybór modelu, poziomu myślenia i roli. Modele pochodzą na żywo z `agy models`, na przykład `gemini-4-argon-high` albo `gemini-3.8-flash-low`, a poziom myślenia jest już w ich nazwie. Przy „Domyślny w Antigravity” poziom myślenia trafia do `agy --effort`. Domyślnie Gemini jest wyłączony, gdy `agy` nie jest zainstalowany. Z trzema modelami turę dostaje ten, który najdawniej pracował, a projekt kończy akceptacja dwóch modeli z rolą obejmującą przegląd.

- **Adapter:** Duet mówi kontraktem Gemini CLI, więc `bin/gemini` tłumaczy go na `agy -p … --output-format json`. Odpowiedź bierze z pola `response`, a sesję wznawia przez `--conversation <id>`. Gdy `agy` bez terminala nic nie wypisze, co zdarza się w części wersji, adapter powtarza wywołanie w pseudo-terminalu.
- **Limity:** Antigravity ich nie podaje. Wyczerpanie poznaję po błędzie (HTTP 429, `RESOURCE_EXHAUSTED`, „quota exceeded”). Wtedy Gemini czeka 30 minut, a każde kolejne wyczerpanie z rzędu podwaja przerwę, do 8 godzin. Udana tura zeruje licznik.
- **Piaskownica:** tura agenta działa w folderze projektu (`--add-dir`), w trybie `accept-edits` z piaskownicą poleceń `agy --sandbox` i bez pytań o zgodę (`--dangerously-skip-permissions`), tak jak Claude z piaskownicą. Pytania o status idą w trybie `plan`, tylko do odczytu. To piaskownica samego Antigravity, a nie systemowa, jak u Claude i Codexa.
- **Zatrzymanie w trakcie tury:** narzędzia uruchomione przez `agy` mogą chwilę dłużej trzymać blokadę indeksu Git. Koordynator czeka na nią do 30 s przed zapisem punktu kontrolnego, a porzuconą usuwa.
- **Projekty sprzed Gemini** pokazują go w Ustawieniach jako wyłączonego. Po włączeniu dołącza po bieżącej turze: silnik uruchamia się od nowa z trzema modelami, wszystkie dostają świeże sesje i zadanie, a numeracja tur i wersji biegnie dalej. Zatrzymany albo ukończony projekt dostaje Gemini przy następnym uruchomieniu.

Sprawdzone na żywo z `agy` 1.4.12: krótka tura trwa około 5 s, wznowienie przez `--conversation` pamięta poprzednią odpowiedź, a `usage` podaje tokeny. Ilustracja 256×256 powstała w około 80 s narzędziem `generate_image`, przez subagenta `image-generator`. Nie wiadomo jeszcze, jak brzmi błąd po wyczerpaniu limitu: dziś rozpoznawane są 429, `RESOURCE_EXHAUSTED` i „quota exceeded”.

## Role modeli

Każdy model ma rolę, wybieraną przy zakładaniu projektu i w Ustawieniach. Przed każdą turą koordynator ustala rodzaj pracy: **plan** (brak planu albo nowe zlecenie), **implementacja** (zadanie z planu) albo **przegląd** (po implementacji albo po zgłoszeniu LGTM). Turę dostaje model, którego rola obejmuje tę pracę.

| Rola | Zakres |
|---|---|
| Ogólna | Wszystko, jak dotąd |
| Architekt | Plan, przebudowa planu, research |
| Implementujący | Zadania z planu |
| Tester | Przegląd, testy, plan regresji |
| Analityk systemowy | Luki względem zadania i plan ich łatania jako dług |
| Twórca treści | Zamówione grafiki, teksty, opisy i fabuła |

- Model z daną rolą ma pierwszeństwo przed modelem Ogólnym. Spośród równych turę dostaje ten, który najdawniej pracował, więc przegląd trafia do innego modelu niż autor zmian.
- Projekt nie wystartuje, jeśli jakiejś pracy nie obejmuje rola żadnego włączonego modelu, na przykład Architekt i Implementujący bez nikogo do przeglądu. Ta sama kontrola działa przy zmianie ról i wyłączaniu modelu.
- Gdy model z rolą jest niedostępny, w Ustawieniach wybierasz: jego pracę **przejmuje model z rolą Ogólna** albo **projekt czeka**. Czekanie na rolę nie wstrzymuje kolejki innych projektów.
- Projekt kończy akceptacja dwóch modeli, których rola obejmuje przegląd, albo jedynego takiego modelu.
- Przykład: Opus jako Architekt, Codex z rolą Ogólna. Opus pracuje tylko przy planie, jego przebudowie i researchu, a resztę robi Codex.

### Twórca treści i zamówienia

Modele, które nie zrobią grafiki albo nie powinny tracić tury na fabułę, zamawiają treść w `.sol83/assets.json`: `{"id", "type": "image" | "text", "prompt", "path", "size", "style", "status": "requested"}`. Gdy w zespole jest włączony model z rolą **Twórca treści**, czekające zamówienia dostają jego turę przed implementacją. Twórca tworzy pliki pod wskazanymi ścieżkami i oznacza zamówienia jako gotowe albo z błędem. Projekt nie kończy się, dopóki zamówienia czekają.

- **Najlepiej Gemini przez Antigravity:** generuje grafikę modelem graficznym (`generate_image`). Sprawdzone na żywo: ilustracja 256×256 w akwareli powstała w około 80 s. Ta rola ma wyjątek od zakazu subagentów, bo Antigravity generuje obrazy przez subagenta `image-generator`.
- **Zakładka Treści** w projekcie pokazuje zamówienia z miniaturami grafik, podglądem tekstów i statusem. Tu też zamawiasz własne: zamówienie trafia do pliku przed następną turą i wznawia ukończony projekt.
- Bez Twórcy treści zamówienia robią modele z rolą Ogólna, jak zwykłą pracę, ale Claude i Codex nie wygenerują ilustracji.

Koordynator wybiera wykonawcę spośród dowolnej liczby modeli, a łatka Duet przyjmuje trzeciego agenta, gdy turami steruje koordynator.

## Plan, backlog i dług techniczny

W pierwszej turze modele zapisują plan w repozytorium projektu, w `.sol83/plan.json`. Zawiera architekturę w kilku zdaniach, sposób uruchomienia aplikacji i drzewo o dwóch poziomach: 5–12 funkcji, a pod nimi zadania na 1–3 tury. Każda pozycja ma priorytet (*musi*, *powinno*, *może*), status i budżet tur. Plan jest wersjonowany razem z kodem.

- **Każda tura wskazuje swoją pozycję** w linii `PRACA: <id>`. Koordynator przypisuje jej koszt w pełnych procentach limitu tygodniowego. Zakładka **Plan** pokazuje drzewo z kosztem każdej pozycji i podział: ile limitu poszło na funkcje obowiązkowe, ile na dodatki, ile na dług, a ile na pracę bez przypisania.
- **Głębokość pracy:** model naprawia od razu tylko to, co psuje build lub testy, blokuje odbiór bieżącej pozycji albo jest tańsze niż opisanie. Każda inna usterka trafia do planu jako **dług** (`kind: debt`) z kategorią (bug, ui, perf, refactor, test, docs) i opisem objawu.
- **Budżet:** gdy pozycja przekroczy budżet tur, koordynator każe w następnej turze zdecydować: domknąć ją minimalnie albo odłożyć z opisem. Przy ponad dwukrotnym przekroczeniu projekt się wstrzymuje.
- **Nowe zlecenie przebudowuje plan** z uwzględnieniem istniejących pozycji i długu.
- **Plan z wcześniejszego projektu:** gdy nowy projekt startuje na repozytorium, które ma już `.sol83/plan.json` (na przykład pobranym z GitHuba po poprzednim projekcie), pierwsza tura buduje plan od nowa pod nowe zadanie. Ze starego planu przechodzi tylko to, co dotyczy nowego zadania.
- **Dowolną pozycję zlecasz przyciskiem „Zleć”** w zakładce Plan, także dług z backlogu. Trafia na początek następnej tury.

Koszt tego podejścia: ułożenie planu to jedna tura na początku i jedna przy każdym nowym zleceniu. Skrót planu w każdej turze to około 300 tokenów, czyli poniżej 1% wejścia tury.

## Wiadomości do modeli

Jedno okno w każdym projekcie przyjmuje pytanie o status, zlecenie albo uwagę. **Koordynator wiadomości** odpowiada i rozpoznaje rodzaj wiadomości. Zlecenie i uwagę koordynator przekazuje agentom, a zlecenie dodatkowo przebudowuje plan. Przełącznik **Przerwij bieżącą pracę** zatrzymuje turę od razu i przekazuje wiadomość.

Koordynatora wybierasz w zakładce Ustawienia, a wybór dotyczy wszystkich projektów:

- **Lokalny LLM przez Ollamę** (`gemma4:31b` pod `http://127.0.0.1:11434`): domyślny, gdy Ollama ma ten model, bo nie zużywa abonamentów. Nie czyta plików, tylko dostaje fakty od koordynatora i skrót planu. Odpowiedź trwa około pół minuty.
- **Model, który teraz nie pracuje:** Claude albo Codex, z odczytem plików projektu. To domyślny wybór bez Ollamy.
- **Claude, Codex albo Gemini:** zawsze ten sam, z odczytem plików, bez zmian w kodzie.

Pod odpowiedzią rozpoznaną jako zlecenie albo uwaga jest przycisk **Cofnij przekazanie**. Usuwa wiadomość, zanim trafi do tury, a projekt, który ta wiadomość wznowiła, wraca do poprzedniego stanu. Wiadomość czekająca na turę budzi też model, który czekał na przegląd drugiego: nowa praca nie czeka do jego powrotu.

Gdy wybrany nie może odpowiedzieć, odpowiada lokalny model. Bez niego koordynator odpowiada z własnych zapisów: wiadomość zakończona znakiem zapytania jest pytaniem, a każda inna trafia do agentów.

## Monitor efektywności

Sol-83 sprawdza, czy praca nadal się opłaca, i mówi Ci, kiedy wkroczyć. Karta **Efektywność** w projekcie pokazuje:

- **Cel według modeli:** liczba spełnionych kryteriów odbioru i jej przebieg.
- **Ocenę kolejnych kroków:** każdy model surowo ocenia poprzedni krok partnera względem celu, a nie jakości kodu. To niezależna ocena drugiego modelu w każdej turze i nie kosztuje żadnego dodatkowego wywołania.
- **Koszt:** punkty limitu, które przesunęła każda tura. Odczyt limitów jest bezpłatny, ale wlicza się do niego także inna praca na tym samym koncie w tym czasie.
- **Tokeny:** suma na model i tabela ostatnich tur: wejście (cały przeczytany kontekst z pamięcią podręczną), wyjście i numer tury w sesji. Claude i Antigravity podają je w wyniku tury, Codex tylko sumę. Wzrost wejścia z każdą turą tej samej sesji pozwala dobrać `GEMINI_ROTATE_AFTER` (dziś 6).

**Sygnał do interwencji** pojawia się na górze projektu, w Activity i jako powiadomienie macOS, gdy:

- cel stoi w miejscu przez 4 tury albo modele oceniają kolejne kroki jako nieprzybliżające,
- są 3 tury bez nowej wersji albo duży koszt bez postępu,
- w ostatnich turach zmienia się dużo wierszy, a netto zostaje mało, czyli praca kręci się w kółko,
- te same testy padają raz za razem albo tury są przerywane.

Projekt sam się wstrzymuje po 4 krokach z rzędu ocenionych jako nieprzybliżające, po 8 turach bez nowej wersji i po 6 turach bez żadnej zmiany w kodzie. Wtedy Ty decydujesz, co dalej.

## Full Power

Gdy drugi model czeka na reset, ten sam model robi przegląd i poprawki w nowej sesji, bez pamięci własnego rozumowania, zamiast czekać. Próg przekazania przestaje obowiązywać, a praca trwa do odmowy dostawcy. **To zużywa limity bardzo agresywnie.** Liczba takich przeglądów pod rząd jest ograniczona do 5. Nie zastępuje to przeglądu drugiego modelu: wersja dostaje osobny poziom, a projekt nadal czeka na jego ocenę albo Twoją decyzję.

## GitHub

Każdy projekt może trafić do repozytorium prywatnego albo publicznego. Wymaga to jednorazowego logowania:

```bash
gh auth login
```

Na GitHub trafiają wyłącznie numerowane wersje, nigdy prace w toku. Wersja zgłoszona jako niedziałająca nie zostanie wysłana. Domyślna widoczność to prywatna.

**Praca w istniejącym repozytorium.** Lista **Repozytoria GitHub** w panelu pokazuje repozytoria Twojego konta. Kliknij jedno, opisz zadanie i zleć je. Sol-83 klonuje repozytorium do `projects/github/`, a agenci pracują na gałęzi `gemini/<id>` od najnowszego `main`. W repozytorium prywatnym każda nowa wersja trafia na tę gałąź automatycznie, a w karcie GitHub jest link do Pull Requesta. `main` pozostaje nietknięty.

**Wysyłka:**

- **Nowe repozytorium:** wybrana wersja trafia na `main`, z tagiem `vN`.
- **Projekt mający już GitHub jako `origin`:** praca trafia na osobną gałąź `gemini/<id>`.
- **Automatycznie:** działa tylko w repozytoriach prywatnych i można ją wyłączyć w karcie GitHub. Repozytorium publiczne zawsze czeka na Twoje kliknięcie.
- **Sekrety:** przed każdą wysyłką (także prywatną i automatyczną) oraz przy zmianie widoczności koordynator szuka sekretów w plikach i w całej historii. Jeśli coś znajdzie, wstrzymuje wysyłkę i podaje pliki; wysłać można dopiero po potwierdzeniu dokładnie tej listy. To kontrola typowych wzorców, a nie gwarancja.
- **Bez nadpisywania:** nie ma wymuszonego wypychania. Jeśli zdalne repozytorium jest dalej, wysyłka się nie uda, a historia zostaje nietknięta.

## Bezpieczeństwo

Agenci działają w piaskownicy systemu macOS: zapisują tylko w swoim folderze roboczym i nie mają sieci. Dzięki temu Claude może uruchamiać testy bez pytania o zgodę, tak jak Codex. W piaskownicy nie ma też GPU ani lokalnego Ollamy.

Kod napisany przez agentów, który uruchamia sam koordynator (polecenie testów, `.gemini-setup`, cały proces Antigravity `agy`), działa w **piaskownicy systemu**: na macOS Seatbelt (`sandbox-exec`), na Linuksie bubblewrap. Zapis tylko w folderze projektu i prywatnym katalogu tymczasowym, bez odczytu kluczy SSH, loginów CLI i danych przeglądarek, a testy domyślnie bez sieci wychodzącej (localhost działa, GPU też). Bez piaskownicy Sol-83 takiego kodu nie uruchamia, chyba że świadomie na to pozwolisz. Szczegóły i ograniczenia: `docs/AUDIT-2026-11-07.md`.

Serwer nasłuchuje tylko na tym komputerze i odrzuca żądania z innych stron, bo POST potrafi uruchamiać agentów. `sol83` odmawia startu, gdy wykryje konfigurację kluczy API.

Agenci nie mają sieci w poleceniach powłoki, więc nie zainstalują zależności. Muszą one być już dostępne. Mogą natomiast szukać w internecie wbudowanym wyszukiwaniem swojego dostawcy, które działa po jego stronie: Codex z własnym narzędziem, a Claude z WebSearch.

## Przygotowanie projektu

Worktree zawiera tylko pliki śledzone przez Git, bez `.venv` czy `node_modules`. Plik `.gemini-setup` w repozytorium projektu linkuje środowisko i kopiuje dane do folderu roboczego i testowego. To kod z repozytorium, więc uruchamia się dopiero po Twojej akceptacji jego dokładnej treści (Ustawienia projektu), w piaskownicy z dostępem do sieci. Każda zmiana skryptu wymaga ponownej akceptacji.

## Budowa

| Miejsce | Rola |
|---|---|
| `gemini_app/scheduler.py` | Wybór wykonawcy, przekazania, przejęcia, wersje |
| `gemini_app/limits.py` | Odczyt limitów, klasyfikacja błędów, polityka dostępności |
| `gemini_app/supervisor.py` | Kolejka, procesy silnika, stop i wznowienie |
| `gemini_app/observer.py` | Odpowiedzi na pytania o status |
| `gemini_app/monitor.py` | Koszt i wartość tur, sygnały do interwencji |
| `gemini_app/plan.py` | Plan projektu, budżety pozycji, dług |
| `gemini_app/roles.py` | Role modeli i rodzaj pracy w turze |
| `gemini_app/livelog.py` | Podgląd pracy modeli na żywo |
| `gemini_app/server.py`, `web/` | Interfejs |
| `bin/claude` | Adapter: zdarzenia limitów, piaskownica, blokada płatnego rozszerzenia |
| `bin/gemini` | Adapter Gemini przez Antigravity `agy`: bez kluczy API, piaskownica `agy` |
| `gemini_app/github.py` | Publikacja wersji, kontrola sekretów |
| `gemini_app/messages.py` | Teksty po polsku i angielsku |
| `patches/duet-gemini.patch` | Zmiany w Duecie: harmonogram tur zamiast sztywnej naprzemienności, do trzech agentów |

Duet nie jest częścią tego repozytorium. `bin/setup` pobiera go w commicie z `config/upstream.json` i nakłada łatkę. Po zmianie `vendor/duet` zaktualizuj łatkę poleceniem `git -C vendor/duet diff > patches/duet-gemini.patch`. Zapisane dane w katalogu danych: `state/gemini.db`, `runs/<id>/`, kod w `worktrees/<id>/`.

## Testy

```bash
python3 -m unittest discover -s tests
```

```bash
cd vendor/duet && DUET_METRICS=0 python3 -m unittest discover -s tests
```

Pierwszy zestaw uruchamia prawdziwy silnik i koordynatora na atrapach obu CLI, które mówią dokładnie ich formatem, także prawdziwym komunikatem limitu Codexa. Nie zużywa abonamentów.

Projekty uruchamia się wyłącznie z panelu, przez koordynatora. Dawne polecenia `start`, `demo`, `resume` usunięto, bo omijały jego zasady.
