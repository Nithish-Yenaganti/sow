"""Keyword research from web search (no keyword tools, no API keys).

The agent proposes keywords from the site's real content, runs each through its own web
search, and writes the results here. findable then works out, for every keyword:
- whether the site already appears in the results (by domain, so the agent can't misjudge it),
- which other sites appear most (the real competitors for that search),
- which page of the site should target it (the agent's suggestion, checked to be a site path).

There is no search volume without paid data, so keywords are ranked by intent and by how many
competitors cover them, never by invented volumes. If a Search Console Performance export is
present, its real impressions and positions are joined in.

Results file (written by the agent):

    {"engine": "Claude Code WebSearch",
     "keywords": [
       {"keyword": "best whiteboard for remote teams", "intent": "commercial",
        "target_page": "/features", "result_urls": ["https://...", ...]}
     ]}
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from findable.visibility import MAX_URLS, _host

MAX_KEYWORDS = 30
INTENTS = ("informational", "commercial", "comparison", "transactional", "navigational")


def store_path(root: Path) -> Path:
    return root / ".findable" / "keywords.json"


def load(root: Path) -> dict | None:
    try:
        data = json.loads(store_path(root).read_text())
    except (OSError, ValueError):
        return None
    return data.get("latest") if isinstance(data, dict) else None


def evaluate_results(raw: dict, site_url: str) -> dict:
    site = _host(site_url)
    if not site:
        raise ValueError("no site URL to match against; pass --site example.com")
    items = raw.get("keywords") if isinstance(raw, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError('expected {"keywords": [{"keyword": "...", "result_urls": ["https://..."]}]}')
    out, seen = [], set()
    competitors: Counter = Counter()
    for k in items[:MAX_KEYWORDS]:
        if not isinstance(k, dict) or not str(k.get("keyword", "")).strip():
            raise ValueError("every entry needs a non-empty 'keyword'")
        kw = " ".join(str(k["keyword"]).split())[:120]
        if kw.lower() in seen:
            continue
        seen.add(kw.lower())
        urls = [str(u) for u in (k.get("result_urls") or []) if isinstance(u, str) and u.strip()][:MAX_URLS]
        hosts = [_host(u) for u in urls]
        rank = next((i + 1 for i, h in enumerate(hosts) if h == site or h.endswith("." + site)), None)
        ranking_url = urls[rank - 1] if rank else None
        others: list[str] = []
        for h in hosts:
            if h and h != site and not h.endswith("." + site) and h not in others:
                others.append(h)
        competitors.update(others)
        target = str(k.get("target_page") or "").strip()
        target = target if target.startswith("/") and " " not in target else None
        intent = str(k.get("intent") or "").strip().lower()
        out.append({"keyword": kw, "intent": intent if intent in INTENTS else None, "ranks": rank is not None,
                    "rank": rank, "ranking_url": ranking_url, "target_page": target,
                    "results": len(urls), "others": others[:8]})
    return {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": str(raw.get("engine") or "web search")[:80],
        "site": site,
        "keywords": out,
        "ranking": sum(1 for x in out if x["ranks"]),
        "total": len(out),
        # sites that show up across many of your keywords: your real search competitors
        "top_competitors": [{"domain": d, "keywords": n} for d, n in competitors.most_common(8) if n >= 2],
    }


def record(root: Path, results_file: Path, site_url: str) -> dict:
    latest = evaluate_results(json.loads(results_file.read_text()), site_url)
    p = store_path(root)
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        data = {}
    history = data.get("history", []) if isinstance(data, dict) else []
    history.append({k: latest[k] for k in ("checked_at", "engine", "ranking", "total")})
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"latest": latest, "history": history[-50:]}, indent=2, ensure_ascii=False) + "\n")
    return latest


def slug(keyword: str) -> str:
    return "kw:" + "-".join("".join(c if c.isalnum() else " " for c in keyword.lower()).split())[:80]
