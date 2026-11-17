"""Single-page HTML report in the shared SOW style (templates/report.css).

This file is identical in the compliance and guarded skills; tests/compliance/test_report_html.py checks that.
Every value from the scanned project is escaped: it's data, never markup.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

# What each severity means for the user. The same wording in every SOW skill.
ACTION_LABEL = {"critical": "Fix now", "high": "Fix now", "medium": "Fix soon", "low": "When you can"}
PILL_CLASS = {"critical": "now", "high": "now", "medium": "soon", "low": "later"}
CSS = (Path(__file__).parent / "templates" / "report.css").read_text()


def _e(v) -> str:
    return escape(str(v), quote=True)


def finding(i: dict, who_label: dict[str, str], source_note: str) -> str:
    sev = i.get("severity", "low")
    lawyer = "⚖️ " if i.get("who") == "lawyer" else ""
    where = ", ".join(i.get("files") or [])
    rows = [("Issue", _e(i.get("title", ""))), ("Rule", f"<code>{_e(i.get('rule', ''))}</code>")]
    if where:
        rows.append(("Where", f"<code>{_e(where)}</code>"))
    if i.get("fix"):
        rows.append(("Fix", f"<code>{_e(i['fix'])}</code>"))
    if i.get("sources"):
        rows.append(("Based on", _e(", ".join(i["sources"])) + f" ({_e(source_note)})"))
    rows.append(("ID", f"<code>{_e(i.get('fingerprint', ''))}</code>"))
    grid = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    who = _e(who_label.get(i.get("who", ""), ""))
    first_file = f" · <code>{_e(i['files'][0])}</code>" if i.get("files") else ""
    return (f'<div class="f"><div class="t"><span class="pill {PILL_CLASS.get(sev, "later")}">{ACTION_LABEL.get(sev, sev)}</span>'
            f'{lawyer}{_e(i.get("plain") or i.get("title", ""))}</div>'
            f'<div class="who">{who}{first_file}</div>'
            f'<details><summary>Technical details</summary><dl class="grid">{grid}</dl></details></div>')


def render(*, title: str, meta: list[str], note: str, items: list[dict], groups: dict[str, str],
           who_label: dict[str, str], footer: str, source_note: str = "see references/sources.md",
           before_findings: str = "") -> str:
    counts = {k: sum(1 for i in items if PILL_CLASS.get(i.get("severity", "low")) == k) for k in ("now", "soon", "later")}
    pills = "".join(f'<span class="pill {k}">{n} {ACTION_LABEL[{"now": "high", "soon": "medium", "later": "low"}[k]].lower()}</span>'
                    for k, n in counts.items() if n) or '<span class="pill okpill">Nothing found</span>'
    body = []
    for g, gtitle in groups.items():
        rows = [i for i in items if i.get("group") == g]
        if rows:
            body.append(f'<h2>{_e(gtitle)} <span class="n">{len(rows)}</span></h2>'
                        f'<section class="card">{"".join(finding(i, who_label, source_note) for i in rows)}</section>')
    meta_html = "".join(f'<div class="meta">{m}</div>' for m in meta)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<style>
{CSS}
</style>
</head>
<body>
<main>
<header>
  <h1>{_e(title)}</h1>
  {meta_html}
  <div class="counts">{pills}</div>
</header>
<div class="note">{_e(note)}</div>
{before_findings}
{"".join(body)}
<footer>{_e(footer)}</footer>
</main>
</body>
</html>
"""
