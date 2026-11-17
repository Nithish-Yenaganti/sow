"""Findings across runs (new → open → fixed / dismissed), the data map, and the markdown report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from compliance import atomic
from compliance.profile import state_dir
from compliance import report_html as rh
from compliance.rules import GROUPS, SEVERITY_RANK

ACTIVE = {"new", "open"}
WHO = {"agent": "the skill can fix", "user": "you", "lawyer": "ask a lawyer"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(p: Path, default):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _save(p: Path, data) -> None:
    atomic.write_json(p, data)


def load_findings(root: Path) -> dict:
    return _load(state_dir(root) / "findings.json", {})


def save_findings(root: Path, store: dict) -> None:
    _save(state_dir(root) / "findings.json", store)


def load_data_map(root: Path) -> list:
    return _load(state_dir(root) / "data-map.json", [])


def save_data_map(root: Path, fresh: list[dict]) -> list[dict]:
    """Keep the user's edits (purpose, basis, retention) for rows that still exist."""
    old = {d["key"]: d for d in load_data_map(root)}
    out = []
    for d in fresh:
        prev = old.get(d["key"])
        if prev and prev.get("edited"):
            d = d | {k: prev[k] for k in ("purpose", "lawful_basis", "retention", "shared_with", "edited") if k in prev}
        out.append(d)
    for k, prev in old.items():
        if prev.get("manual") and k not in {d["key"] for d in out}:
            out.append(prev)
    _save(state_dir(root) / "data-map.json", out)
    return out


def apply_run(store: dict, current: list[dict], only: set[str] | None = None) -> dict:
    seen, delta = set(), {"new": [], "fixed": [], "open": []}
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
            if rec["status"] == "fixed":
                delta["new"].append(fp)
            else:
                delta["open"].append(fp)
            rec["status"] = "open" if rec["status"] != "fixed" else "new"
        rec.update({k: v for k, v in f.items() if k != "status"})
        rec["last_seen"] = _now()
    for fp, rec in store.items():
        if fp not in seen and rec["status"] in ACTIVE and (only is None or fp in only):
            rec["status"] = "fixed"
            rec["fixed_at"] = _now()
            delta["fixed"].append(fp)
    return delta


def active(store: dict) -> list[dict]:
    items = [dict(r, fingerprint=fp) for fp, r in store.items() if r.get("status") in ACTIVE]
    order = list(GROUPS)
    return sorted(items, key=lambda r: (order.index(r["group"]), SEVERITY_RANK.get(r["severity"], 9), r["fingerprint"]))


def report_md(run: dict, items: list[dict], data_map: list[dict]) -> str:
    now = sum(1 for i in items if i["severity"] == "high")
    lines = [f"# Compliance report: {run['name']}", "",
             f"Scanned {run['files']} files on {run['at'][:10]}. Packs: {', '.join(run['packs'])}.", "",
             "> This report finds technical gaps. It is not legal advice and doesn't make your site 'compliant'. "
             "Items marked ⚖️ need a lawyer.", "",
             f"**{len(items)} things to look at, {now} to fix now.**", ""]
    if data_map:
        lines += ["## What your app collects", "", "| Data | Why | Legal basis | Kept for | Shared with |", "|---|---|---|---|---|"]
        lines += [f"| {d['data']} | {d['purpose']} | {d['lawful_basis']} | {d.get('retention') or 'not set yet'} | "
                  f"{', '.join(d['shared_with']) or 'nobody'} |" for d in data_map]
        lines.append("")
    for g, title in GROUPS.items():
        rows = [i for i in items if i["group"] == g]
        if not rows:
            continue
        lines += [f"## {title}", ""]
        for i in rows:
            mark = "⚖️ " if i["who"] == "lawyer" else ""
            lines.append(f"- **{rh.ACTION_LABEL[i['severity']]}** {mark}{i['plain']} *(who: {WHO[i['who']]}; `{i['fingerprint']}`)*")
            if i.get("files"):
                lines.append(f"  - where: {', '.join(i['files'][:5])}")
            if i.get("sources"):
                lines.append(f"  - sources: {', '.join(i['sources'])} (see references/sources.md)")
        lines.append("")
    return "\n".join(lines)


WHO_HTML = {"agent": "The skill can fix this", "user": "You do this", "lawyer": "Ask a lawyer"}


def report_html(run: dict, items: list[dict], data_map: list[dict]) -> str:
    table = ""
    if data_map:
        e = rh._e
        rows = "".join(f"<tr><td>{e(d['data'])}</td><td>{e(d['purpose'])}</td><td>{e(d['lawful_basis'])}</td>"
                       f"<td>{e(d.get('retention') or 'not set yet')}</td><td>{e(', '.join(d['shared_with']) or 'nobody')}</td></tr>"
                       for d in data_map)
        table = ("<h2>What your app collects</h2><section class='card'><table><thead><tr><th>Data</th><th>Why</th>"
                 f"<th>Legal basis</th><th>Kept for</th><th>Shared with</th></tr></thead><tbody>{rows}</tbody></table></section>")
    return rh.render(
        title=f"Compliance report: {run['name']}",
        meta=[f"Scanned {run['files']} files on {rh._e(run['at'][:10])} · packs: {rh._e(', '.join(run['packs']))}"],
        note="This report finds technical gaps. It is not legal advice and doesn't make your site 'compliant'. "
             "Items marked ⚖️ need a lawyer.",
        items=items, groups=GROUPS, who_label=WHO_HTML, before_findings=table,
        footer=f"compliance {run.get('version', '')} · findings are tracked across runs in .compliance/findings.json")


def write_report_html(root: Path, text: str) -> Path:
    return atomic.write_text(state_dir(root) / "report.html", text)


def write_report(root: Path, text: str) -> Path:
    return atomic.write_text(state_dir(root) / "report.md", text)
