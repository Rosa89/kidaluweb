"""Zamienia surową grafikę z Gemini na asset gotowy do publikacji:
wycina tło, czyści krawędź, przycina do zawartości, skaluje i zapisuje webp."""
from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image, ImageFilter


def _cutout(im: Image.Image) -> Image.Image:
    from rembg import remove

    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return Image.open(io.BytesIO(remove(buf.getvalue()))).convert("RGBA")


def _clean_edge(im: Image.Image) -> Image.Image:
    """Erozja alfy o 1 px i lekkie wtopienie — zdejmuje jasną obwódkę po tle."""
    alpha = im.getchannel("A")
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.5))
    im.putalpha(alpha)
    return im


def prepare(src: Path, dst: Path, width: int | None = None, quality: int = 75) -> dict:
    im = Image.open(src).convert("RGBA")
    im = _clean_edge(_cutout(im))

    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)

    if width and im.width != width:
        height = round(im.height * width / im.width)
        im = im.resize((width, height), Image.LANCZOS)

    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, format="WEBP", quality=quality, method=6)

    lo, hi = im.getchannel("A").getextrema()
    return {"size": im.size, "bytes": dst.stat().st_size, "alpha": lo == 0 and hi == 255}


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    w = int(sys.argv[3]) if len(sys.argv) > 3 else None
    info = prepare(src, dst, width=w)
    print(f"{dst}: {info['size'][0]}×{info['size'][1]}, {info['bytes'] / 1024:.0f} KB, alpha={info['alpha']}")
