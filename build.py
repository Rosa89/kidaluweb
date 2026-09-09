#!/usr/bin/env python3
"""Generator witryny kidalu.com. Wejście: content/ + src/. Wyjście: docs/."""
from __future__ import annotations

import hashlib
import json
import re
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


def asset_url(rel: str) -> str:
    """Adres assetu z odciskiem treści.

    Nazwy plików nie zmieniają się między wdrożeniami, więc bez tego przeglądarka
    potrafi trzymać starą grafikę po podmianie — zdarzyło się to przy wymianie
    sowy od czytania.
    """
    path = ASSETS / rel
    if not path.exists():
        return f"/assets/{rel}"
    digest = hashlib.md5(path.read_bytes()).hexdigest()[:8]
    return f"/assets/{rel}?v={digest}"


def stamp_css(css: Path) -> None:
    """Dokleja te same odciski do url(../img/...) w arkuszu, bo tamtych adresów
    szablon nie widzi."""
    def stamp(m: re.Match) -> str:
        return "url(../" + asset_url("img/" + m.group(1)).removeprefix("/assets/") + ")"

    text = re.sub(r"url\(\.\./img/([A-Za-z0-9._-]+)\)", stamp, css.read_text("utf-8"))
    css.write_text(text, "utf-8")


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


def legal_links(c: dict, urls: dict[str, str], lang: str) -> list[dict]:
    """Odnośniki do dokumentów prawnych istniejących w tym języku — do stopki.

    Google Play wymaga stabilnych adresów polityk, więc mają być osiągalne
    z każdej strony, nie tylko z podstrony aplikacji.
    """
    return [
        {"name": c["apps"][app_key]["name"], "url": urls[f"{app_key}_docs"]}
        for app_key in APPS
        if lang in doc_langs(app_key)
    ]


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


def write_meta(written: list[Path]) -> None:
    (OUT / "CNAME").write_text("kidalu.com\n", "utf-8")
    (OUT / ".nojekyll").write_text("", "utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_HOST}/sitemap.xml\n", "utf-8"
    )

    locs = []
    for p in sorted(written):
        if p.name != "index.html":
            continue
        rel = p.parent.relative_to(OUT).as_posix()
        url = SITE_HOST + ("/" if rel == "." else f"/{rel}/")
        locs.append(f"  <url><loc>{url}</loc></url>")

    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(locs)
        + "\n</urlset>\n",
        "utf-8",
    )


def build() -> list[Path]:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copytree(ASSETS, OUT / "assets")
    stamp_css(OUT / "assets" / "css" / "site.css")

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
            "asset": asset_url,
            "page_key": "home",
            "alternates": alternates("home"),
            "langs": available_langs(),
            "site_host": SITE_HOST,
            "legal": legal_links(c, urls, lang),
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

        written.append(_write(urls["kontakt"], env.get_template("contact.html.jinja").render(
            **{**ctx, "page_key": "kontakt", "alternates": alternates("kontakt")},
        )))

    write_meta(written)
    return written


if __name__ == "__main__":
    files = build()
    print(f"zapisano {len(files)} stron")
