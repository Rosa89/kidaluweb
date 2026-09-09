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
