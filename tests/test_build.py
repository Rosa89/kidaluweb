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
