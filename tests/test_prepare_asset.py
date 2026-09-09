import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image

from scipy import ndimage

from tools.prepare_asset import _wypelnij_od_krawedzi, prepare, prepare_band

ZRODLO = Path("/Users/srosinski/Downloads/Gemini_Generated_Image_gspb2dgspb2dgspb.jpeg")
FAR = ROOT / "assets-source" / "far.jpg"

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


# --- prepare_band() -----------------------------------------------------


def test_prepare_band_wypelnia_tlo_i_miesci_sie_w_budzecie(tmp_path):
    if not FAR.exists():
        pytest.skip(f"materiał testowy niedostępny na tej maszynie: {FAR}")
    out = tmp_path / "far.webp"
    info = prepare_band(FAR, out, width=2400)

    assert out.exists()
    assert info["bytes"] <= 180 * 1024, f"warstwa waży {info['bytes']} B, budżet to 180 KB"

    im = Image.open(out)
    assert im.mode == "RGBA"
    assert im.width == 2400
    alpha = np.asarray(im.getchannel("A"))
    # duże przerwy między koronami drzew muszą zniknąć: rogi kadru (niebo nad
    # koronami, w pobliżu granicy kadru) są przezroczyste
    assert alpha[0, 0] == 0 or alpha[0, -1] == 0, "brzeg kadru powinien być przezroczysty"
    # ale warstwa nie jest pusta — drzewa zostają nieprzezroczyste
    assert (alpha > 200).sum() > alpha.size * 0.2


def _ulamek_powierzchni_dziur(src_path: Path) -> tuple[float, int]:
    """Liczy `_wypelnij_od_krawedzi()` na źródle i mierzy ułamek powierzchni
    kadru zajęty przez ZAMKNIĘTE (nie dotykające krawędzi kadru) przezroczyste
    obszary — czyli konkretnie "dziury/przerwy", a nie całe niebo nad koronami
    (które i tak zawsze znika, bo dotyka brzegu albo jest ogromne). Duże,
    przypadkowo odłączone od brzegu płaty nieba (> 1% powierzchni kadru — treeline
    dotyka lewej/prawej krawędzi więc pojedyncze duże fragmenty potrafią stracić
    łączność z brzegiem) są pomijane, żeby metryka mierzyła wyłącznie przerwy
    między koronami, nie przypadkowe fragmenty nieba.

    Zwraca (ułamek_powierzchni, liczba_dziur).
    """
    im = Image.open(src_path).convert("RGB")
    out = _wypelnij_od_krawedzi(im)
    alpha = np.asarray(out.getchannel("A"))
    tlo = alpha == 0

    lab, n = ndimage.label(tlo)
    if n == 0:
        return 0.0, 0
    brzeg = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    brzeg.discard(0)

    area = tlo.shape[0] * tlo.shape[1]
    rozmiary = ndimage.sum(tlo, lab, range(1, n + 1))
    dziury = [r for i, r in enumerate(rozmiary) if (i + 1) not in brzeg and r < area * 0.01]
    return sum(dziury) / area, len(dziury)


def test_prog_dziury_niezmienniczy_wzgledem_skali(tmp_path):
    """Sedno błędu krytycznego (Ruling 38): próg powierzchni dziury musi być
    względny wobec pola kadru, inaczej po przeskalowaniu tej samej sceny do
    połowy rozdzielczości przerwy między koronami (420-1449 px przy 3392 px
    szerokości, 105-362 px przy połowie) przestają być klasyfikowane jako tło.

    Przetwarzamy TO SAMO źródło w dwóch rozdzielczościach (pełnej i połowie) i
    porównujemy ułamek powierzchni kadru zajęty przez zamknięte dziury — przy
    niezmienniczym progu powinien być niemal identyczny w obu skalach.
    """
    if not FAR.exists():
        pytest.skip(f"materiał testowy niedostępny na tej maszynie: {FAR}")

    frac_full, n_full = _ulamek_powierzchni_dziur(FAR)

    polowa_src = tmp_path / "far_half.jpg"
    im = Image.open(FAR).convert("RGB")
    im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(polowa_src, quality=95)
    frac_half, n_half = _ulamek_powierzchni_dziur(polowa_src)

    assert n_full > 5, "test wymaga realnych przerw między koronami w źródle"
    assert n_half > 5, (
        f"przy połowie rozdzielczości zniknęły niemal wszystkie dziury "
        f"({n_half} vs {n_full} przy pełnej) — próg nie jest niezmienniczy względem skali"
    )
    roznica = abs(frac_full - frac_half)
    assert roznica < 0.15 * frac_full, (
        f"ułamek powierzchni dziur różni się między skalami: pełna={frac_full:.5f} "
        f"(n={n_full}), połowa={frac_half:.5f} (n={n_half}), różnica={roznica:.5f} "
        "— próg powierzchni dziury nie jest niezmienniczy względem skali"
    )


def test_duzy_zamkniety_biale_obszar_znika_a_maly_zostaje(tmp_path):
    """Zamknięty biały obszar większy niż próg powierzchni staje się
    przezroczysty (dziura), a mały biały punkt (np. kwiatek) zostaje
    nieprzezroczysty — to jest kryterium poprawności progu z Ruling 38/40."""
    w, h = 300, 300
    a = np.full((h, w, 3), (40, 110, 50), dtype="uint8")  # zielone tło "treści"

    # duży zamknięty biały kwadrat (nie dotyka krawędzi kadru) — powinien zniknąć
    a[100:180, 100:180] = 255  # 80x80 = 6400 px, dużo powyżej progu

    # mały biały punkt (nie dotyka krawędzi kadru) — powinien zostać
    a[250:253, 250:253] = 255  # 3x3 = 9 px

    src = tmp_path / "synth.png"
    Image.fromarray(a, "RGB").save(src)

    out = tmp_path / "synth.webp"
    prepare_band(src, out, width=w)

    im = Image.open(out)
    assert im.size == (w, h), "brak białych pikseli na krawędzi -> bbox = cały obraz"
    alpha = np.asarray(im.getchannel("A"))

    assert alpha[140, 140] == 0, "duży zamknięty biały obszar powinien być przezroczysty"
    assert alpha[251, 251] > 200, "mały biały punkt powinien zostać nieprzezroczysty"


def test_obraz_bez_bialego_piksela_na_krawedzi_kadru(tmp_path):
    """Obraz, w którym żaden piksel na krawędzi kadru nie jest biały (a nawet
    żaden piksel w całym obrazie nie jest bliski bieli) — funkcja nie może się
    wywrócić na pustym zbiorze komponentów `brzeg`/`duze` i cały obraz zostaje
    nieprzezroczysty."""
    w, h = 120, 80
    a = np.full((h, w, 3), (30, 90, 40), dtype="uint8")  # jednolita zieleń, bez bieli

    src = tmp_path / "no_white.png"
    Image.fromarray(a, "RGB").save(src)

    out = tmp_path / "no_white.webp"
    info = prepare_band(src, out, width=w)

    assert out.exists()
    im = Image.open(out)
    if "A" in im.getbands():
        lo, hi = im.getchannel("A").getextrema()
        assert (lo, hi) == (255, 255), "obraz bez bieli powinien zostać w całości nieprzezroczysty"
    else:
        # brak kanału alfa w zapisie webp = obraz w pełni nieprzezroczysty
        # (Pillow/libwebp pomija kanał A, gdy jest wszędzie 255)
        assert im.mode == "RGB"
    assert info["size"] == (w, h)
