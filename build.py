#!/usr/bin/env python3
"""Generator witryny kidalu.com. Wejście: content/ + src/. Wyjście: docs/."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "src" / "templates"
POSTS = CONTENT / "poradnik"
ASSETS = ROOT / "src" / "assets"
OUT = ROOT / "docs"

LANGS = ["pl", "de", "en"]
DEFAULT_LANG = "pl"
SITE_HOST = "https://kidalu.com"

# Pełne kody lokalizacji dla Open Graph — Facebook/LinkedIn nie rozumieją
# samego "pl", oczekują pary język_REGION.
OG_LOCALES = {"pl": "pl_PL", "de": "de_DE", "en": "en_US"}

# Profil wydawcy w Google Play — jedyny zewnętrzny adres, który jednoznacznie
# łączy nazwę Kidalu z tą stroną; stąd sameAs w danych strukturalnych.
PLAY_DEV_URL = "https://play.google.com/store/apps/developer?id=Kidalu"

# Profile Kidalu poza stroną — trafiają do sameAs w danych strukturalnych
# i do stopki; każdy z nich potwierdza Google, że "Kidalu" to ta witryna.
SOCIAL = [
    {"key": "youtube", "url": "https://www.youtube.com/@KidaluOfficial"},
    {"key": "facebook", "url": "https://www.facebook.com/profile.php?id=61593516255677"},
]

# Weryfikacja własności witryny w Bing Webmaster Tools — tag ma zostać na
# stałe, Bing sprawdza go okresowo.
BING_SITE_VERIFICATION = "284E4F1B23AF02D0B0517E29AAC31E74"

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
        "o_nas": f"{p}/{s['o_nas']}/",
        "poradnik": f"{p}/{s['poradnik']}/",
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
        if key == "poradnik" and not articles(l):
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


FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)


@dataclass
class Article:
    """Wpis poradnika wczytany z content/poradnik/<lang>/<slug>.md.

    Nagłówek YAML-owy ogranicza się do par klucz: wartość — tyle wystarcza,
    a nie ciągnie za sobą zależności od parsera YAML.
    """
    lang: str
    slug: str
    title: str
    description: str
    date: str
    key: str
    app: str | None
    body_md: str
    path: Path
    translations: dict[str, str] = field(default_factory=dict)

    @property
    def url(self) -> str:
        c = load_lang(self.lang)
        return f"{prefix(self.lang)}/{c['slugs']['poradnik']}/{self.slug}/"

    @property
    def html(self) -> str:
        return markdown.markdown(self.body_md, extensions=["extra"], output_format="html5")


def _parse_article(path: Path, lang: str) -> Article:
    text = path.read_text("utf-8")
    m = FRONT.match(text)
    if not m:
        raise ValueError(f"{path}: brak nagłówka --- ... ---")
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    for required in ("title", "description", "date", "key"):
        if not meta.get(required):
            raise ValueError(f"{path}: brak pola {required}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["date"]):
        raise ValueError(f"{path}: data ma być w formacie YYYY-MM-DD")
    if meta.get("app") and meta["app"] not in APPS:
        raise ValueError(f"{path}: nieznana aplikacja {meta['app']}")
    return Article(
        lang=lang, slug=path.stem, title=meta["title"], description=meta["description"],
        date=meta["date"], key=meta["key"], app=meta.get("app") or None,
        body_md=text[m.end():], path=path,
    )


def articles(lang: str) -> list[Article]:
    """Artykuły danego języka, najnowsze pierwsze; translations wskazuje wersje
    tego samego wpisu (ten sam key) w pozostałych językach."""
    by_lang: dict[str, list[Article]] = {}
    for l in available_langs():
        d = POSTS / l
        by_lang[l] = [_parse_article(p, l) for p in sorted(d.glob("*.md"))] if d.exists() else []
    for a in by_lang.get(lang, []):
        a.translations = {
            l: b.url for l, items in by_lang.items() for b in items if b.key == a.key
        }
    return sorted(by_lang.get(lang, []), key=lambda a: (a.date, a.title), reverse=True)


@dataclass
class Page:
    """Jedna wygenerowana strona wraz z tym, co potrzebne do sitemapy."""
    url: str
    lang: str
    key: str
    sources: list[Path] = field(default_factory=list)
    alts: dict[str, str] | None = None  # jawne alternatywy (artykuły); domyślnie alternates(key)


def lastmod(sources: list[Path]) -> str:
    """Data ostatniej zmiany strony (YYYY-MM-DD) na podstawie jej plików źródłowych.

    Bierzemy datę ostatniego commita dotykającego źródeł; jeśli któreś z nich ma
    niezacommitowane zmiany albo gita nie ma, uczciwiej podać dzisiejszą datę niż
    sfałszować starą — Google traktuje lastmod poważnie tylko wtedy, gdy jest
    wiarygodny.
    """
    rels = [str(p.relative_to(ROOT)) for p in sources if p.exists()]
    if not rels:
        return date.today().isoformat()
    try:
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", *rels],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if dirty:
            return date.today().isoformat()
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", *rels],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or date.today().isoformat()
    except (OSError, subprocess.CalledProcessError):
        return date.today().isoformat()


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


def _url_entry(page: Page) -> list[str]:
    alts = page.alts if page.alts is not None else alternates(page.key)
    lines = ["  <url>", f"    <loc>{SITE_HOST}{page.url}</loc>",
             f"    <lastmod>{lastmod(page.sources)}</lastmod>"]
    for l, u in alts.items():
        lines.append(f'    <xhtml:link rel="alternate" hreflang="{l}" href="{SITE_HOST}{u}"/>')
    if DEFAULT_LANG in alts:
        lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE_HOST}{alts[DEFAULT_LANG]}"/>')
    lines.append("  </url>")
    return lines


def sitemap_xml(pages: list[Page]) -> str:
    """Sitemapa jednego języka z lastmod i alternatywami (xhtml:link).

    Google zaleca podawanie wersji językowych dla każdej strony z grupy —
    także wpis wskazujący na samego siebie.
    """
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for page in sorted(pages, key=lambda p: p.url):
        lines += _url_entry(page)
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def sitemap_name(lang: str) -> str:
    return f"sitemap-{lang}.xml"


def sitemap_index_xml(langs: list[str], pages: list[Page]) -> str:
    """Indeks sitemap: jeden plik na język. Nie zmienia to nic w rankingu,
    ale Search Console i Bing raportują wtedy indeksowanie osobno dla każdej
    wersji językowej, więc widać, która kuleje."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for lang in langs:
        newest = max(lastmod(p.sources) for p in pages if p.lang == lang)
        lines += ["  <sitemap>", f"    <loc>{SITE_HOST}/{sitemap_name(lang)}</loc>",
                  f"    <lastmod>{newest}</lastmod>", "  </sitemap>"]
    lines.append("</sitemapindex>")
    return "\n".join(lines) + "\n"


def write_meta(pages: list[Page]) -> None:
    (OUT / "CNAME").write_text("kidalu.com\n", "utf-8")
    (OUT / ".nojekyll").write_text("", "utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_HOST}/sitemap.xml\n", "utf-8"
    )
    langs = [l for l in LANGS if any(p.lang == l for p in pages)]
    for lang in langs:
        (OUT / sitemap_name(lang)).write_text(
            sitemap_xml([p for p in pages if p.lang == lang]), "utf-8")
    (OUT / "sitemap.xml").write_text(sitemap_index_xml(langs, pages), "utf-8")


def build() -> list[Path]:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copytree(ASSETS, OUT / "assets")
    stamp_css(OUT / "assets" / "css" / "site.css")

    env = _env()
    written: list[Path] = []
    pages: list[Page] = []
    base_src = [ROOT / "build.py", TEMPLATES / "base.html.jinja"]

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
            "og_locale": OG_LOCALES.get(lang, lang),
            "og_locale_alternates": [OG_LOCALES.get(l, l) for l in available_langs() if l != lang],
            "legal": legal_links(c, urls, lang),
            "app": None,
            "play_url": None,
            "play_dev_url": PLAY_DEV_URL,
            "social": SOCIAL,
            "bing_verification": BING_SITE_VERIFICATION,
            "noindex": False,
            "home_urls": {l: page_urls(load_lang(l), l)["home"] for l in available_langs()},
            "load_lang": load_lang,
            "has_blog": bool(articles(lang)),
        }
        lang_src = base_src + [path]
        written.append(_write(urls["home"], env.get_template("home.html.jinja").render(**ctx)))
        pages.append(Page(urls["home"], lang, "home", lang_src + [TEMPLATES / "home.html.jinja"]))

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
            pages.append(Page(urls[app_key], lang, app_key, lang_src + [TEMPLATES / "app.html.jinja"]))

            if lang in doc_langs(app_key):
                written.append(_write(urls[docs_key], env.get_template("docs.html.jinja").render(
                    **{**ctx,
                       "page_key": docs_key,
                       "alternates": alternates(docs_key),
                       "app": c["apps"][app_key],
                       "doc_html": Markup(doc_path(app_key, lang).read_text("utf-8"))},
                )))
                pages.append(Page(urls[docs_key], lang, docs_key,
                                  lang_src + [TEMPLATES / "docs.html.jinja", doc_path(app_key, lang)]))

        written.append(_write(urls["kontakt"], env.get_template("contact.html.jinja").render(
            **{**ctx, "page_key": "kontakt", "alternates": alternates("kontakt")},
        )))
        pages.append(Page(urls["kontakt"], lang, "kontakt", lang_src + [TEMPLATES / "contact.html.jinja"]))

        written.append(_write(urls["o_nas"], env.get_template("about.html.jinja").render(
            **{**ctx, "page_key": "o_nas", "alternates": alternates("o_nas")},
        )))
        pages.append(Page(urls["o_nas"], lang, "o_nas", lang_src + [TEMPLATES / "about.html.jinja"]))

        posts = articles(lang)
        if posts:
            written.append(_write(urls["poradnik"], env.get_template("blog.html.jinja").render(
                **{**ctx, "page_key": "poradnik", "alternates": alternates("poradnik"), "posts": posts},
            )))
            pages.append(Page(urls["poradnik"], lang, "poradnik",
                              lang_src + [TEMPLATES / "blog.html.jinja"] + [a.path for a in posts]))
            for a in posts:
                art_src = lang_src + [TEMPLATES / "article.html.jinja", a.path]
                written.append(_write(a.url, env.get_template("article.html.jinja").render(
                    **{**ctx, "page_key": "artykul", "alternates": a.translations,
                       "post": a, "modified": lastmod(art_src),
                       "cta_app": c["apps"][a.app] if a.app else None,
                       "cta_url": urls[a.app] if a.app else None},
                )))
                pages.append(Page(a.url, lang, "artykul", art_src, alts=a.translations))

        if lang == DEFAULT_LANG:
            # GitHub Pages serwuje /404.html z korzenia dla każdego brakującego adresu.
            # Strona nie ma własnego adresu, więc nie trafia do sitemapy ani nie ma canonical.
            target = OUT / "404.html"
            target.write_text(env.get_template("notfound.html.jinja").render(
                **{**ctx, "page_key": "404", "alternates": {lang: "/404.html"}, "noindex": True},
            ), "utf-8")
            written.append(target)

    write_meta(pages)
    return written


if __name__ == "__main__":
    files = build()
    print(f"zapisano {len(files)} stron")
