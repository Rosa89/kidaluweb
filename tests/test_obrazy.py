"""Warianty grafik dla srcset. Telefon wyświetla sowę na ok. 70 px szerokości,
a pobierał plik o szerokości 900 px."""
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build
from tools.prepare_asset import portrait, variants


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


# --- tło sceny na telefonie w pionie ---

def test_wycinek_pionowy_to_srodkowy_pas_oryginalu(tmp_path):
    src = tmp_path / "tlo.webp"
    im = Image.new("RGB", (1672, 941), (0, 0, 255))
    im.paste((255, 0, 0), (476, 0, 1196, 941))  # środkowy pas 720 px
    im.save(src, "WEBP", lossless=True)

    out = portrait(src, 720)

    assert out.name == "tlo-portrait.webp"
    p = Image.open(out).convert("RGB")
    assert p.size == (720, 941)
    for xy in ((0, 0), (719, 940), (360, 470)):
        r, _g, b = p.getpixel(xy)
        assert r > 200 and b < 60, f"piksel {xy} spoza środkowego pasa: {p.getpixel(xy)}"


def test_telefon_w_pionie_dostaje_wycinek_tla_sceny():
    """Telefon w pionie widzi ok. 1/4 szerokości sceny, a pobierał całą grafikę
    (238 KB) z wysokim priorytetem. Dostaje środkowy pas w tej samej skali,
    więc wygląda identycznie, a waży ponad dwa razy mniej."""
    build.build()
    html = (build.OUT / "index.html").read_text("utf-8")
    css = (build.OUT / "assets" / "css" / "site.css").read_text("utf-8")

    pre_portrait = re.search(
        r'<link rel="preload" as="image" href="(/assets/img/scene-forest-portrait\.webp\?v=[0-9a-f]{8})" '
        r'media="\(max-aspect-ratio: 2/3\)" fetchpriority="high">', html)
    pre_full = re.search(
        r'<link rel="preload" as="image" href="(/assets/img/scene-forest\.webp\?v=[0-9a-f]{8})" '
        r'media="not all and \(max-aspect-ratio: 2/3\)" fetchpriority="high">', html)
    assert pre_portrait and pre_full, "preload tła ma zależeć od proporcji ekranu"

    rule = re.search(
        r"@media \(max-aspect-ratio:\s*2/3\)\s*\{\s*\.stage\s*\{\s*background-image:\s*"
        r"url\(\.\./(img/scene-forest-portrait\.webp\?v=[0-9a-f]{8})\)", css)
    assert rule, "arkusz nie podmienia tła sceny na wycinek"
    # preload musi wskazywać ten sam adres co arkusz, inaczej plik pobierze się dwa razy
    assert pre_portrait.group(1) == "/assets/" + rule.group(1)

    orig = Image.open(build.ASSETS / "img" / "scene-forest.webp").convert("RGB")
    crop = Image.open(build.OUT / "assets" / "img" / "scene-forest-portrait.webp").convert("RGB")
    assert crop.height == orig.height
    # Wycinek pokrywa każde okno węższe niż jego proporcje; zapas ponad próg 2/3
    # zostawia miejsce na pasek przeglądarki (100svh jest niższe niż okno z media query).
    assert crop.width / crop.height >= (2 / 3) * 1.1, crop.size
    left = (orig.width - crop.width) // 2
    ref = orig.crop((left, 0, left + crop.width, orig.height))
    mean_diff = sum(ImageStat.Stat(ImageChops.difference(ref, crop)).mean) / 3
    assert mean_diff < 6, f"wycinek nie odpowiada środkowi oryginału (średnia różnica {mean_diff:.1f})"
