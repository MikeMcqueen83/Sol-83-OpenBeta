// Sol-83 panel: shared logic of both looks (Classic: index.html, Pro: pro.html). Each look provides the
// same element ids (#view, #projects, #limits, the dialogs ...) and its own layout and styles.
const TEXT = {
pl:{
  lookLabel:'Wygląd panelu',
  geminiDefaultWarn:'„Domyślny w Antigravity” oznacza, że model wybiera agy, a może to być droższy Gemini 4 Argon. Limit Antigravity schodzi według cen API, więc Flash wystarcza na wielokrotnie więcej pracy. Wybierz Gemini 3.8 Flash albo tryb Auto.',
  runNext:'Uruchom jako następny', queuePos:n=>n === 1 ? 'Ruszy jako następny, gdy zwolni się miejsce.' : `W kolejce: ${n}. miejsce.`,
  qClosed:'zapisane, sprawa zamknięta (modele nic nie muszą robić)', qEffect:'„Działa” i „Nie mogę wykonać” bez komentarza tylko zapisują wynik: zakończony projekt zostaje zakończony. „Nie działa”, „Częściowo” albo komentarz wznawia pracę modeli.',
  kindLabel:'Rodzaj projektu', pk_auto:'Wykryj z zadania (domyślnie)', pk_document:'Dokument lub research', pk_app:'Aplikacja', kindHint:'Przy dokumencie i researchu modele nie budują zaplecza (testów, linterów, skryptów) i sprawdzają treść oraz źródła. Wykrywanie szuka w zadaniu słów takich jak handbook, kompendium, research, raport.',
  reviewLabel2:'Przegląd zmian przez drugi model', rm_stage:'Po zakończonym etapie planu (domyślnie)', rm_each:'Po każdej zmianie', reviewHint:'Domyślnie drugi model przegląda pracę, gdy zamknie się etap planu, gdy zmiana jest duża albo gdy model zgłosi gotowość, a najpóźniej co 3 tury. Kolejna tura i tak widzi zmiany partnera. „Po każdej zmianie” jest dokładniejsze, ale zużywa około dwa razy więcej tur.',
  userTestsLabel:'Prośby o testy dla Ciebie', ut_final:'Tylko wersja końcowa (domyślnie)', ut_each:'Każda nowa wersja', ut_none:'Nie proś o testy', userTestsHint:'W trakcie pracy wynik sprawdzają modele i testy automatyczne. Domyślnie dostajesz jedną prośbę o sprawdzenie, gdy projekt się kończy; kartę „Do testów” możesz użyć zawsze. Modele i tak mogą zapytać o test, którego nie wykonają same (np. na telefonie).', webFetchLabel:'Claude może czytać strony WWW (WebFetch)', webFetchHint:'Dla researchu: pełna treść stron źródłowych zamiast fragmentów z wyszukiwarki. Treść stron to materiał, nie polecenia; odwiedzane strony widzą zapytania z tego komputera. Działa od następnej tury.',
  terminalTitle:'Polecenia do terminala', terminalLocal:'Przygotował lokalny koordynator: bez komentarzy i opisów, w kolejności wykonania.', terminalRules:'Z instrukcji modeli, bez komentarzy i opisów. Wklej całość do terminala.', terminalOriginal:'Instrukcja modeli (oryginał)', runOpen:'Otwórz w przeglądarce', runEndedHint:'proces zakończył pracę; ostatnie linie logu:',

  // Project list and waits (2026-11-08)
  g_now:'W toku', g_attention:'Wymaga uwagi', g_stopped:'Zatrzymane', g_done:'Ukończone', g_nowEmpty:'Nic teraz nie pracuje ani nie czeka.',
  k_working:'Pracuje', k_starting:'Uruchamianie', k_stopping:'Zatrzymywanie', k_review:'Czeka na przegląd', k_role:'Czeka na model z rolą', k_limit:'Czeka na limit',
  k_user:'Czeka na Ciebie', k_error:'Błąd', k_queued:'W kolejce', k_stopped:'Zatrzymany', k_done:'Ukończony', k_dependency:'Czeka na zależność',
  w_turn:(w,t,m,k)=>`${w} · tura ${t}/${m}${k ? ' · '+k : ''}`, w_role:(work,able)=>`Pracę „${work}” wykona tylko: ${able}.`, w_review:'Kod gotowy, przegląd zrobi:',
  w_limits:'Wszystkie włączone modele są chwilowo niedostępne:', w_back:c=>`sprawdzę ponownie ${c}`, untilShort:c=>`do ${c}`, estimateShort:'(szacunek)', nobodyShort:'żaden model',
  estimateHelp:'Dostawca nie podał godziny końca limitu: to szacunek Sol-83. Możesz spróbować wcześniej.', retryNow:'Spróbuj teraz', retryNowFor:w=>`Spróbuj teraz: ${w}`,
  retryLifted:w=>`Zdjęto przerwę ${w}. Projekty sprawdzą dostępność od razu.`, retryKept:w=>`${w}: Sol-83 nie wstrzymywał tego modelu. Odczyt limitu pokazuje, że nadal jest wyczerpany.`,
  qWaitingYou:n=>n === 1 ? '1 pytanie/test czeka na Ciebie' : `${n} pytań/testów czeka na Ciebie`, sinceShort:c=>`od ${c}`,
  // Questions and tests
  qTodo:'Czeka na Ciebie', qDoneTitle:'Zrobione', qOldTitle:'Nieaktualne', qNothing:'Nic nie czeka na Ciebie.', qVersionTitle:n=>`Co sprawdzić w wersji v${n}`,
  qFrom:w=>`od: ${w}`, qWhyLabel:'Dlaczego', qStepsLabel:'Kroki', qYour:'Twoja odpowiedź', qDelivered:'przekazana modelom', qQueued:'trafi do modeli w następnej turze',
  qQueuedStopped:'trafi do modeli po wznowieniu projektu', qChange:'Zmień odpowiedź', qDeferred:'odłożone', qResultAsk:'Wynik testu:',
  qCommentFail:'Co nie działa? (opcjonalnie, pomoże modelom)',

  whyRunning:'Projekt już pracuje albo czeka w kolejce.', whyNotRunning:'Projekt nie pracuje.', runApp:'RUN', runRunning:'RUN działa', whyRunActive:'Aplikacja już działa: zatrzymaj ją albo otwórz adres.', whyNoVersion:'Brak wersji do uruchomienia.', runStop:'Zatrzymaj RUN',
  questionsBtn:'Pytania i testy', questionsOpen:'Otwarte pytania i testy', questionsShort:'pytań/testów', langUnknown:'język nieustalony', langFixed:'Język projektu: stały od utworzenia.', actions:'Akcje projektu', seeGates:'Zobacz bramki odbioru',
  progressHelp:'Postęp netto = funkcjonalny minus dług w punktach procentowych, na tej samej podstawie: pozycje zakresu z planu ważone priorytetem (must 3, should 2, could 1). To wskaźnik zarządczy, nie prawdopodobieństwo sukcesu. Bramki odbioru są osobno.',
  progressShort:(n,f,d)=>`postęp netto ${n}% (funkcje ${f}% − dług ${d} p.p.)`, coordName:'Koordynator', turnN:n=>`Tura ${n}`, turnsWord:'tur', eventsWord:'zdarzeń',
  work_plan:'plan', work_implement:'implementacja', work_review:'przegląd', work_content:'treści',
  run_running:'działa', run_stopped:'zatrzymany', run_ended:'zakończył się', portLabel:'port', runLog:'Log uruchomienia', autoTests:'Testy automatyczne', manualTest:'Test ręczny', reviewLabel:'Przegląd',
  res_works:'działa', res_fails:'nie działa', res_partial:'częściowo', res_cannot:'nie mogę wykonać', res_oczekuje:'oczekuje',
  copyPath:'Kopiuj ścieżkę', openFolder:'Pokaż w Finderze', tagOnly:tag=>`Ta wersja istnieje tylko jako tag ${tag}: nie ma jej folderu na dysku.`, prepareFolder:'Przygotuj w folderze użytkownika', recBadge:'rekomendowana', location:'Lokalizacja na dysku', runThis:'Uruchom tę wersję (RUN)',
  k_key:'Klucz', taskFull:'Pełna treść zadania', chars:'znaków', copy:'Kopiuj', copied:'Skopiowano',
  tabQuestions:'Pytania i testy', qNone:'Brak pytań i testów dla Ciebie.', gatesTitle:'Bramki odbioru (blokują zamknięcie zakresu)', qt_clarification:'pytanie', qt_decision:'decyzja', qt_manual_test:'test ręczny', versionCheck:'co sprawdzić w wersji',
  qs_open:'otwarte', qs_answered:'odpowiedziane', qs_applied:'zastosowane', qs_deferred:'odroczone', qs_cancelled:'anulowane', qs_superseded:'zastąpione nowszym', mandatory:'obowiązkowe', why:'Dlaczego', blocks:'Blokuje', independent:'Można kontynuować', environment:'Środowisko',
  ownAnswer:'Własna odpowiedź', lateAnswer:'spóźniona, nie zastosowana', defer:'Odłóż', histTitle:'Historia odpowiedzi', testComment:'Opis wyniku (opcjonalnie):',
  actualSize:s=>`faktyczny rozmiar ${s}`, ad_approve:'Zatwierdź', ad_reject:'Odrzuć', ad_defer:'Odłóż', as_proposed:'propozycja', as_rejected:'odrzucone', as_deferred:'odłożone',
  aSizeHint:'Rozmiar i styl to wskazówki dla generatora: nie każdy wykonawca przyjmuje dokładną rozdzielczość. Po wykonaniu widać faktyczny rozmiar pliku.',
  tipPrio_must:'must: bez tego cel zadania nie jest spełniony', tipPrio_should:'should: wyraźnie lepiej', tipPrio_could:'could: dodatek',
  tipSt_todo:'do zrobienia', tipSt_doing:'w toku', tipSt_done:'zrobione', tipSt_deferred:'odłożone: to nie jest ukończenie; usunięcie z zakresu wymaga decyzji',
  tipCost:'Udział limitu tygodniowego zużyty na pozycje danego rodzaju, z odczytów limitów konta (szacunek).',
  pDone:(a,b)=>`ukończone ${a}/${b}`, pFunctional:'funkcjonalny', pDebt:'dług', pNet:'netto', pDeferredMust:n=>`${n} odłożonych must`, pGates:n=>`${n} bramek odbioru`, pNoEstimate:'Brak planu: brak oszacowania postępu.',
  planStale:r=>`Plik planu jest błędny: pokazana jest ostatnia poprawna rewizja ${r}.`,
  roles:'Role (można kilka)', rd_general:'Plan, implementacja i przegląd. Nie wykonuje zamówionych treści.', rd_architect:'Plan, architektura, research; tury na początku i po nowym zleceniu.', rd_implementer:'Zadania z planu; tura, gdy plan jest gotowy.', rd_tester:'Przegląd i testy; tura po każdej zmianie.', rd_analyst:'Luki, ryzyka, dług; tury przeglądu.', rd_content:'Grafiki, teksty, fabuła z zatwierdzonych zamówień.',
  langChoose:'Język projektu (ustal raz):', langFixedIs:l=>`Język projektu: ${l}. Ustalony przy utworzeniu; zmiana języka strony go nie zmienia.`, projectTitle:'Projekt', projectName:'Nazwa projektu', rename:'Zmień nazwę', keyHint:k=>`Klucz ${k} i folder projektu nie zmieniają się przy zmianie nazwy.`,
  gitBranch:'gałąź', gitDetached:'odłączony HEAD', gitChanges:(a,b,c)=>`zmiany: ${a} w indeksie, ${b} niezapisane, ${c} nowe pliki`, gitInProgress:'trwa merge lub rebase', gitNoRepo:'brak repozytorium',
  gitTitle:'Git projektu', gitRemote:'Remote', gitBase:'Gałąź bazowa', gitStrategy:'Dostarczanie', gs_local:'tylko lokalnie', gs_push:'push gałęzi', gs_pr:'push i PR', gitAllowPush:'zgoda na push', gitAllowPr:'zgoda na PR', gitNeedPermission:'Najpierw zapisz remote i zgodę na push.', gitSendNow:b=>`Wyślij gałąź ${b}`,
  gitHint:'Agenci pracują na własnej gałęzi; commit, push i PR to osobne zgody. Nigdy force push, reset ani zmiana ochrony gałęzi.', lastTurn:'ostatnia tura',
  locale:'pl-PL', newProject:'Nowy projekt', limits:'Limity abonamentów', refresh:'Odśwież', handoffAt:'Przekazuj pracę przy zużyciu',
  thresholdHint:'Okno 5 h: kiedy przekazać pracę drugiemu modelowi. Tydzień: zapas na Twoją własną pracę do końca tygodnia, 100 oznacza brak zapasu.', projects:'Projekty', noProjects:'Brak projektów.',
  rejectHint:'Opis trafi do następnego modelu, a projekt wróci do pracy.', rejectPlaceholder:'Co nie działa? Co zrobiłeś i co się stało?',
  cancel:'Anuluj', sendBack:'Odeślij do poprawy', rejectTitle:n=>`Wersja v${n} nie działa`,
  powerTitle:'Włączyć Full Power?', powerWarn:'To będzie orało limity bardzo agresywnie.',
  powerOne:'Gdy drugi model czeka na reset, ten sam model zrobi przegląd i poprawki w nowej sesji, zamiast czekać. Zużywa to wielokrotnie więcej limitu.',
  powerTwo:'Próg przekazania przestaje obowiązywać: praca trwa, aż dostawca odmówi. Limit może się skończyć na wiele godzin, także dla Twojej własnej pracy.',
  powerThree:'Nie zastępuje to przeglądu drugiego modelu: taka wersja jest osobno oznaczona, a projekt nadal czeka na jego ocenę albo Twoją decyzję.',
  powerConfirm:'Włącz Full Power', powerOn:'Włączony: limity schodzą bardzo szybko, praca trwa do odmowy dostawcy.',
  powerOff:'Gdy drugi model czeka, ten sam robi przegląd i poprawki. Bardzo agresywnie zużywa limity.',
  publicTitle:'Opublikować repozytorium?', publicWarn:'Każdy w internecie zobaczy kod i całą jego historię.',
  publicOne:'Sprawdzę kod i historię pod kątem sekretów i wstrzymam publikację, jeśli coś znajdę. Taka kontrola wykrywa tylko typowe wzorce.',
  publicTwo:'Zmiana na prywatne później nie usuwa kopii, które ktoś zdążył pobrać.', publicConfirm:'Publikuj',
  available:'Dostępny', paused:'Wstrzymany', noReading:'Brak odczytu', window5:'Okno 5 h', week:'Tydzień', handoffTick:'Tu przekazuję pracę',
  readFail:e=>`Nie udało się odczytać limitu: ${e}`, back:(r,w,c)=>`${r}, wróci ${w} (${c})`, windowResets:c=>`Okno 5 h odnawia się o ${c}`,
  read:a=>`Odczyt ${a}`, plan:p=>`plan ${p}`, secAgo:n=>`${n} s temu`, minAgo:n=>`${n} min temu`, hAgo:n=>`${n} godz. temu`,
  inMin:n=>`za ${n} min`, inH:(h,m)=>`za ${h} godz. ${m} min`, inD:n=>`za ${n} dni`, inDH:(d,h)=>`za ${d} d ${h} godz.`,
  s_queued:'W kolejce', s_running:'W toku', s_stopping:'Zatrzymywanie', s_stopped:'Zatrzymany', s_done:'Ukończony', s_attention:'Wymaga uwagi',
  l_approved:'Sprawdzona przez oba modele', l_tested:'Przeszła testy', l_self_reviewed:'Przegląd jednego modelu (Full Power)', l_proposed:'Bez testów: tylko deklaracja agenta', l_single:'Jeden model: bez przeglądu drugiego',
  modelOff:'Wyłączony', inModel:'w nazwie modelu', a_single:' · tryb jednego modelu', role:'Rola', r_general:'Ogólna', r_architect:'Architekt', r_implementer:'Implementujący', r_tester:'Tester', r_analyst:'Analityk systemowy', r_content:'Twórca treści',
  tabAssets:'Treści', aTitle:'Zamów treść', aImage:'Grafika', aText:'Tekst', aPrompt:'Co ma powstać', aPath:'Plik w projekcie', aPathPh:'np. assets/logo.png',
  aSize:'Rozmiar', aStyle:'Styl', aOrder:'Zamów', aNone:'Brak zamówień. Modele zamawiają treści w .sol83/assets.json, a Ty możesz tutaj.', aWaiting:'Czeka na następną turę',
  as_requested:'zamówione', as_done:'gotowe', as_error:'błąd', aByUser:'Twoje zamówienie',
  aHint:'Zamówienia realizuje model z rolą Twórca treści, na przykład Gemini przez Antigravity, który generuje grafikę modelem graficznym. Projekt nie kończy się, dopóki zamówienia czekają.',
  coordTitle:'Koordynator wiadomości', c_local:m=>`Lokalny LLM przez Ollamę (${m})`, c_idle:'Model, który teraz nie pracuje (Claude albo Codex)', c_claude:'Claude', c_codex:'Codex', c_gemini:'Gemini przez Antigravity',
  cUnavailable:'niedostępny', cNow:w=>`Teraz odpowiada: ${w}.`, cDefault:'domyślnie',
  coordHint:'Odpowiada na wiadomości i rozpoznaje, czy to pytanie, zlecenie, czy uwaga. Dotyczy wszystkich projektów. Gdy wybrany nie może odpowiedzieć, odpowiada lokalny model, a bez niego koordynator z własnych zapisów. Lokalny model nie zużywa abonamentów i nie czyta plików: dostaje fakty od koordynatora i skrót planu.',
  fallbackLabel:'Gdy model z rolą jest niedostępny', fb_general:'Przejmuje model z rolą Ogólna', fb_wait:'Projekt czeka', a_role:c=>`Czekam na model z potrzebną rolą · ${c}`,
  setupTitle:'Skrypt .gemini-setup', setupHint:'To kod z repozytorium projektu. Sol-83 uruchamia go tylko w piaskownicy systemu i dopiero po akceptacji tej dokładnej treści. Każda zmiana skryptu wymaga ponownej akceptacji.',
  setupApprove:'Akceptuję tę treść, uruchom w piaskownicy', setupApproved:'Zaakceptowany (sha {0}).', setupNoSandbox:'Brak piaskownicy systemu: skrypt nie zostanie uruchomiony.',
  secretsConfirm:(items) => `Znaleziono możliwe sekrety:\n\n${items}\n\nWysłać mimo to? Sprawdź każdą pozycję: wysyłki nie da się naprawdę cofnąć.`,
  deleteTitle:'Usuń projekt', deleteButton:'Usuń projekt', deleteHint:'Usuwa projekt z Sol-83 na zawsze, bez archiwum. Działający projekt najpierw się zatrzyma.',
  deleteAsk:n=>`Usunąć „${n}” na zawsze?`, deleteWarn:'Tego nie da się cofnąć.', deleteConfirm:'Usuń na zawsze',
  deleteWhat:'Znikną historia, wersje, transkrypty, zamówienia, warsztat agentów i folder testowy.',
  deleteOwn:p=>`Repozytorium utworzone przez Sol-83 też zniknie z dysku: ${p}`, deleteUser:(p,b)=>`Twoje repozytorium zostaje: ${p}. Znikną z niego tylko gałąź ${b}, tagi wersji i foldery robocze Sol-83.`,
  deleteKeeps:'GitHub zostaje nietknięty: to, co tam wysłałeś, jest Twoim archiwum.',
  save:'Zapisz', verifyHint:'Na tej podstawie powstają numerowane wersje i aktualizuje się folder „Uruchamiaj stąd”. Bez polecenia wersja powstaje tylko wtedy, gdy model sam zgłosi gotowość. Zmiana działa od końca bieżącej tury. Polecenie uruchamia się w piaskownicy systemu: zapis tylko w folderze projektu, domyślnie bez sieci (zmienisz to w panelu Bezpieczeństwo).',
  rolesHint:'Architekt: plan, przebudowa planu i research. Implementujący: zadania z planu. Tester: przegląd i testy. Analityk systemowy: luki i plan ich łatania jako dług. Twórca treści: zatwierdzone zamówienia grafik, tekstów i fabuły. Ogólna: plan, implementacja i przegląd, bez wykonywania zamówionych treści. Model może mieć kilka ról. Każdy rodzaj pracy musi mieć włączony model.', a_singleWait:c=>`Model niedostępny, drugi wyłączony · wznowię o ${c}`,
  none:'Bez myślenia', minimal:'Minimalny', low:'Niski', medium:'Średni', high:'Wysoki', xhigh:'Extra (xhigh)', max:'Maksymalny', ultra:'Ultra',
  a_review:(w,t,m)=>`${w} robi przegląd w nowej sesji (Full Power) · tura ${t}/${m}`, a_solo:(w,r)=>` · solo: ${w} niedostępny (${r})`,
  a_turn:(w,t,m)=>`${w} pracuje · tura ${t}/${m}`, a_limits:c=>`Oba modele niedostępne · wznowię o ${c}`,
  a_partner:c=>`Kod gotowy · czekam na przegląd drugiego modelu (${c})`, a_start:'Uruchamianie silnika',
  model:'Model', thinking:'Poziom myślenia', toTest:'Do testów', noVersionYet:'Jeszcze nie ma wersji do testów.', noVersionLeft:'Brak wersji do testów.',
  noVersionHint:'Wersja powstanie, gdy koordynator potwierdzi, że kod działa.', allRejected:'Wszystkie zgłosiłeś jako niedziałające, trwa poprawa.',
  wipNoVersion:n=>`W toku: ${n} checkpoint(ów). To stan roboczy, nie testuj go.`, wipLabel:'W trakcie prac:',
  wipCount:n=>`${n} checkpoint(ów) po ostatniej wersji`, wipFiles:n=>`, ${n} niezapisanych plików`, wipRun:'To stan roboczy, nie testuj go.', wipIdle:'Ten stan nie przeszedł sprawdzenia.',
  works:'Działa', broken:'Nie działa', worksYou:'Działa: Twoje potwierdzenie',
  commit:'commit', newer:n=>`Nowsza v${n} przeszła testy, ale nie sprawdził jej jeszcze drugi model.`, newerRejected:n=>`Nowszą v${n} zgłosiłeś jako niedziałającą, trwa poprawa.`, confirmed:n=>`Ostatnia potwierdzona przez Ciebie: v${n}`,
  whatToCheck:'Co sprawdzić', noEvents:'Jeszcze nic się nie wydarzyło.', noVersions:'Wersje pojawią się, gdy kod przejdzie sprawdzenie.',
  turnBy:(t,w)=>`tura ${t}, ${w}`, inTestFolder:'W folderze „Uruchamiaj stąd”', testThis:'Testuj tę wersję', tag:'tag',
  noTranscript:'Transkrypt pojawi się po pierwszej turze.', k_verify:'Polecenie testów', k_noVerify:'brak: koordynator nie potwierdzi, że kod działa', k_source:'Folder źródłowy', k_later:'powstanie przy starcie',
  k_branch:'Gałąź robocza', k_work:'Folder pracy', k_models:'Modele', k_turns:'Limit tur', k_added:'Dodano',
  byCoordinator:'Koordynator, z własnych zapisów', byObserver:w=>`${w}, obserwacja bez zmian w kodzie`, waitingAnswer:'Czekam na odpowiedź…',
  notePending:'Czeka na następną turę', noteSent:(w,t)=>`Przekazano: ${w}, tura ${t}`, urgent:'Pilna',
  acceptNoReview:'Przyjmij bez przeglądu', stopAfter:'Zatrzymaj po turze', stopNow:'Zatrzymaj teraz', resume:'Wznów', keepWorking:'Kontynuuj pracę',
  tabRun:'Przebieg', tabVersions:'Wersje', tabTranscript:'Transkrypt', tabTask:'Zadanie', modelsTitle:'Modele i poziom myślenia', modelsHint:'Zmiana obowiązuje od następnej tury.',
  askTitle:'Zapytaj o status', askPlaceholder:'Na jakim etapie jest praca?', askHint:'Odpowiada model, który teraz nie pracuje. Pytanie nie zleca pracy: do tego służą uwagi albo przycisk pod odpowiedzią.', orderWork:'Zleć to jako pracę', ordered:'Zlecono jako pracę', ask:'Zapytaj',
  notesTitle:'Twoje uwagi i zlecenia', notePlaceholder:'Następny model uwzględni to przy przekazaniu', urgentCheck:'Pilne: przerwij bieżącą turę', addNote:'Dodaj uwagę',
  heroTitle:'Wybierz projekt albo zleć nowy', heroText:'Codex i Claude pracują na zmianę, sprawdzają się nawzajem i przejmują pracę, gdy jednemu skończy się limit.',
  formLead:'Wklej plik .md albo opisz zadanie. Modele przekazują wynik sobie nawzajem, a Tobie pokazują tylko sprawdzone wersje.',
  fTask:'Zadanie i kryteria odbioru', fTaskPlaceholder:'# Co ma powstać\n\nKryteria odbioru:\n- ...', fDrop:'Możesz przeciągnąć tu plik .md.', fFile:'Wybierz plik',
  fName:'Nazwa', fNameHint:'Domyślnie: pierwszy wiersz zadania', fVerify:'Polecenie testów', fVerifyPlaceholder:'np. python3 -m pytest', fVerifyHint:'Na tej podstawie koordynator nadaje numer wersji. Bez polecenia nie potwierdzi, że kod działa.',
  fFolder:'Folder istniejącego projektu', fFolderPlaceholder:'/pełna/ścieżka. Puste: nowy projekt', fFolderHint:'Musi być repozytorium Git bez niezapisanych zmian. Twój kod zostaje nietknięty: praca toczy się na osobnej gałęzi.',
  fModelsHint:'Możesz to zmienić w każdej chwili, także podczas pracy.', fAdvanced:'Ustawienia zaawansowane', fTurns:'Limit tur', fSubmit:'Zleć projekt',
  tabPlan:'Plan', tabEff:'Efektywność', tabSettings:'Ustawienia',
  msgTitle:'Wiadomość do modeli', msgPlaceholder:'Zapytaj o status, zleć pracę albo dodaj uwagę', send:'Wyślij', interrupt:'Przerwij bieżącą pracę',
  msgHint:'Koordynator wiadomości (wybierasz go w Ustawieniach) odpowie i sam rozpozna, czy to pytanie, czy praca dla agentów. Przerwanie zatrzymuje turę od razu i przekazuje wiadomość.',
  gNoReading:'Antigravity nie podaje limitów: dostępność poznaję po błędach.',
  withdraw:'Cofnij przekazanie', withdrawn:'Przekazanie cofnięte', monTokens:'Tokeny łącznie', monTokensTurns:'Tokeny ostatnich tur',
  accounts:'Konta i logowanie', checkConnection:'Sprawdź połączenie', checkHint:'Sprawdza CLI i logowanie bez wywołania modelu: nie zużywa limitów.', cliVersion:'CLI', authState:'Logowanie', account:'Konto', planLabel:'Abonament', stale:'dane nieaktualne', loginWith:'Zaloguj', authOk:'zalogowany', authNotLogged:'brak logowania', authExpired:'sesja wygasła', authWrongAccount:'niewłaściwe konto', authNoModel:'brak dostępu do modelu', authPlanLimit:'limit abonamentu', authRateLimit:'ograniczenie częstotliwości', authNetwork:'błąd sieci', authOutage:'awaria dostawcy', authUnknown:'przyczyna nieustalona', authNoCli:'brak CLI', authApiKey:'klucz API (nieużywany przez Sol-83)',
  selection:'Wybór modelu', sel_manual:'Ręczny', sel_auto_economy:'Auto — ekonomiczny', sel_auto_power:'Auto — power', topShort:'najwyższy', topWarning:'Najwyższy model dostawcy: może bardzo szybko zużyć limity abonamentu. Auto nigdy go nie wybiera; ręczny wybór wymaga potwierdzenia.', autoHint:'Auto wybiera model tego dostawcy przed każdą turą według rodzaju pracy, wyników i limitów, nigdy najwyższy ani niesklasyfikowany. Decyzja z powodem jest w Activity.', aboutModel:'O modelu', usesLabel:'Zastosowania', autoLabel:'Auto', autoManualOnly:'tylko ręcznie', autoAllowed:'dopuszczony', autoUnclassified:'model niesklasyfikowany: poza Auto',
  licTitle:'Licencja projektu', licNow:l=>`Obecnie: ${l}.`, licKind:'Rodzaj', lic_standard:'standardowa open source', lic_custom:'własna / source-available', lic_none:'brak zadeklarowanej licencji', licStandard:'Licencja standardowa', licHolder:'Właściciel praw (do pliku LICENSE)', licOverwrite:'zastąp istniejący plik LICENSE (świadoma decyzja)', licCustom:'Treść licencji własnej', licHint:'Teksty standardowe są niezmienione (identyfikatory SPDX). Wybór nie zmienia licencji zależności ani cudzego kodu. Brak licencji nie oznacza prawa do dowolnego użycia. Licencja Sol-83 jest od tego niezależna.',
  securityTitle:'Bezpieczeństwo', secNetwork:'Testy z dostępem do sieci', secUnsandboxed:'Uruchamianie bez piaskownicy (niezalecane)', secUnsandboxedWarn:'Kod napisany przez agentów (testy, .gemini-setup, RUN) będzie działał z pełnymi uprawnieniami Twojego konta. Na pewno?', sandboxOn:k=>`Piaskownica systemu: ${k}.`, sandboxOff:'Brak piaskownicy systemu: kod z repozytoriów nie jest uruchamiany.', turnConfigNow:'Bieżąca (ostatnia) tura', turnConfigHint:'Zmiany poniżej obowiązują od następnej tury; bieżąca tura zachowuje swoją konfigurację.',
  notAvailable:'brak danych', usageByModel:'Zużycie tokenów według dostawcy i modelu', colTurns:'Tury', colCache:'Cache (odczyt)', colProvider:'Dostawca', col5h:'Okno 5 h', colEquiv:'Pełne okna', colWeek:'Tydzień', colGaps:'Tury bez odczytu', sharedTurns:'wspólne z innym projektem', modelUnconfirmed:'model niepotwierdzony przez CLI',
  usageHelp:'Wartości na turę: przyrost licznika tej samej sesji. Claude podaje turę, Codex i Antigravity sumę całej sesji, z której koordynator liczy przyrost. Codex podaje tylko sumę, więc wejście i wyjście są niedostępne. „brak danych” nie znaczy zero. Kategorii różnych dostawców nie należy porównywać wprost.',
  windowsTitle:'Udział projektu w limitach abonamentów', windowsHelp:'Szacunek z ruchu odczytów limitów konta w czasie tur projektu: obejmuje też inną pracę na tym koncie. 250% okna 5 h to 2,5 pełnego okna, a nie bieżące saldo. Dostawców nie sumuje się. Antigravity nie udostępnia odczytów, więc brak danych.',
  colTurn:'Tura', colModel:'Model', colIn:'Wejście', colOut:'Wyjście', colTotal:'Razem', colSession:'Tura sesji', freshSession:'nowa',
  tokensHelp:'Wejście to cały kontekst, który tura przeczytała, z pamięcią podręczną. Rośnie z każdą kolejną turą tej samej sesji, dlatego koordynator co kilka tur zaczyna świeżą (dziś co 6). Codex podaje tylko sumę.', gNotReady:'Niegotowy', gOldProject:'Ten projekt powstał przed Gemini, więc Gemini jest wyłączony. Po włączeniu dołączy po bieżącej turze: silnik uruchomi się od nowa, a modele dostaną świeże sesje.',
  planNone:'Plan powstanie w pierwszej turze: modele rozpiszą funkcje, architekturę i budżety tur.', planProblem:'Plan ma błąd: ', planArch:'Architektura', planFile:'Plik planu', planDebt:'Dług techniczny',
  planSpend:'Gdzie poszedł limit tygodniowy', pr_must:'musi', pr_should:'powinno', pr_could:'może', st_todo:'do zrobienia', st_doing:'w toku', st_done:'gotowe', st_deferred:'odłożone',
  grp_must:'musi', grp_should:'powinno', grp_could:'może', grp_debt:'dług', grp_unassigned:'bez przypisania',
  colItem:'Pozycja', colPrio:'Priorytet', colStatus:'Status', colTurns:'Tury', colCost:'% tyg.', startItem:'Zleć', overBudget:'ponad budżet',
  liveNone:'Na razie brak zapisu pracy modeli.', liveAgent:w=>`${w}: ostatnie działania z jego dziennika sesji. Podgląd nic nie kosztuje.`,
  runTitle:'Jak uruchomić i przetestować', pathRepo:'Repozytorium na dysku', pathWork:'Kod w toku (agenci)', pathTest:'Folder testowy',
  runHere:'Uruchamiaj stąd', howToRun:'Jak uruchomić', otherFolders:'Pozostałe foldery', pathRepoBranch:b=>`Repozytorium, kod na gałęzi ${b}`,
  pathWorkNote:'Warsztat agentów: tu trwa praca, nie uruchamiaj stąd', pathTestOld:n=>`Starszy folder testowy · v${n}`, runNotYet:'Folder „Uruchamiaj stąd” dostanie wersję, gdy koordynator potwierdzi, że kod działa.',
  effHelp:'Jak czytać: koszt to procent limitu tygodniowego danego modelu, zmierzony odczytem limitu przed turą i po niej. Claude liczy się w Twoim planie Claude, Codex w planie ChatGPT, więc te procenty nie są ze sobą porównywalne. Do kosztu tury wlicza się też inna praca na tym koncie w tym czasie, np. Twoje własne rozmowy. Cel i ocenę kroków podają modele: każdy ocenia poprzedni krok partnera względem kryteriów odbioru. Sygnał do interwencji oznacza, że praca kosztuje, a cel się nie przybliża: przeczytaj go i zdecyduj, czy zmienić kierunek, odłożyć pozycję, czy zatrzymać projekt.',
  monGoal:'Cel według modeli', monVerdicts:'Ocena kolejnych kroków', v_closer:'przybliżył', v_not_closer:'nie przybliżył', v_back:'cofnął', monNoGoal:'brak oceny',
  monTitle:'Efektywność', monSignal:'Sygnał do interwencji', monTurns:'Tury / wersje', monSince:'Tury od ostatniej wersji', monCost:'Koszt łącznie (% tygodnia)', monPerVersion:'Koszt na wersję', monLines:'Wiersze od wersji: zmienione / netto', monOk:'Bez sygnałów: praca daje nowe wersje.', monSidebar:'sygnał',
  finalTitle:'Odpowiedź końcowa', noteResponse:'Odpowiedź modelu', loading:'Wczytuję…',
  ghRepos:'Repozytoria GitHub', ghFilter:'Szukaj repozytorium', ghNoRepos:'Brak wyników.', ghRepoWork:'Zleć pracę w repozytorium', ghAuto:'Wysyłaj nowe wersje automatycznie', ghPr:'Otwórz Pull Request',
  ghFormRepo:r=>`Repozytorium GitHub: ${r}`, ghFormHint:'Agenci pracują na osobnej gałęzi. Twój main zostaje nietknięty, a w prywatnym repozytorium każda nowa wersja pojawi się na tej gałęzi automatycznie.', ghPushed:d=>`aktualizacja ${d}`,
  ghTitle:'GitHub', ghName:'Nazwa repozytorium', ghPrivate:'Prywatne', ghPublic:'Publiczne', ghCreate:n=>`Utwórz i wyślij v${n}`, ghNeedVersion:'Wysłać można tylko gotową wersję. Prace w toku nie opuszczają tego komputera.',
  ghSent:n=>`Wysłano: v${n}`, ghSend:n=>`Wyślij v${n}`, ghUpToDate:'Najnowsza sprawdzona wersja jest już wysłana.', ghToPublic:'Zmień na publiczne', ghToPrivate:'Zmień na prywatne', ghHint:'Każde wysłanie to Twoje kliknięcie. Nic nie trafia tam samo.',
},
en:{
  lookLabel:'Panel look',
  geminiDefaultWarn:'"Antigravity default" lets agy pick the model, possibly the dearer Gemini 4 Argon. The Antigravity quota is drawn by API prices, so Flash does many times more work. Choose Gemini 3.8 Flash or Auto.',
  runNext:'Run next', queuePos:n=>n === 1 ? 'Starts next, when a slot is free.' : `Queued: position ${n}.`,
  qClosed:'recorded, closed (nothing for the models to do)', qEffect:'"Works" and "Cannot run it" without a comment only record the result: a finished project stays finished. "Does not work", "Partly" or a comment resumes the models\' work.',
  kindLabel:'Project kind', pk_auto:'Detect from the task (default)', pk_document:'Document or research', pk_app:'Application', kindHint:'For documents and research the models build no tooling (tests, linters, scripts) and check content and sources. Detection looks in the task for words such as handbook, compendium, research, report.',
  reviewLabel2:'Review of changes by the other model', rm_stage:'After a finished stage of the plan (default)', rm_each:'After every change', reviewHint:'By default the other model reviews the work when a stage of the plan is finished, when a change is large or when a model says it is done, and at least every 3 turns. The next turn sees the partner\'s changes anyway. "After every change" is more thorough but uses about twice as many turns.',
  userTestsLabel:'Test requests for you', ut_final:'Final version only (default)', ut_each:'Every new version', ut_none:'Do not ask for tests', userTestsHint:'During the work the models and automatic tests check the result. By default you get one request to check when the project ends; you can use the "To test" card at any time. The models may still ask for a test they cannot run themselves (e.g. on a phone).', webFetchLabel:'Claude may read web pages (WebFetch)', webFetchHint:'For research: the full text of source pages instead of search snippets. Page content is material, not instructions; the visited sites see requests from this computer. Applies from the next turn.',
  terminalTitle:'Commands for the terminal', terminalLocal:'Prepared by the local coordinator: no comments or prose, in the order to run.', terminalRules:'From the models\' instructions, without comments or prose. Paste it all into a terminal.', terminalOriginal:'Models\' instructions (original)', runOpen:'Open in the browser', runEndedHint:'the process has exited; last lines of its log:',

  // Project list and waits (2026-11-08)
  g_now:'In progress', g_attention:'Needs attention', g_stopped:'Stopped', g_done:'Finished', g_nowEmpty:'Nothing is working or waiting right now.',
  k_working:'Working', k_starting:'Starting', k_stopping:'Stopping', k_review:'Waiting for review', k_role:'Waiting for a model with the role', k_limit:'Waiting for a limit',
  k_user:'Waiting for you', k_error:'Error', k_queued:'Queued', k_stopped:'Stopped', k_done:'Finished', k_dependency:'Waiting for a dependency',
  w_turn:(w,t,m,k)=>`${w} · turn ${t}/${m}${k ? ' · '+k : ''}`, w_role:(work,able)=>`Only ${able} can do the work "${work}".`, w_review:'Code ready, the review will come from:',
  w_limits:'All switched-on models are unavailable for now:', w_back:c=>`checking again ${c}`, untilShort:c=>`until ${c}`, estimateShort:'(estimate)', nobodyShort:'no model',
  estimateHelp:'The provider gave no end time for the limit: this is Sol-83\'s estimate. You can try earlier.', retryNow:'Try now', retryNowFor:w=>`Try now: ${w}`,
  retryLifted:w=>`${w}'s pause lifted. Projects check availability right away.`, retryKept:w=>`${w}: Sol-83 was not pausing this model. The limit reading shows it is still exhausted.`,
  qWaitingYou:n=>n === 1 ? '1 question/test waits for you' : `${n} questions/tests wait for you`, sinceShort:c=>`since ${c}`,
  // Questions and tests
  qTodo:'Waiting for you', qDoneTitle:'Done', qOldTitle:'No longer current', qNothing:'Nothing waits for you.', qVersionTitle:n=>`What to check in version v${n}`,
  qFrom:w=>`from: ${w}`, qWhyLabel:'Why', qStepsLabel:'Steps', qYour:'Your answer', qDelivered:'delivered to the models', qQueued:'goes to the models in the next turn',
  qQueuedStopped:'goes to the models when the project resumes', qChange:'Change answer', qDeferred:'deferred', qResultAsk:'Test result:',
  qCommentFail:'What does not work? (optional, helps the models)',

  whyRunning:'The project is already working or queued.', whyNotRunning:'The project is not working.', runApp:'RUN', runRunning:'RUN is on', whyRunActive:'The app is already running: stop it or open its address.', whyNoVersion:'No version to run.', runStop:'Stop RUN',
  questionsBtn:'Questions and tests', questionsOpen:'Open questions and tests', questionsShort:'questions/tests', langUnknown:'language not set', langFixed:'Project language: fixed at creation.', actions:'Project actions', seeGates:'See acceptance gates',
  progressHelp:'Net progress = functional minus debt in percentage points, on the same basis: the plan\'s scope items weighted by priority (must 3, should 2, could 1). A management indicator, not a probability of success. Acceptance gates are separate.',
  progressShort:(n,f,d)=>`net progress ${n}% (features ${f}% − debt ${d} pp)`, coordName:'Coordinator', turnN:n=>`Turn ${n}`, turnsWord:'turns', eventsWord:'events',
  work_plan:'plan', work_implement:'implementation', work_review:'review', work_content:'content',
  run_running:'running', run_stopped:'stopped', run_ended:'ended', portLabel:'port', runLog:'Run log', autoTests:'Automatic tests', manualTest:'Manual test', reviewLabel:'Review',
  res_works:'works', res_fails:'does not work', res_partial:'partly', res_cannot:'cannot run it', res_oczekuje:'waiting',
  copyPath:'Copy path', openFolder:'Show in Finder', tagOnly:tag=>`This version exists only as tag ${tag}: it has no folder on disk.`, prepareFolder:'Prepare in the user folder', recBadge:'recommended', location:'Location on disk', runThis:'Run this version (RUN)',
  k_key:'Key', taskFull:'Full task text', chars:'characters', copy:'Copy', copied:'Copied',
  tabQuestions:'Questions and tests', qNone:'No questions or tests for you.', gatesTitle:'Acceptance gates (they block closing the scope)', qt_clarification:'question', qt_decision:'decision', qt_manual_test:'manual test', versionCheck:'what to check in the version',
  qs_open:'open', qs_answered:'answered', qs_applied:'applied', qs_deferred:'deferred', qs_cancelled:'cancelled', qs_superseded:'superseded', mandatory:'mandatory', why:'Why', blocks:'Blocks', independent:'Can continue', environment:'Environment',
  ownAnswer:'Your own answer', lateAnswer:'late, not applied', defer:'Defer', histTitle:'Answer history', testComment:'Describe the result (optional):',
  actualSize:s=>`actual size ${s}`, ad_approve:'Approve', ad_reject:'Reject', ad_defer:'Defer', as_proposed:'proposed', as_rejected:'rejected', as_deferred:'deferred',
  aSizeHint:'Size and style are hints for the generator: not every executor takes an exact resolution. After it is made, the real file size is shown.',
  tipPrio_must:'must: without it the goal is not met', tipPrio_should:'should: clearly better', tipPrio_could:'could: an extra',
  tipSt_todo:'to do', tipSt_doing:'in progress', tipSt_done:'done', tipSt_deferred:'deferred: this is not completion; removing it from scope needs a decision',
  tipCost:'Share of the weekly limit used on items of this kind, from the account\'s limit readings (an estimate).',
  pDone:(a,b)=>`done ${a}/${b}`, pFunctional:'functional', pDebt:'debt', pNet:'net', pDeferredMust:n=>`${n} deferred must`, pGates:n=>`${n} acceptance gates`, pNoEstimate:'No plan: no progress estimate.',
  planStale:r=>`The plan file is invalid: showing the last valid revision ${r}.`,
  roles:'Roles (several allowed)', rd_general:'Planning, implementation and review. Does not make ordered content.', rd_architect:'Plan, architecture, research; turns at the start and after a new request.', rd_implementer:'Plan tasks; a turn when the plan is ready.', rd_tester:'Review and tests; a turn after every change.', rd_analyst:'Gaps, risks, debt; review turns.', rd_content:'Graphics, texts, story from approved orders.',
  langChoose:'Project language (set once):', langFixedIs:l=>`Project language: ${l}. Set at creation; switching the page language does not change it.`, projectTitle:'Project', projectName:'Project name', rename:'Rename', keyHint:k=>`The key ${k} and the project folder do not change with the name.`,
  gitBranch:'branch', gitDetached:'detached HEAD', gitChanges:(a,b,c)=>`changes: ${a} staged, ${b} unsaved, ${c} new files`, gitInProgress:'a merge or rebase is in progress', gitNoRepo:'no repository',
  gitTitle:'Project Git', gitRemote:'Remote', gitBase:'Base branch', gitStrategy:'Delivery', gs_local:'local only', gs_push:'push the branch', gs_pr:'push and PR', gitAllowPush:'allow push', gitAllowPr:'allow PR', gitNeedPermission:'Save a remote and the permission to push first.', gitSendNow:b=>`Push branch ${b}`,
  gitHint:'The agents work on their own branch; commit, push and PR are separate permissions. Never a force push, reset or change of branch protection.', lastTurn:'last turn',
  locale:'en-GB', newProject:'New project', limits:'Subscription limits', refresh:'Refresh', handoffAt:'Hand work over at usage',
  thresholdHint:'5 h window: when to hand work to the other model. Week: a reserve for your own work until the week ends, 100 means none.', projects:'Projects', noProjects:'No projects yet.',
  rejectHint:'The description goes to the next model and the project returns to work.', rejectPlaceholder:'What does not work? What did you do and what happened?',
  cancel:'Cancel', sendBack:'Send back for fixing', rejectTitle:n=>`Version v${n} does not work`,
  powerTitle:'Turn on Full Power?', powerWarn:'This burns through your limits very aggressively.',
  powerOne:'When the second model is waiting for a reset, the same model reviews and refines in a new session instead of waiting. This uses many times more of your limit.',
  powerTwo:'The handoff threshold stops applying: work continues until the provider refuses. The limit can run out for hours, for your own work too.',
  powerThree:'It does not replace the second model\'s review: such a version is marked separately and the project still waits for that review or your decision.',
  powerConfirm:'Turn on Full Power', powerOn:'On: limits drain very fast, work continues until the provider refuses.',
  powerOff:'When the second model waits, the same one reviews and refines. Very aggressive on limits.',
  publicTitle:'Make the repository public?', publicWarn:'Anyone on the internet will see the code and its whole history.',
  publicOne:'The code and history are scanned for secrets and publishing stops if anything turns up. The scan only catches common patterns.',
  publicTwo:'Going private later does not remove copies someone already took.', publicConfirm:'Publish',
  available:'Available', paused:'Paused', noReading:'No reading', window5:'5 h window', week:'Week', handoffTick:'Work is handed over here',
  readFail:e=>`Could not read the limit: ${e}`, back:(r,w,c)=>`${r}, back ${w} (${c})`, windowResets:c=>`5 h window renews at ${c}`,
  read:a=>`Read ${a}`, plan:p=>`${p} plan`, secAgo:n=>`${n} s ago`, minAgo:n=>`${n} min ago`, hAgo:n=>`${n} h ago`,
  inMin:n=>`in ${n} min`, inH:(h,m)=>`in ${h} h ${m} min`, inD:n=>`in ${n} days`, inDH:(d,h)=>`in ${d} d ${h} h`,
  s_queued:'Queued', s_running:'In progress', s_stopping:'Stopping', s_stopped:'Stopped', s_done:'Finished', s_attention:'Needs attention',
  l_approved:'Checked by both models', l_tested:'Tests passed', l_self_reviewed:'Reviewed by one model (Full Power)', l_proposed:'No tests: the agent\'s claim only', l_single:'One model: no second review',
  modelOff:'Off', inModel:'in the model name', a_single:' · one-model mode', role:'Role', r_general:'General', r_architect:'Architect', r_implementer:'Implementer', r_tester:'Tester', r_analyst:'Systems analyst', r_content:'Content creator',
  tabAssets:'Content', aTitle:'Order content', aImage:'Graphic', aText:'Text', aPrompt:'What to make', aPath:'File in the project', aPathPh:'e.g. assets/logo.png',
  aSize:'Size', aStyle:'Style', aOrder:'Order', aNone:'No orders. Models order content in .sol83/assets.json, and you can order it here.', aWaiting:'Waiting for the next turn',
  as_requested:'ordered', as_done:'done', as_error:'error', aByUser:'your order',
  aHint:'A model with the Content creator role makes the orders, for example Gemini through Antigravity, which draws with an image model. The project does not finish while orders wait.',
  coordTitle:'Message coordinator', c_local:m=>`Local LLM through Ollama (${m})`, c_idle:'The model not working right now (Claude or Codex)', c_claude:'Claude', c_codex:'Codex', c_gemini:'Gemini through Antigravity',
  cUnavailable:'unavailable', cNow:w=>`Answering now: ${w}.`, cDefault:'default',
  coordHint:'It answers messages and tells a question from an order or a note. It applies to all projects. When the chosen one cannot answer, the local model does, and without it the coordinator answers from its own records. The local model uses no subscription and reads no files: it gets the coordinator\'s facts and a plan summary.',
  fallbackLabel:'When a model with a role is unavailable', fb_general:'A General model takes over', fb_wait:'The project waits', a_role:c=>`Waiting for a model with the needed role · ${c}`,
  setupTitle:'The .gemini-setup script', setupHint:'This is code from the project repository. Sol-83 runs it only inside the OS sandbox, and only after you approve this exact content. Any change to the script needs a new approval.',
  setupApprove:'I approve this content, run it in the sandbox', setupApproved:'Approved (sha {0}).', setupNoSandbox:'No OS sandbox: the script will not run.',
  secretsConfirm:(items) => `Possible secrets found:\n\n${items}\n\nPublish anyway? Check every item: a push cannot really be taken back.`,
  deleteTitle:'Delete project', deleteButton:'Delete project', deleteHint:'Removes the project from Sol-83 for good, with no archive. A running project stops first.',
  deleteAsk:n=>`Delete "${n}" for good?`, deleteWarn:'This cannot be undone.', deleteConfirm:'Delete for good',
  deleteWhat:'The history, versions, transcripts, orders, the agents\' workshop and the test folder go away.',
  deleteOwn:p=>`The repository Sol-83 created goes too: ${p}`, deleteUser:(p,b)=>`Your repository stays: ${p}. Only branch ${b}, the version tags and Sol-83's working folders go.`,
  deleteKeeps:'GitHub stays untouched: what you sent there is your archive.',
  save:'Save', verifyHint:'Numbered versions and the "Run from here" folder are based on this. Without a command, a version appears only when a model declares it ready. A change applies from the end of the current turn. The command runs in the OS sandbox: writes only in the project folder, no network by default (change it under Security).',
  rolesHint:'Architect: plan, plan rebuilds and research. Implementer: tasks from the plan. Tester: review and tests. Systems analyst: gaps and a plan to close them as debt. Content creator: approved orders of graphics, texts and story. General: planning, implementation and review, without making ordered content. A model may hold several roles. Every kind of work needs a model that is on.', a_singleWait:c=>`Model unavailable, the other is off · resuming at ${c}`,
  none:'No thinking', minimal:'Minimal', low:'Low', medium:'Medium', high:'High', xhigh:'Extra (xhigh)', max:'Maximum', ultra:'Ultra',
  a_review:(w,t,m)=>`${w} is reviewing in a new session (Full Power) · turn ${t}/${m}`, a_solo:(w,r)=>` · solo: ${w} unavailable (${r})`,
  a_turn:(w,t,m)=>`${w} is working · turn ${t}/${m}`, a_limits:c=>`Both models unavailable · resuming at ${c}`,
  a_partner:c=>`Code ready · waiting for the second model's review (${c})`, a_start:'Starting the engine',
  model:'Model', thinking:'Thinking level', toTest:'To test', noVersionYet:'No version to test yet.', noVersionLeft:'No version to test.',
  noVersionHint:'A version appears once the coordinator confirms the code works.', allRejected:'You reported all of them as not working; a fix is under way.',
  wipNoVersion:n=>`In progress: ${n} checkpoint(s). This is work in progress, do not test it.`, wipLabel:'Work in progress:',
  wipCount:n=>`${n} checkpoint(s) after the last version`, wipFiles:n=>`, ${n} unsaved files`, wipRun:'This is work in progress, do not test it.', wipIdle:'This state has not passed the checks.',
  works:'Works', broken:'Does not work', worksYou:'Works: confirmed by you',
  commit:'commit', newer:n=>`Newer v${n} passed the tests, but the second model has not checked it yet.`, newerRejected:n=>`You reported newer v${n} as not working; a fix is under way.`, confirmed:n=>`Last confirmed by you: v${n}`,
  whatToCheck:'What to check', noEvents:'Nothing has happened yet.', noVersions:'Versions appear once the code passes the checks.',
  turnBy:(t,w)=>`turn ${t}, ${w}`, inTestFolder:'In the "Run from here" folder', testThis:'Test this version', tag:'tag',
  noTranscript:'The transcript appears after the first turn.', k_verify:'Test command', k_noVerify:'none: the coordinator cannot confirm the code works', k_source:'Source folder', k_later:'created at start',
  k_branch:'Working branch', k_work:'Working folder', k_models:'Models', k_turns:'Turn limit', k_added:'Added',
  byCoordinator:'Coordinator, from its own records', byObserver:w=>`${w}, observing without changing code`, waitingAnswer:'Waiting for an answer…',
  notePending:'Waiting for the next turn', noteSent:(w,t)=>`Delivered: ${w}, turn ${t}`, urgent:'Urgent',
  acceptNoReview:'Accept without review', stopAfter:'Stop after this turn', stopNow:'Stop now', resume:'Resume', keepWorking:'Continue work',
  tabRun:'Activity', tabVersions:'Versions', tabTranscript:'Transcript', tabTask:'Task', modelsTitle:'Models and thinking level', modelsHint:'Changes apply from the next turn.',
  askTitle:'Ask about status', askPlaceholder:'What stage is the work at?', askHint:'The model that is not working right now answers. A question does not order work: use notes or the button under the answer.', orderWork:'Order this as work', ordered:'Ordered as work', ask:'Ask',
  notesTitle:'Your notes and requests', notePlaceholder:'The next model takes this into account at handoff', urgentCheck:'Urgent: interrupt the current turn', addNote:'Add note',
  heroTitle:'Pick a project or start a new one', heroText:'Codex and Claude take turns, check each other and take over when one runs out of limit.',
  formLead:'Paste a .md file or describe the task. The models hand results to each other and show you only checked versions.',
  fTask:'Task and acceptance criteria', fTaskPlaceholder:'# What to build\n\nAcceptance criteria:\n- ...', fDrop:'You can drop a .md file here.', fFile:'Choose file',
  fName:'Name', fNameHint:'Default: first line of the task', fVerify:'Test command', fVerifyPlaceholder:'e.g. python3 -m pytest', fVerifyHint:'The coordinator numbers versions based on this. Without it, it cannot confirm the code works.',
  fFolder:'Existing project folder', fFolderPlaceholder:'/full/path. Empty: new project', fFolderHint:'Must be a Git repository with no uncommitted changes. Your code stays untouched: work happens on a separate branch.',
  fModelsHint:'You can change this at any time, even during work.', fAdvanced:'Advanced settings', fTurns:'Turn limit', fSubmit:'Start project',
  tabPlan:'Plan', tabEff:'Efficiency', tabSettings:'Settings',
  msgTitle:'Message to the models', msgPlaceholder:'Ask about status, order work or add a note', send:'Send', interrupt:'Interrupt the current work',
  msgHint:'The message coordinator (chosen in Settings) answers and decides whether it is a question or work for the agents. Interrupting stops the turn at once and passes the message on.',
  gNoReading:'Antigravity reports no limits: availability is learned from errors.',
  withdraw:'Take it back', withdrawn:'Taken back', monTokens:'Tokens in total', monTokensTurns:'Tokens of recent turns',
  accounts:'Accounts and sign-in', checkConnection:'Check connection', checkHint:'Checks the CLI and sign-in without calling a model: no limit is used.', cliVersion:'CLI', authState:'Sign-in', account:'Account', planLabel:'Plan', stale:'data out of date', loginWith:'Sign in with', authOk:'signed in', authNotLogged:'not signed in', authExpired:'session expired', authWrongAccount:'wrong account', authNoModel:'no access to the model', authPlanLimit:'subscription limit', authRateLimit:'rate limited', authNetwork:'network error', authOutage:'provider outage', authUnknown:'cause unknown', authNoCli:'no CLI', authApiKey:'API key (not used by Sol-83)',
  selection:'Model choice', sel_manual:'Manual', sel_auto_economy:'Auto — economy', sel_auto_power:'Auto — power', topShort:'top', topWarning:'The provider\'s top model: it can use up subscription limits very fast. Auto never picks it; a manual choice needs confirmation.', autoHint:'Auto picks this provider\'s model before every turn by kind of work, results and limits, never the top or an unclassified one. The decision and its reason are in Activity.', aboutModel:'About the model', usesLabel:'Uses', autoLabel:'Auto', autoManualOnly:'manual only', autoAllowed:'allowed', autoUnclassified:'unclassified model: not used by Auto',
  licTitle:'Project license', licNow:l=>`Now: ${l}.`, licKind:'Kind', lic_standard:'standard open source', lic_custom:'own / source-available', lic_none:'no declared license', licStandard:'Standard license', licHolder:'Copyright holder (for LICENSE)', licOverwrite:'replace the existing LICENSE file (a deliberate decision)', licCustom:'Text of your own license', licHint:'Standard texts are unmodified (SPDX ids). The choice does not change the license of dependencies or anyone else\'s code. No license does not mean free use. Sol-83\'s own license is separate.',
  securityTitle:'Security', secNetwork:'Tests may use the network', secUnsandboxed:'Run without the sandbox (not recommended)', secUnsandboxedWarn:'Code written by the agents (tests, .gemini-setup, RUN) will run with your account\'s full rights. Are you sure?', sandboxOn:k=>`OS sandbox: ${k}.`, sandboxOff:'No OS sandbox: code from repositories is not run.', turnConfigNow:'Current (last) turn', turnConfigHint:'Changes below apply from the next turn; the current turn keeps its configuration.',
  notAvailable:'no data', usageByModel:'Token usage by provider and model', colTurns:'Turns', colCache:'Cache (read)', colProvider:'Provider', col5h:'5 h window', colEquiv:'Full windows', colWeek:'Week', colGaps:'Turns without a reading', sharedTurns:'shared with another project', modelUnconfirmed:'model not confirmed by the CLI',
  usageHelp:'Per-turn values: the increase of the same session\'s counter. Claude reports the turn, Codex and Antigravity the total of the whole session, from which the coordinator takes the increase. Codex reports only a total, so input and output are unavailable. "no data" does not mean zero. Categories of different providers are not directly comparable.',
  windowsTitle:'Project share of subscription limits', windowsHelp:'An estimate from how the account\'s limit readings moved during the project\'s turns: other work on the same account is included. 250% of the 5 h window means 2.5 full windows, not the current balance. Providers are never added together. Antigravity offers no readings, so there is no data.',
  colTurn:'Turn', colModel:'Model', colIn:'Input', colOut:'Output', colTotal:'Total', colSession:'Session turn', freshSession:'new',
  tokensHelp:'Input is the whole context the turn read, cache included. It grows with each turn of the same session, which is why the coordinator starts a fresh one every few turns (6 today). Codex reports only a total.', gNotReady:'Not ready', gOldProject:'This project predates Gemini, so Gemini is off. Switched on, it joins after the current turn: the engine restarts and the models get fresh sessions.',
  planNone:'The plan appears in the first turn: the models lay out features, architecture and turn budgets.', planProblem:'The plan has an error: ', planArch:'Architecture', planFile:'Plan file', planDebt:'Technical debt',
  planSpend:'Where the weekly limit went', pr_must:'must', pr_should:'should', pr_could:'could', st_todo:'to do', st_doing:'in progress', st_done:'done', st_deferred:'deferred',
  grp_must:'must', grp_should:'should', grp_could:'could', grp_debt:'debt', grp_unassigned:'unassigned',
  colItem:'Item', colPrio:'Priority', colStatus:'Status', colTurns:'Turns', colCost:'% week', startItem:'Order', overBudget:'over budget',
  liveNone:'No record of the models\'s work yet.', liveAgent:w=>`${w}: latest actions from its session log. Watching costs nothing.`,
  runTitle:'How to run and test', pathRepo:'Repository on disk', pathWork:'Work in progress (agents)', pathTest:'Test folder',
  runHere:'Run from here', howToRun:'How to run', otherFolders:'Other folders', pathRepoBranch:b=>`Repository, code on branch ${b}`,
  pathWorkNote:'Agents\' workshop: work goes on here, do not run from it', pathTestOld:n=>`Older test folder · v${n}`, runNotYet:'The "Run from here" folder gets a version once the coordinator confirms the code works.',
  effHelp:'How to read this: cost is the percentage of the model\'s weekly limit, measured by reading the limit before and after each turn. Claude counts against your Claude plan and Codex against your ChatGPT plan, so the percentages are not comparable. Other work on the account at the same time, such as your own chats, is included in a turn\'s cost. The goal and the step verdicts come from the models: each judges its partner\'s previous step against the acceptance criteria. A signal to step in means work costs limit while the goal does not get closer: read it and decide whether to change direction, defer an item or stop the project.',
  monGoal:'Goal according to the models', monVerdicts:'Verdicts on recent steps', v_closer:'closer', v_not_closer:'not closer', v_back:'set back', monNoGoal:'not rated yet',
  monTitle:'Efficiency', monSignal:'Time to step in', monTurns:'Turns / versions', monSince:'Turns since the last version', monCost:'Total cost (% of week)', monPerVersion:'Cost per version', monLines:'Lines since version: changed / net', monOk:'No signals: work keeps producing versions.', monSidebar:'signal',
  finalTitle:'Final answer', noteResponse:'Model\'s reply', loading:'Loading…',
  ghRepos:'GitHub repositories', ghFilter:'Search repositories', ghNoRepos:'No results.', ghRepoWork:'Start work in the repository', ghAuto:'Send new versions automatically', ghPr:'Open Pull Request',
  ghFormRepo:r=>`GitHub repository: ${r}`, ghFormHint:'Agents work on a separate branch. Your main stays untouched, and in a private repository each new version appears on that branch automatically.', ghPushed:d=>`updated ${d}`,
  ghTitle:'GitHub', ghName:'Repository name', ghPrivate:'Private', ghPublic:'Public', ghCreate:n=>`Create and send v${n}`, ghNeedVersion:'Only a finished version can be sent. Work in progress never leaves this computer.',
  ghSent:n=>`Sent: v${n}`, ghSend:n=>`Send v${n}`, ghUpToDate:'The latest checked version is already there.', ghToPublic:'Make public', ghToPrivate:'Make private', ghHint:'Every upload is your click. Nothing goes there on its own.',
}};
// A look adds its own texts (window.SOL83_TEXT, set before this file) to the shared ones.
for(const lang of ['pl','en']) Object.assign(TEXT[lang], window.SOL83_TEXT?.[lang] || {});
const ICON = {
  good:'<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 6.5 5 9l4.5-5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  warn:'<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M6 2.5v4.2M6 9.2v.1" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  bad:'<svg viewBox="0 0 12 12" aria-hidden="true"><path d="m3 3 6 6M9 3l-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  idle:'', run:''
};
const STATUS_KIND = {queued:'idle', running:'run', stopping:'warn', stopped:'idle', done:'good', attention:'bad'};
const LEVEL_KIND = {approved:'good', tested:'good', single:'good', self_reviewed:'warn', proposed:'warn'};
const NAME = {claude:'Claude', codex:'Codex', gemini:'Gemini', local:'Lokalny LLM'};
const SIDES = ['codex','claude','gemini'];
const others = (p, speaker) => SIDES.filter(s => s !== speaker && p[s+'_model'] && p[s+'_model'] !== 'none').map(s => NAME[s]).join(', ');
const MAJOR = new Set(['monitor','handoff','takeover','version','done','attention','waiting','github','note','note_reply','question','answer','final','deliver']);
// Gemini: Flash by default. Antigravity draws its quota by API prices, and its "default" may be the far dearer Argon.
const DEFAULT_MODELS = {claude:['opus','xhigh'], codex:['gpt-6.1-sol','high'], gemini:['gemini-3.8-flash-medium','medium']};
const state = {overview:null, detail:null, tab:'przebieg', html:{}, transcript:'', rejecting:null, lang:'pl', github:null, ghKey:null, pendingPublic:null, open:new Set(), bodies:{}};

function loadLang(){
  try{ const saved = localStorage.getItem('gemini-lang'); if(saved === 'pl' || saved === 'en') return saved; }catch(e){}
  return (navigator.language || 'pl').toLowerCase().startsWith('pl') ? 'pl' : 'en';
}
state.lang = loadLang();
const t = (key, ...args) => { const v = TEXT[state.lang][key]; return typeof v === 'function' ? v(...args) : v ?? key; };
const local = (row, field) => (state.lang === 'en' && row?.[field+'_en']) || row?.[field] || '';
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : '';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pill = (text, kind) => `<span class="pill ${kind}">${ICON[kind]||''}${esc(text)}</span>`;
const route = () => { const m = location.hash.match(/^#\/p\/(\w+)/); return m ? m[1] : (location.hash.startsWith('#/nowy') ? 'new' : null); };
const formRepo = () => decodeURIComponent(location.hash.match(/^#\/nowy\/(.+)$/)?.[1] || '');
function clock(ts){
  if(!ts) return '–';
  const d = new Date(ts*1000), now = new Date(), locale = t('locale');
  const time = d.toLocaleTimeString(locale,{hour:'2-digit',minute:'2-digit'});
  return d.toDateString() === now.toDateString() ? time : d.toLocaleDateString(locale,{day:'numeric',month:'short'})+', '+time;
}
function ago(ts){
  const s = Math.max(0, Date.now()/1000 - ts);
  if(s < 60) return t('secAgo', Math.round(s));
  if(s < 3600) return t('minAgo', Math.round(s/60));
  return t('hAgo', Math.round(s/3600));
}
function until(ts){
  const m = Math.max(0, Math.round((ts - Date.now()/1000)/60));
  if(m < 60) return t('inMin', m);
  const h = Math.floor(m/60);
  return h < 24 ? t('inH', h, m%60) : t('inDH', Math.floor(h/24), h%24);
}
// A limit reset or a pause end always with its date and weekday: a wait over a day is not misread.
function dateTime(ts){
  if(!ts) return '–';
  const d = new Date(ts*1000), locale = t('locale');
  return d.toLocaleDateString(locale,{weekday:'short', day:'numeric', month:'short'}) + ', ' + d.toLocaleTimeString(locale,{hour:'2-digit',minute:'2-digit'});
}
function setHTML(id, html){
  const el = document.getElementById(id);
  if(el && state.html[id] !== html){ el.innerHTML = html; state.html[id] = html; }
}
// Sidebar width: dragged by the user, kept between 260 and 640 px, remembered in this browser.
function setSideWidth(px){
  const width = Math.max(260, Math.min(640, Math.round(px)));
  document.documentElement.style.setProperty('--side-width', width + 'px');
  try{ localStorage.setItem('sol83-side-width', width); }catch(error){}
}
try{ const saved = Number(localStorage.getItem('sol83-side-width')); if(saved) setSideWidth(saved); }catch(error){}
(() => {
  const handle = document.getElementById('side-resize');
  if(!handle) return;
  handle.addEventListener('pointerdown', e => {
    handle.setPointerCapture(e.pointerId); handle.classList.add('dragging');
    const move = ev => setSideWidth(ev.clientX);
    const up = () => { handle.classList.remove('dragging'); handle.removeEventListener('pointermove', move); handle.removeEventListener('pointerup', up); };
    handle.addEventListener('pointermove', move); handle.addEventListener('pointerup', up);
  });
  handle.addEventListener('keydown', e => {
    const now = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--side-width')) || 330;
    if(e.key === 'ArrowLeft') setSideWidth(now - 20);
    if(e.key === 'ArrowRight') setSideWidth(now + 20);
  });
})();
// The skin is the user's preference, apart from language and project (spec 18).
function applySkin(skin){
  if(skin) document.documentElement.dataset.theme = skin; else delete document.documentElement.dataset.theme;
  try{ localStorage.setItem('sol83-skin', skin || ''); }catch(error){}
  const pick = document.getElementById('skin-pick'); if(pick) pick.value = skin || '';
}
try{ applySkin(localStorage.getItem('sol83-skin') || ''); }catch(error){ applySkin(''); }
// One key per user action: a retransmitted request is recognised, a new click is new work.
const requestKey = () => (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2));
async function api(path, body){
  const options = body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)};
  const response = await fetch(path, options);
  const data = await response.json();
  if(!response.ok){ const error = new Error(local(data,'error') || 'Server error'); error.data = data; throw error; }
  return data;
}
function applyStatic(){
  document.documentElement.lang = state.lang;
  document.querySelectorAll('[data-t]').forEach(el => { el.textContent = t(el.dataset.t); });
  document.querySelectorAll('[data-t-placeholder]').forEach(el => { el.placeholder = t(el.dataset.tPlaceholder); });
  document.querySelectorAll('[data-lang]').forEach(el => el.setAttribute('aria-pressed', el.dataset.lang === state.lang));
  document.querySelectorAll('[data-t-title]').forEach(el => { el.title = t(el.dataset.tTitle); });
  document.querySelectorAll('[data-t-aria]').forEach(el => el.setAttribute('aria-label', t(el.dataset.tAria)));
  document.querySelectorAll('[data-look]').forEach(el => el.setAttribute('aria-pressed', el.dataset.look === LOOK));
}
// Look (2026-11-09): Classic (/) or Pro (/pro), the same functions and data; the choice is remembered in this browser.
const LOOK = location.pathname === '/pro' ? 'pro' : 'classic';
document.addEventListener('click', e => {
  const button = e.target.closest('[data-look]');
  if(!button) return;
  try{ localStorage.setItem('sol83-look', button.dataset.look); }catch(error){}
  if(button.dataset.look !== LOOK) location.href = (button.dataset.look === 'pro' ? '/pro' : '/') + location.hash;
});

let limitsData = {};
function meter(name, label, win, threshold){
  if(!win) return '';
  const now = Date.now()/1000, rolled = win.resets_at && win.resets_at <= now;
  const used = rolled ? 0 : win.used;
  return `<div class="meter-row"><span>${label}</span>
    <div class="track" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${used}" aria-label="${NAME[name]}: ${label}, ${used}%">
      <div class="fill ${name}" style="width:${Math.min(100,used)}%"></div>
      ${threshold < 100 ? `<div class="tick" style="left:${Math.min(99.5, threshold)}%" title="${esc(t('handoffTick'))}"></div>` : ''}
    </div><span class="pct">${Math.round(used)}%</span></div>`;
}
function renderLimits(limits){
  limitsData = limits;
  setHTML('limits', ['codex','claude'].map(name => {
    const l = limits[name] || {};
    const windows = l.windows || {};
    const status = l.error ? pill(t('noReading'),'warn') : l.available ? pill(t('available'),'good') : pill(t('paused'),'bad');
    const five = windows.five_hour, week = windows.seven_day;
    let foot;
    if(l.error) foot = esc(t('readFail', l.error));
    else if(!l.available) foot = esc(t('back', cap(local(l,'reason')), until(l.until), dateTime(l.until))) + (l.estimate ? ` <span class="est" title="${esc(t('estimateHelp'))}">${esc(t('estimateShort'))}</span>` : '');
    else foot = five?.resets_at ? esc(t('windowResets', dateTime(five.resets_at))) : '';
    if(l.paused) foot += `<br><button class="btn small retry" data-act="retry" data-provider="${name}" title="${esc(t('estimateHelp'))}">${esc(t('retryNow'))}</button>`;
    const plan = l.plan ? ` · ${esc(t('plan', l.plan))}` : '';
    return `<div class="limit"><div class="limit-head"><span class="agent"><span class="swatch ${name}"></span>${NAME[name]}</span>${status}</div>
      ${meter(name,t('window5'),five,l.threshold ?? 95)}${meter(name,t('week'),week,l.weekly_threshold ?? 100)}
      <div class="limit-foot">${foot}${foot?'<br>':''}${esc(t('read', l.read_at?ago(l.read_at):'–'))}${plan}</div></div>`;
  }).join('') + geminiLimit(limits.gemini));
  for(const name of ['claude','codex']){
    for(const [prefix, field] of [['th-','configured'],['wk-','configured_weekly']]){
      const input = document.getElementById(prefix+name);
      if(document.activeElement !== input && limits[name]) input.value = limits[name][field];
    }
  }
}
const AUTH_TEXT = {ok:'authOk', not_logged_in:'authNotLogged', session_expired:'authExpired', wrong_account:'authWrongAccount',
  no_model_access:'authNoModel', plan_limit:'authPlanLimit', rate_limit:'authRateLimit', network:'authNetwork',
  provider_outage:'authOutage', unknown:'authUnknown', missing_cli:'authNoCli', api_key:'authApiKey'};
function renderProviders(rows){
  if(!rows) return;
  setHTML('providers', ['claude','codex','gemini'].map(name => {
    const r = rows[name] || {}, ok = r.auth === 'ok';
    const lines = [r.installed ? `${esc(t('cliVersion'))}: ${esc(r.version || '?')}` : esc(t('authNoCli')),
      `${esc(t('authState'))}: ${esc(t(AUTH_TEXT[r.auth] || 'authUnknown'))}`,
      r.account ? `${esc(t('account'))}: ${esc(r.account)}${r.organization ? ' · ' + esc(r.organization) : ''}` : `${esc(t('account'))}: ${esc(t('notAvailable'))}`,
      `${esc(t('planLabel'))}: ${r.plan ? esc(r.plan) + ' <span class="hint">(' + esc(r.plan_source || '') + ')</span>' : esc(t('notAvailable'))}`,
      r.problem ? `<span class="hint">${esc(r.problem)}</span>` : '', r.note ? `<span class="hint">${esc(r.note)}</span>` : '',
      `<span class="hint">${esc(t('read', r.read_at ? ago(r.read_at) : '–'))}${r.stale ? ' · ' + esc(t('stale')) : ''}</span>`,
      ok ? '' : `<span class="hint">${esc(t('loginWith'))}: <code>${esc(r.login || '')}</code></span>`];
    return `<div class="limit"><div class="limit-head"><span class="agent"><span class="swatch ${name}"></span>${NAME[name]}</span>${pill(t(AUTH_TEXT[r.auth] || 'authUnknown'), ok ? 'good' : 'warn')}</div>
      <div class="limit-foot">${lines.filter(Boolean).join('<br>')}</div></div>`;
  }).join(''));
}
function geminiLimit(g){
  if(!g) return '';
  const status = g.problem ? pill(t('gNotReady'),'warn') : g.available ? pill(t('available'),'good') : pill(t('paused'),'bad');
  const foot = g.problem ? local(g,'problem') : !g.available ? t('back', cap(local(g,'reason')), until(g.until), dateTime(g.until)) : t('gNoReading');
  const est = !g.available && g.estimate ? ` <span class="est" title="${esc(t('estimateHelp'))}">${esc(t('estimateShort'))}</span>` : '';
  const retry = g.paused ? `<br><button class="btn small retry" data-act="retry" data-provider="gemini" title="${esc(t('estimateHelp'))}">${esc(t('retryNow'))}</button>` : '';
  return `<div class="limit"><div class="limit-head"><span class="agent"><span class="swatch gemini"></span>Gemini · Antigravity</span>${status}</div>
    <div class="limit-foot">${esc(foot)}${est}${retry}</div></div>`;
}
function activity(p, live){
  if(!live || !live.phase) return '';
  if(live.phase === 'turn_running'){
    if(live.mode === 'self_review') return t('a_review', NAME[live.speaker], live.turn, p.max_turns);
    const solo = live.mode === 'solo' ? t('a_solo', others(p, live.speaker), local(live,'reason')) : live.mode === 'single' ? t('a_single') : '';
    return t('a_turn', NAME[live.speaker], live.turn, p.max_turns) + solo;
  }
  // A wait recorded by this version names each model, its cause, the time and whether it is a guess.
  if(liveDetail(live)) return local(live,'reason');
  if(live.phase === 'waiting_limits') return SIDES.filter(s => p[s+'_model'] && p[s+'_model'] !== 'none').length === 1 ? t('a_singleWait', dateTime(live.until)) : t('a_limits', dateTime(live.until));
  if(live.phase === 'waiting_partner') return t('a_partner', dateTime(live.until));
  if(live.phase === 'waiting_role') return t('a_role', dateTime(live.until));
  return t('a_start');
}
function effortOptions(side, modelId, current){
  const model = state.catalog?.[side]?.find(m => m.id === modelId);
  const efforts = model?.efforts?.length ? model.efforts : [];
  const list = !current || efforts.includes(current) ? efforts : [current, ...efforts];
  return list.map(e => `<option value="${esc(e)}" ${e===current?'selected':''}>${esc(t(e))}</option>`).join('');
}
const ROLES = ['general','architect','implementer','tester','analyst','content'];
function coordinatorControl(c){
  if(!c) return '';
  const label = k => k === 'local' ? t('c_local', c.local_model) : t('c_'+k);
  const down = k => (k === 'local' && !c.local_ready) || (k === 'gemini' && !c.gemini_ready);
  const options = ['local','idle','claude','codex','gemini'].map(k => `<option value="${k}" ${k===c.effective?'selected':''}>${esc(label(k))}${down(k)?' ('+esc(t('cUnavailable'))+')':''}${!c.choice && k===c.effective?' · '+esc(t('cDefault')):''}</option>`).join('');
  const now = down(c.effective) ? (c.local_ready ? label('local') : t('byCoordinator')) : label(c.effective);
  return `<select id="coordinator-pick" aria-label="${esc(t('coordTitle'))}">${options}</select><p class="hint" style="margin-top:4px">${esc(t('cNow', now))}</p>`;
}
function fallbackControl(value){
  return `<label class="fallback-pick" style="grid-column:1/-1;font-size:12px;color:var(--text-3)">${esc(t('fallbackLabel'))}<select data-side="team" data-kind="fallback">
    ${['general','wait'].map(f => `<option value="${f}" ${f===(value||'general')?'selected':''}>${esc(t('fb_'+f))}</option>`).join('')}</select></label>`;
}
const isTop = (side, id) => (state.catalog?.catalog?.models || []).some(m => m.provider === side && m.id === id && m.tier === 'top');
const catalogEntry = (side, id) => (state.catalog?.catalog?.models || []).find(m => m.provider === side && m.id === id);
// A top model needs a visible warning and a confirmation of exactly that model (spec 6.1).
async function withTopConfirm(path, body){
  try{ return await api(path, body); }
  catch(error){
    if(!error.data?.confirm_top || !confirm(error.message)) throw error;
    return await api(path, {...body, confirm_top:error.data.confirm_top});
  }
}
function selectionControl(side, selection){
  return `<label style="display:block;font-size:12px;color:var(--text-3);margin-top:4px">${esc(t('selection'))}<select data-side="${side}" data-kind="selection">
    ${['manual','auto_economy','auto_power'].map(m => `<option value="${m}" ${m===(selection||'manual')?'selected':''}>${esc(t('sel_'+m))}</option>`).join('')}</select></label>`;
}
function modelNote(side, model, selection){
  if(selection && selection !== 'manual') return `<p class="hint">${esc(t('autoHint'))}</p>`;
  if(side === 'gemini' && model === 'default') return `<p class="alert warn">${esc(t('geminiDefaultWarn'))}</p>`;
  const entry = catalogEntry(side, model);
  const top = isTop(side, model) ? `<p class="alert">${esc(t('topWarning'))}</p>` : '';
  const facts = entry ? `<details class="hint"><summary>${esc(t('aboutModel'))}</summary>${esc(entry.facts?.[state.lang] || '')}<br>${esc(t('usesLabel'))}: ${esc(entry.uses?.[state.lang] || '')} (${esc(entry.uses_basis || '')})<br>${esc(t('autoLabel'))}: ${esc(entry.tier === 'top' ? t('autoManualOnly') : entry.tier ? t('autoAllowed') : t('autoUnclassified'))}<br>${(entry.sources || []).map(s => esc(s.url) + ' · ' + esc(s.checked)).join('<br>')}</details>` : `<p class="hint">${esc(t('autoUnclassified'))}</p>`;
  return top + facts;
}
function sideControls(side, model, effort, role, selection){
  const models = state.catalog?.[side] || [];
  const off = model === 'none';
  const problem = side === 'gemini' && state.catalog?.gemini_problem && off ? local(state.catalog,'gemini_problem') : '';
  const fixed = !off && models.find(m => m.id === model)?.efforts?.length === 0;
  const options = [...(off || models.some(m => m.id === model) ? models : [{id:model,label:model}, ...models]), {id:'none', label:t('modelOff')}];
  return `<div class="side-pick"><div class="agent"><span class="swatch ${side}"></span>${NAME[side]}</div><div class="pair">
    <label>${esc(t('model'))}<select data-side="${side}" data-kind="model" ${problem?'disabled':''}>${options.map(m => `<option value="${esc(m.id)}" ${m.id===model?'selected':''}>${esc(m.label)}${isTop(side, m.id) ? ' ⚠ ' + esc(t('topShort')) : ''}</option>`).join('')}</select></label>
    <label>${esc(t('thinking'))}<select data-side="${side}" data-kind="reasoning" ${off||fixed?'disabled':''}>${off ? '' : fixed ? `<option value="">${esc(t('inModel'))}</option>` : effortOptions(side, model, effort)}</select></label>
  </div><fieldset class="roles-pick" data-side="${side}" style="border:0;padding:0;margin:4px 0 0;font-size:12px;color:var(--text-3)"><legend>${esc(t('roles'))}</legend>
    ${ROLES.map(r => `<label class="check" title="${esc(t('rd_'+r))}"><input type="checkbox" value="${r}" ${(role||'general').split(',').includes(r)?'checked':''}> ${esc(t('r_'+r))}</label>`).join(' ')}</fieldset>${off ? '' : selectionControl(side, selection) + modelNote(side, model, selection)}${problem?`<p class="hint">${esc(problem)}</p>`:''}</div>`;
}
// ---- Project list (2026-11-08) -------------------------------------------------------------
// The state is said in words with an icon, never by colour alone. "In progress" holds what runs,
// waits for a model or a limit, or is queued; the other groups are compact and remember whether the
// user opened them. A wait names the model, the cause, the time and whether that time is a guess.
const SVG = {
  play:'<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3.5 2.2v7.6L9.8 6z" fill="currentColor"/></svg>',
  clock:'<svg viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4.6" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6 3.4V6l1.8 1.2" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  pause:'<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3.6 2.5v7M8.4 2.5v7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
  user:'<svg viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="3.8" r="2.1" fill="currentColor"/><path d="M1.8 10.6c.5-2.3 2.2-3.5 4.2-3.5s3.7 1.2 4.2 3.5z" fill="currentColor"/></svg>',
  warn:'<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M6 1.4 11 10.4H1z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M6 4.6v2.6M6 8.7v.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  queue:'<svg viewBox="0 0 12 12" aria-hidden="true"><circle cx="2.5" cy="6" r="1.2" fill="currentColor"/><circle cx="6" cy="6" r="1.2" fill="currentColor"/><circle cx="9.5" cy="6" r="1.2" fill="currentColor"/></svg>',
  stop:'<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2.8" y="2.8" width="6.4" height="6.4" rx="1" fill="currentColor"/></svg>',
  check:'<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.3 6.4 4.9 9l4.8-5.8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  cross:'<svg viewBox="0 0 12 12" aria-hidden="true"><path d="m3 3 6 6M9 3l-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  half:'<svg viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4.4" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6 1.6a4.4 4.4 0 0 1 0 8.8z" fill="currentColor"/></svg>',
};
const liveDetail = live => { try{ return live?.detail ? JSON.parse(live.detail) : null; }catch(error){ return null; } };
// One state per project: word, icon and tone, from the server's state_kind and the live phase.
function projectState(p){
  const phase = p.live?.phase;
  if(p.status === 'stopping') return {key:'k_stopping', icon:'pause', tone:'k-idle'};
  if(p.status === 'running'){
    if(p.state_kind === 'error') return {key:'k_error', icon:'warn', tone:'k-error'};
    if(phase === 'turn_running') return {key:'k_working', icon:'play', tone:'k-working'};
    if(phase === 'waiting_partner') return {key:'k_review', icon:'clock', tone:'k-wait'};
    if(phase === 'waiting_role') return {key:'k_role', icon:'clock', tone:'k-wait'};
    if(phase === 'waiting_limits') return {key:'k_limit', icon:'pause', tone:'k-wait'};
    return {key:'k_starting', icon:'play', tone:'k-working'};
  }
  return ({queued:{key:'k_queued', icon:'queue', tone:'k-idle'}, user:{key:'k_user', icon:'user', tone:'k-user'},
           error:{key:'k_error', icon:'warn', tone:'k-error'}, dependency:{key:'k_dependency', icon:'clock', tone:'k-wait'},
           done:{key:'k_done', icon:'check', tone:'k-done'}})[p.state_kind] || {key:'k_stopped', icon:'stop', tone:'k-idle'};
}
const stateChip = st => `<span class="state ${st.tone}">${SVG[st.icon]}${esc(t(st.key))}</span>`;
const sideWait = s => `<b>${esc(NAME[s.side] || s.side)}</b>: ${esc(local(s,'reason'))}${s.until ? ' · '+esc(t('untilShort', dateTime(s.until))) : ''}${s.estimate ? ` <span class="est" title="${esc(t('estimateHelp'))}">${esc(t('estimateShort'))}</span>` : ''}`;
// Why a project waits, in one or two lines: who could take the turn and what holds each of them.
function waitWhy(p){
  const live = p.live || {}, detail = liveDetail(live);
  if(live.phase === 'turn_running'){
    const c = p.last_config;
    return esc(t('w_turn', NAME[live.speaker] || '', live.turn ?? '', p.max_turns, c?.work ? t('work_'+c.work) : '')) + (live.mode === 'solo' ? esc(t('a_solo', others(p, live.speaker), local(live,'reason'))) : '');
  }
  if(p.status === 'queued' && p.queue_position) return esc(t('queuePos', p.queue_position));
  if(!['waiting_partner','waiting_role','waiting_limits'].includes(live.phase)) return '';
  if(!detail){
    // An engine started before this version: its own one-line reason.
    return esc(cap(local(live,'reason'))) + (live.until ? ' · '+esc(t('untilShort', dateTime(live.until))) : '');
  }
  const down = (detail.sides || []).filter(s => s.state === 'limit' || s.state === 'down');
  const list = down.length ? down.map(sideWait).join('<br>') : '';
  if(live.phase === 'waiting_role'){
    const able = down.map(s => NAME[s.side] || s.side).join(', ') || t('nobodyShort');
    return `${esc(t('w_role', t('work_'+(detail.work || 'implement')), able))}<br>${list}`;
  }
  if(live.phase === 'waiting_partner') return `${esc(t('w_review'))}<br>${list}`;
  return `${esc(t('w_limits'))}<br>${list}`;
}
function pausedSides(p){
  // Providers Sol-83 itself paused (a block): "Try now" can lift these, a reading it cannot.
  const detail = liveDetail(p.live), limits = state.overview?.limits || {};
  return (detail?.sides || []).filter(s => (s.state === 'limit' || s.state === 'down') && limits[s.side]?.paused).map(s => s.side);
}
function modelsLine(p){
  return SIDES.filter(s => p[s+'_model'] && p[s+'_model'] !== 'none').map(s => `${NAME[s]}: ${p[s+'_selection'] && p[s+'_selection'] !== 'manual' ? t('sel_'+p[s+'_selection']) : p[s+'_model']}`).join(' · ');
}
function projectCard(p, current){
  const st = projectState(p), why = waitWhy(p), ver = p.recommended ? 'v'+p.recommended : '';
  const q = p.questions_open ? `<div class="qbadge">${SVG.user}${esc(t('qWaitingYou', p.questions_open))}</div>` : '';
  const net = p.progress ? ' · '+esc(t('pNet'))+' '+p.progress.net+'%' : '';
  return `<a class="pcard" href="#/p/${p.id}" aria-current="${p.id===current}">
    <div class="proj-top"><span class="proj-title"><span class="hint">${esc(p.key||'')}</span> ${esc(p.title)}</span><span class="proj-ver">${ver}${p.run?.state==='running'?' ▶':''}</span></div>
    <div class="pstate">${stateChip(st)}${p.monitor_level === 'warn' ? `<span class="state k-wait">${SVG.warn}${esc(t('monSidebar'))}</span>` : ''}</div>
    ${why ? `<div class="why">${why}</div>` : ''}${q}
    <div class="proj-sub hint">${esc(modelsLine(p))}${net}</div></a>`;
}
function projectRow(p, current){
  const st = projectState(p), detail = local(p,'status_detail');
  const when = p.status === 'done' ? (p.finished_at || p.updated_at) : p.updated_at;
  const sub = `${t(st.key)}${when ? ' · '+clock(when) : ''}${detail ? ' · '+detail : ''}`;
  return `<a class="prow" href="#/p/${p.id}" aria-current="${p.id===current}" title="${esc(p.title + ' — ' + sub)}">
    <span class="ic ${st.tone}">${SVG[st.icon]}</span><span class="t"><span class="k">${esc(p.key||'')}</span>${esc(p.title)}</span>
    <span class="aside">${p.recommended ? 'v'+p.recommended : ''}${p.questions_open ? `<span class="counter" title="${esc(t('qWaitingYou', p.questions_open))}">${p.questions_open}</span>` : ''}</span>
    <span class="sub">${esc(sub)}</span></a>`;
}
const GROUP_DEFAULT = {attention:true, stopped:false, done:false};
function groupOpen(name){
  try{ const saved = JSON.parse(localStorage.getItem('sol83-groups') || '{}'); if(name in saved) return !!saved[name]; }catch(error){}
  return GROUP_DEFAULT[name];
}
function rememberGroup(name, open){
  try{ const saved = JSON.parse(localStorage.getItem('sol83-groups') || '{}'); saved[name] = open; localStorage.setItem('sol83-groups', JSON.stringify(saved)); }catch(error){}
}
const NOW_ORDER = {k_working:0, k_starting:1, k_stopping:2, k_review:3, k_role:3, k_limit:3, k_error:4, k_queued:5};
function renderProjects(projects){
  const current = route();
  if(!projects.length){ setHTML('projects',`<p class="empty" style="padding:4px 8px">${esc(t('noProjects'))}</p>`); return; }
  const groups = {now:[], attention:[], stopped:[], done:[]};
  for(const p of projects){
    if(['running','stopping','queued'].includes(p.status)) groups.now.push(p);
    else if(p.status === 'attention' || p.state_kind === 'error') groups.attention.push(p);
    else if(p.status === 'done') groups.done.push(p);
    else groups.stopped.push(p);
  }
  groups.now.sort((a, b) => (NOW_ORDER[projectState(a).key] ?? 9) - (NOW_ORDER[projectState(b).key] ?? 9));
  const now = `<section class="pgroup now" aria-label="${esc(t('g_now'))}"><div class="pgroup-head">${esc(t('g_now'))}<span class="gcount">${groups.now.length}</span></div>
    ${groups.now.length ? groups.now.map(p => projectCard(p, current)).join('') : `<p class="hint" style="padding:0 8px 6px">${esc(t('g_nowEmpty'))}</p>`}</section>`;
  const rest = ['attention','stopped','done'].filter(name => groups[name].length).map(name => {
    // The open project's group is shown open, without changing what the user chose to remember.
    const open = groupOpen(name) || groups[name].some(p => p.id === current);
    return `<details class="pgroup" data-group="${name}" ${open ? 'open' : ''}><summary class="pgroup-head">${esc(t('g_'+name))}<span class="gcount">${groups[name].length}</span></summary>
      ${groups[name].map(p => projectRow(p, current)).join('')}</details>`;
  }).join('');
  setHTML('projects', now + rest);
}
function testCard(d){
  const v = d.recommended, work = d.work || {}, p = d.project;
  const running = ['running','stopping'].includes(p.status);
  const commits = work.commits_after_last_version || 0, files = work.uncommitted || 0;
  let wip = '';
  if(v && commits + files){
    wip = `<div class="wip"><strong>${esc(t('wipLabel'))}</strong> ${esc(t('wipCount', commits))}${files?esc(t('wipFiles', files)):''}. ${esc(t(running?'wipRun':'wipIdle'))}</div>`;
  }
  if(!v){
    const rejected = d.versions.length > 0;
    return `<div class="card test-card"><div class="eyebrow"><span>${esc(t('toTest'))}</span></div>
      <p><b>${esc(t(rejected?'noVersionLeft':'noVersionYet'))}</b> ${esc(t(rejected?'allRejected':'noVersionHint'))}</p>
      ${commits?`<div class="wip">${esc(t('wipNoVersion', commits))}</div>`:''}${runInfo(d)}</div>`;
  }
  const verdict = v.user_verdict === 'ok' ? pill(t('worksYou'),'good') : '';
  const top = d.versions[0];
  const newer = top && top.number > v.number ? `<p class="hint">${esc(t(top.user_verdict === 'bad' ? 'newerRejected' : 'newer', top.number))}</p>` : '';
  const confirmed = d.confirmed && d.confirmed.number !== v.number ? t('confirmed', d.confirmed.number) : '';
  return `<div class="card test-card"><div class="eyebrow"><span>${esc(t('toTest'))}</span></div>
    <div class="test-top"><div>
      <div class="vnum">v${v.number}</div>
      <div class="test-meta">${pill(t('l_'+v.level), LEVEL_KIND[v.level]||'idle')}${verdict}<span>${esc(t('commit'))} ${esc(v.commit_sha.slice(0,7))}</span><span>${clock(v.created_at)}</span>${confirmed?`<span>${esc(confirmed)}</span>`:''}</div>
    </div><div class="actions">
      ${v.user_verdict === 'ok' ? '' : `<button class="btn ok" data-act="works" data-n="${v.number}">${SVG.check} ${esc(t('works'))}</button>`}
      <button class="btn danger" data-act="broken" data-n="${v.number}">${esc(t('broken'))}</button>
    </div></div>
    <div class="test-body">
      ${newer}
      ${v.what_to_test?`<div><div class="label">${esc(t('whatToCheck'))}</div><div class="steps">${esc(v.what_to_test)}</div></div>`:`<p class="hint">${esc(v.summary||'')}</p>`}
    </div>${wip}${runInfo(d)}</div>`;
}
function eventRow(e){
  const dot = e.agent ? e.agent : (e.kind === 'attention' || (e.kind === 'deliver' && e.data?.ok === false) ? 'bad' : ['done','deliver'].includes(e.kind) ? 'good' : '');
  const text = local(e,'text'), shown = MAJOR.has(e.kind) ? `<b>${esc(text)}</b>` : esc(text);
  const content = e.has_body
    ? `<details data-event="${e.id}" ${state.open.has(e.id)?'open':''}><summary>${shown}</summary><div class="body">${esc(state.bodies[e.id] ?? t('loading'))}</div></details>`
    : `<span>${shown}</span>`;
  const who = e.agent ? `<span class="who-tag">${esc(NAME[e.agent]||e.agent)}</span>` : `<span class="who-tag">${esc(t('coordName'))}</span>`;
  const row = `<div class="event ${MAJOR.has(e.kind)?'major':''}"><time>${new Date(e.ts*1000).toLocaleTimeString(t('locale'),{hour:'2-digit',minute:'2-digit'})}</time><span class="dot ${dot}"></span>${content}</div>`;
  if(e.kind !== 'turn_start') return row;
  // Turns stand apart: number, executor, model and kind of work, with a text label besides the colour.
  const c = e.data?.config || {};
  return `<div class="turn-head ${esc(e.agent||'')}"><span class="who">${esc(NAME[e.agent]||e.agent||'')}</span><span>${esc(t('turnN', e.data?.turn ?? ''))}</span><span>${esc(c.model || '')}${c.effort ? ' · '+esc(c.effort) : ''}</span><span>${esc(t('work_'+(e.data?.work||'implement')))}</span>${c.selection && c.selection !== 'manual' ? `<span class="hint">${esc(t('sel_'+c.selection))}</span>` : ''}</div>` + row;
}
function activityTab(d){
  if(!d.events.length) return `<p class="empty">${esc(t('noEvents'))}</p>`;
  const turns = {}; let coordinator = 0;
  for(const e of d.events){ if(e.kind === 'turn_start') turns[e.agent] = (turns[e.agent]||0) + 1; else if(!e.agent) coordinator += 1; }
  const share = `<div class="share">${Object.entries(turns).map(([a,n]) => `<span><span class="swatch ${esc(a)}"></span> ${esc(NAME[a]||a)}: ${n} ${esc(t('turnsWord'))}</span>`).join('')}<span>${esc(t('coordName'))}: ${coordinator} ${esc(t('eventsWord'))}</span></div>`;
  return share + d.events.map(eventRow).join('');
}
function versionsTab(d){
  const run = d.app_run, rows = d.versions_view || [];
  const runBox = run ? `<div class="box"><b>RUN v${run.version}</b> · ${esc(t('run_'+run.state))}${run.url ? ` · <a href="${esc(run.url)}" target="_blank" rel="noopener">${esc(run.url)}</a>` : ''} · ${esc(t('portLabel'))} ${run.port}
    ${run.state === 'running' ? `<button class="btn small" data-act="run-stop">${esc(t('runStop'))}</button>` : ''}
    <details><summary>${esc(t('runLog'))}</summary><pre class="task-full">${esc(run.log_tail || '')}</pre></details></div>` : '';
  if(!rows.length) return runBox + `<p class="empty">${esc(t('noVersions'))}</p>`;
  return runBox + rows.map(v => {
    const tests = [`${t('autoTests')}: ${v.automatic_tests || t('notAvailable')}`, `${t('manualTest')}: ${v.manual_test ? t('res_'+v.manual_test) : t('notAvailable')}`,
      `${t('reviewLabel')}: ${(v.review||[]).map(a => NAME[a]||a).join(', ') || t('notAvailable')}`];
    const where = v.folder ? `<div class="path">${esc(v.folder)}</div><button class="btn small" data-act="copy" data-text="${esc(v.folder)}">${esc(t('copyPath'))}</button> <button class="btn small" data-act="reveal" data-path="${esc(v.folder)}">${esc(t('openFolder'))}</button>`
      : `<p class="hint">${esc(t('tagOnly', v.tag))}</p><button class="btn small" data-act="test-copy" data-n="${v.number}">${esc(t('prepareFolder'))}</button>`;
    return `<div class="vcard ${v.recommended?'rec':''}"><div><b>v${v.number}</b> · ${clock(v.created_at)} ${v.recommended ? pill(t('recBadge'),'good') : ''}${v.rejected ? pill(t('broken'),'bad') : ''} ${pill(t('l_'+v.level), LEVEL_KIND[v.level]||'idle')}</div>
      <div class="ver-sub">${esc(v.summary || '')}</div>
      <div class="ver-sub">${tests.map(esc).join(' · ')}</div>
      <div class="ver-sub">${esc(t('commit'))} ${esc(v.commit.slice(0,7))} · ${esc(t('tag'))} ${esc(v.tag)}</div>
      <div class="box"><div class="label">${esc(t('location'))}</div>${where}</div>
      <div class="box"><div class="label">${esc(t('howToRun'))}</div><div class="steps">${esc(v.how_to_run || t('runNotYet'))}</div>
        <button class="btn small" data-act="run-app" data-n="${v.number}">${esc(t('runThis'))}</button></div>
      ${v.what_to_check ? `<div class="box"><div class="label">${esc(t('whatToCheck'))}</div><div class="steps">${esc(v.what_to_check)}</div></div>` : ''}</div>`;
  }).join('');
}
function taskTab(d){
  const p = d.project;
  const rows = [['k_key', p.key || '–'], ['k_verify', p.verify_cmd || t('k_noVerify')], ['k_source', p.repo_path || t('k_later')], ['k_branch', p.branch || '–'],
    ['k_work', p.worktree || '–'], ['k_models', SIDES.map(s => `${NAME[s]}: ${!p[s+'_model'] || p[s+'_model'] === 'none' ? t('modelOff') : p[s+'_model']}`).join(', ')], ['k_turns', p.max_turns], ['k_added', clock(p.created_at)]];
  // The full task, never cut: collapsible, copyable, with its original formatting.
  return `<details open><summary>${esc(t('taskFull'))} (${p.task.length} ${esc(t('chars'))})</summary>
    <div class="row" style="justify-content:flex-end"><button class="btn small" data-act="copy" data-text="${esc(p.task)}">${esc(t('copy'))}</button></div>
    <pre class="task-full">${esc(p.task)}</pre></details><dl class="kv">${rows.map(([k,v])=>`<dt>${esc(t(k))}</dt><dd>${esc(v)}</dd>`).join('')}</dl>`;
}
// Questions and tests (2026-11-08): what waits for the user first, each with a title, why it is asked,
// the steps and the answers as buttons. Once answered it is done for the user: it moves to "Done" with
// the answer and whether the models already have it, and it is never asked again by itself.
function qTitle(q){
  if(q.author === 'version' && q.version_number) return t('qVersionTitle', q.version_number);
  const first = (q.text || '').trim().split(/\n|(?<=[.?!])\s+(?=\S)/)[0] || '';
  return first.length > 160 ? first.slice(0, 157) + '…' : first;
}
function qSteps(q){
  if((q.steps || []).length) return q.steps.map(s => `<li>${esc(s.step||'')}${s.expected ? ` <span class="hint">→ ${esc(s.expected)}</span>` : ''}</li>`);
  const text = (q.text || '').trim();
  if(!/^\s*1[.)]\s/.test(text)) return [];
  return text.split(/\s*(?:^|\s)\d+[.)]\s+/).filter(Boolean).map(step => `<li>${esc(step.trim())}</li>`);
}
function qBody(q){
  const steps = qSteps(q), title = qTitle(q), text = (q.text || '').trim();
  const rest = steps.length && !(q.steps || []).length ? '' : text.slice(text.startsWith(title.replace(/…$/, '')) ? title.replace(/…$/, '').length : 0).trim();
  return `${rest ? `<div class="qtext">${esc(rest)}</div>` : ''}${steps.length ? `<ol>${steps.join('')}</ol>` : ''}`;
}
const RESULT_ICON = {works:'check', fails:'cross', partial:'half', cannot:'stop'};
function qAnswerText(a){
  if(!a) return '';
  return `${a.result ? t('res_'+a.result) : a.value || ''}${a.comment ? ' — ' + a.comment : ''}${a.version ? ' · v'+a.version : ''} · ${clock(a.ts)}`;
}
function qOpenCard(q){
  const test = q.type === 'manual_test';
  const who = NAME[q.author] || (q.author === 'version' ? t('versionCheck') : q.author || '');
  const options = (q.options || []).map(o => `<button class="btn small" data-act="answer" data-q="${q.id}" data-value="${esc(o)}">${esc(o)}${q.recommendation === o ? ' ★' : ''}</button>`).join('');
  const actions = test
    ? `<div class="qactions" role="group" aria-label="${esc(t('qResultAsk'))}">${['works','fails','partial','cannot'].map(r => `<button class="btn small ${r === 'works' ? 'ok' : r === 'fails' ? 'danger' : ''}" data-act="test-result" data-q="${q.id}" data-result="${r}">${SVG[RESULT_ICON[r]]} ${esc(cap(t('res_'+r)))}</button>`).join('')}</div>`
    : `<div class="qactions">${options}</div><div class="row" style="flex-wrap:nowrap;margin-top:6px"><input type="text" id="answer-${q.id}" placeholder="${esc(t('ownAnswer'))}"><button class="btn small primary" data-act="answer" data-q="${q.id}">${esc(t('send'))}</button></div>`;
  const late = (q.answers || []).filter(a => a.late);
  return `<div class="qcard"><div class="qhead"><span class="state ${q.state === 'deferred' ? 'k-idle' : 'k-user'}">${SVG[test ? 'check' : 'user']}${esc(cap(t('qt_'+q.type)))}</span>
      <span class="meta">${esc(q.ref)}${q.version_number ? ' · v'+q.version_number : ''} · ${esc(t('qFrom', who))} · ${clock(q.created_at)}${q.mandatory ? ' · '+esc(t('mandatory')) : ''}${q.state === 'deferred' ? ' · '+esc(t('qDeferred')) : ''}</span></div>
    <div class="qtitle">${esc(qTitle(q))}</div>
    ${q.why && q.author !== 'version' ? `<div class="qwhy"><b>${esc(t('qWhyLabel'))}:</b> ${esc(q.why)}</div>` : ''}
    ${(q.blocks||[]).length ? `<div class="hint">${esc(t('blocks'))}: ${q.blocks.map(esc).join(', ')}${q.independent ? ' · '+esc(t('independent'))+': '+esc(q.independent) : ''}</div>` : ''}
    ${q.environment ? `<div class="hint">${esc(t('environment'))}: ${esc(q.environment)}${q.minutes ? ' · ~'+q.minutes+' min' : ''}</div>` : ''}
    ${qBody(q)}${actions}${test ? `<p class="hint">${esc(t('qEffect'))}</p>` : ''}
    <div class="row" style="justify-content:flex-start;gap:14px">${q.state !== 'deferred' ? `<button class="linkbtn" data-act="q-state" data-q="${q.id}" data-state="deferred">${esc(t('defer'))}</button>` : ''}<button class="linkbtn" data-act="q-state" data-q="${q.id}" data-state="cancelled">${esc(t('cancel'))}</button></div>
    ${late.length ? `<details><summary>${esc(t('histTitle'))}</summary><ul>${late.map(a => `<li>${esc(qAnswerText(a))} · ${esc(t('lateAnswer'))}</li>`).join('')}</ul></details>` : ''}</div>`;
}
function qDoneRow(q, d){
  const answer = [...(q.answers || [])].reverse().find(a => !a.late);
  const bad = answer?.result && answer.result !== 'works';
  const stopped = !['running','stopping','queued'].includes(d.project.status);
  const closed = ['works','cannot'].includes(answer?.result) && !answer?.comment && !answer?.value;
  const where = closed ? t('qClosed') : q.state === 'applied' ? t('qDelivered') : stopped ? t('qQueuedStopped') : t('qQueued');
  return `<div class="qdone"><span class="ic ${bad ? 'k-error' : 'k-done'}">${SVG[bad ? 'cross' : 'check']}</span><div><b>${esc(qTitle(q))}</b> <span class="hint">${esc(q.ref)}</span></div>
    <div class="sub">${esc(t('qYour'))}: ${esc(qAnswerText(answer))} · ${esc(where)} · <button class="linkbtn" data-act="q-state" data-q="${q.id}" data-state="open">${esc(t('qChange'))}</button></div></div>`;
}
function questionsTab(d){
  const items = d.interactions || [];
  const gates = (d.blockers || []).length ? `<div class="alert">${esc(t('gatesTitle'))}: ${(d.blockers||[]).map(esc).join(', ')}</div>` : '';
  if(!items.length) return gates + `<p class="empty">${esc(t('qNone'))}</p>`;
  const todo = items.filter(q => q.state === 'open').concat(items.filter(q => q.state === 'deferred'));
  const done = items.filter(q => ['answered','applied'].includes(q.state));
  const old = items.filter(q => ['superseded','cancelled'].includes(q.state));
  const oldRows = old.map(q => `<div class="qdone"><span class="ic">${SVG.stop}</span><div>${esc(qTitle(q))} <span class="hint">${esc(q.ref)} · ${esc(t('qs_'+q.state))}</span></div></div>`).join('');
  return gates + `<section class="qsection"><h4>${esc(t('qTodo'))} <span class="gcount">${todo.filter(q => q.state === 'open').length}</span></h4>
      ${todo.length ? todo.map(qOpenCard).join('') : `<p class="empty">${esc(t('qNothing'))}</p>`}</section>
    ${done.length ? `<details class="qsection" open><summary>${esc(t('qDoneTitle'))} (${done.length})</summary>${done.map(q => qDoneRow(q, d)).join('')}</details>` : ''}
    ${old.length ? `<details class="qsection"><summary>${esc(t('qOldTitle'))} (${old.length})</summary>${oldRows}</details>` : ''}`;
}
const TABS = [['przebieg','tabRun'],['plan','tabPlan'],['pytania','tabQuestions'],['wersje','tabVersions'],['tresci','tabAssets'],['efekt','tabEff'],['ustawienia','tabSettings'],['zadanie','tabTask']];
const ASSET_KIND = {requested:'idle', done:'good', error:'bad', proposed:'warn', rejected:'bad', deferred:'idle'};
function assetsList(d){
  const waiting = (d.asset_orders || []).map(o => `<div class="asset"><div class="thumb">${esc(t('aWaiting'))}</div><div><b>${esc(o.path)}</b> ${pill(t('aByUser'),'idle')}<div class="ver-sub">${esc(o.prompt)}</div></div></div>`).join('');
  const rows = (d.assets || []).map(a => {
    const thumb = a.image ? `<img src="/api/projects/${esc(d.project.id)}/asset?path=${encodeURIComponent(a.path)}&s=${esc(a.status)}" alt="${esc(a.prompt||a.path)}" loading="lazy">`
      : `<div class="thumb">${esc(t(a.type === 'text' ? 'aText' : 'aImage'))}</div>`;
    const meta = [a.size, a.style, a.actual_size ? t('actualSize', a.actual_size) : ''].filter(Boolean).join(' · ');
    const decide = ['proposed','deferred'].includes(a.status) ? `<div class="row">${['approve','reject','defer'].map(x => `<button class="btn small ${x==='approve'?'primary':''}" data-act="asset-decision" data-id="${esc(a.id)}" data-decision="${x}">${esc(t('ad_'+x))}</button>`).join(' ')}</div>` : '';
    return `<div class="asset">${thumb}<div><b>${esc(a.id)}</b> ${pill(t('as_'+a.status), ASSET_KIND[a.status]||'idle')}${a.by==='user'?' '+pill(t('aByUser'),'idle'):a.by?' '+pill(NAME[a.by]||a.by,'idle'):''}${a.mandatory?' '+pill(t('mandatory'),'warn'):''}
      <div class="ver-sub">${esc(a.prompt||'')}</div>${a.why?`<div class="hint">${esc(t('why'))}: ${esc(a.why)}</div>`:''}${(a.blocks||[]).length?`<div class="hint">${esc(t('blocks'))}: ${a.blocks.map(esc).join(', ')}</div>`:''}
      <div class="path">${esc(a.path||'')}${meta?' · '+esc(meta):''}</div>
      ${a.note?`<div class="ver-sub">${esc(a.note)}</div>`:''}${a.preview?`<div class="steps" style="margin-top:6px;max-height:160px;overflow:auto">${esc(a.preview)}</div>`:''}${decide}</div></div>`;
  }).join('');
  return waiting + rows || `<p class="empty">${esc(t('aNone'))}</p>`;
}
function assetForm(){
  return `<form id="asset-form" class="card" style="margin-bottom:14px;padding:12px"><h3>${esc(t('aTitle'))}</h3>
    <div class="grid2" style="margin-top:4px"><label class="label" style="font-size:13px">${esc(t('aPath'))}<input id="asset-path" type="text" placeholder="${esc(t('aPathPh'))}"></label>
    <label class="label" style="font-size:13px">&nbsp;<select id="asset-type"><option value="image">${esc(t('aImage'))}</option><option value="text">${esc(t('aText'))}</option></select></label></div>
    <label class="label" style="font-size:13px;margin-top:8px">${esc(t('aPrompt'))}<textarea id="asset-prompt" rows="3"></textarea></label>
    <div class="grid2"><label class="label" style="font-size:13px">${esc(t('aSize'))}<input id="asset-size" type="text" list="size-presets" placeholder="1024x1024"><datalist id="size-presets">${['512x512','1024x1024','1920x1080','1080x1920','1:1','16:9','9:16','4:3'].map(x => `<option value="${x}">`).join('')}</datalist></label>
    <label class="label" style="font-size:13px">${esc(t('aStyle'))}<input id="asset-style" type="text"></label></div>
    <p class="hint">${esc(t('aSizeHint'))}</p>
    <div class="row"><span class="hint">${esc(t('aHint'))}</span><button class="btn primary">${esc(t('aOrder'))}</button></div></form>`;
}
// What the last RUN did, in words: running with its address, or ended with the last lines of its log.
function runState(d){
  const run = d.app_run;
  if(!run || run.version !== d.run_here?.version) return '';
  if(run.state === 'running') return `<div class="box"><b>RUN v${run.version}</b> · ${esc(t('run_running'))}${run.url ? ` · <a href="${esc(run.url)}" target="_blank" rel="noopener">${esc(t('runOpen'))}</a>` : ''}</div>`;
  const tail = (run.log_tail || '').trim().split('\n').slice(-4).join('\n');
  return `<div class="box"><b>RUN v${run.version}</b> · ${esc(t('run_'+run.state))}${run.state === 'ended' ? ' · '+esc(t('runEndedHint')) : ''}${tail ? `<pre class="task-full" style="margin-top:6px">${esc(tail)}</pre>` : ''}</div>`;
}
function runInfo(d){
  const r = d.run_here || {}, run = d.plan?.run;
  const name = {repo: o => t('pathRepoBranch', o.branch), work: () => t('pathWorkNote'), test: o => t('pathTestOld', o.version)};
  const here = r.path
    ? `<div class="label">${esc(t('runHere'))} · v${r.version}</div><div class="path">${esc(r.path)}</div>
       ${runState(d)}
       <div class="label" style="margin-top:8px;display:flex;gap:8px;align-items:center">${esc(t('terminalTitle'))}
         <button class="btn small" data-act="copy" data-text="${esc(r.terminal || r.steps)}">${esc(t('copy'))}</button></div>
       <pre class="steps terminal">${esc(r.terminal || r.steps)}</pre>
       <p class="hint">${esc(t(r.terminal_source === 'local' ? 'terminalLocal' : 'terminalRules'))}</p>
       ${r.terminal && r.steps && r.steps !== r.terminal ? `<details><summary>${esc(t('terminalOriginal'))}</summary><div class="steps">${esc(r.steps)}</div></details>` : ''}`
    : `<p class="hint">${esc(t('runNotYet'))}</p>${run ? `<div class="label" style="margin-top:8px">${esc(t('runTitle'))}</div><div class="steps">${esc(run)}</div>` : ''}`;
  const others = (r.others || []).map(o => `<dt>${esc(name[o.kind](o))}</dt><dd class="path">${esc(o.path)}</dd>`).join('');
  return `<div class="wip">${here}${others ? `<details style="margin-top:8px"><summary>${esc(t('otherFolders'))}</summary>
    <dl class="kv" style="border:0;margin-top:6px;padding-top:0;grid-template-columns:minmax(0,1fr)">${others}</dl></details>` : ''}</div>`;
}
function projectSection(d){
  const p = d.project;
  const lang = p.language === 'unknown'
    ? `<label>${esc(t('langChoose'))} <select id="lang-pick"><option value="">–</option><option value="pl">Polski</option><option value="en">English</option></select></label>`
    : `<p class="hint">${esc(t('langFixedIs', (p.language||'pl').toUpperCase()))}</p>`;
  return `<section style="margin-top:18px"><h3>${esc(t('projectTitle'))}</h3>
    <form id="rename-form" class="row" style="flex-wrap:nowrap"><input id="rename-text" type="text" value="${esc(p.title)}" aria-label="${esc(t('projectName'))}"><button class="btn">${esc(t('rename'))}</button></form>
    <p class="hint">${esc(t('keyHint', p.key || '–'))}</p>${lang}
    <label style="display:block;margin-top:12px;font-weight:600">${esc(t('userTestsLabel'))}
      <select id="user-tests-pick">${['final','each','none'].map(m => `<option value="${m}" ${m === (p.user_tests || 'final') ? 'selected' : ''}>${esc(t('ut_'+m))}</option>`).join('')}</select></label>
    <p class="hint">${esc(t('userTestsHint'))}</p>
    <label style="display:block;margin-top:12px;font-weight:600">${esc(t('kindLabel'))}
      <select id="project-kind-pick">${['auto','document','app'].map(m => `<option value="${m}" ${m === (p.project_kind || 'auto') ? 'selected' : ''}>${esc(t('pk_'+m))}</option>`).join('')}</select></label>
    <p class="hint">${esc(t('kindHint'))}</p>
    <label style="display:block;margin-top:12px;font-weight:600">${esc(t('reviewLabel2'))}
      <select id="review-mode-pick">${['stage','each'].map(m => `<option value="${m}" ${m === (p.review_mode || 'stage') ? 'selected' : ''}>${esc(t('rm_'+m))}</option>`).join('')}</select></label>
    <p class="hint">${esc(t('reviewHint'))}</p>
    <label class="check" style="margin-top:10px"><input type="checkbox" id="web-fetch-pick" ${p.web_fetch ? 'checked' : ''}> ${esc(t('webFetchLabel'))}</label>
    <p class="hint">${esc(t('webFetchHint'))}</p></section>`;
}
const LICENSES = ['MIT','Apache-2.0','BSD-3-Clause','MPL-2.0','GPL-3.0-only','AGPL-3.0-only'];
function licenseSection(d){
  const current = JSON.parse(d.project.license || '{}');
  const label = current.kind === 'standard' ? current.spdx : current.kind ? t('lic_'+current.kind) : t('notAvailable');
  return `<section style="margin-top:18px"><h3>${esc(t('licTitle'))}</h3><p class="hint">${esc(t('licNow', label))}</p>
    <form id="license-form" class="grid2">
      <label>${esc(t('licKind'))}<select id="lic-kind">${['standard','custom','none'].map(k => `<option value="${k}" ${current.kind===k?'selected':''}>${esc(t('lic_'+k))}</option>`).join('')}</select></label>
      <label>${esc(t('licStandard'))}<select id="lic-spdx">${LICENSES.map(l => `<option ${current.spdx===l?'selected':''}>${l}</option>`).join('')}</select></label>
      <label>${esc(t('licHolder'))}<input id="lic-holder" type="text" value="${esc(current.holder || '')}"></label>
      <label class="check"><input type="checkbox" id="lic-overwrite"> ${esc(t('licOverwrite'))}</label>
      <label style="grid-column:1/-1">${esc(t('licCustom'))}<textarea id="lic-custom" rows="3">${esc(current.custom || '')}</textarea></label>
      <div class="row" style="grid-column:1/-1"><span class="hint">${esc(t('licHint'))}</span><button class="btn">${esc(t('save'))}</button></div></form></section>`;
}
function gitSection(d){
  const g = d.git || {}, saved = g.saved || {}, repo = g.repository || {}, remotes = Object.keys(repo.remotes || {});
  const state_ = repo.repository ? `${esc(t('gitBranch'))}: ${esc(repo.branch || t('gitDetached'))} · ${esc(t('gitChanges', repo.staged || 0, repo.unstaged || 0, repo.untracked || 0))}${repo.merging||repo.rebasing ? ' · '+esc(t('gitInProgress')) : ''}` : esc(t('gitNoRepo'));
  const ops = (g.operations || []).slice(0, 5).map(o => `<li>${clock(o.created_at)} · ${esc(o.operation)} · ${esc(o.branch || '')} · ${esc(o.state)}${o.pr_url ? ` · <a href="${esc(o.pr_url)}" target="_blank" rel="noopener">PR</a>` : ''}${o.detail ? ' · '+esc(o.detail) : ''}</li>`).join('');
  return `<section style="margin-top:18px"><h3>${esc(t('gitTitle'))}</h3><p class="hint">${state_}</p>
    <form id="git-form" class="grid2">
      <label>${esc(t('gitRemote'))}<select id="git-remote"><option value="">–</option>${remotes.map(r => `<option ${saved.remote===r?'selected':''}>${esc(r)}</option>`).join('')}</select></label>
      <label>${esc(t('gitBase'))}<input id="git-base" type="text" value="${esc(saved.base_branch || '')}" placeholder="main"></label>
      <label>${esc(t('gitStrategy'))}<select id="git-strategy">${['local','push','pr'].map(x => `<option value="${x}" ${saved.strategy===x?'selected':''}>${esc(t('gs_'+x))}</option>`).join('')}</select></label>
      <div><label class="check"><input type="checkbox" id="git-push" ${saved.allow_push?'checked':''}> ${esc(t('gitAllowPush'))}</label><br><label class="check"><input type="checkbox" id="git-pr" ${saved.allow_pr?'checked':''}> ${esc(t('gitAllowPr'))}</label></div>
      <div class="row" style="grid-column:1/-1"><button class="btn">${esc(t('save'))}</button><button type="button" class="btn" data-act="git-deliver" ${saved.allow_push?'':'disabled'} title="${esc(saved.allow_push?'':t('gitNeedPermission'))}">${esc(t('gitSendNow', d.project.branch || ''))}</button></div></form>
    <p class="hint">${esc(t('gitHint'))}</p>${ops ? `<ul class="hint">${ops}</ul>` : ''}</section>`;
}
function setupSection(s){
  const state_ = s.approved ? `<p class="hint">${esc(t('setupApproved').replace('{0}', s.sha.slice(0,12)))}</p>`
    : s.sandbox ? `<button class="btn" data-act="setup-approve" data-sha="${esc(s.sha)}">${esc(t('setupApprove'))}</button>`
    : `<p class="alert">${esc(t('setupNoSandbox'))}</p>`;
  return `<section style="margin-top:18px"><h3>${esc(t('setupTitle'))}</h3><p class="hint">${esc(t('setupHint'))}</p>
    <div class="label">${esc(s.path)}</div><pre class="steps" style="max-height:260px;overflow:auto">${esc(s.content)}</pre>${state_}</section>`;
}
function renderTab(d){
  if(state.renderedTab !== state.tab){
    state.renderedTab = state.tab; state.ghKey = null;
    delete state.html['tab-inner']; delete state.html['models']; delete state.html['turn-config']; delete state.html['coordinator']; delete state.html['assets-list']; delete state.html['monitor'];
    document.getElementById('tab-body').innerHTML = state.tab === 'ustawienia'
      ? `<section><h3>${esc(t('modelsTitle'))}</h3><div id="turn-config"></div><div class="models" id="models"></div><p class="hint" style="margin-top:8px">${esc(t('modelsHint'))} ${esc(t('rolesHint'))}</p></section>
         <section style="margin-top:18px"><h3>${esc(t('fVerify'))}</h3><form id="verify-form" class="row" style="flex-wrap:nowrap">
           <input id="verify-cmd" type="text" value="${esc(d.project.verify_cmd || '')}" placeholder="${esc(t('fVerifyPlaceholder'))}"><button class="btn">${esc(t('save'))}</button></form>
           <p class="hint" style="margin-top:6px">${esc(t('verifyHint'))}</p></section>
         <section style="margin-top:18px"><h3>${esc(t('coordTitle'))}</h3><div id="coordinator"></div><p class="hint" style="margin-top:6px">${esc(t('coordHint'))}</p></section>
         ${projectSection(d)}${licenseSection(d)}${gitSection(d)}
         ${d.setup ? setupSection(d.setup) : ''}
         <section style="margin-top:18px"><h3>${esc(t('ghTitle'))}</h3><div id="github"></div></section>
         <section style="margin-top:24px;padding-top:14px;border-top:1px solid var(--line)"><h3>${esc(t('deleteTitle'))}</h3>
           <p class="hint" style="margin-bottom:8px">${esc(t('deleteHint'))}</p><button class="btn danger" data-act="delete-project">${esc(t('deleteButton'))}</button></section>`
      : state.tab === 'efekt' ? `<div id="monitor"></div><div class="help">${esc(t('effHelp'))}</div>`
      : state.tab === 'tresci' ? `${assetForm()}<div id="assets-list"></div>`
      : `<div id="tab-inner"></div>`;
  }
  const p = d.project;
  if(state.tab === 'ustawienia'){
    const tc = d.turn_config;
    setHTML('turn-config', tc ? `<div class="box"><b>${esc(t('turnConfigNow'))}</b>: ${esc(NAME[tc.agent]||tc.agent)} · ${esc(tc.model||'')}${tc.effort ? ' · '+esc(tc.effort) : ''} · ${esc((tc.role||[]).join ? tc.role.join(', ') : tc.role || '')} · ${esc(t('work_'+(tc.work||'implement')))}${tc.selection && tc.selection !== 'manual' ? ' · '+esc(t('sel_'+tc.selection)) : ''}<br><span class="hint">${esc(t('turnConfigHint'))}</span></div>` : '');
    setHTML('models', SIDES.map(s => sideControls(s, p[s+'_model'] || 'none', p[s+'_reasoning'], p[s+'_role'], p[s+'_selection'])).join('')
      + fallbackControl(p.role_fallback) + (d.sides.includes('gemini') ? '' : `<p class="hint">${esc(t('gOldProject'))}</p>`));
    setHTML('coordinator', coordinatorControl(state.overview?.coordinator));
    renderGitHub(d);
  }
  else if(state.tab === 'efekt') renderMonitor(d.monitor, d.plan);
  else if(state.tab === 'tresci') setHTML('assets-list', assetsList(d));
  else setHTML('tab-inner', ({przebieg: () => activityTab(d),
    plan: () => planTab(d), wersje: () => versionsTab(d), zadanie: () => taskTab(d), pytania: () => questionsTab(d)})[state.tab]());
}
function planTab(d){
  const pl = d.plan || {};
  if(!pl.exists) return `<p class="empty">${esc(t('planNone'))}</p>${pl.problem ? `<div class="alert">${esc(t('planProblem'))}${esc(pl.problem)}</div>` : ''}`;
  const rows = pl.rows || [];
  const line = (r, depth) => {
    const over = r.kind !== 'feature' && r.turns > r.budget && ['todo','doing'].includes(r.status);
    const open = ['todo','deferred'].includes(r.status) && r.kind !== 'feature';
    return `<tr class="${r.status==='done'?'done':''}"><td style="padding-left:${8+depth*18}px"><b>${esc(r.id)}</b> ${esc(r.title)}${r.category?` <span class="pill idle">${esc(r.category)}</span>`:''}${r.note?`<div class="ver-sub">${esc(r.note)}</div>`:''}</td>
      <td title="${esc(t('tipPrio_'+r.priority))}">${esc(t('pr_'+r.priority))}</td><td title="${esc(t('tipSt_'+r.status))}">${esc(t('st_'+r.status))}</td>
      <td class="num">${r.kind==='feature'?'':`${r.turns}/${r.budget}${over?' '+pill(t('overBudget'),'warn'):''}`}</td><td class="num">${r.week ? r.week+'%' : ''}</td>
      <td>${open?`<button class="btn small" data-act="item" data-item="${esc(r.id)}">${esc(t('startItem'))}</button>`:''}</td></tr>`;
  };
  const debt = rows.filter(r => r.kind === 'debt'), main = rows.filter(r => r.kind !== 'debt');
  const tree = main.filter(r => !r.parent || !main.some(m => m.id === r.parent)).flatMap(f => [line(f, 0), ...main.filter(c => c.parent === f.id).map(c => line(c, 1))]).join('');
  const shares = Object.entries(pl.breakdown || {}).filter(([,v]) => v).map(([k,v]) => `${t('grp_'+k)} ${v}%`).join(' · ');
  const head = `<tr><th>${esc(t('colItem'))}</th><th>${esc(t('colPrio'))}</th><th>${esc(t('colStatus'))}</th><th class="num">${esc(t('colTurns'))}</th><th class="num">${esc(t('colCost'))}</th><th></th></tr>`;
  const g = d.progress;
  const progress = g ? `<div class="progress-box" title="${esc(t('progressHelp'))}"><span>${esc(t('pDone', g.done_items, g.scope_items))}</span><span>${esc(t('pFunctional'))}: <b>${g.functional}%</b></span><span>${esc(t('pDebt'))}: <b>−${g.debt_penalty} p.p.</b></span><span>${esc(t('pNet'))}: <b>${g.net}%</b></span>${g.deferred_must ? `<span class="pill warn">${esc(t('pDeferredMust', g.deferred_must))}</span>` : ''}${(d.blockers||[]).length ? `<button class="linkbtn" data-act="tab-questions">${esc(t('pGates', d.blockers.length))}</button>` : ''}</div><p class="hint">${esc(t('progressHelp'))}</p>` : `<p class="hint">${esc(t('pNoEstimate'))}</p>`;
  return `${progress}${pl.stale ? `<div class="alert">${esc(t('planStale', pl.revision))}</div>` : ''}${pl.problem ? `<div class="alert">${esc(t('planProblem'))}${esc(pl.problem)}</div>` : ''}
    <p class="hint" title="${esc(t('tipCost'))}">${esc(t('planSpend'))}: <b>${esc(shares || '–')}</b></p>
    <table class="plan">${head}${tree}</table>
    ${debt.length ? `<h3 style="margin:16px 0 6px">${esc(t('planDebt'))} (${debt.length})</h3><table class="plan">${head}${debt.map(r => line(r, 0)).join('')}</table>` : ''}
    <details style="margin-top:14px"><summary>${esc(t('planArch'))}</summary><p class="task" style="margin-top:6px">${esc(pl.architecture || '–')}</p></details>
    <p class="hint" style="margin-top:8px">${esc(t('planFile'))}: <span class="path">${esc(pl.path)}</span></p>`;
}
function renderThread(d){
  const items = [
    ...d.questions.map(q => ({ts:q.ts, html: (() => {
      const who = q.answered_by === 'koordynator' ? t('byCoordinator') : t('byObserver', NAME[q.answered_by]||'');
      const note = d.notes.find(n => n.text === q.question && n.ts >= q.ts - 1);
      const routed = note && note.status !== 'withdrawn';
      const button = (act, label) => `<div class="row" style="justify-content:flex-start;margin-top:4px"><button class="btn small" data-act="${act}" data-q="${q.id}">${esc(t(label))}</button></div>`;
      const order = q.status !== 'answered' ? '' : !routed ? button('order', 'orderWork') : note.status === 'pending' ? button('withdraw', 'withdraw') : '';
      const mark = routed ? ' · '+esc(t('ordered')) : note ? ' · '+esc(t('withdrawn')) : '';
      return `<div class="msg"><div class="q">${esc(q.question)}</div>${q.status==='answered'?`<div class="a">${esc(String(q.answer).replace(/\*\*/g,''))}</div><div class="who">${esc(who)}${mark}</div>`:`<div class="who">${esc(t('waitingAnswer'))}</div>`}${order}</div>`;
    })()})),
    ...d.notes.filter(n => n.status !== 'withdrawn' && !d.questions.some(q => q.question === n.text)).map(n => ({ts:n.ts, html: (() => {
      const where = n.status === 'pending' ? t('notePending') : t('noteSent', NAME[n.delivered_to]||n.delivered_to, n.delivered_turn);
      const response = n.response ? `<details style="margin-top:4px"><summary class="who">${esc(t('noteResponse'))}</summary><div class="a" style="white-space:pre-wrap">${esc(n.response)}</div></details>` : '';
      return `<div class="msg"><div class="q">${esc(n.text)}</div><div class="who">${n.urgent?esc(t('urgent'))+' · ':''}${esc(where)} · ${clock(n.ts)}</div>${response}</div>`;
    })()}))
  ].sort((a, b) => b.ts - a.ts);
  setHTML('thread', items.map(i => i.html).join(''));
}
function renderRepos(){
  const section = document.getElementById('repos-section'), repos = state.repos || [];
  section.hidden = !repos.length;
  const query = document.getElementById('repo-filter').value.toLowerCase();
  const rows = repos.filter(r => r.nameWithOwner.toLowerCase().includes(query)).slice(0, 12);
  setHTML('repos', rows.length ? rows.map(r => `<a class="proj" href="#/nowy/${encodeURIComponent(r.nameWithOwner)}" title="${esc(t('ghRepoWork'))}">
    <div class="proj-top"><span class="proj-title">${esc(r.nameWithOwner.split('/')[1])}</span><span class="proj-ver">${esc(t(r.isPrivate?'ghPrivate':'ghPublic'))}</span></div>
    <div class="proj-sub"><span>${esc(t('ghPushed', clock(new Date(r.pushedAt).getTime()/1000)))}</span></div></a>`).join('') : `<p class="empty" style="padding:4px 8px">${esc(t('ghNoRepos'))}</p>`);
}
function renderGitHub(d){
  const p = d.project, gh = state.github, v = d.recommended;
  const key = JSON.stringify([state.lang, p.id, gh, p.github_repo, p.github_visibility, p.github_version, p.github_auto, p.github_branch, v?.number]);
  if(state.ghKey === key) return;
  state.ghKey = key;
  const box = document.getElementById('github');
  if(!box) return;
  if(!gh){ box.innerHTML = ''; return; }
  if(!gh.ready){ box.innerHTML = `<p class="hint">${esc(local(gh,'problem'))}</p>`; return; }
  if(p.github_repo){
    const visibility = p.github_visibility === 'public';
    const send = v && v.number !== p.github_version
      ? `<button class="btn primary" data-act="gh-send" data-n="${v.number}">${esc(t('ghSend', v.number))}</button>` : `<p class="hint">${esc(t('ghUpToDate'))}</p>`;
    const pr = p.github_branch && p.github_branch !== 'main' && p.github_version
      ? `<div style="margin-top:6px"><a class="gh-link" href="${esc(p.github_url)}/compare/${esc(p.github_branch)}?expand=1" target="_blank" rel="noopener">${esc(t('ghPr'))}</a></div>` : '';
    const auto = visibility ? '' : `<label class="check" style="margin-top:8px"><input type="checkbox" id="gh-auto" ${p.github_auto?'checked':''}> ${esc(t('ghAuto'))}</label>`;
    box.innerHTML = `<a class="gh-link" href="${esc(p.github_url)}" target="_blank" rel="noopener">${esc(p.github_repo)}</a>
      <div style="margin:6px 0">${pill(t(visibility?'ghPublic':'ghPrivate'), visibility?'warn':'idle')} ${p.github_version?`<span class="hint">${esc(t('ghSent', p.github_version))}</span>`:''}</div>
      ${send}${pr}${auto}<div class="row"><button class="btn small" data-act="gh-visibility" data-to="${visibility?'private':'public'}">${esc(t(visibility?'ghToPrivate':'ghToPublic'))}</button></div>`;
    return;
  }
  if(!v){ box.innerHTML = `<p class="hint">${esc(t('ghNeedVersion'))}</p>`; return; }
  box.innerHTML = `<label class="label" for="gh-name" style="font-size:13px">${esc(t('ghName'))}</label>
    <input id="gh-name" type="text" value="${esc(d.github_default_name)}">
    <div class="gh-row"><label><input type="radio" name="gh-vis" value="private" checked> ${esc(t('ghPrivate'))}</label>
    <label><input type="radio" name="gh-vis" value="public"> ${esc(t('ghPublic'))}</label></div>
    <button class="btn primary" data-act="gh-send" data-n="${v.number}">${esc(t('ghCreate', v.number))}</button>
    <p class="hint" style="margin-top:8px">${esc(t('ghHint'))}</p>`;
}
function renderHead(d){
  const p = d.project, kind = STATUS_KIND[p.status] || 'idle';
  const running = ['running','stopping'].includes(p.status), canStop = ['running','queued'].includes(p.status), canResume = ['stopped','attention'].includes(p.status);
  const rec = d.recommended, run = d.app_run, open = (d.interactions || []).filter(i => i.state === 'open').length;
  const btn = (act, label, cls, enabled, why, extra='') => `<button class="btn ${cls||''}" data-act="${act}" ${extra} ${enabled ? '' : 'disabled'} title="${esc(enabled ? '' : why)}">${esc(t(label))}</button>`;
  const main = [
    btn('resume', p.status === 'done' ? 'keepWorking' : 'resume', 'primary', canResume || p.status === 'done', t('whyRunning')),
    btn('stop', 'stopAfter', '', canStop, t('whyNotRunning')),
    d.live?.phase === 'waiting_partner' ? btn('accept', 'acceptNoReview', '', true, '') : '',
    ['queued','stopped'].includes(p.status) ? btn('run-next', 'runNext', '', true, '') : '',
    rec ? btn('run-app', run?.state === 'running' ? 'runRunning' : 'runApp', '', run?.state !== 'running', t('whyRunActive'), `data-n="${rec.number}"`)
        : btn('run-app', 'runApp', '', false, t('whyNoVersion')),
    run?.state === 'running' ? btn('run-stop', 'runStop', '', true, '') : '',
    btn('tab-questions', 'questionsBtn', '', true, '', '') + (open ? `<span class="counter" title="${esc(t('questionsOpen'))}">${open}</span>` : ''),
    ...(running ? pausedSides({live:d.live}) : []).map(side => `<button class="btn" data-act="retry" data-provider="${side}" title="${esc(t('estimateHelp'))}">${esc(t('retryNowFor', NAME[side]))}</button>`),
  ].join('');
  const danger = `<div class="danger-zone">${btn('stop-now', 'stopNow', 'danger', canStop && running, t('whyNotRunning'))}</div>`;
  const lang = p.language === 'unknown' ? `<span class="pill warn">${esc(t('langUnknown'))}</span>` : `<span class="pill idle" title="${esc(t('langFixed'))}">${esc((p.language||'pl').toUpperCase())}</span>`;
  setHTML('head', `<div style="width:100%"><div class="eyebrow"><span>${esc(p.key || '')}</span>${lang}</div><h2>${esc(p.title)}</h2>
    <div class="activity" aria-live="polite">${pill(t('s_'+p.status),kind)}<span>${esc(activity(p,d.live))}</span>${progressLine(d.progress)}</div>
    <div class="actionbar" role="toolbar" aria-label="${esc(t('actions'))}">${main}${danger}</div></div>`);
  const detail = local(p,'status_detail');
  setHTML('alert', detail ? `<div class="alert">${esc(detail)}${(d.blockers||[]).length ? `<br><button class="linkbtn" data-act="tab-questions">${esc(t('seeGates'))}</button>` : ''}</div>` : '');
}
const progressLine = g => g ? `<span class="hint" title="${esc(t('progressHelp'))}">· ${esc(t('progressShort', g.net, g.functional, g.debt_penalty))}</span>` : '';
function renderDetail(){
  const d = state.detail; if(!d) return;
  renderHead(d); setHTML('test', testCard(d)); renderTab(d); renderThread(d);
  setHTML('final', d.final && d.project.status === 'done' ? `<div class="card final-card"><div class="eyebrow"><span>${esc(t('finalTitle'))} · ${NAME[d.final.agent]||''} · ${clock(d.final.ts)}</span></div><div class="body">${esc(d.final.body)}</div>${runInfo(d)}</div>` : '');
  const m = d.monitor;
  setHTML('monitor-alert', m && m.signals.length ? `<div class="signal" role="alert"><b>⚠ ${esc(t('monSignal'))}</b><ul>${m.signals.map(s => `<li>${esc(local(s,'text'))}</li>`).join('')}</ul></div>` : '');
}
const num = n => Number(n || 0).toLocaleString(t('locale'));
function renderMonitor(m, plan){
  if(!m) return;
  const pair = o => `Claude ${Math.round(o?.claude ?? 0)}% · Codex ${Math.round(o?.codex ?? 0)}%`;
  const goal = m.goal ? `${m.goal[0]}/${m.goal[1]}${m.goal_history.length > 1 ? ' ('+m.goal_history.join(' → ')+')' : ''}` : t('monNoGoal');
  const verdicts = m.verdicts.length ? m.verdicts.map(v => t('v_'+v)).join(', ') : t('monNoGoal');
  const shares = Object.entries(plan?.breakdown || {}).filter(([,v]) => v).map(([k,v]) => `${t('grp_'+k)} ${v}%`).join(' · ') || '–';
  setHTML('monitor', `<dl class="stats"><dt>${esc(t('monGoal'))}</dt><dd>${esc(goal)}</dd>
    <dt>${esc(t('monVerdicts'))}</dt><dd>${esc(verdicts)}</dd>
    <dt>${esc(t('planSpend'))}</dt><dd>${esc(shares)}</dd>
    <dt>${esc(t('monTurns'))}</dt><dd>${m.turns} / ${m.versions}</dd>
    <dt>${esc(t('monSince'))}</dt><dd>${m.since_version}</dd>
    <dt>${esc(t('monCost'))}</dt><dd>${esc(pair(m.weekly_points))}</dd>
    <dt>${esc(t('monPerVersion'))}</dt><dd>${esc(pair(m.weekly_per_version))}</dd>
    <dt>${esc(t('monLines'))}</dt><dd>${m.lines_since} / ${m.lines_net}</dd>
    <dt>${esc(t('monTokens'))}</dt><dd>${esc(Object.entries(m.tokens || {}).map(([a, r]) => `${NAME[a]||a} ${num(r.total)}`).join(' · ') || '–')}</dd></dl>
    ${m.signals.length ? '' : `<p class="hint" style="margin-top:8px">${esc(t('monOk'))}</p>`}
    ${usageTables(m)}`);
}
// Missing data is shown as "n/a", never as 0; per-turn values are deltas of the session counters.
const na = v => v === null || v === undefined ? t('notAvailable') : num(v);
function usageTables(m){
  const usage = m.usage || [], win = Object.entries(m.windows || {});
  const byModel = usage.length ? `<h3 style="margin:16px 0 6px">${esc(t('usageByModel'))}</h3><table class="plan">
    <tr><th>${esc(t('colModel'))}</th><th class="num">${esc(t('colTurns'))}</th><th class="num">${esc(t('colIn'))}</th><th class="num">${esc(t('colCache'))}</th><th class="num">${esc(t('colOut'))}</th><th class="num">${esc(t('colTotal'))}</th></tr>
    ${usage.map(r => `<tr><td>${esc(NAME[r.agent]||r.agent)} · ${esc(r.model || '?')}${r.confirmed ? '' : ' <span class="hint">(' + esc(t('modelUnconfirmed')) + ')</span>'}</td><td class="num">${r.turns}</td><td class="num">${na(r.input)}</td><td class="num">${na(r.cache_read)}</td><td class="num">${na(r.output)}</td><td class="num">${na(r.total)}</td></tr>`).join('')}
    </table><p class="hint" style="margin-top:6px">${esc(t('usageHelp'))}</p>` : '';
  const windows = win.length ? `<h3 style="margin:16px 0 6px">${esc(t('windowsTitle'))}</h3><table class="plan">
    <tr><th>${esc(t('colProvider'))}</th><th class="num">${esc(t('col5h'))}</th><th class="num">${esc(t('colEquiv'))}</th><th class="num">${esc(t('colWeek'))}</th><th class="num">${esc(t('colGaps'))}</th></tr>
    ${win.map(([a, w]) => `<tr><td>${esc(NAME[a]||a)}</td><td class="num">${w.turns > w.unmeasured ? w.five_hour_percent + '%' : esc(t('notAvailable'))}</td><td class="num">${w.turns > w.unmeasured ? w.window_equivalents : esc(t('notAvailable'))}</td><td class="num">${w.turns > w.unmeasured ? w.weekly_percent + '%' : esc(t('notAvailable'))}</td><td class="num">${w.unmeasured}${w.shared ? ' / ' + w.shared + ' ' + esc(t('sharedTurns')) : ''}</td></tr>`).join('')}
    </table><p class="hint" style="margin-top:6px">${esc(t('windowsHelp'))}</p>` : '';
  return byModel + windows;
}
function shell(){
  state.html = {}; state.ghKey = null; state.renderedTab = null; state.live = null;
  document.getElementById('view').innerHTML = `
    <div class="head" id="head"></div><div id="alert"></div><div id="monitor-alert"></div><div id="final"></div><div id="test"></div>
    <div class="columns">
      <section class="card"><div class="tabs" role="tablist">
        ${TABS.map(([id,l])=>`<button class="tab" role="tab" data-tab="${id}" aria-selected="${state.tab===id}">${esc(t(l))}</button>`).join('')}
      </div><div id="tab-body"></div></section>
      <div class="rail">
        <section class="card"><h3>${esc(t('msgTitle'))}</h3>
          <form id="msg"><textarea id="msg-text" rows="3" placeholder="${esc(t('msgPlaceholder'))}" aria-label="${esc(t('msgTitle'))}"></textarea>
          <div class="row"><label class="check"><input type="checkbox" id="msg-interrupt"> ${esc(t('interrupt'))}</label><button class="btn primary">${esc(t('send'))}</button></div>
          <p class="hint" style="margin-top:6px">${esc(t('msgHint'))}</p></form>
          <div class="thread" id="thread"></div></section>
      </div></div>`;
}
function renderHero(){
  document.getElementById('view').innerHTML = `<div class="hero"><h2>${esc(t('heroTitle'))}</h2>
    <p>${esc(t('heroText'))}</p><a class="btn primary" href="#/nowy">${esc(t('newProject'))}</a></div>`;
}
function renderForm(){
  const repo = formRepo();
  document.getElementById('view').innerHTML = `<form class="form" id="new">
    <h2>${esc(repo ? t('ghRepoWork') : t('newProject'))}</h2><p class="lead">${esc(t('formLead'))}</p>
    <div class="field"><label for="task">${esc(t('fTask'))}</label>
      <textarea id="task" required placeholder="${esc(t('fTaskPlaceholder'))}"></textarea>
      <div class="row"><span class="hint">${esc(t('fDrop'))}</span><label class="btn small">${esc(t('fFile'))}<input type="file" id="file" accept=".md,.txt,.markdown" hidden></label></div></div>
    <div class="field"><label for="title">${esc(t('fName'))}</label><input id="title" type="text" placeholder="${esc(t('fNameHint'))}"></div>
    <div class="field"><label for="verify">${esc(t('fVerify'))}</label><input id="verify" type="text" placeholder="${esc(t('fVerifyPlaceholder'))}">
      <p class="hint">${esc(t('fVerifyHint'))}</p></div>
    ${repo ? `<div class="field"><div class="label">${esc(t('ghFormRepo', repo))}</div><p class="hint">${esc(t('ghFormHint'))}</p></div>`
      : `<div class="field"><label for="repo">${esc(t('fFolder'))}</label><input id="repo" type="text" placeholder="${esc(t('fFolderPlaceholder'))}">
      <p class="hint">${esc(t('fFolderHint'))}</p></div>`}
    <div class="field"><div class="label">${esc(t('modelsTitle'))}</div>
      <div class="models" id="form-models">${sideControls('codex',...DEFAULT_MODELS.codex)}${sideControls('claude',...DEFAULT_MODELS.claude)}${sideControls('gemini', state.catalog?.gemini_problem ? 'none' : DEFAULT_MODELS.gemini[0], DEFAULT_MODELS.gemini[1])}${fallbackControl('general')}</div>
      <p class="hint">${esc(t('fModelsHint'))} ${esc(t('rolesHint'))}</p></div>
    <details><summary>${esc(t('fAdvanced'))}</summary><div class="grid2">
      <div class="field"><label for="turns">${esc(t('fTurns'))}</label><input id="turns" type="number" min="2" value="30"></div><div></div>
    </div></details>
    <div class="error" id="form-error" role="alert"></div>
    <div class="row" style="justify-content:flex-start;margin-top:14px"><button class="btn primary">${esc(t('fSubmit'))}</button></div>
  </form>`;
  const task = document.getElementById('task');
  const load = file => { if(file) file.text().then(text => { task.value = text; }); };
  document.getElementById('file').addEventListener('change', e => load(e.target.files[0]));
  task.addEventListener('dragover', e => { e.preventDefault(); task.classList.add('drag'); });
  task.addEventListener('dragleave', () => task.classList.remove('drag'));
  task.addEventListener('drop', e => { e.preventDefault(); task.classList.remove('drag'); load(e.dataTransfer.files[0]); });
  document.getElementById('new').addEventListener('submit', async e => {
    e.preventDefault();
    const value = id => document.getElementById(id).value;
    const pick = (side, kind) => kind === 'role'
      ? [...document.querySelectorAll(`#form-models .roles-pick[data-side=${side}] input:checked`)].map(i => i.value).join(',') || 'general'
      : document.querySelector(`#form-models [data-side=${side}][data-kind=${kind}]`).value;
    try{
      const {id} = await withTopConfirm('/api/projects', {task:value('task'), lang:state.lang,
        claude_selection:pick('claude','selection'), codex_selection:pick('codex','selection'), gemini_selection:document.querySelector('#form-models [data-side=gemini][data-kind=selection]')?.value || 'manual', title:value('title'), verify_cmd:value('verify'), repo_path:repo ? '' : value('repo'), github_repo:repo,
        max_turns:Number(value('turns')), claude_model:pick('claude','model'), claude_reasoning:pick('claude','reasoning'),
        codex_model:pick('codex','model'), codex_reasoning:pick('codex','reasoning'),
        claude_role:pick('claude','role'), codex_role:pick('codex','role'), role_fallback:pick('team','fallback'),
        gemini_model:pick('gemini','model'), gemini_reasoning:pick('gemini','reasoning'), gemini_role:pick('gemini','role')});
      location.hash = '#/p/'+id;
    }catch(error){ document.getElementById('form-error').textContent = error.message; }
  });
}
async function refreshTranscript(id){
  const {text} = await api(`/api/projects/${id}/transcript`);
  state.transcript = text;
  if(state.tab === 'transkrypt' && state.detail) renderTab(state.detail);
}
function renderPower(on){
  document.getElementById('full-power').checked = on;
  document.getElementById('power').classList.toggle('on', on);
  document.getElementById('power-hint').textContent = t(on?'powerOn':'powerOff');
}
async function poll(){
  try{
    state.overview = await api('/api/overview');
    renderLimits(state.overview.limits);
    renderPower(state.overview.full_power);
    renderSecurity(state.overview.security);
    renderProjects(state.overview.projects);
    renderRepos();
    const id = route();
    if(id && id !== 'new'){
      state.detail = await api('/api/projects/'+id);
      renderDetail();
    }
    document.dispatchEvent(new CustomEvent('sol83:poll', {detail:{ok:true}}));
  }catch(error){ console.error(error); document.dispatchEvent(new CustomEvent('sol83:poll', {detail:{ok:false}})); }
}
function navigate(){
  const id = route();
  state.detail = null; state.transcript = '';
  if(id === 'new') renderForm();
  else if(id) shell();
  else renderHero();
  poll();
}
async function withSecretsCheck(path, body){
  try{ return await api(path, body); }
  catch(error){
    const found = error.data?.secrets;
    if(!found || !confirm(t('secretsConfirm', found.map(item => '- ' + item).join('\n')))) throw error;
    return await api(path, {...body, confirmed_secrets:error.data.secrets_token});
  }
}
async function publish(n, visibility){
  const name = document.getElementById('gh-name')?.value || '';
  await withSecretsCheck(`/api/projects/${route()}/github`, {number:n, name, visibility});
  state.ghKey = null; await poll();
}
document.addEventListener('click', async e => {
  const language = e.target.closest('[data-lang]');
  if(language){
    state.lang = language.dataset.lang;
    try{ localStorage.setItem('gemini-lang', state.lang); }catch(error){}
    state.html = {}; state.ghKey = null;
    applyStatic(); navigate();
    return;
  }
  const tab = e.target.closest('[data-tab]');
  if(tab){
    state.tab = tab.dataset.tab;
    document.querySelectorAll('.tab').forEach(item => item.setAttribute('aria-selected', item === tab));
    state.html['tab-body'] = null;
    if(state.detail) renderTab(state.detail);
    return;
  }
  const button = e.target.closest('[data-act]');
  if(!button) return;
  const id = route(), n = Number(button.dataset.n), act = button.dataset.act;
  if(act === 'retry'){
    const provider = button.dataset.provider;
    button.disabled = true;
    try{
      const done = await api('/api/limits/retry', {provider});
      if(!done.lifted) alert(t('retryKept', NAME[provider]));
      await poll();
    }catch(error){ alert(error.message); button.disabled = false; }
    return;
  }
  if(act === 'item'){
    button.disabled = true;
    try{ await api(`/api/projects/${id}/start-item`, {item:button.dataset.item, request_key:requestKey()}); await poll(); }
    catch(error){ alert(error.message); button.disabled = false; }
    return;
  }
  if(act === 'setup-approve'){
    button.disabled = true;
    try{ await api(`/api/projects/${id}/setup-approve`, {sha:button.dataset.sha}); delete state.html['tab-body']; state.renderedTab = null; await poll(); }
    catch(error){ alert(error.message); button.disabled = false; }
    return;
  }
  if(act === 'delete-project'){
    const d = state.detail, p = d.project;
    document.getElementById('delete-title').textContent = t('deleteAsk', p.title);
    document.getElementById('delete-repo').textContent = !p.repo_path ? '' : d.own_repo ? t('deleteOwn', p.repo_path) : t('deleteUser', p.repo_path, p.branch || '');
    document.getElementById('delete-dialog').showModal();
    return;
  }
  if(act === 'withdraw'){
    button.disabled = true;
    try{ await api(`/api/projects/${id}/withdraw`, {question:Number(button.dataset.q)}); await poll(); }
    catch(error){ alert(error.message); button.disabled = false; }
    return;
  }
  if(act === 'order'){
    const q = state.detail.questions.find(x => x.id === Number(button.dataset.q));
    button.disabled = true;
    try{ await api(`/api/projects/${id}/notes`, {text:q.question, order:true, request_key:'order-q' + q.id}); await poll(); }
    catch(error){ alert(error.message); button.disabled = false; }
    return;
  }
  if(act === 'broken'){
    state.rejecting = n;
    document.getElementById('reject-title').textContent = t('rejectTitle', n);
    document.getElementById('reject-text').value = '';
    document.getElementById('reject').showModal();
    return;
  }
  if(act === 'gh-send' || (act === 'gh-visibility' && button.dataset.to === 'public')){
    const chosen = document.querySelector('input[name=gh-vis]:checked')?.value;
    const goingPublic = act === 'gh-visibility' || chosen === 'public' || (!chosen && state.detail?.project.github_visibility === 'public');
    state.pendingPublic = {act, n};
    if(goingPublic){ document.getElementById('public-dialog').showModal(); return; }
    return runGitHub(button, 'private');
  }
  if(act === 'tab-questions'){
    state.tab = 'pytania'; document.querySelectorAll('.tab').forEach(item => item.setAttribute('aria-selected', item.dataset.tab === 'pytania'));
    state.html['tab-body'] = null; renderTab(state.detail); return;
  }
  if(act === 'copy'){
    try{ await navigator.clipboard.writeText(button.dataset.text); button.textContent = t('copied'); }catch(error){ alert(button.dataset.text); }
    return;
  }
  if(act === 'answer' || act === 'test-result'){
    const q = Number(button.dataset.q), own = document.getElementById('answer-'+q);
    const body = {interaction:q, request_key:requestKey()};
    if(act === 'test-result'){
      body.result = button.dataset.result;
      if(body.result !== 'works'){ const comment = prompt(t('qCommentFail')); if(comment === null) return; body.comment = comment; }
    }
    else { body.value = button.dataset.value || own?.value || ''; if(!body.value.trim()) return; }
    button.disabled = true;
    try{ await api(`/api/projects/${id}/answer`, body); await poll(); }catch(error){ alert(error.message); button.disabled = false; }
    return;
  }
  const extra = {
    'run-app':['run',{number:n}], 'run-stop':['run-stop',{}], reveal:['reveal',{path:button.dataset.path}],
    'q-state':['interaction-state',{interaction:Number(button.dataset.q), state:button.dataset.state}],
    'asset-decision':['asset-decision',{id:button.dataset.id, decision:button.dataset.decision}],
    'git-deliver':['git-deliver',{request_key:requestKey()}]
  };
  if(extra[act]){
    button.disabled = true;
    try{ await api(`/api/projects/${id}/${extra[act][0]}`, extra[act][1]); await poll(); }catch(error){ alert(error.message); }
    button.disabled = false;
    return;
  }
  const calls = {
    stop:['stop',{}], 'stop-now':['stop',{immediate:true}], resume:['resume',{}], accept:['accept',{}], 'run-next':['run-next',{}],
    works:['verdict',{number:n,works:true}], 'test-copy':['test-copy',{number:n}], 'gh-visibility':['github-visibility',{visibility:'private'}]
  };
  button.disabled = true;
  try{ await api(`/api/projects/${id}/${calls[act][0]}`, calls[act][1]); state.ghKey = null; await poll(); }
  catch(error){ alert(error.message); button.disabled = false; }
});
async function runGitHub(button, visibility){
  const {act, n} = state.pendingPublic;
  if(button) button.disabled = true;
  try{
    if(act === 'gh-send') await publish(n, visibility);
    else { await withSecretsCheck(`/api/projects/${route()}/github-visibility`, {visibility}); state.ghKey = null; await poll(); }
  }catch(error){ alert(error.message); if(button) button.disabled = false; }
}
document.getElementById('repo-filter').addEventListener('input', renderRepos);
// Only the user's own click is remembered: a group shown open because it holds the open project is not.
document.getElementById('projects').addEventListener('click', e => {
  const summary = e.target.closest('details.pgroup > summary');
  if(!summary) return;
  const group = summary.parentElement;
  rememberGroup(group.dataset.group, !group.open);
  setTimeout(() => { state.html['projects'] = null; }, 0);
});
document.getElementById('providers-box').addEventListener('toggle', async e => {
  if(e.target.open && !state.providers){ try{ state.providers = await api('/api/providers'); renderProviders(state.providers); }catch(error){} }
});
for(const [id, key] of [['sec-network','test_network'],['sec-unsandboxed','allow_unsandboxed']]){
  document.getElementById(id).addEventListener('change', async e => {
    if(key === 'allow_unsandboxed' && e.target.checked && !confirm(t('secUnsandboxedWarn'))){ e.target.checked = false; return; }
    try{ await api('/api/settings', {[key]:e.target.checked}); }catch(error){ alert(error.message); }
  });
}
function renderSecurity(s){
  if(!s) return;
  const net = document.getElementById('sec-network'), raw = document.getElementById('sec-unsandboxed');
  if(document.activeElement !== net) net.checked = s.test_network;
  if(document.activeElement !== raw) raw.checked = s.allow_unsandboxed;
  document.getElementById('sandbox-state').textContent = s.sandbox ? t('sandboxOn', s.sandbox) : t('sandboxOff');
}
document.getElementById('check-providers').addEventListener('click', async e => {
  e.target.disabled = true;
  try{ const r = await api('/api/providers/check', {}); state.providers = r.providers; renderProviders(r.providers); renderLimits(r.limits); }
  catch(error){ alert(error.message); }
  e.target.disabled = false;
});
document.addEventListener('toggle', async e => {
  const id = Number(e.target.dataset?.event);
  if(!id) return;
  if(!e.target.open){ state.open.delete(id); return; }
  state.open.add(id);
  if(state.bodies[id] === undefined){
    const {body} = await api(`/api/projects/${route()}/events/${id}`);
    state.bodies[id] = body || '';
    if(state.detail) renderTab(state.detail);
  }
}, true);
document.addEventListener('change', async e => {
  const rolesBox = e.target.closest('.roles-pick');
  if(rolesBox){
    if(!rolesBox.closest('#models')) return;
    const side = rolesBox.dataset.side, roles = [...rolesBox.querySelectorAll('input:checked')].map(i => i.value).join(',') || 'general';
    try{ await api(`/api/projects/${route()}/models`, {[side+'_role']:roles}); }catch(error){ alert(error.message); }
    delete state.html['models']; poll();
    return;
  }
  if(e.target.id === 'skin-pick'){ applySkin(e.target.value); return; }
  if(['user-tests-pick','web-fetch-pick','review-mode-pick','project-kind-pick'].includes(e.target.id)){
    const body = e.target.id === 'user-tests-pick' ? {user_tests:e.target.value}
      : e.target.id === 'review-mode-pick' ? {review_mode:e.target.value}
      : e.target.id === 'project-kind-pick' ? {project_kind:e.target.value} : {web_fetch:e.target.checked};
    try{ await api(`/api/projects/${route()}/options`, body); }catch(error){ alert(error.message); }
    poll(); return;
  }
  if(e.target.id === 'lang-pick'){
    try{ await api(`/api/projects/${route()}/language`, {language:e.target.value}); }catch(error){ alert(error.message); }
    poll(); return;
  }
  if(e.target.id === 'coordinator-pick'){
    try{ await api('/api/settings', {coordinator:e.target.value}); }catch(error){ alert(error.message); }
    delete state.html['coordinator']; poll();
    return;
  }
  if(e.target.id === 'gh-auto'){
    await api(`/api/projects/${route()}/github-auto`, {enabled:e.target.checked});
    state.ghKey = null; poll();
    return;
  }
  const select = e.target.closest('select[data-side]');
  if(!select) return;
  const side = select.dataset.side, box = select.closest('.side-pick');
  if(select.dataset.kind === 'selection'){
    if(!select.closest('#models')) return;
    try{ await api(`/api/projects/${route()}/models`, {[side+'_selection']:select.value}); }
    catch(error){ alert(error.message); }
    delete state.html['models']; poll();
    return;
  }
  if(['role','fallback'].includes(select.dataset.kind)){
    if(!select.closest('#models')) return;
    try{ await api(`/api/projects/${route()}/models`, {[select.dataset.kind === 'role' ? side+'_role' : 'role_fallback']:select.value}); }
    catch(error){ alert(error.message); delete state.html['models']; }
    poll();
    return;
  }
  const reasoning = box.querySelector('[data-kind=reasoning]');
  if(select.dataset.kind === 'model'){
    const efforts = state.catalog?.[side]?.find(m => m.id === select.value)?.efforts || [];
    const next = efforts.includes(reasoning.value) ? reasoning.value : efforts.includes('high') ? 'high' : efforts.at(-1);
    const fixed = select.value !== 'none' && state.catalog?.[side]?.find(m => m.id === select.value)?.efforts?.length === 0;
    reasoning.disabled = select.value === 'none' || fixed;
    reasoning.innerHTML = select.value === 'none' ? '' : fixed ? `<option value="">${esc(t('inModel'))}</option>` : effortOptions(side, select.value, next);
  }
  if(select.closest('#models')){
    try{ await withTopConfirm(`/api/projects/${route()}/models`, {[side+'_model']:box.querySelector('[data-kind=model]').value, [side+'_reasoning']:reasoning.value}); }
    catch(error){ alert(error.message); }
    delete state.html['models']; poll();
  }
});
document.addEventListener('submit', async e => {
  if(e.target.id === 'rename-form'){
    e.preventDefault();
    try{ await api(`/api/projects/${route()}/rename`, {title:document.getElementById('rename-text').value}); poll(); }catch(error){ alert(error.message); }
    return;
  }
  if(e.target.id === 'license-form'){
    e.preventDefault();
    const v = id => document.getElementById(id);
    try{ await api(`/api/projects/${route()}/license`, {kind:v('lic-kind').value, spdx:v('lic-spdx').value, holder:v('lic-holder').value, custom:v('lic-custom').value, overwrite:v('lic-overwrite').checked}); state.renderedTab = null; poll(); }
    catch(error){ alert(error.message); }
    return;
  }
  if(e.target.id === 'git-form'){
    e.preventDefault();
    const v = id => document.getElementById(id);
    try{ await api(`/api/projects/${route()}/git-context`, {remote:v('git-remote').value, base_branch:v('git-base').value, strategy:v('git-strategy').value, allow_push:v('git-push').checked, allow_pr:v('git-pr').checked}); state.renderedTab = null; poll(); }
    catch(error){ alert(error.message); }
    return;
  }
  if(e.target.id === 'verify-form'){
    e.preventDefault();
    try{ await api(`/api/projects/${route()}/verify`, {command:document.getElementById('verify-cmd').value}); poll(); }
    catch(error){ alert(error.message); }
    return;
  }
  if(e.target.id === 'asset-form'){
    e.preventDefault();
    const value = id => document.getElementById(id).value;
    try{
      await api(`/api/projects/${route()}/asset`, {type:value('asset-type'), prompt:value('asset-prompt'), path:value('asset-path'), size:value('asset-size'), style:value('asset-style')});
      e.target.reset(); poll();
    }catch(error){ alert(error.message); }
    return;
  }
  if(e.target.id === 'msg'){
    e.preventDefault();
    const input = document.getElementById('msg-text'), interrupt = document.getElementById('msg-interrupt');
    if(!input.value.trim()) return;
    const text = input.value; input.value = '';
    try{ await api(`/api/projects/${route()}/message`, {text, interrupt:interrupt.checked, lang:state.lang}); }
    catch(error){ alert(error.message); input.value = text; }
    interrupt.checked = false; poll();
  }
  if(e.target.id === 'ask'){
    e.preventDefault();
    const input = document.getElementById('ask-text');
    if(!input.value.trim()) return;
    const question = input.value; input.value = '';
    await api(`/api/projects/${route()}/ask`, {question, lang:state.lang}); poll();
  }
  if(e.target.id === 'note'){
    e.preventDefault();
    const input = document.getElementById('note-text'), urgent = document.getElementById('note-urgent');
    if(!input.value.trim()) return;
    const text = input.value; input.value = '';
    // The same key until the server confirms: a retry after a lost answer cannot add the note twice.
    state.noteKey = state.noteKey || requestKey();
    try{ await api(`/api/projects/${route()}/notes`, {text, urgent:urgent.checked, request_key:state.noteKey}); state.noteKey = null; urgent.checked = false; }
    catch(error){ input.value = text; alert(error.message); }
    poll();
  }
});
document.getElementById('reject').addEventListener('close', async e => {
  if(e.target.returnValue !== 'send') return;
  await api(`/api/projects/${route()}/verdict`, {number:state.rejecting, works:false, comment:document.getElementById('reject-text').value, request_key:requestKey()});
  poll();
});
document.getElementById('delete-dialog').addEventListener('close', async e => {
  if(e.target.returnValue !== 'delete') return;
  try{ await api(`/api/projects/${route()}/delete`, {}); location.hash = '#/'; }
  catch(error){ alert(error.message); }
});
document.getElementById('public-dialog').addEventListener('close', e => {
  if(e.target.returnValue === 'on') runGitHub(null, 'public');
});
document.getElementById('refresh').addEventListener('click', async () => {
  const {limits} = await api('/api/limits/refresh', {}); renderLimits(limits);
});
for(const name of ['claude','codex']){
  for(const [prefix, key] of [['th-','threshold_'],['wk-','weekly_']]){
    document.getElementById(prefix+name).addEventListener('change', async e => {
      const {limits} = await api('/api/settings', {[key+name]:Number(e.target.value)}); renderLimits(limits);
    });
  }
}
async function setPower(on){ await api('/api/settings', {full_power:on}); poll(); }
document.getElementById('full-power').addEventListener('click', e => {
  if(e.target.checked){ e.preventDefault(); document.getElementById('power-dialog').showModal(); }
  else setPower(false);
});
document.getElementById('power-dialog').addEventListener('close', e => {
  if(e.target.returnValue === 'on') setPower(true);
});
window.addEventListener('hashchange', navigate);
applyStatic();
Promise.all([api('/api/catalog'), api('/api/github')]).then(([catalog, github]) => { state.catalog = catalog; state.github = github; navigate(); }).catch(navigate);
setInterval(poll, 3000);
const refreshGitHub = () => Promise.all([api('/api/github'), api('/api/github/repos')])
  .then(([github, {repos}]) => { state.github = github; state.repos = repos; }).catch(() => {});
refreshGitHub();
setInterval(refreshGitHub, 60000);
