"""Terminal summary (≤ 6 lines + do-first items) and a single-page HTML report."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from findable import __version__
from findable.plain import CHANGE_LABEL, GROUPS, describe

MARK = {"critical": "✗", "high": "✗", "medium": "⚠", "low": "·"}


def do_first(items: list[dict], n: int = 3) -> list[dict]:
    """User-only steps and critical/high issues, regressions first."""
    picked = [r for r in items if r["status"] == "regressed"]
    picked += [r for r in items if r not in picked and (r["severity"] in ("critical", "high") or
                                                         (r.get("who") == "user" and r["severity"] != "low"))]
    picked += [r for r in items if r not in picked]
    return picked[:n]


def _plain(r: dict) -> dict:
    """Plain fields for a stored finding (older stores may not have them)."""
    if "plain" in r and r.get("plain"):
        return r
    return dict(r, **describe(r.get("rule", ""), r.get("url", "site"), r.get("who", "agent"),
                              r.get("title", ""), r.get("current", "")))


def is_minor(r: dict) -> bool:
    """Low-impact fixes are folded away (shown on request), unless they came back after a fix."""
    return r.get("severity") == "low" and r.get("who") != "user" and r.get("status") != "regressed"


def grouped(items: list[dict], include_minor: bool = False) -> list[tuple[str, str, list[dict]]]:
    """[(group id, group question, findings)] in display order, empty groups left out."""
    out = []
    for gid, label in GROUPS.items():
        fs = [x for x in (_plain(r) for r in items) if x["group"] == gid and (include_minor or not is_minor(x))]
        if fs:
            out.append((gid, label, fs))
    return out


def terminal(run: dict, items: list[dict], delta: dict, report_path: str) -> str:
    site = run.get("url") or f"{run.get('name') or run['app']} (code only)"
    checked = "your code and live site" if run.get("live_ok") else "your code only"
    lines = [f"{site}: checked {run['pages']} page{'s' if run['pages'] != 1 else ''} ({checked})"]
    fixable = [r for r in items if r.get("who") != "user"]
    urgent = sum(1 for r in fixable if r["severity"] in ("critical", "high"))
    if not fixable:
        lines.append("Nothing to fix in the site. ✓")
    else:
        lines.append(f"Found {len(fixable)} thing{'s' if len(fixable) != 1 else ''} to improve"
                     + (f" ({urgent} important)" if urgent else "") + ".")
    if run.get("previous_run") and (delta["fixed"] or delta["regressed"]):
        lines.append(f"Since last time: {len(delta['fixed'])} fixed ✓"
                     + (f", {len(delta['regressed'])} came back ✗" if delta["regressed"] else ""))
    for gid, label, fs in grouped(items):
        lines.append("")
        lines.append(f"{label}  ({len(fs)})")
        for r in fs[:3]:
            mark = "→" if gid == "you" else MARK[r["severity"]]
            lines.append(f"  {mark} {r['plain'] or r['title']}")
        if len(fs) > 3:
            lines.append(f"  … and {len(fs) - 3} more in the report")
    minor = [r for r in items if is_minor(r)]
    lines.append("")
    if minor:
        lines.append(f"Plus {len(minor)} minor improvement{'s' if len(minor) != 1 else ''} (low impact), folded away in the report.")
    lines.append(f"Full report: {report_path}")
    return "\n".join(lines)


def html(run: dict, items: list[dict], delta: dict, dismissed: list[dict]) -> str:
    env = Environment(loader=PackageLoader("findable", "templates"), autoescape=select_autoescape(["html"]))
    items = [_plain(r) for r in items]
    by_page: dict[str, list[dict]] = {}
    for r in items:
        by_page.setdefault(r["url"], []).append(r)
    order = sorted(by_page, key=lambda u: (u != "site", u))
    return env.get_template("report.html").render(
        run=run, items=items, delta=delta, top=do_first(items, 5), pages=[(u, by_page[u]) for u in order],
        groups=grouped(items), minor=[r for r in items if is_minor(r)], change_label=CHANGE_LABEL,
        dismissed=dismissed, version=__version__,
        generated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        counts={s: sum(1 for r in items if r["severity"] == s and r.get("who") != "user")
                for s in ("critical", "high", "medium", "low")},
    )


def write_html(root: Path, content: str) -> Path:
    p = root / ".findable" / "report.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p
