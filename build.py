#!/usr/bin/env python3
"""Generator witryny kidalu.com. Wejście: content/ + src/. Wyjście: docs/."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "src" / "templates"
ASSETS = ROOT / "src" / "assets"
OUT = ROOT / "docs"

LANGS = ["pl", "de", "en"]
DEFAULT_LANG = "pl"
SITE_HOST = "https://kidalu.com"


def load_lang(lang: str) -> dict:
    return json.loads((CONTENT / f"{lang}.json").read_text("utf-8"))


def prefix(lang: str) -> str:
    """Prefiks ścieżki dla języka. Domyślny język siedzi w korzeniu."""
    return "" if lang == DEFAULT_LANG else f"/{lang}"


def page_urls(c: dict, lang: str) -> dict[str, str]:
    """Mapa klucz strony -> adres URL, dla jednego języka."""
    s = c["slugs"]
    p = prefix(lang)
    return {"home": f"{p}/"}


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _write(url: str, html: str) -> Path:
    target = OUT / url.strip("/") / "index.html" if url.strip("/") else OUT / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, "utf-8")
    return target


def build() -> list[Path]:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copytree(ASSETS, OUT / "assets")

    env = _env()
    written: list[Path] = []

    for lang in LANGS:
        path = CONTENT / f"{lang}.json"
        if not path.exists():
            continue
        c = load_lang(lang)
        urls = page_urls(c, lang)
        ctx = {
            "lang": lang,
            "c": c,
            "url": lambda key, u=urls: u[key],
            "asset": lambda rel: f"/assets/{rel}",
        }
        written.append(_write(urls["home"], env.get_template("home.html.jinja").render(**ctx)))

    return written


if __name__ == "__main__":
    files = build()
    print(f"zapisano {len(files)} stron")
