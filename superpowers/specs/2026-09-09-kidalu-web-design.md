# kidalu.com — projekt nowej witryny

Data: 2026-09-09
Repo: `Rosa89/kidaluweb` (do 2026-09-09: `Rosa89/readbysyllables-privacy`)

> Lokalizacja tego pliku odbiega od domyślnej `docs/superpowers/specs/`, ponieważ
> katalog `docs/` staje się korzeniem publikowanej witryny — spec nie ma trafić na
> kidalu.com.

## 1. Cel

Zastąpić dotychczasowy hub „Mądre Dzieciaki" pod codedriven.pl nową witryną
**kidalu.com**: bajkowym lasem, w którym każda aplikacja ma własny domek-grzyb
z zapraszającą sową. Witryna prezentuje aplikacje, prowadzi do Google Play
i hostuje dokumenty wymagane przez Play.

## 2. Stan wyjściowy

Repo zawiera statyczny hub: `index.html`, `kontakt.html`, po jednej stronie
dokumentów na aplikację (`nauka-czytania-sylabami/`, `literki-i-cyferki/`,
`literki-i-cyferki/de/`), arkusz `assets/forest.css` (216 linii) i trzy logotypy
webp 500 px. Pages serwuje z `main` `/`, CNAME `codedriven.pl`, certyfikat HTTPS
ważny do 2026-10-27.

Aplikacje:

| Aplikacja | Package | Wersja |
|---|---|---|
| Nauka czytania sylabami | `com.readbysyllables.app` | 1.0.4+31 |
| Literki i Cyferki | `com.literkiicyferki.app` | 1.0.3+9 |

## 3. Decyzje

1. **Marka.** „Kidalu" zastępuje „Mądre Dzieciaki" na witrynie w całości.
2. **Domena.** kidalu.com to główny adres. codedriven.pl zostaje użytkownikowi
   na osobny cel i po migracji przestaje serwować tę witrynę.
3. **Języki.** PL (główny), DE, EN.
4. **Koncept sceny.** Domki-grzyby na polanie, sowa przy każdym domku,
   nazwa aplikacji na drewnianym szyldzie. Render w stylistyce logo, żeby
   grzyby i logo mówiły jednym językiem wizualnym.
5. **Cel linku.** Sowa/domek prowadzi na podstronę aplikacji na kidalu.com,
   nie prosto do sklepu.
6. **Napisy na szyldach** renderowane czcionką webową, nigdy wypalone w grafice —
   inaczej każda nazwa razy trzy języki to plik do przegenerowania przy literówce.

## 4. Architektura informacji

Język jako prefiks ścieżki. Slugi definiowane per język (angielski adres nie ma
zawierać polskiego slugu). Cztery strony na język — las, dwie aplikacje,
kontakt — plus strona dokumentów dla każdego istniejącego przekładu.

```
/                                     las (PL)
/czytanie-sylabami/                   podstrona aplikacji
/czytanie-sylabami/dokumenty/         polityka + regulamin + usunięcie konta
/literki-i-cyferki/
/literki-i-cyferki/dokumenty/
/kontakt/
/de/…  /en/…                          to samo, slugi z pliku treści danego języka
```

Konkretne slugi i nazwy wyświetlane:

| | PL | DE | EN |
|---|---|---|---|
| Czytanie | `czytanie-sylabami` | `lesen-nach-silben` | `reading-by-syllables` |
| Literki | `literki-i-cyferki` | `buchstaben-und-zahlen` | `letters-and-numbers` |
| Kontakt | `kontakt` | `kontakt` | `contact` |
| Segment dokumentów | `dokumenty` | `dokumente` | `legal` |

| Aplikacja | PL | DE | EN |
|---|---|---|---|
| `com.readbysyllables.app` | Nauka czytania sylabami | Lesen nach Silben | Reading by Syllables |
| `com.literkiicyferki.app` | Literki i Cyferki | Buchstaben und Zahlen | Letters and Numbers |

Adresy w sklepie:
`https://play.google.com/store/apps/details?id=com.readbysyllables.app`
`https://play.google.com/store/apps/details?id=com.literkiicyferki.app`

Przypisanie sów: Literki dostają sowę z tabliczką ABC/123 (mamy), Czytanie —
sowę z otwartą książką (do zamówienia).

**URL-e krytyczne dla Google Play** (polityka prywatności — muszą być stabilne
raz na zawsze, bo trafiają do konsoli):

- `https://kidalu.com/czytanie-sylabami/dokumenty/`
- `https://kidalu.com/literki-i-cyferki/dokumenty/`

Dlatego slugi per język ustalamy od razu, a nie „kiedyś" — każda późniejsza
zmiana adresu to ponowna aktualizacja obu listingów w Play.

## 5. System budowania

Kilkanaście stron utrzymywanych ręcznie w trzech językach rozjedzie się gwarantowanie.
Generator: **Python + Jinja2**, wynik commitowany, Pages serwuje `/docs`.
Bez CI, bez `node_modules`.

```
build.py                     ~150 linii
content/{pl,de,en}.json      teksty, slugi, dane aplikacji
content/docs/{app}.{lang}.html   dokumenty prawne jako partiale HTML
src/templates/*.html.jinja   base, forest, app, docs, contact
src/assets/                  css, js, grafiki
  →  docs/                   wynik: HTML + assets + CNAME + .nojekyll
```

Dokumenty prawne trzymamy jako partiale HTML, nie w JSON-ie — są długie,
a istniejące strony przenosimy w całości bez konwersji.

Generator dodatkowo emituje `sitemap.xml`, `robots.txt` i wzajemne `hreflang`
dla trzech wersji każdej strony.

Jedyna nowa zależność: `jinja2`.

## 6. Scena

### Warstwy

Pięć warstw w głąb, każda z własną głębią parallaksy:

| Warstwa | `data-depth` |
|---|---|
| niebo | 0.02 |
| dalekie świerki we mgle | 0.06 |
| drzewa średniego planu | 0.12 |
| polana ze ścieżką | 0.20 |
| paprocie pierwszego planu | 0.34 |

Stacje (domek + sowa + szyld + strefa klikalna) siedzą między polaną
a pierwszym planem.

### Układ

- **Desktop:** stacje w rzędzie wzdłuż wijącej się ścieżki, każda przesunięta
  w pionie o własne `--offset-y`, żeby siedziała na ścieżce.
- **Mobile (≤760 px):** ta sama ścieżka obrócona w pion, stacje w kolumnie,
  naprzemiennie lewa/prawa, wjeżdżają przez `IntersectionObserver`.

Te same grafiki w obu układach. Żadnej osobnej wersji mobilnej.

### Animacje

Parallaksa: jedna pętla `requestAnimationFrame` czyta `scrollY` i pozycję myszy,
zapisuje `--px`/`--py` na kontenerze; warstwy przesuwają się wyłącznie przez
`translate3d`. Jedna pętla, tylko transformacje.

CSS: dryfujące świetliki, spadające listki, oddech sowy (`rotate` ±1.5°).
Parametry losowe (opóźnienie, tor) generowane **w czasie budowania** jako
custom properties — deterministycznie, bez losowania w przeglądarce.

Hover na stacji: domek unosi się i lekko rośnie, okno rozświetla się ciepłym
`radial-gradient`, sowa przechyla głowę.

`prefers-reduced-motion: reduce` wyłącza parallaksę, dryf, spadanie i oddech;
zostają zmiany kolorystyczne na hover.

### Dostępność

Każda stacja to prawdziwy `<a>` z nazwą aplikacji jako nazwą dostępną. Warstwy
dekoracyjne `alt=""` i `aria-hidden="true"`. Widoczny pierścień fokusu.
Tekst na szyldzie musi osiągnąć kontrast 4.5:1 wobec drewna — do zweryfikowania
na gotowym wycinku, w razie potrzeby ciemniejsze drewno pod napisem.

## 7. System wizualny

Paleta zmierzona na logo (udział liczony na pikselach obiektu, nie na kadrze):

| Token | Hex | Rola |
|---|---|---|
| `--paper` | `#FDF6E0` | kremowe tło, litery na szyldzie |
| `--cream-2` | `#FCE8C7` | jaśniejsze piórka, delikatne tła |
| `--wood` | `#994E21` | drewno szyldu, główny brąz |
| `--wood-light` | `#CB8550` | rozjaśnienia drewna i piór |
| `--wood-dark` | `#6E3410` | cienie drewna |
| `--ink` | `#54240A` | tekst |
| `--pine` | `#205740` | ciemna zieleń świerków |
| `--pine-2` | `#2F7056` | jaśniejsza zieleń |
| `--sky` | `#6FCCF3` | niebo |

Bursztyn dzioba do domknięcia na gotowym wycinku — w logo zajmuje zbyt małą
powierzchnię, żeby go wiarygodnie zmierzyć.

Typografia: **Fredoka** na nagłówki i szyldy (najbliżej miękkiego liternictwa
logo), **Nunito** na tekst ciągły. Przed użyciem sprawdzić w obu krojach komplet
`ąćęłńóśźż` i `äöüß`; jeśli któregoś brakuje — zamiana na Baloo 2.

## 8. Pipeline graficzny

Elementy zamawiane w Gemini na koncie `sebastian.rosinski.1989@gmail.com`
(`gemini.google.com/u/1/app` — samo `/app` otwiera konto służbowe merce.com).

Wspólny „klej" stylistyczny doklejany do każdego promptu: miękki render 3D
w stylu maskotki-sowy, ciepłe zaokrąglone bryły, delikatne światło konturowe,
matowe wykończenie, paleta z sekcji 7, **bez tekstu i liter**, obiekt w całości
wykadrowany, na czystym białym tle.

### Do zamówienia

| # | Element | Rozmiar |
|---|---|---|
| 1 | niebo z chmurkami | 2400×1000 |
| 2 | pas dalekich świerków we mgle | 2400×900 |
| 3 | drzewa średniego planu | 2400×1100 |
| 4 | polana z wijącą się ścieżką | 2400×800 |
| 5 | paprocie i kamienie pierwszego planu | 2400×500 |
| 6 | domek-grzyb (Czytanie) | 1024² |
| 7 | domek-grzyb (Literki) | 1024² |
| 8 | sowa z otwartą książką | 1024² |
| 9 | pusty drewniany szyld na słupku | 1024×512 |
| 10 | świetlik | 256² |
| 11 | motyl | 256² |
| 12 | trzy listki | 256² |

12 promptów, 14 plików wynikowych — pozycja 12 to trzy osobne listki.

### Już mamy

- Sowa z tabliczką ABC/123 — 2048², białe tło do wycięcia
- Logo Kidalu — 1254², białe tło; oryginał w pełnej rozdzielczości do
  dociągnięcia z czatu „Logotyp dla aplikacji Kidalu"
- `reading_app/resources/icon/owl_transparent.png` — 1024², już przezroczysta,
  stylistyka do weryfikacji względem logo

### Obróbka lokalna — `tools/prepare_asset.py`

1. `rembg` (model u2net) — wycięcie tła; zwykły flood-fill rozłazi się na
   puszystych piórach
2. czyszczenie krawędzi: erozja alfy o 1 px i wtopienie
3. autokadrowanie do zawartości z niewielkim marginesem
4. skalowanie do docelowego rozmiaru, eksport webp (q=82 dla 1x, q=90 dla 2x)
5. raport wagi pliku

Nowe zależności: `rembg` (ciągnie `onnxruntime`).

### Budżet

Warstwa pełnej szerokości ≤180 KB, obiekt ≤80 KB, ładunek początkowy <900 KB.
Poniżej pierwszego ekranu `loading="lazy"`, wszędzie jawne `width`/`height`.

## 9. Wdrożenie

### Kolejność — i dlaczego akurat taka

Pages obsługuje **jedną** domenę na repo. W chwili przełączenia CNAME na
kidalu.com codedriven.pl przestaje serwować polityki prywatności, na które
wskazuje Google Play. Stąd:

1. Zbudować witrynę, przełączyć Pages na `/docs`, opublikować na kidalu.com
2. Zweryfikować, że kidalu.com żyje i ma ważny certyfikat
3. **Użytkownik** ustawia w OVH przekierowanie 301 codedriven.pl → kidalu.com
   (pomost dla starych linków z Play)
4. **Użytkownik** aktualizuje linki w Play Console dla obu aplikacji
5. Dopiero wtedy codedriven.pl idzie na swoje nowe przeznaczenie

### DNS w OVH — wykonuje użytkownik

```
A     @    185.199.108.153
A     @    185.199.109.153
A     @    185.199.110.153
A     @    185.199.111.153
AAAA  @    2606:50c0:8000::153
AAAA  @    2606:50c0:8001::153
AAAA  @    2606:50c0:8002::153
AAAA  @    2606:50c0:8003::153
CNAME www  rosa89.github.io.
```

Do panelu OVH i do Play Console nie loguję się — nie wpisuję cudzych haseł.
Dostarczam gotowe wartości do wklejenia.

### Po stronie repo

`docs/CNAME` = `kidalu.com`, `docs/.nojekyll`, źródło Pages przestawione na
`main` `/docs`, wymuszony HTTPS po wystawieniu certyfikatu.

## 8a. Scena na pełny ekran — wymóg właściciela

Na desktopie i tablecie scena wypełnia **cały ekran: 100% szerokości i 100% wysokości**.
Odwiedzający ma zobaczyć las od razu, bez przewijania, i mieć wszystkie domki w zasięgu
wzroku. Na telefonie obowiązuje układ pionowy ze ścieżką i przewijaniem.

Z tego wymogu wynikają trzy rzeczy, które trzeba obsłużyć w etapie 2:

**Proporcje kadru.** Wypełnienie obu wymiarów naraz oznacza, że przy panoramicznym monitorze
i przy tablecie w pionie potrzebna jest zupełnie inna część obrazu. Warstwy skalujemy metodą
pokrycia z zakotwiczeniem: niebo do góry, polana i pierwszy plan do dołu. Warstwy muszą mieć
zapas treści na docięcie — jeśli okaże się go za mało przy tablecie w pionie, polana
i paprocie idą do przegenerowania z większą wysokością.

**Pozycje domków.** Stacje pozycjonujemy procentowo względem sceny, nie w pikselach, żeby
wędrowały razem z kadrem. Każda ma minimalną i maksymalną wielkość, więc na panoramicznym
ekranie nie urosną absurdalnie, a na niskim laptopie nie znikną.

**Niskie okna.** Laptop 1440×720 po odjęciu paska przeglądarki daje bardzo płaski kadr.
Logo, domki i szyldy muszą się w nim zmieścić bez przycięcia — to jest twarde kryterium
odbioru etapu 2, nie życzenie.

Układ musi też znieść **więcej niż dwie aplikacje**. Dziś domki są dwa i mieszczą się
wygodnie; przy czterech i więcej ścieżka musi je rozłożyć bez ścisku, a w ostateczności
scena zyskuje drugi plan w głębi.

## 9a. Etapy

Zakres jest spory, a jego części mają różną pilność. Dwa etapy w jednym planie —
wspólny generator i wspólne szablony, więc rozdzielanie na dwa specyfikacje
byłoby sztuczne.

**Etap 1 — szkielet.** Generator, treści w trzech językach, przeniesione
dokumenty prawne, prosta wersja strony głównej bez sceny, deploy na kidalu.com.
Na końcu tego etapu polityki prywatności żyją pod nowym adresem, więc można
zaktualizować Play i zdjąć ryzyko zgodności. Etap nie zależy od żadnej grafiki
z Gemini poza logo.

**Etap 2 — las.** Zamówienie i obróbka grafik, pięciowarstwowa scena, stacje,
animacje, układ mobilny, podstrony aplikacji z pełną prezentacją.

Zamawianie grafik może ruszyć równolegle z etapem 1 — nic w szkielecie na nie
nie czeka.

## 10. Kryteria akceptacji

- `python3 build.py` kończy się kodem 0 i produkuje komplet stron: 4 na język
  (las, dwie aplikacje, kontakt) plus po jednej stronie dokumentów na każdy
  istniejący przekład. Dziś daje to **15 stron** — dokumenty istnieją w PL dla
  obu aplikacji i w DE dla Literek. Komplet 18 stron pojawi się, gdy dojdą
  brakujące przekłady dokumentów
- zero martwych linków wewnętrznych; każdy `hreflang` się rozwiązuje
- brak poziomego przewijania przy 320 px
- każda stacja osiągalna z klawiatury, widoczny fokus
- kontrast napisu na szyldzie ≥4.5:1
- ładunek początkowy <900 KB
- `prefers-reduced-motion` faktycznie wyłącza ruch
- zrzuty desktop (1440×900) i mobile (390×844) dla lasu w trzech językach

## 11. Poza zakresem

CMS, blog, newsletter, wyszukiwarka, tryb ciemny (nasłoneczniony las go nie
potrzebuje), analityka i baner cookie (brak śledzenia = brak banera),
lightbox do zrzutów (w wersji 1 statyczna siatka), mruganie sowy klatkami
(wymagałoby osobnego assetu powieki — ewentualne rozszerzenie).

## 12. Realizacja strony głównej — odstępstwa od sekcji 6 i 8

Data: 2026-09-09, po odbiorze makiety od właściciela.

**Jedna scena zamiast pięciu warstw.** Warstwy z sekcji 6 były renderowane
w różnych stylistykach (płaskie świerki, bryły 3D, malowana łąka, fotorealistyczne
paprocie) i złożone razem wyglądały jak kolaż. Zastąpione jednym spójnym kadrem
`scene-forest.webp` (1672×941) zamówionym w ChatGPT z makietą jako wzorcem.
Parallaksa z sekcji 6 odpada razem z warstwami.

**Kadr o stałych proporcjach zamiast pozycji procentowych na sztywno.** Wymóg
właściciela: „aplikacje powinny się skalować z tłem, mają być w tym samym
miejscu". Realizacja: `.stage` i `.frame` mają identyczny rozmiar liczony metodą
pokrycia (`--stage-w`/`--stage-h`), więc stacje nie wędrują względem ścieżek.
Jednostka `--u` to 1,1% szerokości kadru — cała typografia sceny skaluje się
razem z grafiką.

**Nagłówek i motto zakotwiczone w oknie, nie w kadrze.** Przy proporcjach 2:1
(np. 1440×720) pokrycie obcina kadr w pionie o ~5,5% z każdej strony i tytuł
wjeżdżał pod belkę nawigacji. Nagłówek dostaje własną jednostkę `--hu` liczoną
z realnie wolnej przestrzeni między belką a górą polany, więc kurczy się zamiast
kolidować z domkami.

**Dwie stacje zamiast pięciu z makiety.** Makieta pokazywała pięć aplikacji;
istnieją dwie. Plakietka „wkrótce" została wycofana na życzenie właściciela,
ale deska trzyma na nią zapas szerokości (`.tile-soon` zostaje w arkuszu).

**Budżet wagi.** Limit 180 KB na warstwę pełnej szerokości nie ma już
zastosowania przy jednej scenie — `scene-forest.webp` waży 238 KB przy q=76.
Wiążące pozostaje kryterium z sekcji 10: ładunek początkowy **609 KB** < 900 KB.

**Assety.** Sowy i domki zamawiane w ChatGPT z istniejącym assetem jako
wzorcem stylu (jeden obraz z kilkoma wariantami daje spójność, której osobne
prompty nie dają). Domki celowo różnią się bryłą i ustawieniem.
