import re
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


def test_logo_naglowka_ma_alt_z_marka():
    """Znak marki w nagłówku jest obrazkiem — jedynym nośnikiem nazwy marki dla
    czytnika ekranu jest atrybut alt na <img>, nie sam fakt wystąpienia słowa
    "Kidalu" gdziekolwiek w HTML (np. w <title>)."""
    build.build()
    index = build.OUT / "index.html"
    html = index.read_text("utf-8")

    m = re.search(r'<a class="brand"[^>]*>.*?<img([^>]*)>', html, re.S)
    assert m, "nie znaleziono obrazka logo w bloku .brand nagłówka"

    img_attrs = m.group(1)
    alt_m = re.search(r'alt="([^"]*)"', img_attrs)
    assert alt_m, "obrazek logo nie ma w ogóle atrybutu alt"
    assert alt_m.group(1).strip(), "atrybut alt obrazka logo jest pusty"
    assert "Kidalu" in alt_m.group(1), "atrybut alt obrazka logo nie zawiera nazwy marki"


def test_nie_zostawia_starej_marki():
    build.build()
    for path in build.OUT.rglob("*.html"):
        assert "Mądre Dzieciaki" not in path.read_text("utf-8"), path


def test_build_czysci_katalog_wyjsciowy():
    """Weryfikuje, że build() usuwa sierotę z poprzedniej kompilacji przed regenerowaniem."""
    # Utwórz katalog wyjściowy i sierotę
    build.OUT.mkdir(parents=True, exist_ok=True)
    orphan = build.OUT / "orphan.html"
    orphan.write_text("<p>Stara strona</p>", "utf-8")
    assert orphan.exists()

    # Uruchom build()
    build.build()

    # Sprawdź że sierota zniknęła
    assert not orphan.exists(), "Sierota powinna być usunięta"

    # Sprawdź że nowa strona została wygenerowana
    index = build.OUT / "index.html"
    assert index.exists(), "docs/index.html powinien istnieć"


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
    # Docelowa domena produkcyjna, zahardkodowana tutaj celowo — NIE brać jej
    # z build.SITE_HOST. Ten test ma wykryć pomyłkę w samej stałej, więc nie
    # może porównywać wyniku z tą samą wartością, która go wyprodukowała.
    EXPECTED_SITE_HOST = "https://kidalu.com"

    # Osobna, krótka asercja pinująca stałą produkcyjną — jeśli ktoś ją
    # zmieni (przez pomyłkę albo świadomie), to pęknie tutaj, w oczywistym
    # miejscu, zamiast dopiero w postaci błędnych adresów w wynikach wyszukiwania.
    assert build.SITE_HOST == EXPECTED_SITE_HOST

    build.build()
    html = (build.OUT / "index.html").read_text("utf-8")

    alternates = build.alternates("home")

    # Sprawdzenie każdego języka z alternates
    for lang, url in alternates.items():
        expected_href = f"{EXPECTED_SITE_HOST}{url}"
        expected_tag = f'<link rel="alternate" hreflang="{lang}" href="{expected_href}">'
        assert expected_tag in html, f"Brak znacznika hreflang dla {lang} z adresem {expected_href}"
        target = build.OUT / url.strip("/") / "index.html" if url.strip("/") else build.OUT / "index.html"
        assert target.exists(), f"hreflang {lang} wskazuje na nieistniejący {target}"

    # Sprawdzenie x-default — musi być obecny tylko jeśli 'pl' istnieje
    if 'pl' in alternates:
        pl_url = alternates['pl']
        expected_xdef_href = f"{EXPECTED_SITE_HOST}{pl_url}"
        expected_xdef_tag = f'<link rel="alternate" hreflang="x-default" href="{expected_xdef_href}">'
        assert expected_xdef_tag in html, f"Brak poprawnego znacznika x-default z adresem {expected_xdef_href}"
    else:
        # x-default nie powinien być renderowany jeśli polskiej wersji nie ma
        assert 'hreflang="x-default"' not in html, "x-default powinien być renderowany tylko gdy 'pl' istnieje w alternates"


def test_podstrony_aplikacji_we_wszystkich_jezykach():
    build.build()
    for lang in build.available_langs():
        urls = build.page_urls(build.load_lang(lang), lang)
        for key in ("czytanie", "literki"):
            target = build.OUT / urls[key].strip("/") / "index.html"
            assert target.exists(), target


def test_podstrona_linkuje_do_wlasciwej_aplikacji_w_play():
    # Identyfikatory pakietów są wpisane tutaj dosłownie (nie przez build.APPS
    # ani build.play_url) — inaczej test porównywałby wynik sam ze sobą i nie
    # wykryłby zamiany kluczy miejscami w APPS.
    CZYTANIE_ID = "id=com.readbysyllables.app"
    LITERKI_ID = "id=com.literkiicyferki.app"

    build.build()
    for lang in build.available_langs():
        urls = build.page_urls(build.load_lang(lang), lang)

        czytanie_target = build.OUT / urls["czytanie"].strip("/") / "index.html"
        literki_target = build.OUT / urls["literki"].strip("/") / "index.html"
        czytanie = czytanie_target.read_text("utf-8")
        literki = literki_target.read_text("utf-8")

        assert CZYTANIE_ID in czytanie, f"{czytanie_target} nie linkuje do właściwej aplikacji"
        assert LITERKI_ID not in czytanie, f"{czytanie_target} linkuje też do drugiej aplikacji"

        assert LITERKI_ID in literki, f"{literki_target} nie linkuje do właściwej aplikacji"
        assert CZYTANIE_ID not in literki, f"{literki_target} linkuje też do drugiej aplikacji"


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


# --- SEO: sitemap z lastmod i alternatywami językowymi, dane strukturalne ---

import json


def _sitemap_entry(sitemap: str, url: str) -> str:
    """Wycinek <url>…</url> dla danego adresu."""
    m = re.search(rf"<url>\s*<loc>{re.escape(url)}</loc>(.*?)</url>", sitemap, re.S)
    assert m, f"brak wpisu {url} w sitemap.xml"
    return m.group(1)


def test_sitemap_ma_lastmod_w_formacie_daty():
    build.build()
    sitemap = (build.OUT / "sitemap.xml").read_text("utf-8")
    entries = re.findall(r"<url>.*?</url>", sitemap, re.S)
    assert entries
    for e in entries:
        assert re.search(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", e), e


def test_sitemap_wymienia_alternatywy_jezykowe():
    build.build()
    sitemap = (build.OUT / "sitemap.xml").read_text("utf-8")
    assert 'xmlns:xhtml="http://www.w3.org/1999/xhtml"' in sitemap

    home = _sitemap_entry(sitemap, "https://kidalu.com/")
    for lang, href in (("pl", "https://kidalu.com/"),
                       ("de", "https://kidalu.com/de/"),
                       ("en", "https://kidalu.com/en/"),
                       ("x-default", "https://kidalu.com/")):
        tag = f'<xhtml:link rel="alternate" hreflang="{lang}" href="{href}"/>'
        assert tag in home, f"strona główna: brak {tag}"

    # Ta sama lista alternatyw ma być w wersji DE — Google wymaga, żeby
    # każda strona z grupy wskazywała na wszystkie pozostałe.
    de_home = _sitemap_entry(sitemap, "https://kidalu.com/de/")
    assert 'hreflang="pl" href="https://kidalu.com/"' in de_home
    assert 'hreflang="en" href="https://kidalu.com/en/"' in de_home


def test_sitemap_nie_wymysla_alternatyw_dla_brakujacych_tlumaczen():
    build.build()
    sitemap = (build.OUT / "sitemap.xml").read_text("utf-8")
    docs = _sitemap_entry(sitemap, "https://kidalu.com/czytanie-sylabami/dokumenty/")
    assert 'hreflang="de"' not in docs
    assert 'hreflang="en"' not in docs
    assert 'hreflang="pl" href="https://kidalu.com/czytanie-sylabami/dokumenty/"' in docs


def _jsonld(html: str) -> list[dict]:
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert blocks, "brak bloku JSON-LD"
    return [json.loads(b) for b in blocks]


def test_strona_glowna_ma_dane_strukturalne_organizacji():
    build.build()
    html = (build.OUT / "index.html").read_text("utf-8")
    types = {d["@type"]: d for d in _jsonld(html)}
    assert "Organization" in types
    assert types["Organization"]["name"] == "Kidalu"
    assert types["Organization"]["url"] == "https://kidalu.com/"
    assert "WebSite" in types
    assert types["WebSite"]["inLanguage"] == "pl"


def test_podstrona_aplikacji_ma_dane_strukturalne_aplikacji():
    build.build()
    html = (build.OUT / "literki-i-cyferki" / "index.html").read_text("utf-8")
    types = {d["@type"]: d for d in _jsonld(html)}
    app = types["MobileApplication"]
    assert app["name"] == "Literki i Cyferki"
    assert app["operatingSystem"] == "Android"
    assert app["applicationCategory"] == "EducationalApplication"
    assert app["installUrl"].endswith("id=com.literkiicyferki.app")
    assert app["url"] == "https://kidalu.com/literki-i-cyferki/"
    assert app["inLanguage"] == "pl"

    # Strona kontaktu nie jest aplikacją
    kontakt = (build.OUT / "kontakt" / "index.html").read_text("utf-8")
    assert "MobileApplication" not in kontakt


def test_og_locale_w_pelnym_formacie():
    build.build()
    pl = (build.OUT / "index.html").read_text("utf-8")
    de = (build.OUT / "de" / "index.html").read_text("utf-8")
    en = (build.OUT / "en" / "index.html").read_text("utf-8")
    assert '<meta property="og:locale" content="pl_PL">' in pl
    assert '<meta property="og:locale" content="de_DE">' in de
    assert '<meta property="og:locale" content="en_US">' in en
    assert '<meta property="og:locale:alternate" content="de_DE">' in pl
    assert '<meta property="og:image:width" content="1200">' in pl


# --- podstrona „O Kidalu", powiązanie z Google Play, strona 404 ---

PLAY_DEV_URL = "https://play.google.com/store/apps/developer?id=Kidalu"


def test_o_kidalu_we_wszystkich_jezykach_i_w_sitemapie():
    build.build()
    sitemap = (build.OUT / "sitemap.xml").read_text("utf-8")
    expected = {
        "pl": "/o-kidalu/",
        "de": "/ueber-kidalu/",
        "en": "/about-kidalu/",
    }
    for lang, slug in expected.items():
        urls = build.page_urls(build.load_lang(lang), lang)
        assert urls["o_nas"].endswith(slug), urls["o_nas"]
        target = build.OUT / urls["o_nas"].strip("/") / "index.html"
        assert target.exists(), target
        html = target.read_text("utf-8")
        assert "<h1>" in html and "Kidalu" in html
        assert f"<loc>{build.SITE_HOST}{urls['o_nas']}</loc>" in sitemap

    pl = _sitemap_entry(sitemap, "https://kidalu.com/o-kidalu/")
    assert 'hreflang="de" href="https://kidalu.com/de/ueber-kidalu/"' in pl
    assert 'hreflang="en" href="https://kidalu.com/en/about-kidalu/"' in pl


def test_nawigacja_ma_zakladke_o_kidalu():
    build.build()
    html = (build.OUT / "index.html").read_text("utf-8")
    nav = re.search(r'<nav class="topnav".*?</nav>', html, re.S).group(0)
    assert 'href="/o-kidalu/"' in nav
    about = (build.OUT / "o-kidalu" / "index.html").read_text("utf-8")
    nav = re.search(r'<nav class="topnav".*?</nav>', about, re.S).group(0)
    assert re.search(r'href="/o-kidalu/"[^>]*aria-current="page"', nav)


def test_organizacja_powiazana_z_profilem_w_google_play():
    build.build()
    for rel in ("index.html", "de/index.html", "kontakt/index.html"):
        html = (build.OUT / rel).read_text("utf-8")
        org = next(d for d in _jsonld(html) if d["@type"] == "Organization")
        assert PLAY_DEV_URL in org["sameAs"], rel
        foot = re.search(r'<footer class="site-foot">.*?</footer>', html, re.S).group(0)
        assert PLAY_DEV_URL in foot, rel


def test_strona_404_istnieje_i_nie_jest_indeksowana():
    build.build()
    page = build.OUT / "404.html"
    assert page.exists(), "GitHub Pages serwuje 404.html z korzenia"
    html = page.read_text("utf-8")
    assert '<meta name="robots" content="noindex">' in html
    assert 'rel="canonical"' not in html
    assert 'rel="alternate"' not in html
    assert 'href="/"' in html and 'href="/de/"' in html and 'href="/en/"' in html
    # 404 nie trafia do sitemapy
    assert "404" not in (build.OUT / "sitemap.xml").read_text("utf-8")
