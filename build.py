#!/usr/bin/env python3
"""Generator witryny kidalu.com. Wejście: content/ + src/. Wyjście: docs/."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "src" / "templates"
ASSETS = ROOT / "src" / "assets"
OUT = ROOT / "docs"

LANGS = ["pl", "de", "en"]
DEFAULT_LANG = "pl"
SITE_HOST = "https://kidalu.com"

APPS = {
    "czytanie": "com.readbysyllables.app",
    "literki": "com.literkiicyferki.app",
}


def play_url(app_key: str) -> str:
    return f"https://play.google.com/store/apps/details?id={APPS[app_key]}"


def load_lang(lang: str) -> dict:
    return json.loads((CONTENT / f"{lang}.json").read_text("utf-8"))


def prefix(lang: str) -> str:
    """Prefiks ścieżki dla języka. Domyślny język siedzi w korzeniu."""
    return "" if lang == DEFAULT_LANG else f"/{lang}"


def page_urls(c: dict, lang: str) -> dict[str, str]:
    """Mapa klucz strony -> adres URL, dla jednego języka."""
    s = c["slugs"]
    p = prefix(lang)
    return {
        "home": f"{p}/",
        "czytanie": f"{p}/{s['czytanie']}/",
        "czytanie_docs": f"{p}/{s['czytanie']}/{s['docs']}/",
        "literki": f"{p}/{s['literki']}/",
        "literki_docs": f"{p}/{s['literki']}/{s['docs']}/",
        "kontakt": f"{p}/{s['kontakt']}/",
    }


def available_langs() -> list[str]:
    return [l for l in LANGS if (CONTENT / f"{l}.json").exists()]


def doc_path(app_key: str, lang: str) -> Path:
    return CONTENT / "docs" / f"{app_key}.{lang}.html"


def doc_langs(app_key: str) -> list[str]:
    return [l for l in available_langs() if doc_path(app_key, l).exists()]


def alternates(key: str) -> dict[str, str]:
    """Adresy tej samej strony w pozostałych językach — tylko te, które istnieją."""
    out: dict[str, str] = {}
    for l in available_langs():
        if key.endswith("_docs"):
            app_key = key[: -len("_docs")]
            if not doc_path(app_key, l).exists():
                continue
        urls = page_urls(load_lang(l), l)
        if key in urls:
            out[l] = urls[key]
    return out


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _write(url: str, html: str) -> Path:
    target = (OUT / url.strip("/") / "index.html") if url.strip("/") else (OUT / "index.html")
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
            "page_key": "home",
            "alternates": alternates("home"),
            "langs": available_langs(),
            "site_host": SITE_HOST,
        }
        written.append(_write(urls["home"], env.get_template("home.html.jinja").render(**ctx)))

        for app_key in APPS:
            docs_key = f"{app_key}_docs"
            docs_url = urls[docs_key] if lang in doc_langs(app_key) else None

            written.append(_write(urls[app_key], env.get_template("app.html.jinja").render(
                **{**ctx,
                   "page_key": app_key,
                   "alternates": alternates(app_key),
                   "app": c["apps"][app_key],
                   "play_url": play_url(app_key),
                   "docs_url": docs_url},
            )))

            if lang in doc_langs(app_key):
                written.append(_write(urls[docs_key], env.get_template("docs.html.jinja").render(
                    **{**ctx,
                       "page_key": docs_key,
                       "alternates": alternates(docs_key),
                       "app": c["apps"][app_key],
                       "doc_html": Markup(doc_path(app_key, lang).read_text("utf-8"))},
                )))

    return written


if __name__ == "__main__":
    files = build()
    print(f"zapisano {len(files)} stron")
