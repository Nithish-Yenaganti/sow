"""Findings across runs (new → open → fixed / dismissed) and the markdown report. Writes only inside .guarded/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from guarded import atomic
from guarded.rules import GROUPS, SEVERITY_RANK

ACTIVE = {"new", "open"}
WHO = {"agent": "the skill can fix", "user": "you"}


def state_dir(root: Path) -> Path:
    return root / ".guarded"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_findings(root: Path) -> dict:
    try:
        return json.loads((state_dir(root) / "findings.json").read_text())
    except (OSError, ValueError):
        return {}


def save_findings(root: Path, store: dict) -> None:
    p = state_dir(root) / "findings.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    ignore = p.parent / ".gitignore"
    if not ignore.exists():
        ignore.write_text("# guarded scan output; keep it out of git\n*\n")
    atomic.write_json(p, store)


def apply_run(store: dict, current: list[dict], only: set[str] | None = None, scope: set[str] | None = None,
              suppressed: set[str] = frozenset()) -> dict:
    """scope: rules this run checked. Findings from rules it skipped (packages, when offline) stay as they were.
    suppressed: fingerprints a guarded-ignore comment silenced. They leave the active list but are not "fixed"."""
    seen, delta = set(), {"new": [], "fixed": [], "open": [], "suppressed": []}
    for f in current:
        fp = f["fingerprint"]
        seen.add(fp)
        rec = store.get(fp)
        if rec is None:
            rec = store[fp] = {"status": "new", "first_seen": _now()}
            delta["new"].append(fp)
        elif rec["status"] == "dismissed":
            rec.update({k: v for k, v in f.items() if k != "status"})
            continue
        else:
            delta["new" if rec["status"] == "fixed" else "open"].append(fp)
            rec["status"] = "new" if rec["status"] == "fixed" else "open"
        rec.update({k: v for k, v in f.items() if k != "status"})
        rec["last_seen"] = _now()
    for fp, rec in store.items():
        if fp in seen or rec["status"] not in ACTIVE or (only is not None and fp not in only):
            continue
        if scope is not None and rec.get("rule") not in scope:
            continue
        if fp in suppressed:
            rec["status"] = "suppressed"
            delta["suppressed"].append(fp)
            continue
        rec["status"] = "fixed"
        rec["fixed_at"] = _now()
        delta["fixed"].append(fp)
    return delta


def active(store: dict) -> list[dict]:
    items = [dict(r, fingerprint=fp) for fp, r in store.items() if r.get("status") in ACTIVE]
    order = list(GROUPS)
    return sorted(items, key=lambda r: (SEVERITY_RANK.get(r["severity"], 9), order.index(r["group"]), r["fingerprint"]))


def report_md(run: dict, items: list[dict]) -> str:
    counts = {s: sum(1 for i in items if i["severity"] == s) for s in ("high", "medium", "low")}
    lines = [f"# Security report: {run['name']}", "",
             f"Scanned {run['files']} files on {run['at'][:10]} with guarded {run['version']}. "
             f"Package lookups: {'on' if run['online'] else 'off (run with --online to check packages and known CVEs)'}.", "",
             "> This is a code check that looks for known risky patterns. It is not a penetration test and can't prove "
             "an app is secure. It can also flag code that is actually fine: each item says why, so you can check.", "",
             f"**{len(items)} things to look at: {counts['high']} high, {counts['medium']} medium, {counts['low']} low.**", ""]
    for g, title in GROUPS.items():
        rows = [i for i in items if i["group"] == g]
        if not rows:
            continue
        lines += [f"## {title}", ""]
        for i in rows:
            lines.append(f"- **{i['severity']}** {i['plain']} *(who: {WHO[i['who']]}; `{i['fingerprint']}`)*")
            if i.get("files"):
                lines.append(f"  - where: {', '.join(i['files'][:5])}")
            if i.get("sources"):
                lines.append(f"  - based on: {', '.join(i['sources'])} (see references/sources.md)")
        lines.append("")
    return "\n".join(lines)


def write_report(root: Path, text: str) -> Path:
    return atomic.write_text(state_dir(root) / "report.md", text)
