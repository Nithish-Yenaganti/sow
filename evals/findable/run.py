"""Live accuracy eval for findable.

Scans each site in sites.json (12 pages, 2 at a time, robots.txt respected) and checks
the hand-verified expectations. Writes RESULTS.md next to this file.

    uv run --project skills/findable/cli python evals/findable/run.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

from findable import __version__
from findable.rules import evaluate
from findable.scan_live import scan_live

HERE = Path(__file__).parent
LIVE_ONLY_CODE = {"pages": {}, "site": {"framework": "static", "robots": "(live only)", "sitemap": "(live only)", "orphans": []}}


def main() -> int:
    cfg = json.loads((HERE / "sites.json").read_text())
    rows, failures, total_findings, checks = [], [], 0, 0
    for s in cfg["sites"]:
        t = time.time()
        live = scan_live(s["url"], [], max_pages=12, concurrency=2)
        rules = Counter(f.rule for f in evaluate(LIVE_ONLY_CODE, live, None))
        total_findings += sum(rules.values())
        missing = [r for r in s["must"] if r not in rules]
        false_alarms = [r for r in s["must_not"] if r in rules]
        checks += len(s["must"]) + len(s["must_not"])
        ok = not missing and not false_alarms and live["site"].get("reachable")
        if not ok:
            failures.append((s["url"], missing, false_alarms))
        rows.append((s, live["site"].get("scanned", 0), sum(rules.values()), ok, round(time.time() - t, 1)))
        print(f"{'PASS' if ok else 'FAIL'}  {s['url']}  missing={missing} false_alarms={false_alarms}", file=sys.stderr)

    passed = sum(1 for r in rows if r[3])
    lines = [
        "# findable accuracy eval",
        "",
        f"findable {__version__} · run {date.today().isoformat()} · {len(rows)} real sites · "
        f"{checks} hand-verified checks · **{passed}/{len(rows)} sites pass**",
        "",
        "Each site is scanned live (12 pages). A site passes when findable reports every real problem we verified by hand "
        "(`must`) and none of the false alarms it used to raise (`must_not`).",
        "",
        "| Site | Stack | Pages | Findings | Result |",
        "|---|---|---|---|---|",
    ]
    for s, scanned, n, ok, secs in rows:
        lines.append(f"| {s['url']} | {s['stack']} | {scanned} | {n} | {'✅ pass' if ok else '❌ fail'} |")
    if failures:
        lines += ["", "## Failures", ""]
        for url, missing, fa in failures:
            lines.append(f"- {url}: missed {missing or '—'}, false alarms {fa or '—'}")
    lines += ["", "Expectations and why: [sites.json](sites.json). Re-run: "
              "`uv run --project skills/findable/cli python evals/findable/run.py`", ""]
    (HERE / "RESULTS.md").write_text("\n".join(lines))
    print(f"\n{passed}/{len(rows)} sites pass, {total_findings} findings", file=sys.stderr)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
