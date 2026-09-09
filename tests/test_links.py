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
