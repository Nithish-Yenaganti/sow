"""AI visibility: do the answers people get for their questions mention this site?

findable has no API keys, so it can't ask ChatGPT or Perplexity directly. Instead the
coding agent runs the questions through its own web search tool (the same kind of index
AI answer engines cite from) and writes the results to a JSON file. This module checks and
stores those results; rules.py turns them into findings.

Results file (written by the agent):

    {
      "engine": "Claude Code WebSearch",
      "results": [
        {"query": "best static site generator for docs",
         "result_urls": ["https://astro.build/...", "https://gohugo.io/...", ...]}
      ]
    }

findable decides "cited" itself by matching the site's domain against result_urls, so the
agent can't misjudge it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

MAX_QUERIES = 20
MAX_URLS = 20


def _host(u: str) -> str:
    h = urlparse(u if "://" in u else "https://" + u).netloc.lower().split(":")[0]
    return h[4:] if h.startswith("www.") else h


def store_path(root: Path) -> Path:
    return root / ".findable" / "visibility.json"


def load(root: Path) -> dict | None:
    """Latest recorded check, or None."""
    try:
        data = json.loads(store_path(root).read_text())
    except (OSError, ValueError):
        return None
    return data.get("latest") if isinstance(data, dict) else None


def evaluate_results(raw: dict, site_url: str) -> dict:
    """Validate the agent's file and decide, per query, whether the site appears."""
    site = _host(site_url)
    if not site:
        raise ValueError("no site URL to match against; scan with --url first or pass --site")
    results = raw.get("results") if isinstance(raw, dict) else None
    if not isinstance(results, list) or not results:
        raise ValueError('expected {"results": [{"query": "...", "result_urls": ["https://..."]}]}')
    out = []
    for r in results[:MAX_QUERIES]:
        if not isinstance(r, dict) or not str(r.get("query", "")).strip():
            raise ValueError("every result needs a non-empty 'query'")
        urls = [str(u) for u in (r.get("result_urls") or []) if isinstance(u, str) and u.strip()][:MAX_URLS]
        hosts = [_host(u) for u in urls]
        rank = next((i + 1 for i, h in enumerate(hosts) if h == site or h.endswith("." + site)), None)
        others = []
        for h in hosts:
            if h and h != site and not h.endswith("." + site) and h not in others:
                others.append(h)
        out.append({"query": " ".join(str(r["query"]).split())[:200], "cited": rank is not None,
                    "rank": rank, "results": len(urls), "others": others[:8]})
    return {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": str(raw.get("engine") or "web search")[:80],
        "site": site,
        "results": out,
        "cited": sum(1 for x in out if x["cited"]),
        "total": len(out),
    }


def record(root: Path, results_file: Path, site_url: str) -> dict:
    raw = json.loads(results_file.read_text())
    latest = evaluate_results(raw, site_url)
    p = store_path(root)
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        data = {}
    history = data.get("history", []) if isinstance(data, dict) else []
    history.append({k: latest[k] for k in ("checked_at", "engine", "cited", "total")})
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"latest": latest, "history": history[-50:]}, indent=2, ensure_ascii=False) + "\n")
    return latest


def slug(query: str) -> str:
    return "q:" + "-".join("".join(c if c.isalnum() else " " for c in query.lower()).split())[:80]
