"""Terminal summary (≤ 6 lines + do-first items) and a single-page HTML report."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from findable import __version__

MARK = {"critical": "✗", "high": "✗", "medium": "⚠", "low": "·"}


def do_first(items: list[dict], n: int = 3) -> list[dict]:
    """User-only steps and critical/high issues, regressions first."""
    picked = [r for r in items if r["status"] == "regressed"]
    picked += [r for r in items if r not in picked and (r["severity"] in ("critical", "high") or
                                                         (r.get("who") == "user" and r["severity"] != "low"))]
    picked += [r for r in items if r not in picked]
    return picked[:n]


def terminal(run: dict, items: list[dict], delta: dict, report_path: str) -> str:
    site = run.get("url") or f"{run.get('name') or run['app']} (code only)"
    sources = "code" + (" + live" if run.get("live_ok") else "") + (" + Search Console CSV" if run.get("gsc") else "")
    skipped = [] if run.get("live_ok") else ["live: no URL" if not run.get("url") else "live: unreachable"]
    if not run.get("gsc"):
        skipped.append("no GSC CSV")
    lines = [f"{site} · {run['pages']} pages · {sources}" + (f" ({', '.join(skipped)})" if skipped else "")]
    counts = {s: sum(1 for r in items if r["severity"] == s) for s in ("critical", "high", "medium", "low")}
    lines.append("Open: " + " · ".join(f"{v} {k}" for k, v in counts.items() if v) if items else "Open: nothing — all checks pass ✓")
    if run.get("previous_run"):
        lines.append(f"Since last run: {len(delta['fixed'])} fixed ✓ · {len(delta['regressed'])} regressed ✗ · {len(delta['new'])} new")
    top = do_first(items)
    if top:
        lines.append("Do these first:")
        for i, r in enumerate(top, 1):
            who = "you" if r.get("who") == "user" else ("auto-fix" if r.get("auto_fixable") else "agent")
            tag = " [regressed]" if r["status"] == "regressed" else ""
            lines.append(f"  {i}. {MARK[r['severity']]} {r['title']}{tag}  — {who}")
    lines.append(f"Report: {report_path}")
    return "\n".join(lines)


def html(run: dict, items: list[dict], delta: dict, dismissed: list[dict]) -> str:
    env = Environment(loader=PackageLoader("findable", "templates"), autoescape=select_autoescape(["html"]))
    by_page: dict[str, list[dict]] = {}
    for r in items:
        by_page.setdefault(r["url"], []).append(r)
    order = sorted(by_page, key=lambda u: (u != "site", u))
    return env.get_template("report.html").render(
        run=run, items=items, delta=delta, top=do_first(items, 5), pages=[(u, by_page[u]) for u in order],
        dismissed=dismissed, version=__version__,
        generated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        counts={s: sum(1 for r in items if r["severity"] == s) for s in ("critical", "high", "medium", "low")},
    )


def write_html(root: Path, content: str) -> Path:
    p = root / ".findable" / "report.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p
