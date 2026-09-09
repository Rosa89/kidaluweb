"""Sprawdza, czy każdy wewnętrzny odnośnik i hreflang w zbudowanej witrynie
wskazuje na istniejący plik."""
from __future__ import annotations

import re
import sys
from pathlib import Path

HREF = re.compile(r'(?:href|src)="([^"]+)"')


def _resolve(root: Path, url: str) -> Path | None:
    """Zamienia adres na plik na dysku. None oznacza adres, którego nie sprawdzamy."""
    if url.startswith(("http://", "https://", "mailto:", "#", "data:")):
        return None
    path = url.split("#")[0].split("?")[0]
    if not path.startswith("/"):
        return None
    target = root / path.lstrip("/")
    return target / "index.html" if path.endswith("/") else target


def check(root: Path) -> list[str]:
    problems: list[str] = []
    for page in sorted(root.rglob("*.html")):
        html = page.read_text("utf-8")
        for url in HREF.findall(html):
            target = _resolve(root, url)
            if target is not None and not target.exists():
                problems.append(f"{page.relative_to(root)} → {url} (brak {target})")
    return problems


if __name__ == "__main__":
    found = check(Path(sys.argv[1] if len(sys.argv) > 1 else "docs"))
    for p in found:
        print(p)
    print(f"zepsutych odnośników: {len(found)}")
    sys.exit(1 if found else 0)
