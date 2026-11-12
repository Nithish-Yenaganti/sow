"""Code scan: collect per-page and site-level facts from the repo (offline).

Also provides `analyze_html`, shared with the live scan, which turns an HTML
document into the same per-page facts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from selectolax.lexbor import LexborHTMLParser as HTMLParser

from findable.detect import App, _walk

SOURCE_EXTS = {".tsx", ".jsx", ".ts", ".js", ".mjs", ".vue", ".svelte", ".astro", ".mdx", ".md", ".html"}
WORD_RE = re.compile(r"[\w'-]+", re.U)


# --------------------------------------------------------------------------- HTML

def analyze_html(html: str, page_url: str = "/") -> dict:
    """Facts from one HTML document. `page_url` resolves relative links."""
    tree = HTMLParser(html)
    head_title = tree.css_first("title")
    facts: dict = {
        "title": head_title.text(strip=True) if head_title else None,
        "description": None, "canonical": None, "noindex": False,
        "h1_count": 0, "images_no_alt": [], "ld_types": [], "ld_errors": [],
        "links": [], "word_count": 0, "questions_without_answer": [],
        "has_gsc_verification": False, "has_clarity": False,
    }
    for m in tree.css("meta"):
        name = (m.attributes.get("name") or m.attributes.get("property") or "").lower()
        content = m.attributes.get("content") or ""
        if name == "description":
            facts["description"] = content.strip()
        elif name in ("robots", "googlebot") and "noindex" in content.lower():
            facts["noindex"] = True
        elif name == "google-site-verification":
            facts["has_gsc_verification"] = True
    for l in tree.css("link"):
        if (l.attributes.get("rel") or "").lower() == "canonical":
            facts["canonical"] = l.attributes.get("href")
    for s in tree.css('script[type="application/ld+json"]'):
        raw = s.text() or ""
        try:
            data = json.loads(raw)
        except ValueError as e:
            facts["ld_errors"].append(f"invalid JSON-LD: {e}")
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for it in items:
            if isinstance(it, dict):
                t = it.get("@type")
                facts["ld_types"] += t if isinstance(t, list) else [t] if t else []
    for s in tree.css("script"):
        src = (s.attributes.get("src") or "") + (s.text() or "")[:2000]
        if "clarity.ms" in src:
            facts["has_clarity"] = True
    facts["h1_count"] = len(tree.css("h1"))
    for img in tree.css("img"):
        alt = img.attributes.get("alt")
        if alt is None:
            facts["images_no_alt"].append(img.attributes.get("src") or "(no src)")
    host = urlparse(page_url).netloc
    for a in tree.css("a[href]"):
        href = a.attributes.get("href") or ""
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absu = urlparse(urljoin(page_url if page_url.startswith("http") else "http://x" + page_url, href))
        if absu.netloc in (host, "x", ""):
            path = absu.path.rstrip("/") or "/"
            if path not in facts["links"]:
                facts["links"].append(path)
    # Question headings: is there a direct answer right after?
    for h in tree.css("h2, h3"):
        text = h.text(strip=True)
        if not text.endswith("?"):
            continue
        nxt = h.next
        while nxt is not None and (nxt.tag or "").startswith(("-", "_")) and not (
                nxt.tag == "-text" and (nxt.text() or "").strip()):
            nxt = nxt.next
        answer_words = len(WORD_RE.findall(nxt.text())) if nxt is not None and nxt.tag in ("p", "ul", "ol", "div") else 0
        if answer_words == 0 or answer_words > 120:
            facts["questions_without_answer"].append(text)
    body = tree.body
    if body is not None:
        for bad in body.css("script, style, noscript, template, svg"):
            bad.decompose()
        facts["word_count"] = len(WORD_RE.findall(body.text(separator=" ")))
    return facts


# --------------------------------------------------------------------------- Next.js source heuristics

USE_CLIENT = re.compile(r"""^\s*(?:(?://[^\n]*|/\*.*?\*/)\s*)*['"]use client['"]""", re.S)
HAS_METADATA = re.compile(r"export\s+(?:const\s+metadata\b|(?:async\s+)?function\s+generateMetadata\b)")
TITLE_RE = re.compile(r"(?:\btitle\s*:|<title[\s>])")
DESC_RE = re.compile(r"""(?:\bdescription\s*:|name=["']description["'])""")
CANON_RE = re.compile(r"\bcanonical\s*:|rel=[\"']canonical")
NOINDEX_RE = re.compile(r"\bindex\s*:\s*false|noindex")
LD_RE = re.compile(r"application/ld\+json")
IMG_TAG = re.compile(r"<(img|Image)\b([^>]*)>", re.S)
H1_RE = re.compile(r"<h1[\s>]")


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def _layout_chain(project_root: Path, page_file: Path) -> list[Path]:
    """layout.* files from the app dir root down to the page's folder."""
    parts = page_file.parent.parts
    root_len = len(project_root.parts)
    try:
        i = parts.index("app", root_len)       # first "app" dir *inside* the project
    except ValueError:
        return []
    chain = []
    for j in range(i, len(parts)):
        d = Path(*parts[: j + 1])
        for ext in (".tsx", ".jsx", ".ts", ".js"):
            f = d / f"layout{ext}"
            if f.is_file():
                chain.append(f)
                break
    return chain


def _next_page_facts(project_root: Path, rel_file: str) -> dict:
    f = project_root / rel_file
    text = f.read_text(encoding="utf-8", errors="ignore")
    layouts = [l for l in _layout_chain(project_root, f) if l != f]
    layout_texts = {str(l.relative_to(project_root)): l.read_text(encoding="utf-8", errors="ignore") for l in layouts}
    own_meta = bool(HAS_METADATA.search(text)) or "next/head" in text
    facts: dict = {
        "client_rendered": bool(USE_CLIENT.search(text)),
        "own_metadata": own_meta,
        "title": "present" if TITLE_RE.search(text) else None,
        "description": "present" if DESC_RE.search(text) else None,
        "canonical": "present" if CANON_RE.search(text) else None,
        "noindex": bool(NOINDEX_RE.search(text)),
        "ld_types": ["(in code)"] if LD_RE.search(text) else [],
        "ld_errors": [], "links": [], "questions_without_answer": [],
        "h1_count": len(H1_RE.findall(text)),
        "images_no_alt": [],
        "title_from_layout": None,
    }
    for lpath, lt in layout_texts.items():
        if facts["title"] is None and TITLE_RE.search(lt):
            facts["title_from_layout"] = lpath
        if facts["description"] is None and DESC_RE.search(lt):
            facts["description"] = f"inherited from {lpath}"
        if facts["canonical"] is None and CANON_RE.search(lt):
            facts["canonical"] = f"inherited from {lpath}"
        if NOINDEX_RE.search(lt):
            facts["noindex"] = True
            facts["noindex_from"] = lpath
        if LD_RE.search(lt) and not facts["ld_types"]:
            facts["ld_types"] = [f"(in {lpath})"]
    for m in IMG_TAG.finditer(text):
        if not re.search(r"\balt\s*=", m.group(2)):
            facts["images_no_alt"].append(f"{rel_file}:{_line_of(text, m.start())}")
    m = USE_CLIENT.search(text)
    facts["client_line"] = _line_of(text, m.end()) if m else None
    return facts


# --------------------------------------------------------------------------- site files

def _site_files(app_dir: Path, project_root: Path) -> dict:
    def rel(p: Path) -> str:
        return str(p.relative_to(project_root))

    out: dict = {"robots": None, "robots_text": None, "sitemap": None}
    robots_candidates = ["app/robots.ts", "app/robots.js", "src/app/robots.ts", "src/app/robots.js",
                         "public/robots.txt", "static/robots.txt", "robots.txt"]
    sitemap_candidates = ["app/sitemap.ts", "app/sitemap.js", "app/sitemap.xml", "src/app/sitemap.ts",
                          "src/app/sitemap.js", "public/sitemap.xml", "public/sitemap-index.xml",
                          "static/sitemap.xml", "sitemap.xml", "next-sitemap.config.js", "next-sitemap.config.cjs"]
    for c in robots_candidates:
        p = app_dir / c
        if p.is_file():
            out["robots"] = rel(p)
            if p.suffix == ".txt":
                out["robots_text"] = p.read_text(encoding="utf-8", errors="ignore")
            break
    for c in sitemap_candidates:
        p = app_dir / c
        if p.is_file():
            out["sitemap"] = rel(p)
            break
    pkg = app_dir / "package.json"
    if out["sitemap"] is None and pkg.is_file():
        t = pkg.read_text()
        if "@astrojs/sitemap" in t or "@nuxtjs/sitemap" in t or "next-sitemap" in t:
            out["sitemap"] = rel(pkg) + " (sitemap plugin)"
    return out


def _orphans(app: App, project_root: Path) -> set[str]:
    """Routes whose path never appears as a link target anywhere in the source."""
    app_dir = project_root / app.root
    corpus = []
    for f in _walk(app_dir, 10):
        if f.suffix in SOURCE_EXTS and f.stat().st_size < 500_000:
            corpus.append((str(f.relative_to(project_root)), f.read_text(encoding="utf-8", errors="ignore")))
    orphans = set()
    for r in app.routes:
        if r.path == "/" or r.dynamic:
            continue
        pat = re.compile(r"""(?:href\s*=\s*\{?\s*|to\s*=\s*\{?\s*|['"`])""" + re.escape(r.path) + r"""/?['"`#?]""")
        if not any(pat.search(t) for name, t in corpus if name != r.file):
            orphans.add(r.path)
    return orphans


# --------------------------------------------------------------------------- entry

def scan_code(app: App, project_root: str | Path) -> dict:
    root = Path(project_root).resolve()
    app_dir = root / app.root
    pages: dict[str, dict] = {}
    for r in app.routes:
        if r.dynamic:
            continue
        if app.framework.startswith("nextjs") and not r.file.endswith(".html"):
            facts = _next_page_facts(root, r.file)
        elif r.file.endswith((".html", ".htm")):
            facts = analyze_html((root / r.file).read_text(encoding="utf-8", errors="ignore"), r.path)
        else:
            continue
        facts["file"] = r.file
        facts["source"] = "code"
        pages[r.path] = facts
    site = _site_files(app_dir, root)
    site["orphans"] = sorted(_orphans(app, root)) if app.routes else []
    site["dynamic_routes"] = [r.path for r in app.routes if r.dynamic]
    site["framework"] = app.framework
    # snippet presence across source (Clarity / GSC verification meta)
    site["has_gsc_verification"] = any(p.get("has_gsc_verification") for p in pages.values())
    for f in _walk(app_dir, 6):
        if f.suffix in SOURCE_EXTS and f.stat().st_size < 300_000:
            t = f.read_text(encoding="utf-8", errors="ignore")
            if "google-site-verification" in t or "verification: {" in t and "google" in t:
                site["has_gsc_verification"] = True
                break
    return {"pages": pages, "site": site}
