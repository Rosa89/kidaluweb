# Kidalu — etap 1: szkielet witryny

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Postawić kidalu.com jako generowaną statyczną witrynę w trzech językach, z przeniesionymi dokumentami prawnymi pod stabilnymi adresami, i przygotować pipeline graficzny pod etap 2.

**Architecture:** Generator w Pythonie (Jinja2) czyta treści z JSON-ów i partiali HTML, renderuje komplet stron do `docs/`, skąd serwuje je GitHub Pages. Język jest prefiksem ścieżki, slugi są definiowane per język. Dostępność dokumentu w danym języku wynika z obecności pliku na dysku, nie z konfiguracji — brakujące tłumaczenie po prostu nie generuje strony i nie trafia do `hreflang`.

**Tech Stack:** Python 3.12.9 (`/Users/srosinski/venv/isys/bin/python3`), Jinja2, pytest, rembg + Pillow do obróbki grafik, `cwebp` (jest w systemie), GitHub Pages.

**Spec:** `superpowers/specs/2026-09-09-kidalu-web-design.md`

## Global Constraints

- Katalog wyjściowy to `docs/`; **nigdy** nie umieszczać tam niczego, co nie ma trafić na kidalu.com. Spec i plan mieszkają w `superpowers/`.
- Praca wyłącznie na gałęzi `kidalu-rebrand`. `main` serwuje żywą stronę pod codedriven.pl i do zakończenia migracji pozostaje nietknięty.
- Interpreter: `/Users/srosinski/venv/isys/bin/python3`. To jest domyślny `python3` w tym środowisku.
- Języki: `pl` (domyślny, bez prefiksu), `de`, `en`.
- Adresy dokumentów prawnych są nieodwracalne — trafiają do Google Play Console:
  `https://kidalu.com/czytanie-sylabami/dokumenty/`
  `https://kidalu.com/literki-i-cyferki/dokumenty/`
- Slugi: PL `czytanie-sylabami` / `literki-i-cyferki` / `kontakt` / `dokumenty`; DE `lesen-nach-silben` / `buchstaben-und-zahlen` / `kontakt` / `dokumente`; EN `reading-by-syllables` / `letters-and-numbers` / `contact` / `legal`.
- Identyfikatory aplikacji: `com.readbysyllables.app`, `com.literkiicyferki.app`.
- Marka na witrynie to wyłącznie „Kidalu". Ciąg „Mądre Dzieciaki" nie może wystąpić w żadnym wygenerowanym pliku.
- Paleta (tokeny CSS): `--paper:#FDF6E0` `--cream-2:#FCE8C7` `--wood:#994E21` `--wood-light:#CB8550` `--wood-dark:#6E3410` `--ink:#54240A` `--pine:#205740` `--pine-2:#2F7056` `--sky:#6FCCF3`.
- Kroje: Fredoka (nagłówki, szyldy), Nunito (tekst). Jeśli Task 1 wykaże brak `ąćęłńóśźż` lub `äöüß` — zamiana obu na Baloo 2.
- Budżet: warstwa pełnej szerokości ≤180 KB, obiekt ≤80 KB, ładunek początkowy <900 KB.
- Do panelu OVH i Google Play Console nie logujemy się. Wartości do wklejenia dostarczamy użytkownikowi.

---

## Struktura plików

| Plik | Odpowiedzialność |
|---|---|
| `build.py` | Jedyny punkt wejścia generatora: wczytanie treści, renderowanie, kopiowanie assetów |
| `content/{pl,de,en}.json` | Teksty, slugi i dane aplikacji dla jednego języka |
| `content/docs/{app}.{lang}.html` | Treść dokumentu prawnego, fragment HTML bez `<html>`/`<body>` |
| `src/templates/base.html.jinja` | Szkielet: `<head>`, nagłówek z logo, przełącznik języka, stopka |
| `src/templates/home.html.jinja` | Strona główna (w etapie 1 bez sceny) |
| `src/templates/app.html.jinja` | Podstrona aplikacji |
| `src/templates/docs.html.jinja` | Strona dokumentów prawnych |
| `src/templates/contact.html.jinja` | Kontakt |
| `src/assets/css/site.css` | Arkusz witryny, tokeny z palety |
| `src/assets/img/` | Grafiki gotowe do publikacji (webp) |
| `tools/prepare_asset.py` | Wycięcie tła, kadrowanie, konwersja do webp |
| `tools/check_links.py` | Walidacja linków wewnętrznych i `hreflang` w wyniku |
| `tests/test_build.py` | Testy generatora |
| `tests/test_links.py` | Testy walidatora |
| `requirements.txt` | Zależności |
| `docs/` | **Wynik generatora.** Nie edytować ręcznie |

---

### Task 1: Fundament generatora i strona główna PL

Zakłada instalację zależności, konfigurację testów i najcieńszy możliwy przebieg generatora — od JSON-a do pliku w `docs/`.

**Files:**
- Create: `requirements.txt`
- Create: `content/pl.json`
- Create: `src/templates/base.html.jinja`
- Create: `src/templates/home.html.jinja`
- Create: `src/assets/css/site.css`
- Create: `build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: nic (pierwsze zadanie)
- Produces: `build.build() -> list[Path]` zwraca listę zapisanych plików; `build.load_lang(lang: str) -> dict`; `build.prefix(lang: str) -> str`; stałe `build.LANGS: list[str]`, `build.DEFAULT_LANG: str`, `build.OUT: Path`, `build.SITE_HOST: str`

- [ ] **Step 1: Zależności i sprawdzenie krojów**

```bash
cd /Users/srosinski/Desktop/test/kidalu
cat > requirements.txt <<'EOF'
jinja2==3.1.4
pytest==8.3.3
EOF
python3 -m pip install -r requirements.txt

printf '\n# Artefakty Pythona\n__pycache__/\n.pytest_cache/\n' >> .gitignore
```

Otwórz https://fonts.google.com/specimen/Fredoka i https://fonts.google.com/specimen/Nunito, w polu podglądu wpisz `ąćęłńóśźż ĄĆĘŁŃÓŚŹŻ äöüß ÄÖÜ`. Jeśli którykolwiek znak renderuje się zastępczo — w `site.css` i w tym planie zamień `Fredoka` na `Baloo 2` (adres rodziny: `Baloo+2`), resztę zostaw.

- [ ] **Step 2: Napisz test, który ma się wywalić**

```python
# tests/test_build.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build


def test_buduje_strone_glowna_pl():
    written = build.build()
    index = build.OUT / "index.html"
    assert index in written
    html = index.read_text("utf-8")
    assert "Kidalu" in html
    assert '<html lang="pl"' in html


def test_nie_zostawia_starej_marki():
    build.build()
    for path in build.OUT.rglob("*.html"):
        assert "Mądre Dzieciaki" not in path.read_text("utf-8"), path
```

- [ ] **Step 3: Uruchom test i potwierdź, że nie przechodzi**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build'`

- [ ] **Step 4: Treść i szablony**

```bash
mkdir -p content src/templates src/assets/css tests
```

```json
// content/pl.json
{
  "lang": "pl",
  "site": {
    "brand": "Kidalu",
    "title": "Kidalu — aplikacje, które uczą bawiąc",
    "description": "Aplikacje edukacyjne dla dzieci 4–8 lat. Bez reklam, bez profilowania, bez śledzenia."
  },
  "slugs": {
    "czytanie": "czytanie-sylabami",
    "literki": "literki-i-cyferki",
    "kontakt": "kontakt",
    "docs": "dokumenty"
  },
  "nav": { "home": "Las", "contact": "Kontakt" },
  "home": {
    "headline": "Zajrzyj do lasu Kidalu",
    "intro": "Przy każdym domku czeka sowa z inną aplikacją. Bez reklam, bez profilowania, bez śledzenia poza aplikacją."
  },
  "footer": { "rights": "Kidalu" }
}
```

```jinja
{# src/templates/base.html.jinja #}
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}{{ c.site.title }}{% endblock %}</title>
<meta name="description" content="{% block description %}{{ c.site.description }}{% endblock %}">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600&family=Nunito:wght@400;600;700&display=swap">
<link rel="stylesheet" href="{{ asset('css/site.css') }}">
</head>
<body>
<header class="site-head">
  <a class="brand" href="{{ url('home') }}">{{ c.site.brand }}</a>
</header>
<main>{% block content %}{% endblock %}</main>
<footer class="site-foot">
  <span>© 2026 {{ c.footer.rights }}</span>
</footer>
</body>
</html>
```

```jinja
{# src/templates/home.html.jinja #}
{% extends "base.html.jinja" %}
{% block content %}
<section class="hero">
  <h1>{{ c.home.headline }}</h1>
  <p>{{ c.home.intro }}</p>
</section>
{% endblock %}
```

```css
/* src/assets/css/site.css */
:root{
  --paper:#FDF6E0; --cream-2:#FCE8C7;
  --wood:#994E21; --wood-light:#CB8550; --wood-dark:#6E3410;
  --ink:#54240A; --pine:#205740; --pine-2:#2F7056; --sky:#6FCCF3;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:Nunito,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  font-size:17px; line-height:1.7;
}
h1,h2,h3,.brand{font-family:Fredoka,system-ui,sans-serif; font-weight:600; letter-spacing:-.015em}
.site-head{padding:1.25rem 1.5rem}
.brand{font-size:1.5rem; color:var(--wood-dark); text-decoration:none}
main{max-width:960px; margin:0 auto; padding:0 1.5rem}
.hero h1{font-size:clamp(2rem,5vw,3rem); margin:0 0 .75rem; text-wrap:balance}
.site-foot{max-width:960px; margin:4rem auto 0; padding:1.5rem; color:var(--wood-dark); font-size:.9rem}
:focus-visible{outline:2px solid var(--pine); outline-offset:3px}
```

- [ ] **Step 5: Napisz generator**

```python
#!/usr/bin/env python3
"""Generator witryny kidalu.com. Wejście: content/ + src/. Wyjście: docs/."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "src" / "templates"
ASSETS = ROOT / "src" / "assets"
OUT = ROOT / "docs"

LANGS = ["pl", "de", "en"]
DEFAULT_LANG = "pl"
SITE_HOST = "https://kidalu.com"


def load_lang(lang: str) -> dict:
    return json.loads((CONTENT / f"{lang}.json").read_text("utf-8"))


def prefix(lang: str) -> str:
    """Prefiks ścieżki dla języka. Domyślny język siedzi w korzeniu."""
    return "" if lang == DEFAULT_LANG else f"/{lang}"


def page_urls(c: dict, lang: str) -> dict[str, str]:
    """Mapa klucz strony -> adres URL, dla jednego języka."""
    s = c["slugs"]
    p = prefix(lang)
    return {"home": f"{p}/"}


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _write(url: str, html: str) -> Path:
    target = OUT / url.strip("/") / "index.html" if url.strip("/") else OUT / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, "utf-8")
    return target


def build() -> list[Path]:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copytree(ASSETS, OUT / "assets")

    env = _env()
    written: list[Path] = []

    for lang in LANGS:
        path = CONTENT / f"{lang}.json"
        if not path.exists():
            continue
        c = load_lang(lang)
        urls = page_urls(c, lang)
        ctx = {
            "lang": lang,
            "c": c,
            "url": lambda key, u=urls: u[key],
            "asset": lambda rel: f"/assets/{rel}",
        }
        written.append(_write(urls["home"], env.get_template("home.html.jinja").render(**ctx)))

    return written


if __name__ == "__main__":
    files = build()
    print(f"zapisano {len(files)} stron")
```

- [ ] **Step 6: Uruchom testy i potwierdź, że przechodzą**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: PASS, oba testy

- [ ] **Step 7: Commit**

```bash
git add requirements.txt content/pl.json src/ build.py tests/test_build.py
git commit -m "feat: generator witryny i strona główna PL"
```

---

### Task 2: Trzy języki, slugi per język, hreflang i przełącznik

**Files:**
- Create: `content/de.json`, `content/en.json`
- Modify: `build.py` — `page_urls`, `build`, nowa `alternates`
- Modify: `src/templates/base.html.jinja` — `hreflang` i przełącznik
- Modify: `src/assets/css/site.css` — style przełącznika
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `build.load_lang`, `build.prefix`, `build.LANGS`, `build.OUT`
- Produces: `build.page_urls(c: dict, lang: str) -> dict[str, str]` z kluczami `home`, `czytanie`, `czytanie_docs`, `literki`, `literki_docs`, `kontakt`; `build.alternates(key: str) -> dict[str, str]` mapa język → URL, wyłącznie dla języków, w których strona istnieje

- [ ] **Step 1: Napisz testy, które mają się wywalić**

```python
# dopisz do tests/test_build.py

def test_generuje_trzy_wersje_jezykowe():
    build.build()
    assert (build.OUT / "index.html").exists()
    assert (build.OUT / "de" / "index.html").exists()
    assert (build.OUT / "en" / "index.html").exists()


def test_slugi_roznia_sie_miedzy_jezykami():
    pl = build.page_urls(build.load_lang("pl"), "pl")
    de = build.page_urls(build.load_lang("de"), "de")
    en = build.page_urls(build.load_lang("en"), "en")
    assert pl["czytanie"] == "/czytanie-sylabami/"
    assert de["czytanie"] == "/de/lesen-nach-silben/"
    assert en["czytanie"] == "/en/reading-by-syllables/"
    assert pl["literki_docs"] == "/literki-i-cyferki/dokumenty/"
    assert de["literki_docs"] == "/de/buchstaben-und-zahlen/dokumente/"
    assert en["literki_docs"] == "/en/letters-and-numbers/legal/"


def test_hreflang_wskazuje_istniejace_strony():
    build.build()
    html = (build.OUT / "index.html").read_text("utf-8")
    for lang, url in build.alternates("home").items():
        assert f'hreflang="{lang}"' in html
        target = build.OUT / url.strip("/") / "index.html" if url.strip("/") else build.OUT / "index.html"
        assert target.exists(), f"hreflang {lang} wskazuje na nieistniejący {target}"
    assert 'hreflang="x-default"' in html
```

- [ ] **Step 2: Uruchom i potwierdź, że nie przechodzą**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: FAIL — `KeyError: 'czytanie'` oraz brak `de/index.html`

- [ ] **Step 3: Treści DE i EN**

```json
// content/de.json
{
  "lang": "de",
  "site": {
    "brand": "Kidalu",
    "title": "Kidalu — Apps, die spielerisch lehren",
    "description": "Lern-Apps für Kinder von 4 bis 8 Jahren. Keine Werbung, kein Profiling, kein Tracking."
  },
  "slugs": {
    "czytanie": "lesen-nach-silben",
    "literki": "buchstaben-und-zahlen",
    "kontakt": "kontakt",
    "docs": "dokumente"
  },
  "nav": { "home": "Wald", "contact": "Kontakt" },
  "home": {
    "headline": "Schau in den Kidalu-Wald",
    "intro": "An jedem Häuschen wartet eine Eule mit einer anderen App. Keine Werbung, kein Profiling, kein Tracking außerhalb der App."
  },
  "footer": { "rights": "Kidalu" }
}
```

```json
// content/en.json
{
  "lang": "en",
  "site": {
    "brand": "Kidalu",
    "title": "Kidalu — apps that teach through play",
    "description": "Learning apps for children aged 4 to 8. No ads, no profiling, no tracking."
  },
  "slugs": {
    "czytanie": "reading-by-syllables",
    "literki": "letters-and-numbers",
    "kontakt": "contact",
    "docs": "legal"
  },
  "nav": { "home": "Forest", "contact": "Contact" },
  "home": {
    "headline": "Step into the Kidalu forest",
    "intro": "An owl waits at every little house, each with a different app. No ads, no profiling, no tracking outside the app."
  },
  "footer": { "rights": "Kidalu" }
}
```

- [ ] **Step 4: Rozbuduj generator**

W `build.py` zastąp `page_urls` i dopisz `alternates`:

```python
def page_urls(c: dict, lang: str) -> dict[str, str]:
    """Mapa klucz strony -> adres URL, dla jednego języka."""
    s = c["slugs"]
    p = prefix(lang)
    return {
        "home": f"{p}/",
        "czytanie": f"{p}/{s['czytanie']}/",
        "czytanie_docs": f"{p}/{s['czytanie']}/{s['docs']}/",
        "literki": f"{p}/{s['literki']}/",
        "literki_docs": f"{p}/{s['literki']}/{s['docs']}/",
        "kontakt": f"{p}/{s['kontakt']}/",
    }


def available_langs() -> list[str]:
    return [l for l in LANGS if (CONTENT / f"{l}.json").exists()]


def alternates(key: str) -> dict[str, str]:
    """Adresy tej samej strony w pozostałych językach — tylko te, które istnieją."""
    out: dict[str, str] = {}
    for l in available_langs():
        urls = page_urls(load_lang(l), l)
        if key in urls:
            out[l] = urls[key]
    return out
```

W `build()` przekaż do kontekstu klucz strony i alternatywy:

```python
        ctx = {
            "lang": lang,
            "c": c,
            "url": lambda key, u=urls: u[key],
            "asset": lambda rel: f"/assets/{rel}",
            "page_key": "home",
            "alternates": alternates("home"),
            "langs": available_langs(),
        }
```

- [ ] **Step 5: hreflang i przełącznik w szablonie**

W `base.html.jinja` dodaj przed `</head>`:

```jinja
{% for l, u in alternates.items() %}
<link rel="alternate" hreflang="{{ l }}" href="{{ site_host }}{{ u }}">
{% endfor %}
<link rel="alternate" hreflang="x-default" href="{{ site_host }}{{ alternates['pl'] }}">
```

I w `<header class="site-head">`, po `.brand`:

```jinja
  <nav class="langs" aria-label="Język">
    {% for l, u in alternates.items() %}
    <a href="{{ u }}"{% if l == lang %} aria-current="true"{% endif %}>{{ l|upper }}</a>
    {% endfor %}
  </nav>
```

W `build()` dopisz do `ctx`: `"site_host": SITE_HOST`. W `site.css` dopisz:

```css
.site-head{display:flex; align-items:center; justify-content:space-between; gap:1rem}
.langs{display:flex; gap:.4rem; font-size:.82rem; font-weight:700}
.langs a{
  color:var(--wood-dark); text-decoration:none; padding:.2rem .5rem;
  border:1px solid var(--wood-light); border-radius:999px;
}
.langs a[aria-current]{background:var(--wood); color:var(--paper); border-color:var(--wood)}
```

- [ ] **Step 6: Uruchom testy**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: PASS, pięć testów

- [ ] **Step 7: Commit**

```bash
git add content/ src/ build.py tests/test_build.py
git commit -m "feat: trzy wersje językowe, slugi per język i hreflang"
```

---

### Task 3: Podstrony aplikacji

**Files:**
- Modify: `content/{pl,de,en}.json` — sekcja `apps`
- Create: `src/templates/app.html.jinja`
- Modify: `build.py` — renderowanie podstron
- Modify: `src/assets/css/site.css`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `build.page_urls`, `build.alternates`, `build.available_langs`
- Produces: `build.APPS: dict[str, str]` mapa klucz aplikacji → identyfikator pakietu; `build.play_url(app_key: str) -> str`

- [ ] **Step 1: Napisz testy, które mają się wywalić**

```python
# dopisz do tests/test_build.py

def test_podstrony_aplikacji_we_wszystkich_jezykach():
    build.build()
    for lang in build.available_langs():
        urls = build.page_urls(build.load_lang(lang), lang)
        for key in ("czytanie", "literki"):
            target = build.OUT / urls[key].strip("/") / "index.html"
            assert target.exists(), target


def test_podstrona_linkuje_do_wlasciwej_aplikacji_w_play():
    build.build()
    czytanie = (build.OUT / "czytanie-sylabami" / "index.html").read_text("utf-8")
    literki = (build.OUT / "literki-i-cyferki" / "index.html").read_text("utf-8")
    assert "id=com.readbysyllables.app" in czytanie
    assert "id=com.literkiicyferki.app" in literki
    assert "id=com.literkiicyferki.app" not in czytanie
```

- [ ] **Step 2: Uruchom i potwierdź, że nie przechodzą**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: FAIL — brak `docs/czytanie-sylabami/index.html`

- [ ] **Step 3: Dane aplikacji w treściach**

Dopisz do `content/pl.json` na poziomie głównym:

```json
  "apps": {
    "czytanie": {
      "name": "Nauka czytania sylabami",
      "sign": "Czytam",
      "tagline": "Dziecko czyta samo, sylaba po sylabie.",
      "features": [
        "Kolorowanie sylab, które prowadzi wzrok przez wyraz",
        "Ponad sto tekstów, w tym lektury z Wolnych Lektur",
        "Panel rodzica z postępami dziecka"
      ],
      "docs_label": "Polityka prywatności i regulamin"
    },
    "literki": {
      "name": "Literki i Cyferki",
      "sign": "Piszę",
      "tagline": "Nauka pisania liter i cyfr palcem po ekranie.",
      "features": [
        "Kształt każdej litery pokazany krok po kroku",
        "Ćwiczenia liter i cyfr dopasowane do wieku",
        "Panel rodzica z postępami dziecka"
      ],
      "docs_label": "Polityka prywatności i informacje"
    }
  }
```

Do `content/de.json`:

```json
  "apps": {
    "czytanie": {
      "name": "Lesen nach Silben",
      "sign": "Ich lese",
      "tagline": "Das Kind liest selbst, Silbe für Silbe.",
      "features": [
        "Farbige Silben führen den Blick durch das Wort",
        "Über hundert Texte zum Lesen",
        "Elternbereich mit dem Lernfortschritt"
      ],
      "docs_label": "Datenschutz und Nutzungsbedingungen"
    },
    "literki": {
      "name": "Buchstaben und Zahlen",
      "sign": "Ich schreibe",
      "tagline": "Buchstaben und Zahlen mit dem Finger auf dem Bildschirm schreiben.",
      "features": [
        "Jede Buchstabenform Schritt für Schritt gezeigt",
        "Übungen passend zum Alter des Kindes",
        "Elternbereich mit dem Lernfortschritt"
      ],
      "docs_label": "Datenschutz und Informationen"
    }
  }
```

Do `content/en.json`:

```json
  "apps": {
    "czytanie": {
      "name": "Reading by Syllables",
      "sign": "I read",
      "tagline": "Your child reads on their own, one syllable at a time.",
      "features": [
        "Coloured syllables guide the eye through each word",
        "More than a hundred texts to read",
        "A parent panel showing progress"
      ],
      "docs_label": "Privacy policy and terms"
    },
    "literki": {
      "name": "Letters and Numbers",
      "sign": "I write",
      "tagline": "Writing letters and numbers with a finger on the screen.",
      "features": [
        "Every letter shape shown stroke by stroke",
        "Exercises matched to the child's age",
        "A parent panel showing progress"
      ],
      "docs_label": "Privacy policy and information"
    }
  }
```

- [ ] **Step 4: Szablon podstrony**

```jinja
{# src/templates/app.html.jinja #}
{% extends "base.html.jinja" %}
{% block title %}{{ app.name }} — {{ c.site.brand }}{% endblock %}
{% block description %}{{ app.tagline }}{% endblock %}
{% block content %}
<article class="app">
  <h1>{{ app.name }}</h1>
  <p class="tagline">{{ app.tagline }}</p>
  <ul class="features">
    {% for f in app.features %}
    <li>{{ f }}</li>
    {% endfor %}
  </ul>
  <p class="cta">
    <a class="play" href="{{ play_url }}" rel="noopener">Google Play</a>
  </p>
{% if docs_url %}
  <p><a href="{{ docs_url }}">{{ app.docs_label }}</a></p>
{% endif %}
</article>
{% endblock %}
```

- [ ] **Step 5: Renderowanie w generatorze**

W `build.py` dopisz po stałych:

```python
APPS = {
    "czytanie": "com.readbysyllables.app",
    "literki": "com.literkiicyferki.app",
}


def play_url(app_key: str) -> str:
    return f"https://play.google.com/store/apps/details?id={APPS[app_key]}"
```

W `build()`, wewnątrz pętli po językach, po zapisaniu strony głównej:

```python
        for app_key in APPS:
            written.append(_write(urls[app_key], env.get_template("app.html.jinja").render(
                **{**ctx,
                   "page_key": app_key,
                   "alternates": alternates(app_key),
                   "app": c["apps"][app_key],
                   "play_url": play_url(app_key),
                   "docs_url": None},
            )))
```

Dokumenty powstaną dopiero w Tasku 4, więc `docs_url` jest tu `None` i odnośnik
się nie renderuje. Gdyby renderował się bezwarunkowo, walidator z Taska 6
zgłosiłby martwy odnośnik w każdym języku pozbawionym tłumaczenia dokumentu.

W `site.css` dopisz:

```css
.app .tagline{font-size:1.15rem; color:var(--wood-dark); margin:0 0 1.5rem}
.features{padding-left:1.2rem; margin:0 0 1.75rem}
.features li{margin:.4rem 0}
.play{
  display:inline-block; background:var(--wood); color:var(--paper);
  text-decoration:none; font-weight:700; padding:.7rem 1.4rem; border-radius:999px;
}
.play:hover{background:var(--wood-dark)}
```

- [ ] **Step 6: Uruchom testy**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: PASS, siedem testów

- [ ] **Step 7: Commit**

```bash
git add content/ src/ build.py tests/test_build.py
git commit -m "feat: podstrony aplikacji z linkiem do Google Play"
```

---

### Task 4: Dokumenty prawne przeniesione pod nowe adresy

Dostępność dokumentu w danym języku wynika z obecności pliku `content/docs/{app}.{lang}.html`. Dziś istnieją trzy: `czytanie.pl`, `literki.pl`, `literki.de`. Brakujące tłumaczenia dojdą później bez zmiany adresów.

**Files:**
- Create: `content/docs/czytanie.pl.html`, `content/docs/literki.pl.html`, `content/docs/literki.de.html`
- Create: `src/templates/docs.html.jinja`
- Modify: `build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `build.APPS`, `build.page_urls`, `build.alternates`
- Produces: `build.doc_path(app_key: str, lang: str) -> Path`; `build.doc_langs(app_key: str) -> list[str]`

- [ ] **Step 1: Napisz testy, które mają się wywalić**

```python
# dopisz do tests/test_build.py

PLAY_URLS = [
    "czytanie-sylabami/dokumenty",
    "literki-i-cyferki/dokumenty",
]


def test_adresy_wymagane_przez_play_istnieja():
    build.build()
    for rel in PLAY_URLS:
        target = build.OUT / rel / "index.html"
        assert target.exists(), f"{rel} to adres podany w Play Console"


def test_dokument_zawiera_polityke_prywatnosci():
    build.build()
    html = (build.OUT / "czytanie-sylabami" / "dokumenty" / "index.html").read_text("utf-8")
    assert "Polityka prywatności" in html
    assert "Administrator danych" in html


def test_niemiecka_wersja_literek_zachowana():
    build.build()
    target = build.OUT / "de" / "buchstaben-und-zahlen" / "dokumente" / "index.html"
    assert target.exists()
    assert "Datenschutzerklärung" in target.read_text("utf-8")


def test_brakujace_tlumaczenie_nie_generuje_strony_ani_hreflang():
    build.build()
    # czytanie nie ma wersji DE — strona nie powstaje
    assert not (build.OUT / "de" / "lesen-nach-silben" / "dokumente" / "index.html").exists()
    # i nie pojawia się w alternatywach
    assert "de" not in build.alternates("czytanie_docs")
```

- [ ] **Step 2: Uruchom i potwierdź, że nie przechodzą**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: FAIL — brak `docs/czytanie-sylabami/dokumenty/index.html`

- [ ] **Step 3: Wyodrębnij treść z istniejących stron**

Stare strony mają treść wewnątrz `<main>`. Wyciągnij ją do partiali, zachowując strukturę nagłówków:

```bash
mkdir -p content/docs
python3 - <<'EOF'
import re
from pathlib import Path

src = {
    "czytanie.pl": "nauka-czytania-sylabami/index.html",
    "literki.pl": "literki-i-cyferki/index.html",
    "literki.de": "literki-i-cyferki/de/index.html",
}
for name, path in src.items():
    html = Path(path).read_text("utf-8")
    m = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
    body = m.group(1) if m else html
    # stara marka nie może przejść do nowej witryny
    body = body.replace("Mądre Dzieciaki", "Kidalu").replace("codedriven.pl", "kidalu.com")
    Path(f"content/docs/{name}.html").write_text(body.strip() + "\n", "utf-8")
    print(f"{name}: {len(body)} znaków")
EOF
```

Otwórz każdy z trzech plików i sprawdź, że zaczyna się od nagłówka dokumentu, nie od fragmentu nawigacji. Jeśli `<main>` nie istniał w źródle, wytnij ręcznie zakres od pierwszego `<h1>` do końca treści.

- [ ] **Step 4: Szablon i generator**

```jinja
{# src/templates/docs.html.jinja #}
{% extends "base.html.jinja" %}
{% block title %}{{ app.name }} — {{ app.docs_label }}{% endblock %}
{% block description %}{{ app.docs_label }} — {{ app.name }}{% endblock %}
{% block content %}
<article class="docs">
{{ doc_html }}
</article>
{% endblock %}
```

Treść dokumentu jest zaufanym HTML-em z naszego repo, więc wstrzykujemy ją bez escapowania. W `build.py` dopisz:

```python
def doc_path(app_key: str, lang: str) -> Path:
    return CONTENT / "docs" / f"{app_key}.{lang}.html"


def doc_langs(app_key: str) -> list[str]:
    return [l for l in available_langs() if doc_path(app_key, l).exists()]
```

Rozszerz `alternates`, żeby dla kluczy dokumentów pytała o istnienie pliku:

```python
def alternates(key: str) -> dict[str, str]:
    """Adresy tej samej strony w pozostałych językach — tylko te, które istnieją."""
    out: dict[str, str] = {}
    for l in available_langs():
        if key.endswith("_docs"):
            app_key = key[: -len("_docs")]
            if not doc_path(app_key, l).exists():
                continue
        urls = page_urls(load_lang(l), l)
        if key in urls:
            out[l] = urls[key]
    return out
```

W `build()`, wewnątrz pętli po aplikacjach, **poniżej** renderowania podstrony
aplikacji z Taska 3:

```python
            if lang in doc_langs(app_key):
                from markupsafe import Markup
                written.append(_write(urls[docs_key], env.get_template("docs.html.jinja").render(
                    **{**ctx,
                       "page_key": docs_key,
                       "alternates": alternates(docs_key),
                       "app": c["apps"][app_key],
                       "doc_html": Markup(doc_path(app_key, lang).read_text("utf-8"))},
                )))
```

Przenieś `from markupsafe import Markup` na górę pliku, do pozostałych importów.

Na koniec podłącz odnośnik do dokumentu na podstronie aplikacji. Ciało pętli po
aplikacjach musi zaczynać się od wyliczenia klucza dokumentu — inaczej użycie go
w renderowaniu podstrony wywoła `NameError` na pierwszym obiegu:

```python
        for app_key in APPS:
            docs_key = f"{app_key}_docs"
            docs_url = urls[docs_key] if lang in doc_langs(app_key) else None
```

a w renderowaniu podstrony z Taska 3 zamień `"docs_url": None` na:

```python
                   "docs_url": docs_url},
```

Dzięki temu podstrona linkuje do dokumentu wyłącznie w tych językach, w których
dokument faktycznie istnieje. Kolejność w ciele pętli jest więc taka:
wyliczenie `docs_key` i `docs_url`, render podstrony aplikacji, render dokumentu.

- [ ] **Step 5: Uruchom testy**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: PASS, jedenaście testów

- [ ] **Step 6: Commit**

```bash
git add content/docs/ src/templates/docs.html.jinja build.py tests/test_build.py
git commit -m "feat: dokumenty prawne pod stabilnymi adresami dla Play"
```

---

### Task 5: Kontakt, sitemap, robots, CNAME i .nojekyll

**Files:**
- Modify: `content/{pl,de,en}.json` — sekcja `contact`
- Create: `src/templates/contact.html.jinja`
- Modify: `build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `build.page_urls`, `build.alternates`, `build.SITE_HOST`
- Produces: `build.write_meta(written: list[Path]) -> None` zapisuje `sitemap.xml`, `robots.txt`, `CNAME`, `.nojekyll`

- [ ] **Step 1: Napisz testy, które mają się wywalić**

```python
# dopisz do tests/test_build.py

def test_kontakt_we_wszystkich_jezykach():
    build.build()
    for lang in build.available_langs():
        urls = build.page_urls(build.load_lang(lang), lang)
        assert (build.OUT / urls["kontakt"].strip("/") / "index.html").exists()


def test_cname_i_nojekyll():
    build.build()
    assert (build.OUT / "CNAME").read_text("utf-8").strip() == "kidalu.com"
    assert (build.OUT / ".nojekyll").exists()


def test_sitemap_wymienia_kazda_wygenerowana_strone():
    written = build.build()
    sitemap = (build.OUT / "sitemap.xml").read_text("utf-8")
    strony = [p for p in written if p.name == "index.html"]
    assert len(strony) > 0
    for p in strony:
        rel = p.parent.relative_to(build.OUT).as_posix()
        url = build.SITE_HOST + ("/" if rel == "." else f"/{rel}/")
        assert f"<loc>{url}</loc>" in sitemap, url
```

- [ ] **Step 2: Uruchom i potwierdź, że nie przechodzą**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: FAIL — brak `docs/kontakt/index.html` i `docs/CNAME`

- [ ] **Step 3: Treści kontaktu**

Do `content/pl.json`:

```json
  "contact": {
    "headline": "Napisz do nas",
    "body": "Pytania o prywatność, dane dziecka albo współpracę? Odpowiadamy na wiadomości.",
    "email": "sebastian.rosinski.1989@gmail.com"
  }
```

Do `content/de.json`:

```json
  "contact": {
    "headline": "Schreiben Sie uns",
    "body": "Fragen zum Datenschutz, zu den Daten Ihres Kindes oder zur Zusammenarbeit? Wir antworten auf jede Nachricht.",
    "email": "sebastian.rosinski.1989@gmail.com"
  }
```

Do `content/en.json`:

```json
  "contact": {
    "headline": "Get in touch",
    "body": "Questions about privacy, your child's data, or working together? We answer every message.",
    "email": "sebastian.rosinski.1989@gmail.com"
  }
```

- [ ] **Step 4: Szablon kontaktu**

```jinja
{# src/templates/contact.html.jinja #}
{% extends "base.html.jinja" %}
{% block title %}{{ c.contact.headline }} — {{ c.site.brand }}{% endblock %}
{% block description %}{{ c.contact.body }}{% endblock %}
{% block content %}
<article class="contact">
  <h1>{{ c.contact.headline }}</h1>
  <p>{{ c.contact.body }}</p>
  <p><a class="play" href="mailto:{{ c.contact.email }}">{{ c.contact.email }}</a></p>
</article>
{% endblock %}
```

- [ ] **Step 5: Generator — kontakt i pliki towarzyszące**

W `build()`, w pętli po językach, po podstronach aplikacji:

```python
        written.append(_write(urls["kontakt"], env.get_template("contact.html.jinja").render(
            **{**ctx, "page_key": "kontakt", "alternates": alternates("kontakt")},
        )))
```

I nowa funkcja, wołana na końcu `build()` przez `write_meta(written)`:

```python
def write_meta(written: list[Path]) -> None:
    (OUT / "CNAME").write_text("kidalu.com\n", "utf-8")
    (OUT / ".nojekyll").write_text("", "utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_HOST}/sitemap.xml\n", "utf-8"
    )

    locs = []
    for p in sorted(written):
        if p.name != "index.html":
            continue
        rel = p.parent.relative_to(OUT).as_posix()
        url = SITE_HOST + ("/" if rel == "." else f"/{rel}/")
        locs.append(f"  <url><loc>{url}</loc></url>")

    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(locs)
        + "\n</urlset>\n",
        "utf-8",
    )
```

W `build()` przed `return written` dodaj `write_meta(written)`.

- [ ] **Step 6: Uruchom testy**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: PASS, czternaście testów

- [ ] **Step 7: Commit**

```bash
git add content/ src/templates/contact.html.jinja build.py tests/test_build.py
git commit -m "feat: kontakt, sitemap, robots, CNAME i .nojekyll"
```

---

### Task 6: Walidator linków

**Files:**
- Create: `tools/check_links.py`
- Test: `tests/test_links.py`

**Interfaces:**
- Consumes: `build.OUT`, `build.build`
- Produces: `tools.check_links.check(root: Path) -> list[str]` zwraca listę opisów zepsutych odnośników; pusta lista oznacza brak błędów

- [ ] **Step 1: Napisz testy, które mają się wywalić**

```python
# tests/test_links.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build
from tools.check_links import check


def test_wykrywa_zepsuty_link(tmp_path):
    (tmp_path / "index.html").write_text(
        '<a href="/nie-ma-mnie/">x</a>', "utf-8"
    )
    problems = check(tmp_path)
    assert any("/nie-ma-mnie/" in p for p in problems)


def test_zbudowana_witryna_nie_ma_zepsutych_linkow():
    build.build()
    problems = check(build.OUT)
    assert problems == [], "\n".join(problems)


# Inwentarz: 4 strony na język plus po jednej stronie dokumentów na każdy
# istniejący przekład. Gdy dojdzie tłumaczenie, dopisz je tutaj — test ma
# wyłapać zarówno stronę, która zniknęła, jak i taką, która pojawiła się
# przez przypadek.
OCZEKIWANE = {
    "index.html",
    "czytanie-sylabami/index.html",
    "czytanie-sylabami/dokumenty/index.html",
    "literki-i-cyferki/index.html",
    "literki-i-cyferki/dokumenty/index.html",
    "kontakt/index.html",
    "de/index.html",
    "de/lesen-nach-silben/index.html",
    "de/buchstaben-und-zahlen/index.html",
    "de/buchstaben-und-zahlen/dokumente/index.html",
    "de/kontakt/index.html",
    "en/index.html",
    "en/reading-by-syllables/index.html",
    "en/letters-and-numbers/index.html",
    "en/contact/index.html",
}


def test_inwentarz_stron_zgadza_sie_co_do_jednej():
    build.build()
    faktyczne = {
        p.relative_to(build.OUT).as_posix()
        for p in build.OUT.rglob("index.html")
    }
    assert faktyczne == OCZEKIWANE, (
        f"brakuje: {sorted(OCZEKIWANE - faktyczne)}\n"
        f"nadmiarowe: {sorted(faktyczne - OCZEKIWANE)}"
    )
```

Piętnaście stron: cztery na każdy z trzech języków plus trzy strony dokumentów
(PL obu aplikacji, DE Literek). Osiemnaście będzie, gdy dojdą brakujące przekłady
dokumentów — wtedy wystarczy dopisać adresy do `OCZEKIWANE`.

- [ ] **Step 2: Uruchom i potwierdź, że nie przechodzą**

Run: `python3 -m pytest tests/test_links.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 3: Napisz walidator**

```bash
mkdir -p tools && touch tools/__init__.py
```

```python
# tools/check_links.py
"""Sprawdza, czy każdy wewnętrzny odnośnik i hreflang w zbudowanej witrynie
wskazuje na istniejący plik."""
from __future__ import annotations

import re
import sys
from pathlib import Path

HREF = re.compile(r'(?:href|src)="([^"]+)"')


def _resolve(root: Path, url: str) -> Path | None:
    """Zamienia adres na plik na dysku. None oznacza adres, którego nie sprawdzamy."""
    if url.startswith(("http://", "https://", "mailto:", "#", "data:")):
        return None
    path = url.split("#")[0].split("?")[0]
    if not path.startswith("/"):
        return None
    target = root / path.lstrip("/")
    return target / "index.html" if path.endswith("/") else target


def check(root: Path) -> list[str]:
    problems: list[str] = []
    for page in sorted(root.rglob("*.html")):
        html = page.read_text("utf-8")
        for url in HREF.findall(html):
            target = _resolve(root, url)
            if target is not None and not target.exists():
                problems.append(f"{page.relative_to(root)} → {url} (brak {target})")
    return problems


if __name__ == "__main__":
    found = check(Path(sys.argv[1] if len(sys.argv) > 1 else "docs"))
    for p in found:
        print(p)
    print(f"zepsutych odnośników: {len(found)}")
    sys.exit(1 if found else 0)
```

Adres `https://kidalu.com/...` w `hreflang` jest bezwzględny, więc walidator go pomija — jego poprawność pokrywa `test_hreflang_wskazuje_istniejace_strony` z Taska 2.

- [ ] **Step 4: Uruchom testy**

Run: `python3 -m pytest tests/ -v`
Expected: PASS, siedemnaście testów

- [ ] **Step 5: Commit**

```bash
git add tools/ tests/test_links.py
git commit -m "feat: walidator linków wewnętrznych"
```

---

### Task 7: Pipeline graficzny i logo w witrynie

**Files:**
- Modify: `requirements.txt`
- Create: `tools/prepare_asset.py`
- Create: `src/assets/img/logo-kidalu.webp` (wynik narzędzia)
- Modify: `src/templates/base.html.jinja`, `src/assets/css/site.css`
- Test: `tests/test_prepare_asset.py`

**Interfaces:**
- Consumes: nic z wcześniejszych zadań
- Produces: `tools.prepare_asset.prepare(src: Path, dst: Path, width: int | None = None, quality: int = 82) -> dict` zwraca `{"size": int, "bytes": int, "alpha": bool}`

- [ ] **Step 1: Zależności**

```bash
cd /Users/srosinski/Desktop/test/kidalu
cat >> requirements.txt <<'EOF'
rembg==2.0.59
onnxruntime==1.19.2
Pillow==12.2.0
EOF
python3 -m pip install -r requirements.txt
```

Pierwsze uruchomienie `rembg` pobiera model u2net (ok. 176 MB) do `~/.u2net/`. To jednorazowe.

- [ ] **Step 2: Napisz test, który ma się wywalić**

```python
# tests/test_prepare_asset.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image

from tools.prepare_asset import prepare

ZRODLO = Path("/Users/srosinski/Downloads/Gemini_Generated_Image_gspb2dgspb2dgspb.jpeg")


def test_wycina_tlo_i_miesci_sie_w_budzecie(tmp_path):
    assert ZRODLO.exists(), "sowa Literek jest materiałem wyjściowym tego testu"
    out = tmp_path / "owl.webp"
    info = prepare(ZRODLO, out, width=1024)

    assert out.exists()
    assert info["alpha"] is True, "tło nie zostało wycięte"
    assert info["bytes"] <= 80 * 1024, f"obiekt waży {info['bytes']} B, budżet to 80 KB"

    im = Image.open(out)
    assert im.mode == "RGBA"
    assert im.width == 1024
    # rogi muszą być przezroczyste po wycięciu i przycięciu
    for xy in ((0, 0), (im.width - 1, 0)):
        assert im.getpixel(xy)[3] == 0, f"róg {xy} nie jest przezroczysty"
```

- [ ] **Step 3: Uruchom i potwierdź, że nie przechodzi**

Run: `python3 -m pytest tests/test_prepare_asset.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.prepare_asset'`

- [ ] **Step 4: Napisz narzędzie**

```python
# tools/prepare_asset.py
"""Zamienia surową grafikę z Gemini na asset gotowy do publikacji:
wycina tło, czyści krawędź, przycina do zawartości, skaluje i zapisuje webp."""
from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image, ImageFilter


def _cutout(im: Image.Image) -> Image.Image:
    from rembg import remove

    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return Image.open(io.BytesIO(remove(buf.getvalue()))).convert("RGBA")


def _clean_edge(im: Image.Image) -> Image.Image:
    """Erozja alfy o 1 px i lekkie wtopienie — zdejmuje jasną obwódkę po tle."""
    alpha = im.getchannel("A")
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.5))
    im.putalpha(alpha)
    return im


def prepare(src: Path, dst: Path, width: int | None = None, quality: int = 82) -> dict:
    im = Image.open(src).convert("RGBA")
    im = _clean_edge(_cutout(im))

    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)

    if width and im.width != width:
        height = round(im.height * width / im.width)
        im = im.resize((width, height), Image.LANCZOS)

    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, format="WEBP", quality=quality, method=6)

    lo, hi = im.getchannel("A").getextrema()
    return {"size": im.size, "bytes": dst.stat().st_size, "alpha": lo == 0 and hi == 255}


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    w = int(sys.argv[3]) if len(sys.argv) > 3 else None
    info = prepare(src, dst, width=w)
    print(f"{dst}: {info['size'][0]}×{info['size'][1]}, {info['bytes'] / 1024:.0f} KB, alpha={info['alpha']}")
```

- [ ] **Step 5: Uruchom test**

Run: `python3 -m pytest tests/test_prepare_asset.py -v`
Expected: PASS

Jeśli `bytes` przekracza budżet, obniż `quality` do 78 i uruchom ponownie.

- [ ] **Step 6: Przygotuj logo i wstaw je do nagłówka**

```bash
python3 tools/prepare_asset.py assets-source/logo-kidalu.png src/assets/img/logo-kidalu.webp 320
```

W `base.html.jinja` zastąp zawartość `.brand`:

```jinja
  <a class="brand" href="{{ url('home') }}">
    <img src="{{ asset('img/logo-kidalu.webp') }}" alt="{{ c.site.brand }}" width="160" height="160">
  </a>
```

W `site.css` zastąp regułę `.brand`:

```css
.brand{display:inline-flex; align-items:center; line-height:0}
.brand img{width:clamp(72px,9vw,104px); height:auto}
```

- [ ] **Step 7: Zbuduj i sprawdź, że logo trafiło do wyniku**

Run: `python3 build.py && python3 -m pytest tests/ -v && ls -la docs/assets/img/`
Expected: testy PASS, `logo-kidalu.webp` obecne w `docs/assets/img/`

- [ ] **Step 8: Commit**

```bash
git add requirements.txt tools/prepare_asset.py tests/test_prepare_asset.py src/ 
git commit -m "feat: pipeline obróbki grafik i logo Kidalu w nagłówku"
```

---

### Task 8: Zamówienie grafik w Gemini

Zadanie ręczne, prowadzone przez przeglądarkę. Nie ma testu jednostkowego — kryterium odbioru jest komplet plików przechodzących przez `prepare_asset` w budżecie.

**Files:**
- Create: `assets-source/*.png` (pobrane z Gemini)
- Create: `src/assets/img/*.webp` (po obróbce)

**Interfaces:**
- Consumes: `tools.prepare_asset.prepare`
- Produces: pliki graficzne dla etapu 2

- [ ] **Step 1: Wejdź na właściwe konto**

Otwórz `https://gemini.google.com/u/1/app`. **Nie** `/app` — to konto służbowe merce.com. Potwierdź zielony awatar „S" w lewym dolnym rogu przed pierwszym promptem.

- [ ] **Step 2: Dociągnij oryginał logo**

W historii czatów otwórz „Logotyp dla aplikacji Kidalu", pobierz plik w pełnej rozdzielczości do `assets-source/logo-kidalu-full.png`. Jeśli jest większy niż posiadane 1254², powtórz Step 6 z Taska 7 na nowym pliku.

- [ ] **Step 3: Zamów pięć warstw tła**

Prompty pisz po angielsku — generacja obrazu daje wtedy stabilniejsze wyniki. Do każdego doklej ten sam wstęp:

```
Soft 3D rendered children's storybook illustration. Warm rounded volumes,
soft ambient occlusion, gentle rim light, matte finish, no harsh shadows.
Colour palette: cream #FDF6E0, warm wood brown #994E21, deep pine green
#205740, sky blue #6FCCF3. Absolutely no text, no letters, no numbers,
no watermark.
```

Następnie, kolejno, po jednym czacie na warstwę:

1. `A wide panoramic morning sky with a few soft rounded clouds, warm low sunlight. Full-bleed horizontal banner, aspect ratio 12:5, nothing but sky.`
2. `A horizontal band of distant pine trees seen through morning mist, simplified silhouettes, cool desaturated green. Aspect ratio 8:3. Isolated on a pure flat white background, nothing else in frame.`
3. `A horizontal row of mid-distance storybook trees, rounded canopies, varied heights, warm green. Aspect ratio 12:5.5. Isolated on a pure flat white background, nothing else in frame.`
4. `A grassy forest clearing seen from slightly above, with a winding dirt path curving from the lower left to the right. Aspect ratio 3:1. Isolated on a pure flat white background, nothing else in frame.`
5. `A foreground border of ferns, low bushes and a few smooth stones, as if closest to the viewer at the bottom of a scene. Aspect ratio 24:5. Isolated on a pure flat white background, nothing else in frame.`

Warstwa 1 jest spodem sceny i nie wymaga wycinania. Warstwy 2–5 wymagają.

- [ ] **Step 4: Zamów obiekty**

6. `A cosy fairytale mushroom house: thick rounded stem with a small round wooden door and one round window, wide domed cap in warm terracotta with soft cream spots. Cute, inviting, child-friendly. Centred, complete, isolated on a pure flat white background.`
7. `A cosy fairytale mushroom house: thick rounded stem with a small arched wooden door and one round window, wide domed cap in deep pine green with soft cream spots. Cute, inviting, child-friendly. Centred, complete, isolated on a pure flat white background.`
8. `A cute fluffy brown owl with very large amber eyes, sitting upright and holding an open picture book with both wings, looking at the viewer. Same character design as a friendly owl mascot. Centred, complete, isolated on a pure flat white background.`
9. `An empty rustic wooden signboard on a single short post, oval plank with visible wood grain, warm brown, completely blank surface with no writing whatsoever. Centred, complete, isolated on a pure flat white background.`
10. `A single small glowing firefly, soft warm yellow light with a gentle halo. Centred, isolated on a pure flat white background.`
11. `A single small butterfly with softly rounded wings in warm amber and cream. Wings open, seen from above. Centred, isolated on a pure flat white background.`
12. `Three separate simple leaves arranged apart from each other with clear space between them: one fresh green, one yellow-green, one warm amber. Each leaf complete and not overlapping. Isolated on a pure flat white background.`

Pozycję 12 po pobraniu potnij na trzy osobne pliki.

- [ ] **Step 5: Zapisz i przetwórz**

Pobierz każdy obraz do `assets-source/` pod nazwami: `sky.png`, `far.png`, `mid.png`, `ground.png`, `fg.png`, `house-czytanie.png`, `house-literki.png`, `owl-czytanie.png`, `sign.png`, `firefly.png`, `butterfly.png`, `leaf-a.png`, `leaf-b.png`, `leaf-c.png`.

Sowę Literek skopiuj z tego, co już mamy:

```bash
cp /Users/srosinski/Downloads/Gemini_Generated_Image_gspb2dgspb2dgspb.jpeg assets-source/owl-literki.jpg
```

Przetwórz wszystko poza niebem:

```bash
cd /Users/srosinski/Desktop/test/kidalu
python3 - <<'EOF'
from pathlib import Path
from tools.prepare_asset import prepare
from PIL import Image

# niebo jest spodem sceny — bez wycinania, sama konwersja
sky = Image.open("assets-source/sky.png").convert("RGB")
sky.resize((2400, round(sky.height * 2400 / sky.width)), Image.LANCZOS).save(
    "src/assets/img/sky.webp", format="WEBP", quality=80, method=6
)

zadania = [
    ("far", 2400), ("mid", 2400), ("ground", 2400), ("fg", 2400),
    ("house-czytanie", 1024), ("house-literki", 1024),
    ("owl-czytanie", 1024), ("owl-literki", 1024), ("sign", 1024),
    ("firefly", 256), ("butterfly", 256),
    ("leaf-a", 256), ("leaf-b", 256), ("leaf-c", 256),
]
for name, w in zadania:
    src = next(Path("assets-source").glob(f"{name}.*"))
    info = prepare(src, Path(f"src/assets/img/{name}.webp"), width=w)
    limit = 180 if w >= 2400 else 80
    stan = "OK" if info["bytes"] <= limit * 1024 else "PRZEKROCZONY BUDŻET"
    print(f"{name:16s} {info['size'][0]}×{info['size'][1]:5d}  {info['bytes']/1024:6.0f} KB  {stan}")
EOF
```

Każda pozycja musi wyjść jako `OK`. Przy przekroczeniu budżetu obniż `quality` dla tego pliku.

- [ ] **Step 6: Commit**

```bash
git add assets-source/ src/assets/img/
git commit -m "assets: komplet grafik lasu z Gemini po obróbce"
```

---

### Task 9: Wdrożenie na kidalu.com

**Files:**
- Modify: ustawienia GitHub Pages (przez API, nie plik)

**Interfaces:**
- Consumes: `docs/` wygenerowane przez `build.py`
- Produces: działająca witryna pod kidalu.com

- [ ] **Step 1: Pełny przebieg przed wypchnięciem**

```bash
cd /Users/srosinski/Desktop/test/kidalu
python3 build.py
python3 -m pytest tests/ -v
python3 tools/check_links.py docs
grep -rl "Mądre Dzieciaki\|codedriven.pl" docs/ || echo "brak starej marki i starej domeny — OK"
```

Wszystko musi przejść. `grep` ma nie znaleźć nic.

- [ ] **Step 2: Usuń stare pliki witryny z korzenia repo**

Stare strony zostały przeniesione do `content/docs/` i są teraz generowane. Korzeń repo przestaje być katalogiem publikacji.

```bash
git rm -r --cached index.html kontakt.html assets nauka-czytania-sylabami literki-i-cyferki CNAME
rm -rf index.html kontakt.html assets nauka-czytania-sylabami literki-i-cyferki CNAME
git add -A
git commit -m "chore: korzeń repo przestaje być katalogiem publikacji"
```

- [ ] **Step 3: Scal do main i wypchnij**

```bash
git switch main
git merge --no-ff kidalu-rebrand -m "Kidalu: nowa witryna generowana do docs/"
git push origin main
```

- [ ] **Step 4: Przełącz Pages na /docs i ustaw domenę**

```bash
gh api -X PUT repos/Rosa89/kidaluweb/pages -f 'source[branch]=main' -f 'source[path]=/docs'
gh api -X PUT repos/Rosa89/kidaluweb/pages -f 'cname=kidalu.com'
gh api repos/Rosa89/kidaluweb/pages
```

Expected: `"source": {"branch":"main","path":"/docs"}` oraz `"cname":"kidalu.com"`.

- [ ] **Step 5: Przekaż użytkownikowi rekordy DNS**

Rekordy do wklejenia w OVH — **wykonuje użytkownik**, nie agent:

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

Poproś też o przekierowanie 301 `codedriven.pl` → `kidalu.com` jako pomost dla linków z Play.

- [ ] **Step 6: Zweryfikuj po propagacji DNS**

```bash
dig +short kidalu.com
curl -sSI https://kidalu.com/ | head -3
curl -sS -o /dev/null -w "%{http_code}\n" https://kidalu.com/czytanie-sylabami/dokumenty/
curl -sS -o /dev/null -w "%{http_code}\n" https://kidalu.com/literki-i-cyferki/dokumenty/
```

Expected: adresy IP GitHuba, `HTTP/2 200`, oraz `200` dla obu adresów dokumentów.

- [ ] **Step 7: Wymuś HTTPS**

Dopiero gdy certyfikat zostanie wystawiony (widoczne w `gh api repos/Rosa89/kidaluweb/pages` jako `https_certificate.state == "approved"`):

```bash
gh api -X PUT repos/Rosa89/kidaluweb/pages -F 'https_enforced=true'
```

- [ ] **Step 8: Przekaż użytkownikowi adresy do Play Console**

Do wklejenia w Play Console, w polu polityki prywatności — **wykonuje użytkownik**:

- `com.readbysyllables.app` → `https://kidalu.com/czytanie-sylabami/dokumenty/`
- `com.literkiicyferki.app` → `https://kidalu.com/literki-i-cyferki/dokumenty/`

Dla listingu niemieckiego Literek: `https://kidalu.com/de/buchstaben-und-zahlen/dokumente/`

---

## Etap 2 — planowany osobno

Scena lasu dostaje własny plan po zakończeniu Taska 8. Powód jest praktyczny: zadania składające pięciowarstwową scenę wymagają znajomości realnych proporcji, sylwetek i marginesów gotowych wycinków. Rozpisanie ich teraz wymusiłoby placeholdery w miejscach, gdzie potrzebne są konkretne liczby.
