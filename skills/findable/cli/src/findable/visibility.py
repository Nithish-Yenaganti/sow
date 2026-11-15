"""AI visibility: do the answers people get for their questions mention this site?

findable has no API keys, so it can't ask ChatGPT or Perplexity directly. The agent runs the
questions through its own web search (the kind of index AI answer engines cite from) and writes
{"engine": "...", "results": [{"query": "...", "result_urls": ["https://...", ...]}]}.
"""

from __future__ import annotations

import json
from pathlib import Path

from findable import search

NAME = "visibility"
MAX_QUERIES = 20


def store_path(root: Path) -> Path:
    return search.store_path(root, NAME)


def load(root: Path) -> dict | None:
    return search.load(root, NAME)


def evaluate_results(raw: dict, site_url: str) -> dict:
    site = search.site_of(site_url)
    out = []
    for r in search.entries(raw, "results", "query", MAX_QUERIES):
        m = search.match(r.get("result_urls"), site)
        out.append({"query": r["query"], "cited": m["found"], "rank": m["rank"], "results": m["results"],
                    "others": m["others"][:8]})
    return {**search.stamp(raw, site), "results": out,
            "cited": sum(1 for x in out if x["cited"]), "total": len(out)}


def record(root: Path, results_file: Path, site_url: str) -> dict:
    return search.save(root, NAME, evaluate_results(json.loads(results_file.read_text()), site_url), ("cited", "total"))
