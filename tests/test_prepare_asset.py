import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image

from tools.prepare_asset import prepare

ZRODLO = Path("/Users/srosinski/Downloads/Gemini_Generated_Image_gspb2dgspb2dgspb.jpeg")

# Jakość dobrana empirycznie dla tego konkretnego materiału testowego: przy
# domyślnej jakości 82 sowa waży ~93 KB (poza budżetem 80 KB obiektów). 76 to
# najwyższa jakość, przy której obraz nadal mieści się w budżecie (~77.7 KB).
JAKOSC_SOWY = 76


def test_wycina_tlo_i_miesci_sie_w_budzecie(tmp_path):
    if not ZRODLO.exists():
        pytest.skip(f"materiał testowy niedostępny na tej maszynie: {ZRODLO}")
    out = tmp_path / "owl.webp"
    info = prepare(ZRODLO, out, width=1024, quality=JAKOSC_SOWY)

    assert out.exists()
    assert info["alpha"] is True, "tło nie zostało wycięte"
    assert info["bytes"] <= 80 * 1024, f"obiekt waży {info['bytes']} B, budżet to 80 KB"

    im = Image.open(out)
    assert im.mode == "RGBA"
    assert im.width == 1024
    # rogi muszą być przezroczyste po wycięciu i przycięciu
    for xy in ((0, 0), (im.width - 1, 0)):
        assert im.getpixel(xy)[3] == 0, f"róg {xy} nie jest przezroczysty"
