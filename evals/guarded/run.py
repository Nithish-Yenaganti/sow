"""Accuracy eval for the guarded skill on real open-source projects.

Each project in repos.json is fetched at a pinned commit (so results don't drift) and scanned offline. Expectations were
checked by reading the code at that commit:

    must          fingerprints (fnmatch patterns) the scan has to report: real problems in that code
    must_not      fingerprints it must never report: false alarms, or a CVE that the pinned commit has fixed
    online_must   like must, only checked with --online (package lookups against npm, PyPI and OSV)

The set includes MCP servers at the commit just before a published CVE fix, and the same servers at the fix commit, so
the eval shows the scan catches the bug and goes quiet once it's fixed.

Writes RESULTS.md next to this file. Needs git and network access on the first run; checkouts are cached in
evals/guarded/.cache/.

    uv run --project skills/guarded/cli python evals/guarded/run.py [--only name,name] [--show] [--online]
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

from guarded import __version__
from guarded.scan import scan

HERE = Path(__file__).parent
CACHE = HERE / ".cache"


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
    ap.add_argument("--online", action="store_true", help="also check packages (npm, PyPI, OSV) and online_must")
    args = ap.parse_args()
    cfg = json.loads((HERE / "repos.json").read_text())
    only = {x for x in args.only.split(",") if x}
    rows, failures, checks = [], [], 0
    for p in cfg["repos"]:
        if only and p["name"] not in only:
            continue
        t = time.time()
        root = checkout(p["name"], p["url"], p["sha"])
        res = scan(root, online=args.online)
        fps = {f.fingerprint for f in res["findings"]}
        if args.show:
            print(f"\n## {p['name']} stack={res['stack']}", file=sys.stderr)
            for f in sorted(res["findings"], key=lambda f: f.fingerprint):
                print(f"  {f.fingerprint}   {f.files[:2]}", file=sys.stderr)
        must = p["must"] + (p.get("online_must", []) if args.online else [])
        missing = [pat for pat, hit in matches(must, fps).items() if not hit]
        false_alarms = {pat: hit for pat, hit in matches(p["must_not"], fps).items() if hit}
        checks += len(must) + len(p["must_not"])
        ok = not missing and not false_alarms
        if not ok:
            failures.append((p["name"], missing, false_alarms))
        high = sum(1 for f in res["findings"] if f.to_dict()["severity"] == "high")
        rows.append((p, len(fps), high, ok, round(time.time() - t, 1)))
        print(f"{'PASS' if ok else 'FAIL'}  {p['name']}  missing={missing} false_alarms={false_alarms}", file=sys.stderr)

    if only or args.show:
        return 0 if not failures else 1
    passed = sum(1 for r in rows if r[3])
    mode = "offline and online (packages)" if args.online else "offline"
    lines = [
        "# guarded accuracy eval", "",
        f"guarded {__version__} · run {date.today().isoformat()} · {len(rows)} open-source projects at pinned commits · "
        f"scanned {mode} · {checks} hand-verified checks · **{passed}/{len(rows)} projects pass**", "",
        "A project passes when the scan reports every real problem verified by reading the code (`must`) and none of the "
        "false alarms checked the same way (`must_not`). Three MCP servers are scanned at the commit just before their "
        "CVE fix; two of them are also scanned at the fix commit, where the shell-injection finding has to be gone.", "",
        "| Project | What it is | Findings (high) | Result |", "|---|---|---|---|",
    ]
    for p, n, high, ok, secs in rows:
        lines.append(f"| [{p['name']}]({p['url'].removesuffix('.git')}/tree/{p['sha'][:12]}) | {p['kind']} | {n} ({high}) | "
                     f"{'✅ pass' if ok else '❌ fail'} |")
    if failures:
        lines += ["", "## Failures", ""]
        for name, missing, fa in failures:
            lines.append(f"- {name}: missed {missing or '—'}, false alarms {fa or '—'}")
    gaps = [(p["name"], k, v) for p, *_ in rows for k, v in p.get("known_gaps", {}).items()]
    if gaps:
        lines += ["", "## Known gaps (real problems the scan misses today; not counted as failures)", ""]
        lines += [f"- {name}: `{k}`: {v}" for name, k, v in gaps]
    lines += ["", "## Limits", "",
              "- This measures known bugs in these projects, not every bug they have. A clean result on the production "
              "templates means no false alarms on them, not that they're bug-free.",
              "- Package checks (`pkg.*`) depend on live npm, PyPI and OSV data, so they run only with `--online` and aren't "
              "part of the weekly numbers.",
              "- Every expectation was checked by reading the code at the pinned commit. A person should re-check them "
              "before relying on the numbers."]
    lines += ["", "Expectations and the reason for each: [repos.json](repos.json). Re-run: "
              "`uv run --project skills/guarded/cli python evals/guarded/run.py`", ""]
    (HERE / "RESULTS.md").write_text("\n".join(lines))
    print(f"\n{passed}/{len(rows)} projects pass", file=sys.stderr)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
