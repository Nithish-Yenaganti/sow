"""Live scan over plain HTTP: robots.txt, sitemap, page fetches, AI-bot access, no-JS view.

Polite by design: identifies itself, respects robots.txt for its own user agent,
stays on one host, limited concurrency, page budget.
"""

from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import httpx
from protego import Protego

from findable import __version__
from findable.scan_code import analyze_html

OWN_UA = f"findable/{__version__} (site self-audit)"
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")

# name -> (user agent, purpose). "search" = fetches to cite/answer; "training" = model training crawl.
AI_BOTS = {
    "OAI-SearchBot": ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot", "search"),
    "ChatGPT-User": ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot", "search"),
    "GPTBot": ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.1; +https://openai.com/gptbot", "training"),
    "PerplexityBot": ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)", "search"),
    "ClaudeBot": ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)", "training"),
    "Claude-SearchBot": ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-SearchBot/1.0; +https://www.anthropic.com)", "search"),
    "Bingbot": ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm) Chrome/130.0 Safari/537.36", "search"),
    "Googlebot": ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/130.0 Safari/537.36", "search"),
}
# robots.txt-only tokens (no separate crawler UA to fetch with)
ROBOTS_ONLY_TOKENS = {"Google-Extended": "training", "CCBot": "training", "Applebot-Extended": "training"}

CHALLENGE_MARKERS = ("cf-chl", "challenge-platform", "Just a moment...", "Attention Required!",
                     "captcha", "px-captcha", "Access denied", "_Incapsula_")
SHELL_IDS = ("__next", "root", "app", "__nuxt", "svelte", "___gatsby")
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
MAX_PAGE_BYTES = 5_000_000          # untrusted responses are read up to this size
MAX_SITEMAP_BYTES = 20_000_000


def site_host(netloc: str) -> str:
    """Host without port case and a leading www., so example.com and www.example.com match."""
    h = netloc.lower()
    return h[4:] if h.startswith("www.") else h


def _rel(path: str, prefix: str) -> str:
    """Site-relative path: strip the base path (sites served under /repo) and trailing slash."""
    path = path or "/"
    if prefix and (path == prefix or path.startswith(prefix + "/")):
        path = path[len(prefix):] or "/"
    return path.rstrip("/") or "/"


def _allowed_redirect(source: str, target: str) -> bool:
    """Stay on the selected host (including www aliases) and port; allow HTTPS upgrades."""
    old, new = urlparse(source), urlparse(target)
    if new.scheme not in ("http", "https") or new.username is not None or new.password is not None:
        return False
    if site_host(old.hostname or "") != site_host(new.hostname or ""):
        return False
    old_port = old.port or (443 if old.scheme == "https" else 80)
    new_port = new.port or (443 if new.scheme == "https" else 80)
    return (old.scheme == new.scheme and old_port == new_port or
            old.scheme == "http" and new.scheme == "https" and old_port == 80 and new_port == 443)


async def _get(client: httpx.AsyncClient, url: str, ua: str, max_bytes: int = MAX_PAGE_BYTES) -> dict:
    redirects = []
    initial = url
    try:
        for _ in range(21):
            # Never let the HTTP client follow an unvalidated Location header.
            async with client.stream("GET", url, follow_redirects=False,
                                     headers={"User-Agent": ua, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"}) as r:
                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                    target = urljoin(str(r.url), r.headers["location"])
                    if not _allowed_redirect(initial, target):
                        return {"status": None, "final_url": target, "redirects": redirects,
                                "error": "skipped: redirect outside the selected site", "text": ""}
                    redirects.append(str(r.url))
                    url = target
                    continue
                ctype = r.headers.get("content-type", "")
                texty = "html" in ctype or "xml" in ctype or ctype.startswith("text/")
                body = bytearray()
                truncated = False
                if texty:
                    async for chunk in r.aiter_bytes():
                        body += chunk
                        if len(body) > max_bytes:
                            truncated = True
                            break
                text = body[:max_bytes].decode(r.encoding or "utf-8", errors="replace") if texty else ""
                return {"status": r.status_code, "final_url": str(r.url), "redirects": redirects,
                        "text": text, "truncated": truncated, "server": r.headers.get("server", "")}
        return {"status": None, "error": "too many redirects", "redirects": redirects, "text": ""}
    except (httpx.HTTPError, ValueError) as e:
        return {"status": None, "error": f"{type(e).__name__}: {e}", "redirects": redirects, "text": ""}


async def _sitemap_urls(client: httpx.AsyncClient, url: str, host: str, depth: int = 0, limit: int = 2000) -> tuple[list[str], dict]:
    info: dict = {"url": url, "status": None, "error": None}
    if site_host(urlparse(url).netloc) != host:
        # Never follow sitemap references to other hosts (could be internal addresses).
        info["error"] = "skipped: sitemap on another host"
        return [], info
    res = await _get(client, url, OWN_UA, MAX_SITEMAP_BYTES)
    info.update(status=res.get("status"), error=res.get("error"))
    text = res["text"].lstrip()
    if res.get("status") != 200 or not text.startswith("<"):
        return [], info
    if res.get("truncated"):
        info["error"] = f"sitemap larger than {MAX_SITEMAP_BYTES // 1_000_000} MB; not parsed"
        return [], info
    if "<!DOCTYPE" in text[:2000].upper() or "<!ENTITY" in text.upper():
        info["error"] = "sitemap contains a DTD/entities; not parsed"
        return [], info
    try:
        root = ET.fromstring(text.encode())
    except ET.ParseError as e:
        info["error"] = f"invalid XML: {e}"
        return [], info
    tag = root.tag.split("}")[-1]
    locs = [e.text.strip() for e in root.iter() if e.tag.split("}")[-1] == "loc" and e.text]
    if tag == "sitemapindex" and depth < 2:
        out: list[str] = []
        for child in locs[:20]:
            sub, _ = await _sitemap_urls(client, child, host, depth + 1, limit)
            out += sub
            if len(out) >= limit:
                break
        return out[:limit], info
    return locs[:limit], info


def _looks_like_shell(html: str, word_count: int) -> bool:
    if word_count >= 80:
        return False
    return any(re.search(rf'id=["\']{i}["\']', html) for i in SHELL_IDS) or html.count("<script") >= 3


async def _scan(base: str, paths: list[str], max_pages: int, concurrency: int) -> dict:
    base = base.rstrip("/")
    limits = httpx.Limits(max_connections=concurrency)
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, limits=limits) as client:
        # Follow the homepage redirect first (example.com -> www.example.com, http -> https),
        # so every later URL is built on the address the site actually serves.
        home = await _get(client, base + "/", BROWSER_UA)
        if home.get("status") is not None and home.get("final_url"):
            fu = urlparse(home["final_url"])
            gp = urlparse(base)
            if site_host(fu.netloc) == site_host(gp.netloc):
                base = f"{fu.scheme}://{fu.netloc}{gp.path}".rstrip("/")
        parsed = urlparse(base)
        host = site_host(parsed.netloc)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        prefix = parsed.path.rstrip("/")            # e.g. "/repo" for user.github.io/repo
        site: dict = {"base": base, "reachable": True}
        # reuse the homepage we just fetched instead of fetching it again (its redirects belong to the given URL)
        cached = {base + "/": dict(home, redirects=[])} if home.get("status") == 200 else {}

        # robots.txt always lives at the origin root
        rb = await _get(client, origin + "/robots.txt", OWN_UA)
        robots_txt = rb["text"] if rb.get("status") == 200 else ""
        site["robots_status"] = rb.get("status")
        site["robots_text"] = robots_txt
        parser = Protego.parse(robots_txt) if robots_txt else None
        site["robots_ai"] = {}
        if parser:
            for name in list(AI_BOTS) + list(ROBOTS_ONLY_TOKENS):
                purpose = AI_BOTS[name][1] if name in AI_BOTS else ROBOTS_ONLY_TOKENS[name]
                site["robots_ai"][name] = {"allowed_home": parser.can_fetch(base + "/", name), "purpose": purpose}
            sitemaps = list(parser.sitemaps)
        else:
            sitemaps = []

        # sitemap(s)
        if not sitemaps:
            sitemaps = [base + "/sitemap.xml"]
        sm_urls: list[str] = []
        site["sitemaps"] = []
        for sm in sitemaps[:5]:
            urls, info = await _sitemap_urls(client, sm, host)
            info["count"] = len(urls)
            site["sitemaps"].append(info)
            sm_urls += urls
        def in_site(u: str) -> bool:
            pu = urlparse(u)
            same_host = site_host(pu.netloc) in (host, "")
            # for a site under /repo, sitemap entries outside /repo belong to another site
            return same_host and (not prefix or pu.path == prefix or pu.path.startswith(prefix + "/"))
        ours = [u for u in sm_urls if in_site(u)]
        # remember the exact URL to fetch for each path (trailing slash etc. as the site writes it)
        fetch_url: dict[str, str] = {}
        for u in ours:
            fetch_url.setdefault(_rel(urlparse(u).path, prefix), u)
        site["sitemap_paths"] = sorted(fetch_url)
        site["sitemap_foreign_hosts"] = sorted({urlparse(u).netloc for u in sm_urls
                                                if site_host(urlparse(u).netloc) not in (host, "")})

        # homepage first, then code routes, then sitemap, then discovered links
        queue: list[str] = ["/"]
        for p in paths + site["sitemap_paths"]:
            if p not in queue:
                queue.append(p)
        pages: dict[str, dict] = {}
        sem = asyncio.Semaphore(concurrency)

        def url_for(path: str) -> str:
            return fetch_url.get(path) or base + (path if path != "/" else "/")

        async def fetch(path: str):
            url = url_for(path)
            if parser and not parser.can_fetch(url, "findable"):
                pages[path] = {"status": None, "skipped": "disallowed for findable in robots.txt", "source": "live"}
                return
            res = cached.pop(url, None)
            if res is None:
                async with sem:
                    res = await _get(client, url, BROWSER_UA)
            facts: dict = {"status": res.get("status"), "redirects": res.get("redirects", []),
                           "final_url": res.get("final_url"), "source": "live"}
            if res.get("error"):
                facts["error"] = res["error"]
            final = urlparse(res.get("final_url") or url)
            if final.netloc and site_host(final.netloc) != host:
                # this link leaves the site (e.g. /chat -> discord.com): not one of the site's pages
                facts["redirected_off_host"] = final.netloc
                pages[path] = facts
                return
            if res.get("status") == 200 and res["text"]:
                facts.update(analyze_html(res["text"], url))
                # links and canonical as site-relative paths (handles www/apex and /repo base paths)
                rel_links = []
                for link in facts.get("links", []):
                    rl = _rel(link, prefix)
                    if rl not in rel_links:
                        rel_links.append(rl)
                facts["links"] = rel_links
                for link, abs_url in facts.pop("link_urls", {}).items():
                    au = urlparse(abs_url)
                    if site_host(au.netloc) == host:
                        fetch_url.setdefault(_rel(link, prefix), abs_url)
                if facts.get("canonical"):
                    cu = urlparse(facts["canonical"])
                    facts["canonical_path"] = _rel(cu.path, prefix)
                    facts["canonical_other_host"] = bool(cu.netloc) and site_host(cu.netloc) != host
                low = res["text"][:20000].lower()
                facts["_markers"] = [m for m in CHALLENGE_MARKERS if m.lower() in low]
                facts["empty_without_js"] = _looks_like_shell(res["text"], facts["word_count"])
            pages[path] = facts

        i = 0
        while i < len(queue) and len(pages) < max_pages:
            batch = queue[i: i + concurrency]
            i += len(batch)
            await asyncio.gather(*(fetch(p) for p in batch))
            for p in batch:
                for link in pages.get(p, {}).get("links", []):
                    if link not in queue and not re.search(r"\.(png|jpe?g|gif|svg|webp|pdf|zip|css|js|ico|xml|txt)$", link, re.I):
                        queue.append(link)
        site["discovered"] = len(queue)
        site["scanned"] = len(pages)
        if pages.get("/", {}).get("status") is None and "error" in pages.get("/", {}):
            site["reachable"] = False
            site["error"] = pages["/"]["error"]
            return {"pages": pages, "site": site}

        # AI-bot access: homepage + up to 2 other OK pages, each bot UA vs. a browser baseline
        sample = ["/"] + [p for p, f in pages.items()
                          if p != "/" and f.get("status") == 200 and "title" in f and not f.get("redirected_off_host")][:2]
        async def probe(ua: str, p: str) -> dict:
            async with sem:
                r = await _get(client, url_for(p), ua)
            base_status = pages.get(p, {}).get("status")
            txt = r.get("text", "")[:20000].lower()
            baseline_markers = set(pages.get(p, {}).get("_markers", []))
            challenged = any(m.lower() in txt and m not in baseline_markers for m in CHALLENGE_MARKERS)
            blocked = base_status == 200 and (r.get("status") in (401, 403, 429, 503) or r.get("status") is None or challenged)
            return {"path": p, "status": r.get("status"), "baseline": base_status,
                    "challenged": challenged, "blocked": blocked, "server": r.get("server", "")}

        # all bot requests at once (limited by the same concurrency as the crawl)
        probes = await asyncio.gather(*(probe(ua, p) for ua, _ in AI_BOTS.values() for p in sample))
        site["bot_access"] = {}
        for i, (name, (ua, purpose)) in enumerate(AI_BOTS.items()):
            results = probes[i * len(sample):(i + 1) * len(sample)]
            site["bot_access"][name] = {"purpose": purpose, "results": results, "blocked": any(x["blocked"] for x in results)}
        return {"pages": pages, "site": site}


def scan_live(base_url: str, code_paths: list[str] | None = None, max_pages: int = 50,
              concurrency: int = 4, only_paths: list[str] | None = None) -> dict:
    """Scan a live site. `only_paths` limits page fetches (used by verify)."""
    paths = only_paths if only_paths is not None else (code_paths or [])
    budget = len(paths) + 1 if only_paths is not None else max_pages
    return asyncio.run(_scan(base_url, paths, budget, concurrency))
