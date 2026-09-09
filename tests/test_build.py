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
    build.build()
    html = (build.OUT / "index.html").read_text("utf-8")
    for lang, url in build.alternates("home").items():
        assert f'hreflang="{lang}"' in html
        target = build.OUT / url.strip("/") / "index.html" if url.strip("/") else build.OUT / "index.html"
        assert target.exists(), f"hreflang {lang} wskazuje na nieistniejący {target}"
    assert 'hreflang="x-default"' in html
