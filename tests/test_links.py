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


def test_odnosnik_wzgledny_jest_zglaszany_jako_problem(tmp_path):
    (tmp_path / "index.html").write_text(
        '<a href="../kontakt.html">x</a>', "utf-8"
    )
    problems = check(tmp_path)
    assert len(problems) == 1
    assert "../kontakt.html" in problems[0]
    assert "wzgl" in problems[0].lower(), (
        "komunikat ma jasno mówić, że to odnośnik względny, a nie martwy plik"
    )


def test_odnosnik_zewnetrzny_nie_jest_zglaszany(tmp_path):
    (tmp_path / "index.html").write_text(
        '<a href="https://example.com/">x</a>'
        '<a href="mailto:ktos@example.com">y</a>',
        "utf-8",
    )
    problems = check(tmp_path)
    assert problems == []


def test_pojedynczy_cudzyslow_jest_sprawdzany(tmp_path):
    (tmp_path / "index.html").write_text(
        "<a href='/nie-ma-mnie/'>x</a>", "utf-8"
    )
    problems = check(tmp_path)
    assert any("/nie-ma-mnie/" in p for p in problems)


def test_adres_od_korzenia_z_kotwica_i_parametrem_dziala_jak_dotychczas(tmp_path):
    (tmp_path / "kontakt").mkdir()
    (tmp_path / "kontakt" / "index.html").write_text("x", "utf-8")
    (tmp_path / "index.html").write_text(
        '<a href="/kontakt/#privacy">a</a>'
        '<a href="/kontakt/?ref=x">b</a>',
        "utf-8",
    )
    problems = check(tmp_path)
    assert problems == []


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
