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


def _crop_to_content(im: Image.Image) -> Image.Image:
    """Przycina do bbox nieprzezroczystej zawartości (no-op, gdy kanał alfa jest pusty)."""
    bbox = im.getchannel("A").getbbox()
    return im.crop(bbox) if bbox else im


def _scale_to_width(im: Image.Image, width: int | None) -> Image.Image:
    """Skaluje proporcjonalnie do zadanej szerokości (no-op, gdy już jej odpowiada)."""
    if width and im.width != width:
        height = round(im.height * width / im.width)
        im = im.resize((width, height), Image.LANCZOS)
    return im


def _finish(im: Image.Image, dst: Path, width: int | None, quality: int) -> dict:
    """Wspólny ogon obu ścieżek: kadrowanie do zawartości, skalowanie, zapis webp i raport."""
    im = _crop_to_content(im)
    im = _scale_to_width(im, width)

    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, format="WEBP", quality=quality, method=6)

    lo, hi = im.getchannel("A").getextrema()
    return {"size": im.size, "bytes": dst.stat().st_size, "alpha": lo == 0 and hi == 255}


def prepare(src: Path, dst: Path, width: int | None = None, quality: int = 82) -> dict:
    im = Image.open(src).convert("RGBA")
    im = _clean_edge(_cutout(im))
    return _finish(im, dst, width, quality)


# Próg bieli: kanał minimalny (R,G,B) musi przekroczyć tę wartość, żeby piksel
# liczył się jako "biały" kandydat na tło. Stary próg (238) miał zerowy margines:
# najjaśniejsze piksele realnej treści w assets-source/ sięgają dokładnie 238.
# Zmierzone na far/mid/ground/fg: najciemniejszy piksel tła (szum JPEG) to 239
# w każdym z czterech źródeł, ale to tylko pojedyncze piksele — 99,9% tła leży
# powyżej 240-243 (percentyl p0.1). Podniesienie do 240 daje 2 px marginesu nad
# treścią, odcina tylko znikomy ułamek najbardziej zaszumionych pikseli tła
# (łączność z krawędzią kadru mierzalnie nie pęka — liczba pikseli tła spada
# <0.1% względem progu 238) i nie rozmywa niepotrzebnie krawędzi realnych dziur
# (patrz UDZIAL_DZIURY: separacja tekstury/dziur sprawdzona też przy tym progu).
PROG_BIELI = 240

# Próg powierzchni zamkniętego białego obszaru: ułamek pola całego kadru, a nie
# liczba bezwzględna pikseli. Bezwzględny próg (dawniej 400 px) klasyfikował
# poprawnie przy 3392×1248 (przerwy między koronami: 420–1449 px), ale po
# przeskalowaniu tej samej sceny do połowy rozdzielczości te same przerwy mają
# już tylko 105–362 px i żadna nie przekraczała 400 — defekt, który miał
# naprawić prepare_band, wracał. 8e-5 pola kadru (czyli próg = pole / 12500)
# zweryfikowane na far/mid/ground/fg z assets-source/ w pełnej rozdzielczości
# i przy połowie: w obu skalach oddziela drobną teksturę/kwiatki (zostają) od
# realnych przerw (znikają) z wyraźnym marginesem.
UDZIAL_DZIURY = 8e-5

# Dolna granica w pikselach, żeby przy bardzo małych obrazach (mała powierzchnia
# kadru) próg względny nie zszedł praktycznie do zera.
MIN_DZIURA_PX = 25


def _wypelnij_od_krawedzi(im: Image.Image) -> Image.Image:
    """Wypełnia biel od krawędzi kadru: co jest białe i połączone z brzegiem,
    jest tłem; biel wewnątrz kształtu zostaje. Zamknięte białe obszary większe
    niż `UDZIAL_DZIURY` pola kadru też liczą się jako tło (np. przerwy między
    koronami drzew) — próg jest względny, więc klasyfikacja jest niezmiennicza
    względem skali obrazu. Drobne białe punkty (np. kwiatki na polanie)
    zostają nieprzezroczyste niezależnie od rozdzielczości.
    """
    import numpy as np
    from scipy import ndimage

    a = np.asarray(im)

    near_white = a.min(axis=2) > PROG_BIELI
    lab, n = ndimage.label(near_white)
    brzeg = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    brzeg.discard(0)

    prog = max(a.shape[0] * a.shape[1] * UDZIAL_DZIURY, MIN_DZIURA_PX)
    rozmiary = ndimage.sum(near_white, lab, range(1, n + 1)) if n else []
    duze = {i + 1 for i, r in enumerate(rozmiary) if r > prog}
    tlo = np.isin(lab, list(brzeg | duze))

    alpha = np.where(tlo, 0, 255).astype("uint8")
    return Image.fromarray(np.dstack([a, alpha]), "RGBA")


def prepare_band(src: Path, dst: Path, width: int, quality: int = 82) -> dict:
    """Wariant dla szerokich warstw tła.

    `rembg` wykrywa obiekt wyróżniający się, więc na pasie z wieloma drobnymi
    elementami potrafi uznać część roślinności za tło i ją skasować. Tutaj
    zamiast tego wypełniamy biel od krawędzi kadru (`_wypelnij_od_krawedzi`),
    a krawędź czyścimy tym samym zabiegiem co w `prepare()`, żeby obie ścieżki
    nie rozjeżdżały się w traktowaniu obwódki.
    """
    im = Image.open(src).convert("RGB")
    out = _clean_edge(_wypelnij_od_krawedzi(im))
    return _finish(out, dst, width, quality)


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
