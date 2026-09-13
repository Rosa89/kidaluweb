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


def variants(src: Path, widths, quality: int = 82) -> list[Path]:
    """Mniejsze kopie gotowego assetu dla srcset, zapisane obok jako <nazwa>-<szerokość>w.webp.

    Źródłem jest już wycięty i przycięty webp, więc zostaje samo skalowanie.
    Szerokości równe oryginałowi lub większe są pomijane — powiększenie nic nie daje.
    """
    im = Image.open(src).convert("RGBA")
    out: list[Path] = []
    for width in sorted(widths):
        if width >= im.width:
            continue
        dst = src.with_name(f"{src.stem}-{width}w.webp")
        _scale_to_width(im, width).save(dst, format="WEBP", quality=quality, method=6)
        out.append(dst)
    return out


def portrait(src: Path, width: int, quality: int = 82) -> Path:
    """Środkowy pas szerokiej grafiki tła o szerokości `width` i pełnej wysokości,
    zapisany obok jako <nazwa>-portrait.webp.

    Tło w trybie cover na ekranie w pionie skaluje się do wysokości, więc widać
    tylko jego środek. Wycinek w tej samej skali wygląda identycznie, a waży ułamek
    całości. Na ekranach szerszych niż proporcje wycinka potrzebny jest oryginał.
    """
    im = Image.open(src)
    left = (im.width - width) // 2
    dst = src.with_name(f"{src.stem}-portrait.webp")
    im.crop((left, 0, left + width, im.height)).save(dst, format="WEBP", quality=quality, method=6)
    return dst


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

# Runda 2 (Ruling 46): próg powierzchni WZGLĘDNY wobec pola kadru (dawne
# UDZIAL_DZIURY=8e-5) został odrzucony jako podejście. Był niezmienniczy
# względem skali (to co miał naprawić — i naprawił), ale przy natywnej
# rozdzielczości far.jpg (3392×1248, próg ≈339 px) prześwity między gałęziami
# świerków i listkami paproci mają w tym materiale 80–194 px w gotowym
# assecie, czyli ok. 160–388 px w źródle — konkretnie poniżej progu, więc
# dalej były uznawane za treść. Podkręcanie współczynnika w dół jest kruche:
# trafia między najmniejszą zamierzoną bielą (kwiatki na `ground`, do ok.
# 75 px w źródle) a najmniejszym realnym prześwitem w innym materiale, ale ten
# przedział przesuwa się z każdą nową grafiką i nie ma go jak zweryfikować raz
# a dobrze — sam rozkład rozmiarów w `far.jpg` jest ciągły (patrz commit),
# bez czystej luki do wycelowania.
#
# Zamiast zgadywać z rozkładu rozmiarów: wywołujący jawnie deklaruje, czy
# warstwa ma jakąkolwiek zamierzoną białą treść (patrz `zamierzona_biel_px`
# niżej). Domyślnie nie ma — więc każdy zamknięty biały obszar, niezależnie od
# rozmiaru, jest prześwitem tła i znika. To odróżnia „ta warstwa nie ma
# zamierzonej bieli" (far/mid/fg) od „ta warstwa ma drobne białe elementy do
# zachowania, oto jak duże" (ground) — i jest odporne na to, że przyszły
# materiał przesunie rozkład rozmiarów: nowy materiał bez zamierzonej bieli
# dalej dostaje 0, a każda warstwa z zamierzoną bielą dostaje próg zmierzony
# na tym konkretnym źródle w momencie jego przygotowania, a nie odziedziczony
# po innym pliku.


def _wypelnij_od_krawedzi(im: Image.Image, *, zamierzona_biel_px: int = 0) -> Image.Image:
    """Wypełnia biel od krawędzi kadru: co jest białe i połączone z brzegiem,
    jest tłem. Każdy ZAMKNIĘTY biały obszar (niedotykający brzegu kadru) też
    jest tłem — chyba że wywołujący jawnie zadeklarował `zamierzona_biel_px`:
    górną granicę powierzchni (w pikselach źródła), poniżej której zamknięty
    biały obszar ma zostać uznany za zamierzoną treść, a nie za prześwit tła
    (np. drobne kwiatki na murawie w `ground`).

    Domyślnie `zamierzona_biel_px=0`: warstwa nie ma żadnej zamierzonej
    bieli, więc KAŻDY zamknięty biały obszar — bez względu na rozmiar —
    staje się przezroczysty. Komponenty dotykające brzegu kadru są tłem
    zawsze, niezależnie od tego progu.
    """
    import numpy as np
    from scipy import ndimage

    a = np.asarray(im)

    near_white = a.min(axis=2) > PROG_BIELI
    lab, n = ndimage.label(near_white)
    brzeg = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    brzeg.discard(0)

    rozmiary = ndimage.sum(near_white, lab, range(1, n + 1)) if n else []
    zamkniete_tlo = {
        i + 1 for i, r in enumerate(rozmiary)
        if (i + 1) not in brzeg and r > zamierzona_biel_px
    }
    tlo = np.isin(lab, list(brzeg | zamkniete_tlo))

    alpha = np.where(tlo, 0, 255).astype("uint8")
    return Image.fromarray(np.dstack([a, alpha]), "RGBA")


# `ground.jpg` to jedyna warstwa z zamierzoną bielą: drobne kwiatki na
# murawie. Zmierzone na assets-source/ground.jpg (3584×1184): WSZYSTKIE 63
# zamknięte białe obszary w tym źródle to kwiatki — rozkład rozmiarów zaczyna
# się od 75 px (bbox 12×8) i opada (71, 43, 22, 14, ...); murawa to ciągła
# tekstura bez luk, więc nie ma w tym źródle żadnego realnego prześwitu tła
# do pomylenia z kwiatkiem. Próg ustawiony z ok. 2× marginesem nad zmierzonym
# maksimum.
GROUND_ZAMIERZONA_BIEL_PX = 150


def prepare_band(
    src: Path, dst: Path, width: int, quality: int = 82, *, zamierzona_biel_px: int = 0
) -> dict:
    """Wariant dla szerokich warstw tła.

    `rembg` wykrywa obiekt wyróżniający się, więc na pasie z wieloma drobnymi
    elementami potrafi uznać część roślinności za tło i ją skasować. Tutaj
    zamiast tego wypełniamy biel od krawędzi kadru (`_wypelnij_od_krawedzi`),
    a krawędź czyścimy tym samym zabiegiem co w `prepare()`, żeby obie ścieżki
    nie rozjeżdżały się w traktowaniu obwódki.

    `zamierzona_biel_px`: deklaracja wywołującego, czy ta konkretna warstwa ma
    zamierzoną białą treść (patrz `_wypelnij_od_krawedzi`). Domyślnie 0 — brak
    zamierzonej bieli, każdy zamknięty biały obszar (prześwit tła) znika,
    niezależnie od jego rozmiaru. Jednostka to piksele ŹRÓDŁA, przed
    skalowaniem do `width`.
    """
    im = Image.open(src).convert("RGB")
    out = _clean_edge(_wypelnij_od_krawedzi(im, zamierzona_biel_px=zamierzona_biel_px))
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
