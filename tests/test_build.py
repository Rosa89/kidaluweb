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
