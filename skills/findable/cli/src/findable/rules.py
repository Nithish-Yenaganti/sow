"""Rules: collected facts → findings.

Wording and defaults (group, severity, target, fix guide, plain sentence) live in the catalog
in plain.py; a rule here only decides *whether* it applies and records the evidence. Live
HTML is the truth for page facts; the code scan adds file locations and code-only facts.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from findable.plain import CATALOG, UNKNOWN, describe

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
MAX_TEXT = 300      # site-derived text (titles, descriptions, headings) is untrusted: keep it short
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069]")


def _clean(s) -> str:
    s = _CTRL.sub("", " ".join(str(s).split()))
    return s if len(s) <= MAX_TEXT else s[: MAX_TEXT - 1] + "…"


def playbook(fix: str, framework: str = "static") -> str:
    """'@anchor' → the framework's playbook section; anything else is already a path."""
    if not fix.startswith("@"):
        return fix
    return f"playbooks/{'nextjs.md' if framework.startswith('nextjs') else 'generic.md'}#{fix[1:]}"


@dataclass
class Finding:
    rule: str
    url: str                      # page path, "site", or a query slug
    title: str                    # one technical line
    current: str = ""
    target: str = ""              # default: the catalog's
    severity: str = ""            # default: the catalog's
    who: str = ""                 # agent (fixable in code) | user; default from the catalog group
    file: str | None = None       # path[:line]
    evidence: str = ""
    source: str = "code"          # code | live | code+live | gsc | gsc_index | visibility | keywords
    fix: str = ""                 # fix guide; default: the catalog's
    fix_options: list[dict] = field(default_factory=list)   # variants, first = recommended
    values: dict = field(default_factory=dict)              # filled into the plain sentence

    def __post_init__(self) -> None:
        r = CATALOG.get(self.rule, UNKNOWN)
        self.severity = self.severity or r.severity
        self.target = self.target or r.target
        self.who = self.who or ("user" if r.group == "you" else "agent")
        self.fix = playbook(self.fix or r.fix)
        for k in ("title", "current", "target", "evidence"):
            setattr(self, k, _clean(getattr(self, k)))
        self.values = {k: _clean(v) for k, v in self.values.items()}

    @property
    def fingerprint(self) -> str:
        return f"{self.rule}|{self.url}"

    def to_dict(self) -> dict:
        d = asdict(self)
        values = d.pop("values")
        d["fingerprint"] = self.fingerprint
        d.update(describe(self.rule, self.url, self.who, **values))
        return d


def merge_pages(code: dict, live: dict | None) -> dict[str, dict]:
    """One record per path: {"code": facts|None, "live": facts|None}."""
    out: dict[str, dict] = defaultdict(lambda: {"code": None, "live": None})
    for p, f in (code or {}).get("pages", {}).items():
        out[p]["code"] = f
    for p, f in ((live or {}).get("pages", {}) or {}).items():
        out[p]["live"] = f
    return dict(out)


def evaluate(code: dict, live: dict | None, gsc: dict | None, vis: dict | None = None,
             kw: dict | None = None) -> list[Finding]:
    fw = code["site"].get("framework", "static")
    pages = merge_pages(code, live)
    lsite = (live or {}).get("site", {}) if live else {}
    live_ok = bool(live) and lsite.get("reachable", False)
    sitemap_paths = set(lsite.get("sitemap_paths", []))
    F: list[Finding] = []

    def add(rule: str, url: str, title: str, current: str = "", **kw) -> None:
        kw["fix"] = playbook(kw.get("fix") or CATALOG.get(rule, UNKNOWN).fix, fw)
        F.append(Finding(rule, url, title, current, **kw))

    titles: dict[str, list[str]] = defaultdict(list)
    descs: dict[str, list[str]] = defaultdict(list)
    for path, rec in sorted(pages.items()):
        c, l = rec["code"], rec["live"]
        file = (c or {}).get("file")
        if l and l.get("status") == 200 and "title" in l:
            _document_rules(add, path, l, file, "live" if not c else "code+live", sitemap_paths, titles, descs)
            if l.get("empty_without_js"):
                key_page = path == "/" or path in sitemap_paths or bool(c)    # others may be app/login pages
                add("geo.no_js_view", path, f"{path} is an empty shell without JavaScript",
                    f"{l.get('word_count', 0)} words in served HTML", severity="critical" if key_page else "medium",
                    file=file, source="live" if not c else "code+live",
                    evidence="most AI crawlers (GPTBot, ClaudeBot, PerplexityBot) don't run JavaScript",
                    fix_options=_render_options(fw))
        elif c and not l and file and file.endswith((".html", ".htm")):
            _document_rules(add, path, c, file, "code", sitemap_paths, titles, descs)    # static HTML is the document
        elif c and not l:
            _nextjs_source_rules(add, path, c)

        if c and c.get("client_rendered") and not (l and l.get("empty_without_js")):
            prerendered = bool(l and l.get("word_count", 0) >= 80)
            add("geo.client_rendered", path, f"{path} page is a client component ('use client')",
                "'use client' at the top of the page file", severity="medium" if prerendered else "high",
                file=f"{file}:{c.get('client_line') or 1}", source="code+live" if l else "code",
                evidence=("served HTML still has content (likely pre-rendered), but data fetched in the browser is invisible to AI crawlers"
                          if prerendered else "the whole page is a client component; content may be missing from the initial HTML"),
                fix_options=_render_options(fw))
        if l and l.get("status") is not None and l["status"] >= 400:
            add("seo.status", path, f"{path} returns {l['status']}", f"HTTP {l['status']}", file=file, source="live",
                evidence="listed in sitemap" if path in sitemap_paths else "linked from the site")
        elif l and l.get("error"):
            add("seo.status", path, f"{path} failed to load", l["error"], file=file, source="live")
        if l and len(l.get("redirects", [])) > 1 and not l.get("redirected_off_host"):
            add("seo.redirect_chain", path, f"{path} redirects {len(l['redirects'])} times",
                " → ".join(l["redirects"] + [l.get("final_url") or ""]), file=file, source="live")

    for rule, what, groups in (("seo.title_duplicate", "title", titles), ("seo.description_duplicate", "meta description", descs)):
        for text, ps in groups.items():
            if len(ps) > 1:
                for p in ps:
                    add(rule, p, f"{p} shares its {what} with {len(ps) - 1} other page(s)", f'"{text[:80]}"',
                        file=(pages[p]["code"] or {}).get("file"), source="live",
                        evidence=f"same {what} on: " + ", ".join(ps[:8]))

    _site_rules(add, code["site"], lsite if live_ok else None, pages)
    if gsc:
        _gsc_rules(add, gsc, F, pages)
        _index_rules(add, gsc.get("index") or {}, pages)
    if vis:
        _visibility_rules(add, vis)
    if kw:
        _keyword_rules(add, kw, gsc, pages)
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


def _document_rules(add, path: str, f: dict, file: str | None, src: str, sitemap_paths: set,
                    titles: dict, descs: dict) -> None:
    """Checks on one HTML document: a served page, or a static HTML file in the code."""
    t, d, canon = f.get("title"), f.get("description"), f.get("canonical")
    if not t:
        add("seo.title", path, f"{path} has no <title>", "missing", file=file, source=src)
    else:
        titles[t].append(path)
        if not 15 <= len(t) <= 60:
            add("seo.title_length", path, f"{path} title is {len(t)} characters", f'"{t}" ({len(t)} chars)', file=file, source=src)
    if not d:
        add("seo.description", path, f"{path} has no meta description", "missing", file=file, source=src)
    else:
        descs[d].append(path)
    if not canon:
        add("seo.canonical", path, f"{path} has no canonical link", "missing", file=file, source=src)
    elif "canonical_path" in f:                 # live pages: canonical resolved against the site
        if f["canonical_path"] != path or f.get("canonical_other_host"):
            add("seo.canonical_mismatch", path, f"{path} canonical points to {f['canonical_path']}", canon, file=file, source=src,
                evidence="Google will likely index the canonical target instead of this page")
    if f.get("noindex"):
        add("seo.noindex_leak", path, f"{path} is set to noindex", "noindex in robots meta", file=file, source=src,
            evidence="page is listed in the sitemap" if path in sitemap_paths else "page is served publicly",
            fix_options=[{"value": "remove", "label": "Remove noindex (make it indexable)", "recommended": True},
                         {"value": "keep", "label": "Keep noindex and remove it from the sitemap and links"}])
    h1 = f.get("h1_count", 0)
    if h1 != 1:
        add("aeo.h1", path, f"{path} has {h1} <h1> tags", f"{h1} <h1>", severity="medium" if h1 == 0 else "low",
            file=file, source=src)
    q = f.get("questions_without_answer") or []
    if q:
        add("aeo.answer_first", path, f"{path}: {len(q)} question heading(s) without a direct answer",
            "; ".join(q[:3]) + ("…" if len(q) > 3 else ""), file=file, source=src,
            evidence="answer engines quote the paragraph directly under a question")
    if f.get("ld_errors"):
        add("aeo.schema_invalid", path, f"{path} has invalid JSON-LD", f["ld_errors"][0], file=file, source=src)
    imgs = f.get("images_no_alt") or []
    if imgs:
        add("seo.alt", path, f"{path}: {len(imgs)} image(s) without alt text", ", ".join(imgs[:5]), file=file, source=src)


def _nextjs_source_rules(add, path: str, c: dict) -> None:
    """Code-only checks from Next.js page source (no live page to read)."""
    file = c.get("file")
    if not c.get("title") and path != "/":       # the homepage normally uses the layout's default title
        if c.get("title_from_layout"):
            add("seo.title_inherited", path, f"{path} uses the site-wide title from {c['title_from_layout']}",
                "no page-level title", file=file,
                evidence="every page without its own title shows the same title in search results")
        else:
            add("seo.title", path, f"{path} has no title in code", "no metadata title", file=file,
                target="title in `export const metadata` or generateMetadata")
    if not c.get("description"):
        add("seo.description", path, f"{path} has no meta description in code", "missing", file=file,
            target="description in this page's metadata")
    elif str(c["description"]).startswith("inherited from") and path != "/":
        add("seo.description_inherited", path, f"{path} uses the site-wide description", c["description"], file=file,
            evidence="pages sharing one description get generic snippets in search results")
    if c.get("noindex"):
        add("seo.noindex_leak", path, f"{path} is set to noindex", f"noindex in {c.get('noindex_from', file)}",
            file=c.get("noindex_from", file))
    imgs = c.get("images_no_alt") or []
    if imgs:
        add("seo.alt", path, f"{path}: {len(imgs)} image(s) without alt", ", ".join(imgs[:5]), file=file)
    if c.get("h1_count", 0) > 1:
        add("aeo.h1", path, f"{path} has {c['h1_count']} <h1> in its source", f"{c['h1_count']} <h1>", severity="low", file=file)


def _site_rules(add, cs: dict, ls: dict | None, pages: dict) -> None:
    # robots.txt
    robots_text = (ls or {}).get("robots_text") or cs.get("robots_text") or ""
    if not cs.get("robots") and (ls is None or ls.get("robots_status") != 200):
        add("seo.robots", "site", "No robots.txt",
            "missing" if ls is None else f"/robots.txt returns {ls.get('robots_status')}")
    if robots_text and _disallows_all(robots_text):
        add("seo.robots_blocks_all", "site", "robots.txt blocks all crawlers", "User-agent: * / Disallow: /",
            file=cs.get("robots"), evidence="nothing on the site can be crawled or cited")

    # sitemap
    sms = (ls or {}).get("sitemaps", [])
    live_has_sitemap = any(s.get("status") == 200 and s.get("count", 0) > 0 for s in sms)
    if ls is not None and not live_has_sitemap:
        add("seo.sitemap", "site", "No working sitemap on the live site",
            "; ".join(f"{s['url']} → {s.get('status') or s.get('error')}" for s in sms) or "none", file=cs.get("sitemap"))
    elif ls is None and not cs.get("sitemap"):
        add("seo.sitemap", "site", "No sitemap found in the code", "missing", target="sitemap generation (e.g. app/sitemap.ts)")
    if ls is not None and live_has_sitemap:
        if ls.get("sitemap_foreign_hosts"):
            add("seo.sitemap_host", "site", "Sitemap lists URLs on another host", ", ".join(ls["sitemap_foreign_hosts"][:5]),
                file=cs.get("sitemap"), evidence="often localhost or a staging domain baked in at build time")
        smp = set(ls.get("sitemap_paths", []))
        missing = [p for p, r in pages.items() if r["code"] and p not in smp
                   and not (r["live"] or {}).get("noindex") and not (r["code"] or {}).get("noindex")]
        if missing:
            add("seo.sitemap_missing", "site", f"{len(missing)} page(s) missing from the sitemap",
                ", ".join(sorted(missing)[:10]) + ("…" if len(missing) > 10 else ""), file=cs.get("sitemap"))
        bad = [p for p in smp if (pages.get(p, {}).get("live") or {}).get("status") not in (None, 200)
               or (pages.get(p, {}).get("live") or {}).get("redirects")]
        if bad:
            add("seo.sitemap_dead", "site", f"{len(bad)} sitemap URL(s) don't return 200 directly",
                ", ".join(sorted(bad)[:10]), file=cs.get("sitemap"), source="live")

    # structured data
    facts = [(r["live"] or r["code"] or {}) for r in pages.values()]
    home = pages.get("/", {})
    home_types = set((home.get("live") or home.get("code") or {}).get("ld_types") or [])
    if pages and not any(f.get("ld_types") or f.get("ld_errors") for f in facts):
        add("aeo.schema", "site", "No structured data (JSON-LD) anywhere", "0 pages with JSON-LD",
            file=(home.get("code") or {}).get("file"), evidence="AI and answer engines use schema to extract facts about you")
    elif home.get("live") and not ({"Organization", "WebSite", "LocalBusiness", "Corporation"} & home_types):
        add("aeo.schema_org", "/", "Homepage has no Organization/WebSite schema",
            ", ".join(sorted(t for t in home_types if t)) or "none", file=(home.get("code") or {}).get("file"))

    # orphans: in the code, and not linked from any fetched page
    live_links = {link for r in pages.values() for link in (r["live"] or {}).get("links", [])}
    orphans = [p for p in cs.get("orphans", []) if p not in live_links]
    if orphans:
        add("seo.orphan", "site", f"{len(orphans)} page(s) nothing links to", ", ".join(orphans[:10]),
            evidence="search engines find and rank pages mainly through internal links")

    if ls is None:
        return
    blocked_search = [n for n, v in ls.get("robots_ai", {}).items() if not v["allowed_home"] and v["purpose"] == "search"]
    if blocked_search:
        add("geo.robots_ai", "site", f"robots.txt blocks AI search bots: {', '.join(blocked_search)}",
            "Disallow for " + ", ".join(blocked_search), file=cs.get("robots"),
            evidence="these bots fetch pages to answer and cite in ChatGPT, Perplexity, Claude and Bing",
            fix_options=[{"value": "search_only", "label": "Allow AI search bots, keep training bots blocked", "recommended": True},
                         {"value": "all", "label": "Allow all AI bots (search + training)"},
                         {"value": "keep", "label": "Keep blocking them"}])
    blocked = {n: v for n, v in ls.get("bot_access", {}).items() if v["blocked"]}
    if blocked:
        detail = []
        for n, v in blocked.items():
            r = next(x for x in v["results"] if x["blocked"])
            detail.append(f"{n} → {r['status']}{' (challenge page)' if r['challenged'] else ''} on {r['path']}")
        server = next((x["server"] for v in blocked.values() for x in v["results"] if x["server"]), "")
        add("geo.bot_access", "site", f"Your server/CDN blocks {len(blocked)} AI/search bot(s)" + (f" ({server})" if server else ""),
            "; ".join(detail), severity="critical" if any(v["purpose"] == "search" for v in blocked.values()) else "medium",
            who="user", source="live", evidence="browser user agent got 200 on the same pages"
                                    + ("" if blocked_search else "; robots.txt is not the cause"))


def _disallows_all(text: str) -> bool:
    """True if a crawler with no rules of its own may not fetch the homepage or a normal page."""
    from protego import Protego
    rp = Protego.parse(text)
    ua = "SomeSearchBot"     # falls under the `User-agent: *` group, grouped UA lines included
    return not rp.can_fetch("https://site.invalid/", ua) and not rp.can_fetch("https://site.invalid/about", ua)


def _search_values(r: dict) -> dict:
    return {"others": ", ".join(r.get("others", [])[:3]) or "other sites"}


def _keyword_rules(add, kw: dict, gsc: dict | None, pages: dict) -> None:
    from findable.search import slug
    gsc_q = {q["key"].lower(): q for q in (gsc or {}).get("queries", [])}
    when = (kw.get("checked_at") or "")[:10]
    for k in kw.get("keywords", []):
        q = gsc_q.get(k["keyword"].lower())
        gsc_ev = f"; Search Console: {int(q['impressions'])} impressions, position {q['position']:.1f}" if q else ""
        target = k.get("target_page")
        file = (pages.get(target, {}).get("code") or {}).get("file") if target else None
        intent = f"{k['intent']} search" if k.get("intent") else "search"
        values = {"query": k["keyword"], **_search_values(k)}
        if not k.get("ranks"):
            add("seo.keyword_gap", slug("kw", k["keyword"]), f'Not in the results for "{k["keyword"]}"',
                f"top results: {values['others']}",
                target=f"a page that answers this search ({'improve ' + target if target else 'new page'})",
                severity="medium" if k.get("intent") in ("commercial", "comparison", "transactional") or q else "low",
                file=file, source="keywords", values=values,
                evidence=f"{intent}; {kw.get('engine', 'web search')} on {when}: none of {k.get('results', 0)} results from {kw.get('site')}{gsc_ev}")
        elif (k.get("rank") or 0) > 5:
            add("seo.keyword_low", slug("kw", k["keyword"]), f'Only #{k["rank"]} for "{k["keyword"]}"',
                f"#{k['rank']}: {k.get('ranking_url')}", file=file, source="keywords",
                evidence=f"{intent}{gsc_ev}", values={**values, "rank": k["rank"]})


def _visibility_rules(add, vis: dict) -> None:
    from findable.search import slug
    when = (vis.get("checked_at") or "")[:10]
    for r in vis.get("results", []):
        if not r.get("cited"):
            values = {"query": r["query"], **_search_values(r)}
            add("geo.ai_not_cited", slug("q", r["query"]), f'Not in the results for "{r["query"]}"',
                f"top results: {values['others']}", source="visibility", values=values,
                evidence=f"{vis.get('engine', 'web search')} on {when}: {r.get('results', 0)} results, none from {vis.get('site')}")


# Page indexing reasons (Search Console wording, lower-case, dashes normalised):
# reason -> (severity, short explanation, fix). Normal reasons (redirects, proper canonicals) are skipped.
INDEX_REASONS = {
    "server error (5xx)": ("high", "Google got a server error", "@broken-page"),
    "redirect error": ("high", "the redirect is broken or loops", "@redirects"),
    "blocked by robots.txt": ("high", "robots.txt blocks Google from it", "@robots"),
    "excluded by 'noindex' tag": ("high", "a noindex setting tells Google not to index it", "@noindex"),
    "not found (404)": ("medium", "Google gets 'not found'", "@broken-page"),
    "soft 404": ("medium", "Google thinks it's an empty or error page", ""),
    "crawled - currently not indexed": ("medium", "Google visited it but chose not to index it, usually because it looks thin or too similar to other pages", ""),
    "discovered - currently not indexed": ("medium", "Google knows it exists but hasn't visited it yet; more internal links help", ""),
    "duplicate without user-selected canonical": ("medium", "Google sees it as a copy of another page and you haven't said which is the original", "@canonical"),
    "duplicate, google chose different canonical than user": ("medium", "Google picked a different page as the original than the one you set", "@canonical"),
    "blocked due to unauthorized request (401)": ("low", "it needs a login, which is often on purpose", ""),
    "blocked due to access forbidden (403)": ("low", "access is forbidden, which is often on purpose", ""),
}
NORMAL_INDEX_REASONS = {"page with redirect", "alternate page with proper canonical tag"}
MAX_INDEX_URLS_PER_REASON = 30


def _norm_reason(r: str) -> str:
    return " ".join(r.replace("–", "-").replace("—", "-").replace("’", "'").lower().split())


def _index_rules(add, index: dict, pages: dict) -> None:
    by_reason: dict[str, list[dict]] = defaultdict(list)
    for u in index.get("urls", []):
        by_reason[u["reason"]].append(u)
    for reason, urls in by_reason.items():
        key = _norm_reason(reason)
        if key in NORMAL_INDEX_REASONS:
            continue
        sev, why, fix = INDEX_REASONS.get(key, ("medium", f"Search Console says “{reason}”", ""))
        for u in urls[:MAX_INDEX_URLS_PER_REASON]:
            path = u["path"]
            code = (pages.get(path) or {}).get("code")
            add("seo.not_indexed", path, f"Google isn't indexing {path}", reason, severity=sev, fix=fix,
                file=(code or {}).get("file"), source="gsc_index", values={"why": why},
                evidence=f"Search Console: {why}" + (f"; last crawled {u['last_crawled']}" if u.get("last_crawled") else "")
                         + ("" if code else "; not one of the routes in this app's code"))
    if not by_reason:       # only the summary table: one site-level finding
        bad = [r for r in index.get("reasons", []) if r["pages"] > 0 and _norm_reason(r["reason"]) not in NORMAL_INDEX_REASONS]
        if bad:
            total = sum(r["pages"] for r in bad)
            top = sorted(bad, key=lambda r: -r["pages"])[:5]
            add("seo.index_summary", "site", f"Google isn't indexing {total} page(s)",
                "; ".join(f"{r['reason']}: {r['pages']}" for r in top), severity="high" if total >= 10 else "medium",
                source="gsc_index",
                evidence="Search Console Page indexing report. Export one reason's page list to see which URLs")


def _gsc_rules(add, gsc: dict, existing: list[Finding], pages: dict) -> None:
    by_url = defaultdict(set)
    for f in existing:
        by_url[f.url].add(f.rule)
    sd = [p for p in gsc.get("pages", []) if 8 <= p["position"] <= 20 and p["impressions"] >= 50]
    for p in sorted(sd, key=lambda x: -x["impressions"])[:20]:
        issues = by_url.get(p["path"], set())
        add("seo.striking_distance", p["path"], f"{p['path']} ranks {p['position']:.1f} with {int(p['impressions'])} impressions",
            f"avg position {p['position']:.1f}, {int(p['clicks'])} clicks", severity="high" if issues else "medium",
            file=(pages.get(p["path"], {}).get("code") or {}).get("file"), source="gsc",
            evidence=(f"same page also has: {', '.join(sorted(issues))}" if issues
                      else "no technical issues found on this page; improve content depth, internal links, answer-first sections"))
    q = [x for x in gsc.get("queries", []) if 8 <= x["position"] <= 20 and x["impressions"] >= 50]
    if q:
        top = sorted(q, key=lambda x: -x["impressions"])[:10]
        add("seo.striking_queries", "site", f"{len(q)} queries rank on page 2 (positions 8–20)",
            "; ".join(f"{x['key']} ({x['position']:.1f}, {int(x['impressions'])} impr.)" for x in top), source="gsc")
