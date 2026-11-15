"""Shared plumbing for the two web-search checks (AI visibility, keyword research).

The agent runs searches with its own web search tool and writes the result URLs to a file;
findable decides by domain whether the site appears, so the agent can't misjudge it.
Each check keeps its latest result plus a short history in .findable/<name>.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

MAX_URLS = 20


def host(u: str) -> str:
    h = urlparse(u if "://" in u else "https://" + u).netloc.lower().split(":")[0]
    return h[4:] if h.startswith("www.") else h


def site_of(site_url: str) -> str:
    site = host(site_url)
    if not site:
        raise ValueError("no site URL to match against; pass --site example.com")
    return site


def match(raw_urls, site: str) -> dict:
    """Where (if anywhere) the site appears in one search's results, and who appears instead."""
    urls = [str(u) for u in (raw_urls or []) if isinstance(u, str) and u.strip()][:MAX_URLS]
    ours = lambda h: h == site or h.endswith("." + site)    # noqa: E731
    hosts = [host(u) for u in urls]
    rank = next((i + 1 for i, h in enumerate(hosts) if ours(h)), None)
    others: list[str] = []
    for h in hosts:
        if h and not ours(h) and h not in others:
            others.append(h)
    return {"rank": rank, "found": rank is not None, "url": urls[rank - 1] if rank else None,
            "results": len(urls), "others": others}


def entries(raw: dict, key: str, field: str, limit: int) -> list[dict]:
    """The agent's list, validated: every entry needs a non-empty text field; duplicates dropped."""
    items = raw.get(key) if isinstance(raw, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError(f'expected {{"{key}": [{{"{field}": "...", "result_urls": ["https://..."]}}]}}')
    out, seen = [], set()
    for it in items[:limit]:
        text = " ".join(str(it.get(field, "")).split()) if isinstance(it, dict) else ""
        if not text:
            raise ValueError(f"every entry needs a non-empty '{field}'")
        if text.lower() not in seen:
            seen.add(text.lower())
            out.append({**it, field: text[:200]})
    return out


def stamp(raw: dict, site: str) -> dict:
    return {"checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "engine": str(raw.get("engine") or "web search")[:80], "site": site}


def store_path(root: Path, name: str) -> Path:
    return root / ".findable" / f"{name}.json"


def load(root: Path, name: str) -> dict | None:
    try:
        data = json.loads(store_path(root, name).read_text())
    except (OSError, ValueError):
        return None
    return data.get("latest") if isinstance(data, dict) else None


def save(root: Path, name: str, latest: dict, summary: tuple[str, ...]) -> dict:
    p = store_path(root, name)
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        data = {}
    history = data.get("history", []) if isinstance(data, dict) else []
    history.append({k: latest[k] for k in ("checked_at", "engine", *summary)})
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"latest": latest, "history": history[-50:]}, indent=2, ensure_ascii=False) + "\n")
    return latest


def slug(prefix: str, text: str) -> str:
    return f"{prefix}:" + "-".join("".join(c if c.isalnum() else " " for c in text.lower()).split())[:80]
