"""Zamienia surową grafikę z Gemini na asset gotowy do publikacji:
wycina tło, czyści krawędź, przycina do zawartości, skaluje i zapisuje webp."""
from __future__ import annotations

import argparse
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


def prepare(src: Path, dst: Path, width: int | None = None, quality: int = 82) -> dict:
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


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path, help="źródłowa grafika (np. z Gemini)")
    parser.add_argument("dst", type=Path, help="ścieżka docelowa .webp")
    parser.add_argument("width", type=int, nargs="?", default=None, help="docelowa szerokość w px")
    parser.add_argument(
        "--quality", type=int, default=82,
        help="jakość zapisu WEBP, 0-100 (domyślnie 82)",
    )
    parser.add_argument(
        "--budget-kb", type=float, default=None,
        help="maksymalna dopuszczalna waga pliku w KB; przekroczenie kończy się kodem != 0",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    info = prepare(args.src, args.dst, width=args.width, quality=args.quality)
    print(
        f"{args.dst}: {info['size'][0]}×{info['size'][1]}, "
        f"{info['bytes'] / 1024:.1f} KB, alpha={info['alpha']}"
    )

    if args.budget_kb is not None:
        budget_bytes = args.budget_kb * 1024
        if info["bytes"] > budget_bytes:
            over_kb = (info["bytes"] - budget_bytes) / 1024
            print(
                f"BŁĄD: {args.dst} przekracza budżet {args.budget_kb:.0f} KB "
                f"o {over_kb:.1f} KB ({info['bytes'] / 1024:.1f} KB > {args.budget_kb:.0f} KB)",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
