"""Warianty grafik dla srcset. Telefon wyświetla sowę na ok. 70 px szerokości,
a pobierał plik o szerokości 900 px."""
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build
from tools.prepare_asset import variants


def test_warianty_maja_zadana_szerokosc_proporcje_i_przezroczystosc(tmp_path):
    src = tmp_path / "sowa.webp"
    im = Image.new("RGBA", (900, 770), (200, 120, 40, 255))
    im.paste((0, 0, 0, 0), (0, 0, 450, 770))
    im.save(src, "WEBP", lossless=True)

    out = variants(src, (240, 480, 900, 1200))

    # Szerokości równe oryginałowi lub większe nic nie dają — pomijamy je.
    assert [p.name for p in out] == ["sowa-240w.webp", "sowa-480w.webp"]
    for path, width in zip(out, (240, 480)):
        v = Image.open(path)
        assert v.mode == "RGBA"
        assert v.size == (width, round(770 * width / 900))
        assert v.getpixel((0, v.height // 2))[3] == 0, "przezroczystość zgubiona"
        assert v.getpixel((width - 1, v.height // 2))[3] == 255


def test_srcset_wymienia_warianty_i_oryginal():
    parts = [p.strip() for p in build.srcset("img/owl-czytanie.webp", 900).split(",")]
    assert re.fullmatch(r"/assets/img/owl-czytanie-240w\.webp\?v=[0-9a-f]{8} 240w", parts[0]), parts
    assert re.fullmatch(r"/assets/img/owl-czytanie-480w\.webp\?v=[0-9a-f]{8} 480w", parts[1]), parts
    assert re.fullmatch(r"/assets/img/owl-czytanie\.webp\?v=[0-9a-f]{8} 900w", parts[-1]), parts


def test_warianty_odpowiadaja_oryginalom():
    """Wariant wygenerowany ze starej wersji grafiki zdradzi się innymi proporcjami."""
    for rel, widths in build.VARIANTS.items():
        orig = Image.open(build.ASSETS / rel)
        for width in widths:
            v = Image.open(build.ASSETS / build.variant_rel(rel, width))
            assert v.width == width, (rel, width)
            assert abs(v.height - orig.height * width / orig.width) <= 1, (rel, width)


IMG = re.compile(r"<img\b[^>]*>")


def _attr(tag: str, name: str) -> str | None:
    m = re.search(rf'\s{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def test_grafiki_z_wariantami_maja_srcset_z_prawdziwymi_szerokosciami():
    build.build()
    for lang in build.available_langs():
        urls = build.page_urls(build.load_lang(lang), lang)
        for key in ("home", "czytanie", "literki", "kontakt"):
            page = build.OUT / urls[key].strip("/") / "index.html"
            html = page.read_text("utf-8")
            checked = 0
            for tag in IMG.findall(html):
                rel = _attr(tag, "src").split("?")[0].removeprefix("/assets/")
                if rel not in build.VARIANTS:
                    continue
                srcset = _attr(tag, "srcset")
                assert srcset, f"{page}: {rel} bez srcset"
                assert _attr(tag, "sizes"), f"{page}: {rel} ma srcset, ale nie ma sizes"
                for candidate in srcset.split(","):
                    path, descriptor = candidate.split()
                    file = build.OUT / path.split("?")[0].lstrip("/")
                    assert file.exists(), (page, path)
                    assert Image.open(file).width == int(descriptor.removesuffix("w")), (page, candidate)
                checked += 1
            assert checked, f"{page}: żadna grafika nie ma wariantów — test niczego nie sprawdził"
