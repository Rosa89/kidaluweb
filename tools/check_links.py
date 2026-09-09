"""Sprawdza, czy każdy wewnętrzny odnośnik i hreflang w zbudowanej witrynie
wskazuje na istniejący plik."""
from __future__ import annotations

import re
import sys
from pathlib import Path

HREF = re.compile(r'''(?:href|src)=(["'])(.*?)\1''')


class Skip(Exception):
    """Adres świadomie poza zakresem walidatora (zewnętrzny albo sam fragment)."""


class Relative(Exception):
    """Odnośnik względny — w tym generatorze nie powinien nigdy powstać.

    asset() i url() zawsze zwracają ścieżkę od korzenia; jedyną drogą, którą
    względny odnośnik może się przemycić, jest surowa treść dokumentów
    prawnych wklejana z content/docs/*.html bez przepisania adresów przy
    przenoszeniu. To błąd, nie coś do pominięcia.
    """


def _resolve(root: Path, url: str) -> Path:
    """Zamienia adres wewnętrzny (od korzenia) na plik na dysku.

    Zgłasza Skip dla adresu świadomie poza zakresem (zewnętrzny, mailto,
    data, sam fragment) i Relative dla odnośnika względnego — to jest błąd,
    a nie coś do pominięcia.
    """
    if url.startswith(("http://", "https://", "mailto:", "#", "data:")):
        raise Skip(url)
    path = url.split("#")[0].split("?")[0]
    if not path.startswith("/"):
        raise Relative(url)
    target = root / path.lstrip("/")
    return target / "index.html" if path.endswith("/") else target


def check(root: Path) -> list[str]:
    problems: list[str] = []
    for page in sorted(root.rglob("*.html")):
        html = page.read_text("utf-8")
        for _quote, url in HREF.findall(html):
            try:
                target = _resolve(root, url)
            except Skip:
                continue
            except Relative:
                problems.append(
                    f"{page.relative_to(root)} → {url} "
                    "(odnośnik względny — w tej witrynie nie powinien wystąpić, "
                    "wskazuje na treść przeniesioną bez przepisania adresów)"
                )
                continue
            if not target.exists():
                problems.append(f"{page.relative_to(root)} → {url} (brak {target})")
    return problems


if __name__ == "__main__":
    found = check(Path(sys.argv[1] if len(sys.argv) > 1 else "docs"))
    for p in found:
        print(p)
    print(f"zepsutych odnośników: {len(found)}")
    sys.exit(1 if found else 0)
