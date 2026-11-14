"""Rules: collected facts → concrete findings.

Every finding names the URL, the source file when known, the current value,
the target value and the evidence. Live HTML is treated as the truth for
page-level facts; the code scan supplies file locations and code-only facts.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
MAX_TEXT = 300      # site-derived text (titles, descriptions, headings) is untrusted: keep it short
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069]")


def _clean(s: str) -> str:
    s = _CTRL.sub("", " ".join(str(s).split()))
    return s if len(s) <= MAX_TEXT else s[: MAX_TEXT - 1] + "…"


@dataclass
class Finding:
    rule: str
    url: str                      # page path, or "site"
    title: str                    # one line, human
    current: str
    target: str
    severity: str                 # critical | high | medium | low
    pillar: str                   # SEO | AEO | GEO
    who: str = "agent"            # agent = can fix in code; user = only the user can do it
    file: str | None = None       # path[:line]
    evidence: str = ""
    source: str = "code"          # code | live | gsc | code+live
    fix: str = ""                 # playbook anchor, e.g. "nextjs.md#client-rendered"
    fix_options: list[dict] = field(default_factory=list)   # Q4 variants, first = recommended
    auto_fixable: bool = False

    def __post_init__(self) -> None:
        for k in ("title", "current", "target", "evidence"):
            setattr(self, k, _clean(getattr(self, k)))

    @property
    def fingerprint(self) -> str:
        return f"{self.rule}|{self.url}"

    def to_dict(self) -> dict:
        from findable.plain import describe
        d = asdict(self)
        d["fingerprint"] = self.fingerprint
        d.update(describe(self.rule, self.url, self.who, self.title, self.current))
        return d


def _playbook(framework: str, anchor: str) -> str:
    book = "nextjs.md" if framework.startswith("nextjs") else "generic.md"
    return f"playbooks/{book}#{anchor}"


def merge_pages(code: dict, live: dict | None) -> dict[str, dict]:
    """One record per path: {"code": facts|None, "live": facts|None}."""
    out: dict[str, dict] = defaultdict(lambda: {"code": None, "live": None})
    for p, f in (code or {}).get("pages", {}).items():
        out[p]["code"] = f
    for p, f in ((live or {}).get("pages", {}) or {}).items():
        out[p]["live"] = f
    return dict(out)


def evaluate(code: dict, live: dict | None, gsc: dict | None, vis: dict | None = None) -> list[Finding]:
    fw = code["site"].get("framework", "static")
    pages = merge_pages(code, live)
    lsite = (live or {}).get("site", {}) if live else {}
    live_ok = bool(live) and lsite.get("reachable", False)
    F: list[Finding] = []

    # ------------------------------------------------------------ page rules
    titles: dict[str, list[str]] = defaultdict(list)
    descs: dict[str, list[str]] = defaultdict(list)
    sitemap_paths = set(lsite.get("sitemap_paths", []))

    for path, rec in sorted(pages.items()):
        c, l = rec["code"], rec["live"]
        file = (c or {}).get("file")
        if l and l.get("status") == 200 and "title" in l:
            src = "live" if not c else "code+live"
            t, d = l.get("title"), l.get("description")
            if not t:
                F.append(Finding("seo.title", path, f"{path} has no <title>", "missing", "unique title, 15–60 characters",
                                 "high", "SEO", file=file, source=src, evidence="no <title> in served HTML",
                                 fix=_playbook(fw, "title"), auto_fixable=True))
            else:
                titles[t].append(path)
                if len(t) < 15 or len(t) > 65:
                    F.append(Finding("seo.title_length", path, f"{path} title is {len(t)} characters", f'"{t}" ({len(t)} chars)',
                                     "15–60 characters", "low", "SEO", file=file, source=src, fix=_playbook(fw, "title"), auto_fixable=True))
            if not d:
                F.append(Finding("seo.description", path, f"{path} has no meta description", "missing",
                                 "unique description, 70–160 characters", "medium", "SEO", file=file, source=src,
                                 evidence='no <meta name="description"> in served HTML', fix=_playbook(fw, "description"), auto_fixable=True))
            else:
                descs[d].append(path)
            canon = l.get("canonical")
            if not canon:
                F.append(Finding("seo.canonical", path, f"{path} has no canonical link", "missing",
                                 f'<link rel="canonical" href="…{path}">', "low", "SEO", file=file, source=src,
                                 fix=_playbook(fw, "canonical"), auto_fixable=True))
            else:
                from urllib.parse import urlparse
                cpath = l.get("canonical_path") or urlparse(canon).path.rstrip("/") or "/"
                if cpath != path or l.get("canonical_other_host"):
                    F.append(Finding("seo.canonical_mismatch", path, f"{path} canonical points to {cpath}", canon,
                                     f"self-referencing canonical ({path}) unless this page is a deliberate duplicate",
                                     "high", "SEO", file=file, source=src,
                                     evidence="Google will likely index the canonical target instead of this page",
                                     fix=_playbook(fw, "canonical"), auto_fixable=True))
            if l.get("noindex"):
                F.append(Finding("seo.noindex_leak", path, f"{path} is set to noindex", "noindex in robots meta",
                                 "indexable (remove noindex) unless intentionally hidden", "high", "SEO", file=file, source=src,
                                 evidence=("page is listed in the sitemap" if path in sitemap_paths else "page is served publicly"),
                                 fix=_playbook(fw, "noindex"), auto_fixable=True,
                                 fix_options=[{"value": "remove", "label": "Remove noindex (make it indexable)", "recommended": True},
                                              {"value": "keep", "label": "Keep noindex and remove it from the sitemap/links"}]))
            _content_rules(F, path, l, file, src, fw)
            if l.get("empty_without_js"):
                # Critical for pages the site wants found (homepage, sitemap); others may be app/login pages.
                key_page = path == "/" or path in sitemap_paths or bool(c)
                F.append(Finding("geo.no_js_view", path, f"{path} is an empty shell without JavaScript",
                                 f"{l.get('word_count', 0)} words in served HTML", "main content in the initial HTML",
                                 "critical" if key_page else "medium", "GEO", file=file, source=src,
                                 evidence="most AI crawlers (GPTBot, ClaudeBot, PerplexityBot) don't run JavaScript",
                                 fix=_playbook(fw, "client-rendered"), auto_fixable=True,
                                 fix_options=_render_options(fw)))
        elif c and not l:
            _code_only_page_rules(F, path, c, fw)

        if c and c.get("client_rendered") and not (l and l.get("empty_without_js")):
            sev = "medium" if (l and l.get("word_count", 0) >= 80) else "high"
            ev = ("served HTML still has content (likely pre-rendered), but data fetched in the browser is invisible to AI crawlers"
                  if sev == "medium" else "the whole page is a client component; content may be missing from the initial HTML")
            F.append(Finding("geo.client_rendered", path, f"{path} page is a client component ('use client')",
                             "'use client' at the top of the page file", "server component page; client parts moved into child components",
                             sev, "GEO", file=f"{file}:{c.get('client_line') or 1}", source="code" if not l else "code+live",
                             evidence=ev, fix=_playbook(fw, "client-rendered"), auto_fixable=True, fix_options=_render_options(fw)))
        if l and l.get("status") is not None and l["status"] >= 400:
            F.append(Finding("seo.status", path, f"{path} returns {l['status']}", f"HTTP {l['status']}",
                             "HTTP 200, or remove links/sitemap entries pointing here", "high", "SEO", file=file, source="live",
                             evidence=("listed in sitemap" if path in sitemap_paths else "linked from the site"),
                             fix=_playbook(fw, "broken-page")))
        elif l and l.get("error"):
            F.append(Finding("seo.status", path, f"{path} failed to load", l["error"], "HTTP 200", "high", "SEO",
                             file=file, source="live"))
        if l and len(l.get("redirects", [])) > 1 and not l.get("redirected_off_host"):
            F.append(Finding("seo.redirect_chain", path, f"{path} redirects {len(l['redirects'])} times",
                             " → ".join(l["redirects"] + [l.get("final_url") or ""]), "a single redirect (or link straight to the final URL)",
                             "low", "SEO", file=file, source="live", fix=_playbook(fw, "redirects")))

    for t, ps in titles.items():
        if len(ps) > 1:
            for p in ps:
                F.append(Finding("seo.title_duplicate", p, f"{p} shares its title with {len(ps) - 1} other page(s)", f'"{t}"',
                                 "a unique title per page", "medium", "SEO", file=(pages[p]["code"] or {}).get("file"),
                                 source="live", evidence="same title on: " + ", ".join(ps[:8]),
                                 fix=_playbook(fw, "title"), auto_fixable=True))
    for d, ps in descs.items():
        if len(ps) > 1:
            for p in ps:
                F.append(Finding("seo.description_duplicate", p, f"{p} shares its meta description with {len(ps) - 1} other page(s)",
                                 d[:80] + ("…" if len(d) > 80 else ""), "a unique description per page", "low", "SEO",
                                 file=(pages[p]["code"] or {}).get("file"), source="live",
                                 evidence="same description on: " + ", ".join(ps[:8]), fix=_playbook(fw, "description"), auto_fixable=True))

    # ------------------------------------------------------------ site rules
    _site_rules(F, code["site"], lsite if live_ok else None, pages, fw)
    if gsc:
        _gsc_rules(F, gsc, F, pages)
    if vis:
        _visibility_rules(F, vis)
    return sorted(F, key=lambda f: (SEVERITY_RANK[f.severity], 0 if f.who == "user" else 1, f.url, f.rule))


def _render_options(fw: str) -> list[dict]:
    if fw.startswith("nextjs"):
        return [
            {"value": "server", "label": "Make the page a server component; move interactive parts into a small client component", "recommended": True},
            {"value": "prerender", "label": "Keep the client component but pre-render the content at build time (generateStaticParams / static data)"},
            {"value": "skip", "label": "Leave it (page isn't meant to be found by search or AI)"},
        ]
    return [
        {"value": "ssr", "label": "Render the main content on the server (SSR/SSG)", "recommended": True},
        {"value": "prerender", "label": "Pre-render the page at build time"},
        {"value": "skip", "label": "Leave it"},
    ]


def _content_rules(F: list[Finding], path: str, f: dict, file: str | None, src: str, fw: str) -> None:
    if f.get("h1_count", 0) == 0:
        F.append(Finding("aeo.h1", path, f"{path} has no <h1>", "0 <h1>", "exactly one <h1> stating what the page is about",
                         "medium", "AEO", file=file, source=src, fix=_playbook(fw, "headings"), auto_fixable=True))
    elif f.get("h1_count", 0) > 1:
        F.append(Finding("aeo.h1", path, f"{path} has {f['h1_count']} <h1> tags", f"{f['h1_count']} <h1>", "exactly one <h1>",
                         "low", "AEO", file=file, source=src, fix=_playbook(fw, "headings"), auto_fixable=True))
    q = f.get("questions_without_answer") or []
    if q:
        F.append(Finding("aeo.answer_first", path, f"{path}: {len(q)} question heading(s) without a direct answer",
                         "; ".join(q[:3]) + ("…" if len(q) > 3 else ""),
                         "a 40–60 word direct answer right under each question heading",
                         "low", "AEO", file=file, source=src, evidence="answer engines quote the paragraph directly under a question",
                         fix="references/aeo-content.md#answer-first"))
    if f.get("ld_errors"):
        F.append(Finding("aeo.schema_invalid", path, f"{path} has invalid JSON-LD", f["ld_errors"][0], "valid JSON-LD",
                         "high", "AEO", file=file, source=src, fix="references/schema.md", auto_fixable=True))
    imgs = f.get("images_no_alt") or []
    if imgs:
        F.append(Finding("seo.alt", path, f"{path}: {len(imgs)} image(s) without alt text", ", ".join(imgs[:5]),
                         'descriptive alt text (or alt="" for decorative images)', "low", "SEO", file=file, source=src,
                         fix=_playbook(fw, "alt"), auto_fixable=True))


def _code_only_page_rules(F: list[Finding], path: str, c: dict, fw: str) -> None:
    file = c.get("file")
    if c.get("source") == "code" and file and file.endswith((".html", ".htm")):
        # static HTML: code facts are the real document
        if not c.get("title"):
            F.append(Finding("seo.title", path, f"{path} has no <title>", "missing", "unique title, 15–60 characters",
                             "high", "SEO", file=file, fix=_playbook(fw, "title"), auto_fixable=True))
        if not c.get("description"):
            F.append(Finding("seo.description", path, f"{path} has no meta description", "missing",
                             "unique description, 70–160 characters", "medium", "SEO", file=file,
                             fix=_playbook(fw, "description"), auto_fixable=True))
        if not c.get("canonical"):
            F.append(Finding("seo.canonical", path, f"{path} has no canonical link", "missing",
                             f'<link rel="canonical" href="…{path}">', "low", "SEO", file=file,
                             fix=_playbook(fw, "canonical"), auto_fixable=True))
        if c.get("noindex"):
            F.append(Finding("seo.noindex_leak", path, f"{path} is set to noindex", "noindex in robots meta",
                             "indexable unless intentionally hidden", "high", "SEO", file=file,
                             fix=_playbook(fw, "noindex"), auto_fixable=True))
        _content_rules(F, path, c, file, "code", fw)
        return
    # Next.js source heuristics
    if not c.get("title") and path != "/":       # the homepage normally uses the layout's default title
        if c.get("title_from_layout"):
            F.append(Finding("seo.title_inherited", path, f"{path} uses the site-wide title from {c['title_from_layout']}",
                             "no page-level title", "page-specific title in this page's metadata", "medium", "SEO",
                             file=file, evidence="every page without its own title shows the same title in search results",
                             fix=_playbook(fw, "title"), auto_fixable=True))
        else:
            F.append(Finding("seo.title", path, f"{path} has no title in code", "no metadata title",
                             "title in `export const metadata` or generateMetadata", "high", "SEO", file=file,
                             fix=_playbook(fw, "title"), auto_fixable=True))
    if not c.get("description"):
        F.append(Finding("seo.description", path, f"{path} has no meta description in code", "missing",
                         "description in this page's metadata", "medium", "SEO", file=file,
                         fix=_playbook(fw, "description"), auto_fixable=True))
    elif str(c.get("description", "")).startswith("inherited from") and path != "/":
        F.append(Finding("seo.description_inherited", path, f"{path} uses the site-wide description",
                         c["description"], "page-specific description in this page's metadata", "low", "SEO",
                         file=file, evidence="pages sharing one description get generic snippets in search results",
                         fix=_playbook(fw, "description"), auto_fixable=True))
    if c.get("noindex"):
        F.append(Finding("seo.noindex_leak", path, f"{path} is set to noindex", f"noindex in {c.get('noindex_from', file)}",
                         "indexable unless intentionally hidden", "high", "SEO", file=c.get("noindex_from", file),
                         fix=_playbook(fw, "noindex"), auto_fixable=True))
    imgs = c.get("images_no_alt") or []
    if imgs:
        F.append(Finding("seo.alt", path, f"{path}: {len(imgs)} image(s) without alt", ", ".join(imgs[:5]),
                         "descriptive alt text", "low", "SEO", file=file, fix=_playbook(fw, "alt"), auto_fixable=True))
    if c.get("h1_count", 0) > 1:
        F.append(Finding("aeo.h1", path, f"{path} has {c['h1_count']} <h1> in its source", f"{c['h1_count']} <h1>",
                         "exactly one <h1>", "low", "AEO", file=file, fix=_playbook(fw, "headings"), auto_fixable=True))


def _site_rules(F: list[Finding], cs: dict, ls: dict | None, pages: dict, fw: str) -> None:
    # robots.txt
    robots_text = (ls or {}).get("robots_text") or cs.get("robots_text") or ""
    if ls is not None and ls.get("robots_status") != 200 and not cs.get("robots"):
        F.append(Finding("seo.robots", "site", "No robots.txt", f"/robots.txt returns {ls.get('robots_status')}",
                         "robots.txt that allows crawling and lists the sitemap", "medium", "SEO",
                         fix=_playbook(fw, "robots"), auto_fixable=True))
    elif ls is None and not cs.get("robots"):
        F.append(Finding("seo.robots", "site", "No robots.txt found in the code", "missing",
                         "robots.txt (or app/robots.ts) that allows crawling and lists the sitemap", "medium", "SEO",
                         fix=_playbook(fw, "robots"), auto_fixable=True))
    if robots_text and _disallows_all(robots_text):
        F.append(Finding("seo.robots_blocks_all", "site", "robots.txt blocks all crawlers", "User-agent: * / Disallow: /",
                         "Allow crawling of public pages", "critical", "SEO", file=cs.get("robots"),
                         evidence="nothing on the site can be crawled or cited", fix=_playbook(fw, "robots"), auto_fixable=True))

    # sitemap
    sms = (ls or {}).get("sitemaps", [])
    live_has_sitemap = any(s.get("status") == 200 and s.get("count", 0) > 0 for s in sms)
    if ls is not None and not live_has_sitemap:
        F.append(Finding("seo.sitemap", "site", "No working sitemap on the live site",
                         "; ".join(f"{s['url']} → {s.get('status') or s.get('error')}" for s in sms) or "none",
                         "sitemap.xml listing every indexable page, referenced in robots.txt", "high", "SEO",
                         file=cs.get("sitemap"), fix=_playbook(fw, "sitemap"), auto_fixable=True))
    elif ls is None and not cs.get("sitemap"):
        F.append(Finding("seo.sitemap", "site", "No sitemap found in the code", "missing",
                         "sitemap generation (e.g. app/sitemap.ts)", "high", "SEO", fix=_playbook(fw, "sitemap"), auto_fixable=True))
    if ls is not None and live_has_sitemap:
        if ls.get("sitemap_foreign_hosts"):
            F.append(Finding("seo.sitemap_host", "site", "Sitemap lists URLs on another host",
                             ", ".join(ls["sitemap_foreign_hosts"][:5]), f"only URLs on {ls['base']}", "high", "SEO",
                             file=cs.get("sitemap"), evidence="often localhost or a staging domain baked in at build time",
                             fix=_playbook(fw, "sitemap"), auto_fixable=True))
        smp = set(ls.get("sitemap_paths", []))
        missing = [p for p, r in pages.items() if r["code"] and p not in smp
                   and not (r["live"] or {}).get("noindex") and not (r["code"] or {}).get("noindex")]
        if missing:
            F.append(Finding("seo.sitemap_missing", "site", f"{len(missing)} page(s) missing from the sitemap",
                             ", ".join(sorted(missing)[:10]) + ("…" if len(missing) > 10 else ""),
                             "every indexable route listed in the sitemap", "medium", "SEO", file=cs.get("sitemap"),
                             fix=_playbook(fw, "sitemap"), auto_fixable=True))
        bad = [p for p in smp if (pages.get(p, {}).get("live") or {}).get("status") not in (None, 200)]
        redir = [p for p in smp if (pages.get(p, {}).get("live") or {}).get("redirects")]
        if bad or redir:
            F.append(Finding("seo.sitemap_dead", "site", f"{len(bad) + len(redir)} sitemap URL(s) don't return 200 directly",
                             ", ".join(sorted(bad + redir)[:10]), "only final, 200-status URLs in the sitemap", "medium", "SEO",
                             file=cs.get("sitemap"), source="live", fix=_playbook(fw, "sitemap"), auto_fixable=True))

    # schema (site-level)
    any_ld = any(((r["live"] or r["code"] or {}).get("ld_types")) or ((r["live"] or r["code"] or {}).get("ld_errors"))
                 for r in pages.values())
    home = pages.get("/", {})
    home_types = set((home.get("live") or home.get("code") or {}).get("ld_types") or [])
    if pages and not any_ld:
        F.append(Finding("aeo.schema", "site", "No structured data (JSON-LD) anywhere", "0 pages with JSON-LD",
                         "Organization + WebSite on the homepage; Article/Product/FAQPage where they apply", "medium", "AEO",
                         file=(home.get("code") or {}).get("file"),
                         evidence="AI and answer engines use schema to extract facts about you",
                         fix="references/schema.md", auto_fixable=True))
    elif home and home.get("live") and not ({"Organization", "WebSite", "LocalBusiness", "Corporation"} & home_types):
        F.append(Finding("aeo.schema_org", "/", "Homepage has no Organization/WebSite schema",
                         ", ".join(sorted(t for t in home_types if t)) or "none", "Organization + WebSite JSON-LD", "medium", "AEO",
                         file=(home.get("code") or {}).get("file"), fix="references/schema.md#organization", auto_fixable=True))

    # orphans (code + not linked from any live page)
    live_links = set()
    for r in pages.values():
        live_links |= set((r["live"] or {}).get("links", []))
    orphans = [p for p in cs.get("orphans", []) if p not in live_links]
    if orphans:
        F.append(Finding("seo.orphan", "site", f"{len(orphans)} page(s) nothing links to", ", ".join(orphans[:10]),
                         "at least one internal link to each page", "low", "SEO",
                         evidence="search engines find and rank pages mainly through internal links",
                         fix=_playbook(fw, "internal-links"), auto_fixable=True))

    if ls is None:
        return
    # AI bots: robots.txt rules
    blocked_search = [n for n, v in ls.get("robots_ai", {}).items() if not v["allowed_home"] and v["purpose"] == "search"]
    if blocked_search:
        F.append(Finding("geo.robots_ai", "site", f"robots.txt blocks AI search bots: {', '.join(blocked_search)}",
                         "Disallow for " + ", ".join(blocked_search), "allow AI search bots (they fetch pages to cite them)",
                         "high", "GEO", file=cs.get("robots"),
                         evidence="these bots fetch pages to answer and cite in ChatGPT, Perplexity, Claude and Bing",
                         fix="references/ai-bots.md", auto_fixable=True,
                         fix_options=[{"value": "search_only", "label": "Allow AI search bots, keep training bots blocked", "recommended": True},
                                      {"value": "all", "label": "Allow all AI bots (search + training)"},
                                      {"value": "keep", "label": "Keep blocking them"}]))
    # AI bots: actual access (CDN/WAF)
    blocked = {n: v for n, v in ls.get("bot_access", {}).items() if v["blocked"]}
    if blocked:
        search = [n for n, v in blocked.items() if v["purpose"] == "search"]
        detail = []
        for n, v in blocked.items():
            r = next(x for x in v["results"] if x["blocked"])
            detail.append(f"{n} → {r['status']}{' (challenge page)' if r['challenged'] else ''} on {r['path']}")
        server = next((x["server"] for v in blocked.values() for x in v["results"] if x["server"]), "")
        F.append(Finding("geo.bot_access", "site",
                         f"Your server/CDN blocks {len(blocked)} AI/search bot(s)" + (f" ({server})" if server else ""),
                         "; ".join(detail), "HTTP 200 for AI search bots", "critical" if search else "medium", "GEO",
                         who="user", source="live",
                         evidence="browser user agent got 200 on the same pages; robots.txt is not the cause"
                                  if not blocked_search else "browser user agent got 200 on the same pages",
                         fix="playbooks/cdn.md"))


def _disallows_all(text: str) -> bool:
    """True if a crawler with no rules of its own may not fetch the homepage or a normal page."""
    from protego import Protego
    rp = Protego.parse(text)
    ua = "SomeSearchBot"     # falls under the `User-agent: *` group, grouped UA lines included
    return not rp.can_fetch("https://site.invalid/", ua) and not rp.can_fetch("https://site.invalid/about", ua)


def _visibility_rules(F: list[Finding], vis: dict) -> None:
    from findable.visibility import slug
    when = (vis.get("checked_at") or "")[:10]
    for r in vis.get("results", []):
        if r.get("cited"):
            continue
        others = ", ".join(r.get("others", [])[:3]) or "other sites"
        F.append(Finding("geo.ai_not_cited", slug(r["query"]), f'Not in the results for "{r["query"]}"',
                         f"top results: {others}", "your site among the sources for this question", "medium", "GEO",
                         source="visibility",
                         evidence=f"{vis.get('engine', 'web search')} on {when}: {r.get('results', 0)} results, none from {vis.get('site')}",
                         fix="references/ai-visibility.md#improve"))


def _gsc_rules(F: list[Finding], gsc: dict, existing: list[Finding], pages: dict) -> None:
    by_url = defaultdict(list)
    for f in existing:
        by_url[f.url].append(f)
    sd = [p for p in gsc.get("pages", []) if 8 <= p["position"] <= 20 and p["impressions"] >= 50]
    for p in sorted(sd, key=lambda x: -x["impressions"])[:20]:
        issues = by_url.get(p["path"], [])
        ev = (f"same page also has: {', '.join(sorted({i.rule for i in issues}))}" if issues
              else "no technical issues found on this page; improve content depth, internal links, answer-first sections")
        F.append(Finding("seo.striking_distance", p["path"],
                         f"{p['path']} ranks {p['position']:.1f} with {int(p['impressions'])} impressions",
                         f"avg position {p['position']:.1f}, {int(p['clicks'])} clicks", "page 1 (position ≤ 7)",
                         "high" if issues else "medium", "SEO", file=(pages.get(p["path"], {}).get("code") or {}).get("file"),
                         source="gsc", evidence=ev, fix="references/checks.md#striking-distance"))
    q = [x for x in gsc.get("queries", []) if 8 <= x["position"] <= 20 and x["impressions"] >= 50]
    if q:
        top = sorted(q, key=lambda x: -x["impressions"])[:10]
        F.append(Finding("seo.striking_queries", "site", f"{len(q)} queries rank on page 2 (positions 8–20)",
                         "; ".join(f"{x['key']} ({x['position']:.1f}, {int(x['impressions'])} impr.)" for x in top),
                         "map each query to one page and add an answer-first section for it", "medium", "AEO",
                         source="gsc", fix="references/aeo-content.md#answer-first"))
