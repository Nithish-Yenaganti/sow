"""Live scan over plain HTTP: robots.txt, sitemap, page fetches, AI-bot access, no-JS view.

Polite by design: identifies itself, respects robots.txt for its own user agent,
stays on one host, limited concurrency, page budget.
"""

from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

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


def _norm(u: str) -> str:
    p = urlparse(u)
    path = p.path.rstrip("/") or "/"
    return path


async def _get(client: httpx.AsyncClient, url: str, ua: str) -> dict:
    try:
        r = await client.get(url, headers={"User-Agent": ua, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"})
        return {
            "status": r.status_code,
            "final_url": str(r.url),
            "redirects": [str(h.url) for h in r.history],
            "text": r.text if "html" in r.headers.get("content-type", "") or "xml" in r.headers.get("content-type", "") or r.headers.get("content-type", "").startswith("text/") else "",
            "server": r.headers.get("server", ""),
        }
    except httpx.HTTPError as e:
        return {"status": None, "error": f"{type(e).__name__}: {e}", "redirects": [], "text": ""}


async def _sitemap_urls(client: httpx.AsyncClient, url: str, depth: int = 0, limit: int = 2000) -> tuple[list[str], dict]:
    res = await _get(client, url, OWN_UA)
    info = {"url": url, "status": res.get("status"), "error": res.get("error")}
    if res.get("status") != 200 or not res["text"].lstrip().startswith("<"):
        return [], info
    try:
        root = ET.fromstring(res["text"].encode())
    except ET.ParseError as e:
        info["error"] = f"invalid XML: {e}"
        return [], info
    tag = root.tag.split("}")[-1]
    locs = [e.text.strip() for e in root.iter() if e.tag.split("}")[-1] == "loc" and e.text]
    if tag == "sitemapindex" and depth < 2:
        out: list[str] = []
        for child in locs[:20]:
            sub, _ = await _sitemap_urls(client, child, depth + 1, limit)
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
    host = urlparse(base).netloc
    limits = httpx.Limits(max_connections=concurrency)
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, limits=limits) as client:
        site: dict = {"base": base, "reachable": True}

        # robots.txt
        rb = await _get(client, base + "/robots.txt", OWN_UA)
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
            urls, info = await _sitemap_urls(client, sm)
            info["count"] = len(urls)
            site["sitemaps"].append(info)
            sm_urls += urls
        site["sitemap_paths"] = sorted({_norm(u) for u in sm_urls if urlparse(u).netloc in (host, "")})
        foreign = sorted({urlparse(u).netloc for u in sm_urls if urlparse(u).netloc not in (host, "")})
        site["sitemap_foreign_hosts"] = foreign

        # homepage first, then code routes, then sitemap, then discovered links
        queue: list[str] = ["/"]
        for p in paths + site["sitemap_paths"]:
            if p not in queue:
                queue.append(p)
        pages: dict[str, dict] = {}
        sem = asyncio.Semaphore(concurrency)

        async def fetch(path: str):
            url = base + (path if path != "/" else "/")
            if parser and not parser.can_fetch(url, "findable"):
                pages[path] = {"status": None, "skipped": "disallowed for findable in robots.txt", "source": "live"}
                return
            async with sem:
                res = await _get(client, url, BROWSER_UA)
            facts: dict = {"status": res.get("status"), "redirects": res.get("redirects", []),
                           "final_url": res.get("final_url"), "source": "live"}
            if res.get("error"):
                facts["error"] = res["error"]
            if res.get("status") == 200 and res["text"]:
                facts.update(analyze_html(res["text"], url))
                low = res["text"][:20000].lower()
                facts["_markers"] = [m for m in CHALLENGE_MARKERS if m.lower() in low]
                facts["empty_without_js"] = _looks_like_shell(res["text"], facts["word_count"])
                final = urlparse(res.get("final_url") or url)
                if final.netloc and final.netloc != host:
                    facts["redirected_off_host"] = final.netloc
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
        sample = ["/"] + [p for p, f in pages.items() if p != "/" and f.get("status") == 200][:2]
        site["bot_access"] = {}
        for name, (ua, purpose) in AI_BOTS.items():
            results = []
            for p in sample:
                base_status = pages.get(p, {}).get("status")
                r = await _get(client, base + p, ua)
                txt = r.get("text", "")[:20000]
                baseline_markers = set(pages.get(p, {}).get("_markers", []))
                challenged = any(m.lower() in txt.lower() and m not in baseline_markers for m in CHALLENGE_MARKERS)
                blocked = (base_status == 200 and (r.get("status") in (401, 403, 429, 503) or r.get("status") is None or challenged))
                results.append({"path": p, "status": r.get("status"), "baseline": base_status,
                                "challenged": challenged, "blocked": blocked, "server": r.get("server", "")})
            site["bot_access"][name] = {"purpose": purpose, "results": results,
                                        "blocked": any(x["blocked"] for x in results)}
        return {"pages": pages, "site": site}


def scan_live(base_url: str, code_paths: list[str] | None = None, max_pages: int = 50,
              concurrency: int = 4, only_paths: list[str] | None = None) -> dict:
    """Scan a live site. `only_paths` limits page fetches (used by verify)."""
    paths = only_paths if only_paths is not None else (code_paths or [])
    budget = len(paths) + 1 if only_paths is not None else max_pages
    return asyncio.run(_scan(base_url, paths, budget, concurrency))
