"""Accuracy eval for the compliance skill on real open-source projects.

Each project in repos.json is fetched at a pinned commit (so results don't drift), scanned
with a fixed intake profile, and checked against hand-verified expectations:

    must      fingerprints (fnmatch patterns) the scan has to report: real gaps in that code
    must_not  fingerprints it must never report: false alarms checked by reading the code

Writes RESULTS.md next to this file. Needs git and network access on the first run;
checkouts are cached in evals/compliance/.cache/.

    uv run --project skills/compliance/cli python evals/compliance/run.py [--only name,name] [--show]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from compliance import __version__
from compliance.scan import scan

HERE = Path(__file__).parent
CACHE = HERE / ".cache"
BUSINESS = {"business_name": "Eval Co", "contact_email": "privacy@eval.test", "business_address": "1 Test Street",
            "business_country": "United States"}


def checkout(name: str, url: str, sha: str) -> Path:
    dest = CACHE / name
    if (dest / ".git").exists():
        head = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if head == sha:
            return dest
    dest.mkdir(parents=True, exist_ok=True)
    for cmd in (["git", "init", "-q"], ["git", "remote", "remove", "origin"], ["git", "remote", "add", "origin", url],
                ["git", "fetch", "-q", "--depth", "1", "origin", sha], ["git", "checkout", "-q", "--force", "FETCH_HEAD"]):
        r = subprocess.run(cmd, cwd=dest, capture_output=True, text=True)
        if r.returncode and cmd[1] not in ("remote",):
            raise RuntimeError(f"{name}: {' '.join(cmd)} failed: {r.stderr.strip()}")
    return dest


def matches(patterns: list[str], fps: set[str]) -> dict[str, list[str]]:
    """Exact fingerprint first (paths like app/[locale]/… contain fnmatch brackets), then the pattern."""
    return {p: [p] if p in fps else sorted(fnmatch.filter(fps, p)) for p in patterns}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated project names")
    ap.add_argument("--show", action="store_true", help="print every finding (for writing expectations)")
    args = ap.parse_args()
    cfg = json.loads((HERE / "repos.json").read_text())
    only = {x for x in args.only.split(",") if x}
    rows, failures, checks = [], [], 0
    for p in cfg["repos"]:
        if only and p["name"] not in only:
            continue
        t = time.time()
        root = checkout(p["name"], p["url"], p["sha"])
        res = scan(root, p["profile"] | BUSINESS)
        fps = {f.fingerprint for f in res["findings"]}
        if args.show:
            print(f"\n## {p['name']} packs={res['packs']} vendors={[v['name'] for v in res['vendors']]}", file=sys.stderr)
            for f in sorted(res["findings"], key=lambda f: f.fingerprint):
                print(f"  {f.fingerprint}   {f.files[:2]}", file=sys.stderr)
        missing = [pat for pat, hit in matches(p["must"], fps).items() if not hit]
        false_alarms = {pat: hit for pat, hit in matches(p["must_not"], fps).items() if hit}
        checks += len(p["must"]) + len(p["must_not"])
        ok = not missing and not false_alarms
        if not ok:
            failures.append((p["name"], missing, false_alarms))
        rows.append((p, len(fps), ok, round(time.time() - t, 1), res["packs"]))
        print(f"{'PASS' if ok else 'FAIL'}  {p['name']}  missing={missing} false_alarms={false_alarms}", file=sys.stderr)

    if only or args.show:
        return 0 if not failures else 1
    passed = sum(1 for r in rows if r[2])
    lines = [
        "# compliance accuracy eval", "",
        f"compliance {__version__} · run {date.today().isoformat()} · {len(rows)} open-source projects at pinned commits · "
        f"{checks} hand-verified checks · **{passed}/{len(rows)} projects pass**", "",
        "Each project is scanned with a fixed intake profile. A project passes when the scan reports every real gap verified "
        "by reading the code (`must`) and none of the false alarms checked the same way (`must_not`).", "",
        "| Project | Kind | Packs | Findings | Result |", "|---|---|---|---|---|",
    ]
    for p, n, ok, secs, packs in rows:
        lines.append(f"| [{p['name']}]({p['url'].removesuffix('.git')}/tree/{p['sha'][:12]}) | {p['kind']} | "
                     f"{', '.join(packs)} | {n} | {'✅ pass' if ok else '❌ fail'} |")
    if failures:
        lines += ["", "## Failures", ""]
        for name, missing, fa in failures:
            lines.append(f"- {name}: missed {missing or '—'}, false alarms {fa or '—'}")
    gaps = [(p["name"], k, v) for p, *_ in rows for k, v in p.get("known_gaps", {}).items()]
    if gaps:
        lines += ["", "## Known gaps (real problems the scan misses today; not counted as failures)", ""]
        lines += [f"- {name}: `{k}`: {v}" for name, k, v in gaps]
    lines += ["", "## Limits", "",
              "- The scan reads code, so pages managed in a CMS or a hosted platform (Shopify policies, for example) can't be seen.",
              "- Dependency licenses are only read from `package-lock.json` license fields or an installed `node_modules`. "
              "These projects are scanned without installing, so most report `licenses.unchecked`.",
              "- Every expectation was checked by reading the code at the pinned commit. A person should re-check them "
              "before relying on the numbers."]
    lines += ["", "Expectations and the reason for each: [repos.json](repos.json). Re-run: "
              "`uv run --project skills/compliance/cli python evals/compliance/run.py`", ""]
    (HERE / "RESULTS.md").write_text("\n".join(lines))
    print(f"\n{passed}/{len(rows)} projects pass", file=sys.stderr)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
