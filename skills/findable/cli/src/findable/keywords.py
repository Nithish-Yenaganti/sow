"""Keyword research from web search (no keyword tools, no API keys).

The agent proposes keywords from the site's real content, searches each, and writes
{"engine": "...", "keywords": [{"keyword": "...", "intent": "commercial", "target_page": "/features",
"result_urls": ["https://...", ...]}]}. findable works out whether the site appears, who appears
instead, and the sites that show up most across all searches. There are no search volumes:
keywords are ranked by intent, never by invented numbers.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from findable import search

NAME = "keywords"
MAX_KEYWORDS = 30
INTENTS = ("informational", "commercial", "comparison", "transactional", "navigational")


def store_path(root: Path) -> Path:
    return search.store_path(root, NAME)


def load(root: Path) -> dict | None:
    return search.load(root, NAME)


def evaluate_results(raw: dict, site_url: str) -> dict:
    site = search.site_of(site_url)
    out, competitors = [], Counter()
    for k in search.entries(raw, "keywords", "keyword", MAX_KEYWORDS):
        m = search.match(k.get("result_urls"), site)
        competitors.update(m["others"])
        target = str(k.get("target_page") or "").strip()
        intent = str(k.get("intent") or "").strip().lower()
        out.append({"keyword": k["keyword"][:120], "intent": intent if intent in INTENTS else None,
                    "ranks": m["found"], "rank": m["rank"], "ranking_url": m["url"],
                    "target_page": target if target.startswith("/") and " " not in target else None,
                    "results": m["results"], "others": m["others"][:8]})
    return {**search.stamp(raw, site), "keywords": out,
            "ranking": sum(1 for x in out if x["ranks"]), "total": len(out),
            # sites that show up across many of your keywords: your real search competitors
            "top_competitors": [{"domain": d, "keywords": n} for d, n in competitors.most_common(8) if n >= 2]}


def record(root: Path, results_file: Path, site_url: str) -> dict:
    return search.save(root, NAME, evaluate_results(json.loads(results_file.read_text()), site_url), ("ranking", "total"))
