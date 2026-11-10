# Changelog

## OpenBeta 0.7.8 — 2026-11-10

- Pro jest domyślnym wyglądem: `/` otwiera Pro, Classic tylko po wybraniu przełącznikiem (`/?classic` zawsze Classic).
- Bez widoku Grid: Pro ma Focus i Canvas.
- Notatki na Canvas: stały blok z przewijanym tekstem, zapisywany na serwerze (`POST /api/canvas-notes`, `GET /api/recent` → `notes`). „▶ Utwórz projekt” zakłada z notatki projekt (zadanie = treść notatki) z dostępnymi modelami w trybie Auto — ekonomiczny; model z wyczerpanym limitem tygodniowym albo niedostępny jest wyłączony, wyczerpane okno 5 h nie. Notatka pokazuje potem numer i stan projektu.
- Migająca plakietka ▶ RUN przy projektach z działającą aplikacją (stos, okno projektu, notatka) i ich liczba w pasku stanu.
- Notatki zapisywane pojedynczo (`{"note"}` / `{"delete"}`; dwie karty nie nadpisują sobie notatek); niezapisana notatka zostaje na Canvas z ostrzeżeniem, zapis jest ponawiany, a tekst trzymany też w przeglądarce. Wcześniej nieudany zapis (np. przed restartem serwera) po kilku sekundach usuwał notatkę z ekranu.
- Poprawka: formularz nowego projektu i ustawienia modeli w Pro miały rozjechaną szerokość (klasa okien modeli na Canvas kolidowała z klasą formularza).

## OpenBeta 0.7.7 — 2026-11-10

Porządek w widoku Canvas wyglądu Pro; wygląd (przesuwanie, powiększanie, rozmyte panele) bez zmian.

- Canvas: po lewej aktywny projekt (ten, który pracuje) z oknami modeli, pod nim projekt wybrany ze stosu; po prawej stos zwiniętych projektów. Trzy bloki przeciąga się za nagłówek, całość przesuwa i powiększa jak dotąd.
- Belka projektu: klucz i nazwa, postęp netto, suma tokenów („2,3 mln”), ikona repozytorium GitHub (nowa karta). Lampka stanu świeci, nie mruga: pomarańczowa przy zatrzymanym, zielona przy ukończonym.
- Kolejka w nawiasie: kolejność zmienia się przeciąganiem belek albo z menu ⋯ (Alt + ↑ / ↓). Przestawia tylko projekty czekające w kolejce; zatrzymanego nie uruchamia.
- Grupy projektów i archiwum (przeciąganie na nagłówek albo menu ⋯), zapisane na serwerze; archiwum zwinięte, zarchiwizowane projekty nie zajmują miejsca w Grid.
- Bez animowanego tła (spadające znaki) i bez mrugania; lżejsza strona: na Canvas są dwa okna projektów zamiast wszystkich.
- Powiadomienia systemowe o nowych pytaniach i testach (Ustawienia Pro), które zostają do zamknięcia.
- Serwer: `POST /api/queue/order`, `POST /api/groups`; `GET /api/recent` podaje też tokeny projektu i grupy.

## OpenBeta 0.7.6 — 2026-11-09

Drugi wygląd panelu: Pro (futurystyczny terminal), przełączany z dotychczasowym Classic. Funkcje, dane i API bez zmian.

- Przełącznik CLASSIC / PRO w obu wyglądach, zapamiętany w przeglądarce: Classic pod `/`, Pro pod `/pro` (zapamiętany Pro otwiera się też z `/`; `/?classic` zawsze pokazuje Classic).
- Wspólna logika i komponenty obu wyglądów w `gemini_app/web/panel.js` i `panel.css` (przeniesione z `index.html` bez zmian działania). Pro ładuje te same pliki, więc widok Focus ma wszystkie zakładki i akcje Classic.
- Pro: górny pasek (widoki Focus / Grid / Canvas, palety BURSZTYN, FOSFOR, CYJAN, SAKURA, LIGHT), lewa szyna (projekty, historia, pytania i testy z licznikiem, limity, ustawienia), pasek stanu (liczby projektów i stanów, limity Claude, Codex, Gemini z datą odnowienia), powiadomienia w prawym górnym rogu (pytania i testy z przyciskami, przerwa limitu ze „Spróbuj teraz”, akceptacja skryptu przygotowania).
- Okna projektów jak terminale: klucz, tytuł, „led by @model”, ostatnie zdarzenia, stan słowem i ikoną, „❯” wysyła wiadomość do koordynatora. W Canvas okna modeli otwartego projektu są oknami podrzędnymi połączonymi liniami (animowana, gdy model pracuje); przeciąganie, powiększanie i układ zapisany w przeglądarce.
- Półprzezroczyste panele z rozmyciem tła i poświatą aktywnego okna; linie skanowania i znaki w tle z przełącznikiem, suwakami intensywności i przezroczystości; wyłączone przy `prefers-reduced-motion`, zatrzymane, gdy karta jest niewidoczna.
- Autor i link do licencji na belce obu wyglądów (Classic: dół panelu bocznego, Pro: pasek stanu i Ustawienia).
- README (PL/EN) i przewodniki (PL/EN) opisują oba wyglądy.
- Nowy punkt API tylko do odczytu `GET /api/recent`: ostatnie zdarzenia każdego projektu, model prowadzący, otwarte pytania i testy, skrypt czekający na akceptację.

## OpenBeta 0.7.5 — 2026-11-08

Wycieki tokenów znalezione w audycie projektów po wersji 0.7.4 (PR15–PR21).

- Wznowiony projekt nie wraca do starych sesji: pierwsza tura każdego modelu po restarcie silnika zaczyna nową sesję (PR15: Claude z kontekstem 441 tys.; PR17: Gemini 4,3 mln tokenów w czterech turach).
- Przegląd dostaje zmiany (diff od ostatniej tury recenzenta, do 30 000 znaków) i instrukcję, by nie otwierać całych plików bez potrzeby (przeglądy czytały pliki przez cat: 37–64% kosztu Claude).
- Zlecenie przy poprawnym planie trafia do najbliższej tury pracy jako nowe pozycje planu; osobna tura planu (w Auto: najwyższy dozwolony model) tylko bez planu albo z dedykowanym architektem (PR18: 6 tur planu na 17).
- RUN dokumentu buduje w osobnej kopii wersji (`runs/<projekt>/doc-vN`), nie w folderze „Uruchamiaj stąd”: budowanie zmieniało tam śledzone pliki i blokowało przestawienie folderu na nowszą wersję (PR17).
- Wersja polecana (RUN, folder „Uruchamiaj stąd”, wysyłka na GitHub) to najnowsza sprawdzona: przez oba modele, testy koordynatora albo jedyny włączony model. Wcześniej starsza wersja zaakceptowana przez dwa modele wygrywała z każdą nowszą (PR17: zakończony na v6, a RUN i folder zostały na v3). Komunikat końca projektu w trybie jednego modelu nie mówi już, że zaakceptowały „oba modele”.
- Antigravity (agy): każde uruchomienie z `useG1Credits: false` (bez płatnych kredytów, niezależnie od ustawień użytkownika) i limitem czasu tury 20 min (`SOL83_GEMINI_TURN_TIMEOUT`); nowy projekt domyślnie z Gemini 3.8 Flash, a „Domyślny w Antigravity” ma ostrzeżenie (limit schodzi według cen API, a domyślny model może być droższy).
- Projekt dokumentowy w Auto: pisze Gemini, a przegląd, który najwięcej czyta, przypada partnerowi (przegląd Gemini kosztował ok. 1,2 mln tokenów, PR21).

## OpenBeta 0.7.4 — 2026-11-08

Oszczędność limitów i przepływ przy awariach (audyt PR9 i PR15, `docs/AUDYT-TOKENY-2026-11-08.md`).

- Nowa sesja agenta w każdej turze (`GEMINI_ROTATE_AFTER`, domyślnie 1): kontekst niesie pakiet przekazania (zadanie, plan, zmiany od ostatniej tury modelu, skrócone do 4000 znaków) zamiast całej historii. Wcześniej wznawiana sesja czytała historię przy każdym kroku: w PR9 szósta tura sesji Gemini kosztowała 2,6 raza tyle co pierwsza.
- Zasada oszczędnej pracy dla modeli: plik w całości zamiast wielu edycji, testy i budowanie raz na koniec tury, krótkie wyjście poleceń, notatki z wyszukiwania w pliku.
- Rodzaj projektu (wykrywany z zadania albo wybrany): przy dokumencie i researchu modele nie budują zaplecza (testów, linterów, skryptów) i sprawdzają treść oraz źródła.
- Model, który zaakceptował kod, czeka tylko na partnera, który wróci w ciągu godziny (nie na limit tygodniowy).
- „Uruchom jako następny” dla projektu w kolejce albo zatrzymanego: wybrany projekt rusza jako pierwszy, gdy zwolni się miejsce; karta pokazuje miejsce w kolejce.
- Zatrzymanie zapisane w bazie jest respektowane przed każdą turą i w trakcie oczekiwania, także gdy sygnał do silnika zginął w trakcie jego startu (PR17: „Zatrzymaj teraz” 3 s po starcie silnika, a tura Gemini i tak ruszyła).
- „Działa” i „Nie mogę wykonać” bez komentarza tylko zapisują wynik testu i zamykają sprawę: zakończony projekt zostaje zakończony, a wersja jest oznaczona jako potwierdzona. Projekt wznawia dopiero „Nie działa”, „Częściowo” albo komentarz (PR15: dwa „Działa” wznowiły go na dwie rundy Opus xhigh).
- Awarie: kolejna próba modelu po nieudanej turze zaczyna nową sesję; błędy liczone osobno dla każdego modelu, z rosnącą przerwą (10, 20, 40… min, do 2 h) i komunikatem po trzech z rzędu; model, który zaakceptował bieżący kod, nie dostaje pustej tury ani wymuszonego przejęcia (PR9: sześć utraconych przeglądów Gemini i pięć pustych tur Claude).

## OpenBeta 0.7.3 — 2026-11-08

- Rzadszy przegląd zmian: drugi model przegląda pracę, gdy zamknie się etap planu (funkcja, której zadania są gotowe), przy dużej zmianie (od 500 linii), przy deklaracji gotowości albo gdy nie ma poprawnego planu, a najpóźniej co 3 tury implementacji (`SOL83_REVIEW_EVERY`). Wcześniej przegląd był po każdej turze: połowa tur w PR9, 76% tokenów w PR14. Ustawienie projektu „Po każdej zmianie” przywraca dawny rytm.

## OpenBeta 0.7.2 — 2026-11-08

Po zgłoszeniu dotyczącym PR13/PR14 i audycie zużycia tokenów (`docs/AUDYT-TOKENY-2026-11-08.md`).

- RUN: komentarze w instrukcjach nie trafiają już jako argumenty (PR14: `build.py '#' writes ...` kończył się od razu błędem); prozatorskie „Open dist/x.html…” nie jest odrzucane jako program.
- RUN dla dokumentów: budowanie do końca, potem folder wersji serwowany na osobnym porcie i link do pliku HTML; stan ostatniego RUN z końcówką logu w karcie „Do testów”.
- Polecenia do terminala: gotowa sekwencja `cd` + polecenia bez komentarzy; lokalny koordynator przepisuje ją w tle, a wynik jest sprawdzany linia po linii.
- Daty przy odnowieniu limitu i końcu przerwy (dzień tygodnia, data, godzina; odliczanie w dniach i godzinach).
- Prośby o testy: domyślnie tylko przy wersji końcowej (ustawienie projektu: końcowa / każda wersja / wcale); modele nie zlecają testów, budowania ani skryptów, a w dokumentach i researchu nie proszą o testy w trakcie pracy.
- Ustawienie projektu „Claude może czytać strony WWW (WebFetch)”; modele nie pytają o dostęp do narzędzi w pytaniach do użytkownika.
- Reguła „modele oceniły kroki jako nieprzybliżające” i sygnał efektywności pomijają ocenę własnego kroku (PR9 zatrzymał się na czterech samoocenach Codexa).

## OpenBeta 0.7.1 — 2026-11-08

Poprawki po zgłoszeniu z 8 listopada (projekty PR10, PR11, PR13, PR14). Szczegóły i dowody: `docs/TRACEABILITY.md`, sekcja „Etap 9”.

- Oczekiwanie na limit: odrzucenie przez Claude niesie godzinę resetu podaną przez dostawcę (`resetsAt`), a nie zgadywane +30 min (8.11: blokada do 03:29 przy resecie o 03:00). Godzina z `claude /usage` (z dokładnością do minuty, zaokrąglona w dół) dostaje minutę zapasu.
- Każda przerwa ma źródło: odczyt, komunikat dostawcy, szacunek, awaria, logowanie. Szacunek jest w panelu oznaczony „(szacunek)”.
- Krótsze i jawne przerwy: limit bez godziny resetu 15 min, podwajane do 2 h (było 30 min do 8 h); chwilowa awaria (rate limit, sieć, przeciążenie) 5 min; inny błąd 10 min; logowanie 60 min.
- „Spróbuj teraz”: zdejmuje przerwę Sol-83 dla dostawcy i budzi czekające projekty, które od razu czytają limity na nowo (panel limitów i belka projektu).
- Komunikat oczekiwania mówi prawdę: który model, dlaczego, do kiedy i czy to szacunek (np. „Pracę „plan” może wykonać tylko Claude, a teraz nie może: Claude: limit 5h 100%, do 03:00. Gemini: nie ma roli do pracy „plan”.”). Czekanie na przegląd pokazuje recenzenta, który wróci najwcześniej, a nie pierwszego w kolejności.
- Lista projektów: sekcja „W toku” z jednoznacznym stanem (słowo i ikona) i powodem oczekiwania, pod nią zwinięte grupy „Wymaga uwagi”, „Zatrzymane”, „Ukończone” z licznikami; rozwinięcie zapamiętane w przeglądarce.
- Pytania i testy: wynik testu dla nowszej wersji rozstrzyga test zapisany przy starszej (wcześniej uznawany za „spóźniony”, przez co rekord zostawał otwarty, a powiadomienie wracało); odpowiedziane trafiają do „Zrobione” z informacją, czy modele już je dostały; zmiana odpowiedzi zastępuje notatkę czekającą w kolejce; „Działa” w karcie wersji nie dubluje wyniku. Naprawa przy starcie poprawia rekordy zostawione przez starą regułę i wycofuje zdublowane notatki.

## OpenBeta 0.7.0 — 2026-11-07

Przebudowa według specyfikacji z 7 listopada 2026 i audytu z 3 listopada 2026. Szczegóły: `docs/TRACEABILITY.md`, `docs/AUDIT-2026-11-07.md`.

- Bezpieczeństwo: piaskownica systemu dla testów, `.gemini-setup` (po akceptacji treści), procesu Antigravity i RUN; skan sekretów każdej wysyłki; maskowanie sekretów; brak kluczy API u agentów; usunięte stare polecenia CLI.
- Dane oddzielone od kodu (`~/Sol-83-data`, `SOL83_HOME`), `sol83 migrate`, `sol83 doctor`.
- Trwała kolejka zleceń, atomowe zamykanie, praca z przerwanych tur wraca do kolejki; scalające zapisy stanu projektu.
- Kontrakt planu (PL/EN), rewizje ostatniego poprawnego planu, ograniczona naprawa; postęp netto i bramki odbioru.
- Panel kont i logowania, klasy błędów, reset podany przez dostawcę; znormalizowane tokeny (przyrosty sesji, poprawka odczytu Codex), udział w oknach limitów.
- Auto — ekonomiczny / power, katalog modeli ze źródłami, najwyższe modele tylko ręcznie z potwierdzeniem.
- Kilka ról na model; pytania, decyzje i testy ręczne; zamówienia treści z akceptacją; stały język projektu; klucze PRn/rr.
- RUN z kontrolowanym runnerem; widok wersji; Git w kontekście projektu; licencja projektu.
- Interfejs: belka akcji, Activity z turami, Pytania i testy, usunięta zakładka Live, skórki LIGHT/DARK/SAKURA/TERMINAL, przesuwany panel boczny.

## 0.6.x — 2026-11-02/03

Wersje sprzed OpenBeta (repozytorium MikeMcqueen83/Sol-83). Opis: `docs/history/`.
