# Sol-83 Source-Available License — PROJEKT / DRAFT

> **Projekt warunków, wymaga weryfikacji prawnej przed użyciem. Do czasu przyjęcia ostatecznej wersji przez autora
> obowiązuje zasada „wszelkie prawa zastrzeżone”, z wyjątkiem komponentów na własnych licencjach (THIRD_PARTY_NOTICES.md).**
>
> **Draft terms, to be reviewed by a lawyer before use. Until the author adopts a final version, all rights are reserved,
> except for components under their own licenses (THIRD_PARTY_NOTICES.md).**

Copyright (c) 2026 Michał Werpachowski. Wszelkie prawa zastrzeżone, z zastrzeżeniem poniższych warunków.

To jest licencja **source-available**, a nie licencja open source zgodna z definicją OSI.

## 1. Zakres

Warunki dotyczą kodu i dokumentacji Sol-83 autorstwa Michała Werpachowskiego w tym repozytorium. Nie dotyczą:
- komponentów zewnętrznych, które zachowują swoje licencje (w szczególności silnika Duet na licencji MIT),
- projektów tworzonych przez użytkowników przy pomocy Sol-83: ich licencję wybiera użytkownik.

## 2. Dozwolone bez osobnej zgody (wyłącznie użycie niekomercyjne)

Osoba fizyczna może bez osobnej zgody przeglądać, pobierać, uruchamiać i modyfikować oprogramowanie wyłącznie do celów niekomercyjnych: prywatnych, edukacyjnych, naukowych i do oceny oprogramowania. Może też udostępniać swoje zmiany przez fork lub osobną gałąź, na warunkach tej licencji, z zachowaniem tej informacji o prawach autorskich i bez prawa udzielania dalszych licencji.

## 3. Użycie komercyjne: wyłącznie za uprzednią pisemną zgodą autora

Bez uprzedniej pisemnej zgody autora zabronione jest każde użycie komercyjne. Użyciem komercyjnym jest w szczególności:

1. każde użycie przez przedsiębiorcę, spółkę, firmę lub inną organizację działającą w celu zarobkowym albo na jej rzecz, także użycie wyłącznie wewnętrzne, testowe lub pilotażowe;
2. użycie w działalności, która przynosi lub ma przynosić przychód, bezpośrednio lub pośrednio, w tym przy świadczeniu usług, doradztwie i pracy na zlecenie;
3. udostępnianie oprogramowania lub jego funkcji innym jako usługi (np. SaaS, hosting, API) albo jako części oferty płatnej lub finansowanej reklamą;
4. włączenie oprogramowania albo **dowolnej jego części**, zmienionej lub nie, w tym kodu przepisanego, przetłumaczonego na inny język programowania lub przeniesionego na inną platformę, oraz opracowań (utworów zależnych), do produktu, usługi lub rozwiązania, które jest sprzedawane, licencjonowane, oferowane albo w inny sposób monetyzowane;
5. wykorzystanie kodu lub dokumentacji do trenowania albo dostrajania modeli AI przeznaczonych do użycia komercyjnego.

Zgoda dotyczy wyłącznie zakresu w niej wskazanego i nie przechodzi na inne podmioty.

## 3a. Granica ochrony: pomysł a kod

Prawo autorskie chroni sposób wyrażenia (kod, dokumentację, interfejs), a nie pomysły, procedury, metody i zasady działania (art. 1 ust. 2¹ ustawy o prawie autorskim i prawach pokrewnych). Ta licencja ogranicza więc korzystanie z kodu i jego opracowań, ale sama nie zabrania komuś niezależnego zbudowania rozwiązania opartego na podobnej koncepcji. Szersza ochrona koncepcji wymagałaby innych środków (np. umów z osobami, którym udostępniasz projekt, znaku towarowego dla nazwy) i porady prawnej.

## 4. Wnoszenie zmian

Zmiany wnosi się przez fork lub osobną gałąź i Pull Request. Zasady w CONTRIBUTING.md. Fork nie zmienia warunków tej licencji: obowiązują one także wobec kopii i opracowań.

## 4a. Wygaśnięcie

Naruszenie tych warunków powoduje automatyczne wygaśnięcie uprawnień z punktu 2. Nie uchyla to innych roszczeń autora.

## 5. Brak gwarancji

Oprogramowanie jest dostarczane „takie, jakie jest”, bez jakiejkolwiek gwarancji. Autor nie odpowiada za szkody wynikłe z jego użycia, w tym za działanie agentów AI uruchamianych przez Sol-83, zużycie limitów abonamentów ani zmiany w repozytoriach użytkownika.

---

## Decyzje do podjęcia przez autora / Author's decisions

Cel autora (7.11.2026): ochrona przed komercyjnym użyciem bez zgody (np. przez firmy) i przed wykorzystaniem kodu lub jego części w cudzych, monetyzowanych rozwiązaniach.

1. **Gotowa licencja zamiast własnej**: rozważ przyjęcie sprawdzonego tekstu, np. *PolyForm Noncommercial License 1.0.0* (zakazuje użycia komercyjnego, dopuszcza prywatne i niekomercyjne) albo *Business Source License 1.1* (kod jawny, użycie produkcyjne tylko za zgodą, z opcjonalną datą zmiany licencji), oraz osobną płatną licencję komercyjną. Gotowe teksty mają mniej luk niż projekt pisany od zera.
2. **Użycie Sol-83 jako narzędzia przez osoby prywatne do projektów zarobkowych** (np. freelancer buduje aplikację dla klienta): obecny projekt traktuje to jako użycie komercyjne (pkt 3.2); potwierdź albo złagodź.
3. **Organizacje niekomercyjne** (szkoły, fundacje, administracja): czy dopuścić bez zgody.
4. **Zgoda**: forma i kanał (dane kontaktowe do uzupełnienia przez autora; ten projekt ich nie podaje).
5. **Wkład zewnętrzny**: CLA (przeniesienie lub licencja praw do wkładu, co pozwala później udzielać licencji komercyjnych) albo DCO.
6. **Łatka do Duet** (`patches/duet-gemini.patch`): proponowane udostępnienie na licencji MIT, jak sam Duet; Duet jest na MIT, więc jego kod każdy może używać komercyjnie niezależnie od Sol-83.
7. **Nazwa „Sol-83”**: rejestracja znaku towarowego, jeśli nazwa ma być chroniona.
8. **Weryfikacja prawna** zgodności z prawem polskim i UE oraz z warunkami usług dostawców AI.
