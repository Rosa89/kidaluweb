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
