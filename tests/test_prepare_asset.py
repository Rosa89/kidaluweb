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
    """Sedno błędu krytycznego (Ruling 38), zaadaptowane w rundzie 2 (Ruling 46).

    Runda 1 wprowadziła próg powierzchni WZGLĘDNY wobec pola kadru
    (`UDZIAL_DZIURY=8e-5`) — sam w sobie faktycznie niezmienniczy względem
    skali, ale niezmienniczo trafiający w ZŁĄ wartość: przy natywnej
    rozdzielczości `far.jpg` (3392×1248) łapał tylko 15 z 52 realnych,
    zamkniętych prześwitów między koronami/gałęziami (próg ≈339 px, a
    prześwity mają w tym materiale 80–388 px w zależności od miejsca
    pomiaru) — reszta zostawała błędnie potraktowana jako treść. Ten sam
    test w swojej pierwotnej postaci PRZECHODZIŁ na tamtym kodzie (bo mierzył
    tylko niezmienniczość skali, nie kompletność wykrywania), więc recenzja
    (Ruling 46) słusznie nie uznała go za dowód poprawności.

    Runda 2 usuwa próg powierzchni w ogóle dla warstw bez zamierzonej bieli
    (`zamierzona_biel_px=0` domyślnie w `_wypelnij_od_krawedzi`) — KAŻDY
    zamknięty biały obszar jest tłem, więc wynik jest niezmienniczy względem
    skali TRYWIALNIE (nie ma już współczynnika, względem którego coś mogłoby
    przestać być niezmiennicze) i jednocześnie kompletny. Test poniżej
    sprawdza obie rzeczy na `far.jpg` w pełnej i połowie rozdzielczości:
    liczbę wykrytych zamkniętych prześwitów (musi być wysoka — konkretnie
    dużo wyższa niż 15, żeby odróżnić od dawnego, niekompletnego progu
    względnego) ORAZ że ułamek powierzchni kadru zajęty przez te prześwity
    jest spójny między skalami.
    """
    if not FAR.exists():
        pytest.skip(f"materiał testowy niedostępny na tej maszynie: {FAR}")

    frac_full, n_full = _ulamek_powierzchni_dziur(FAR)

    polowa_src = tmp_path / "far_half.jpg"
    im = Image.open(FAR).convert("RGB")
    im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(polowa_src, quality=95)
    frac_half, n_half = _ulamek_powierzchni_dziur(polowa_src)

    # Zmierzone: nowy kod (bez progu powierzchni) znajduje 52/55 zamkniętych
    # prześwitów (pełna/połowa); dawny próg względny (8e-5 pola kadru) —
    # tylko 15/16. Próg 40 jest wyraźnie powyżej dawnego zachowania i
    # wyraźnie poniżej nowego — regresja do progu powierzchni (jakiejkolwiek
    # wartości UDZIAL_DZIURY) sprowadzającego liczbę wykrytych prześwitów
    # poniżej pełnego zbioru komponentów zamkniętych musi tu paść.
    assert n_full > 40, (
        f"za mało wykrytych zamkniętych prześwitów przy pełnej rozdzielczości "
        f"({n_full}) — sugeruje, że jakiś próg powierzchni znów odcina realne "
        "prześwity zamiast usuwać każdy zamknięty biały obszar"
    )
    assert n_half > 40, (
        f"przy połowie rozdzielczości zniknęła większość prześwitów "
        f"({n_half} vs {n_full} przy pełnej) — wykrywanie nie jest niezmiennicze "
        "względem skali"
    )
    roznica = abs(frac_full - frac_half)
    assert roznica < 0.15 * frac_full, (
        f"ułamek powierzchni dziur różni się między skalami: pełna={frac_full:.5f} "
        f"(n={n_full}), połowa={frac_half:.5f} (n={n_half}), różnica={roznica:.5f} "
        "— wykrywanie prześwitów nie jest niezmiennicze względem skali"
    )


def test_bez_deklaracji_kazdy_zamkniety_biale_obszar_znika(tmp_path):
    """Runda 2 (Ruling 46): bez jawnej deklaracji zamierzonej bieli
    (`zamierzona_biel_px` domyślnie 0) warstwa nie ma żadnej zamierzonej
    bieli, więc KAŻDY zamknięty biały obszar znika — zarówno duży (dawna
    "dziura"), jak i mały (dawny "kwiatek"). Zgadywanie klasyfikacji z samej
    powierzchni komponentu (Ruling 38/40) zastąpione jawną deklaracją
    wywołującego — patrz `test_zadeklarowana_biel_zachowuje_male_a_duze_nadal_znikaja`
    niżej dla warstwy, która taką biel ma."""
    w, h = 300, 300
    a = np.full((h, w, 3), (40, 110, 50), dtype="uint8")  # zielone tło "treści"

    # duży zamknięty biały kwadrat (nie dotyka krawędzi kadru)
    a[100:180, 100:180] = 255  # 80x80 = 6400 px

    # mały biały punkt (nie dotyka krawędzi kadru)
    a[250:253, 250:253] = 255  # 3x3 = 9 px

    src = tmp_path / "synth.png"
    Image.fromarray(a, "RGB").save(src)

    out = tmp_path / "synth.webp"
    prepare_band(src, out, width=w)  # bez deklaracji -> zamierzona_biel_px=0

    im = Image.open(out)
    assert im.size == (w, h), "brak białych pikseli na krawędzi -> bbox = cały obraz"
    alpha = np.asarray(im.getchannel("A"))

    assert alpha[140, 140] == 0, "duży zamknięty biały obszar powinien być przezroczysty"
    assert alpha[251, 251] == 0, "bez deklaracji mały biały punkt też powinien zniknąć"


def test_zadeklarowana_biel_zachowuje_male_a_duze_nadal_znikaja(tmp_path):
    """Gdy wywołujący jawnie deklaruje próg zamierzonej bieli (np. dla warstwy
    z kwiatkami na murawie), mały zamknięty biały obszar mieszczący się w
    progu zostaje nieprzezroczysty, a duży (powyżej progu) nadal znika —
    dokładnie mechanizm użyty dla `ground` (`GROUND_ZAMIERZONA_BIEL_PX`)."""
    w, h = 300, 300
    a = np.full((h, w, 3), (40, 110, 50), dtype="uint8")  # zielone tło "treści"

    a[100:180, 100:180] = 255  # 80x80 = 6400 px — nadal powinien zniknąć
    a[250:253, 250:253] = 255  # 3x3 = 9 px — poniżej progu, powinien zostać

    src = tmp_path / "synth.png"
    Image.fromarray(a, "RGB").save(src)

    out = tmp_path / "synth.webp"
    prepare_band(src, out, width=w, zamierzona_biel_px=50)

    im = Image.open(out)
    assert im.size == (w, h)
    alpha = np.asarray(im.getchannel("A"))

    assert alpha[140, 140] == 0, "duży zamknięty biały obszar powinien nadal być przezroczysty"
    assert alpha[251, 251] > 200, "zadeklarowana zamierzona biel powinna zostać nieprzezroczysta"


def test_bez_zamierzonej_bieli_dziura_rzedu_100px_znika(tmp_path):
    """Sedno poprawki rundy 2 (Ruling 46): w warstwie BEZ zamierzonej bieli
    (domyślne wywołanie `prepare_band`, dokładnie jak dla far/mid/fg) zamknięty
    biały obszar o powierzchni rzędu stu pikseli MUSI zniknąć.

    Kanwa 2000×1200 (pole 2 400 000 px) dobrana tak, żeby dawny próg WZGLĘDNY
    wobec pola kadru z rundy 1 (`UDZIAL_DZIURY=8e-5` → próg = 2 400 000 × 8e-5
    = 192 px) był WYŻSZY niż powierzchnia tej dziury (11×11 = 121 px) — czyli
    ten test odtwarza dokładnie defekt, który recenzja wykryła piksel w piksel
    w `far`/`fg`: bboxy rzędu 9–18 px, powierzchnia 80–194 px, próg rzędu
    339 px przy natywnej rozdzielczości `far.jpg`. Ten test PADA na kodzie
    rundy 1 (próg względny) — sprawdzone i zapisane w raporcie."""
    w, h = 2000, 1200
    a = np.full((h, w, 3), (40, 110, 50), dtype="uint8")  # zielone tło "treści"

    # mały biały narożnik dotykający krawędzi (jak skrawek nieba w far.jpg) —
    # zapewnia, że kanał alfa realnie istnieje w zapisie (bez tego, przy
    # starym kodzie, cały obraz wychodzi w pełni nieprzezroczysty i webp w
    # ogóle traci kanał A, co maskowałoby błąd wyjątkiem zamiast asercją).
    # Wystarczająco mały, żeby nie ruszyć bbox przycinania do zawartości.
    a[0:3, 0:3] = 255

    y0, x0 = h // 2, w // 2
    a[y0 : y0 + 11, x0 : x0 + 11] = 255  # 11x11 = 121 px, zamknięty, rzędu 100 px

    src = tmp_path / "synth_no_intent.png"
    Image.fromarray(a, "RGB").save(src)

    out = tmp_path / "synth_no_intent.webp"
    prepare_band(src, out, width=w)  # bez deklaracji -> zamierzona_biel_px=0

    im = Image.open(out)
    assert im.size == (w, h), "opaque tło na krawędziach -> crop to bbox = cały kadr"
    alpha = np.asarray(im.getchannel("A"))

    assert alpha[y0 + 5, x0 + 5] == 0, (
        "zamknięty biały obszar rzędu 100 px w warstwie bez zamierzonej bieli "
        "musi stać się przezroczysty — pod starym progiem względnym "
        "(8e-5 pola kadru = 192 px na tej kanwie) zostawał błędnie nieprzezroczysty"
    )


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
