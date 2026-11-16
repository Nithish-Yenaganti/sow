"""Inline suppressions: a reviewable comment in the code, like `# nosemgrep`, `# nosec` or `# zizmor: ignore[...]`.

    db.query(sql)  // guarded-ignore[inject.sql] built from constants only
    # guarded-ignore[server.ssrf, server.redirect]   (on the line above also works)

Unlike `guarded dismiss` (stored in the git-ignored .guarded/ folder), the comment is committed, so the whole team
and CI see the same result, and the reason sits next to the code. A rule id is required: a bare `guarded-ignore`
matches nothing, so one comment can't silence checks nobody looked at.

Never honoured for the aitools.* rules. Those flag files that may have been planted to steer AI tools, and whoever
planted the file could plant the comment too.
"""

import re
from pathlib import Path

from guarded.project import Project
from guarded.rules import Finding

TOKEN = re.compile(r"guarded-ignore\[([\w.,\s]+)\]")
NEVER = ("aitools.",)
_PLACES = re.compile(r", in \d+ places$")
_LOC = re.compile(r"^(?P<path>.+):(?P<line>\d+)$")


def _rules_on(line: str) -> set[str]:
    return {r.strip() for m in TOKEN.finditer(line) for r in m.group(1).split(",") if r.strip()}


def _suppressed(pj: Project, rule: str, loc: str) -> bool:
    m = _LOC.match(loc)
    if not m:
        return False
    lines = pj.text(Path(m["path"])).split("\n")
    n = int(m["line"])
    near = lines[max(0, n - 2): n]                     # the reported line and the one above it
    return any(rule in _rules_on(ln) for ln in near)


def apply(pj: Project, findings: list[Finding]) -> tuple[list[Finding], list[dict]]:
    """Drop the locations a comment suppresses; drop a finding once all of its locations are suppressed.
    Returns (kept findings, what was suppressed) so the report can say how much was silenced, and where."""
    kept, silenced = [], []
    for f in findings:
        if f.rule.startswith(NEVER) or not f.files:
            kept.append(f)
            continue
        hit = [loc for loc in f.files if _suppressed(pj, f.rule, loc)]
        if not hit:
            kept.append(f)
            continue
        f.files = [loc for loc in f.files if loc not in hit]
        silenced += [{"fingerprint": f.fingerprint, "rule": f.rule, "where": loc, "whole_finding": not f.files}
                     for loc in hit]
        if f.files:
            f.detail = _PLACES.sub(f", in {len(f.files)} places" if len(f.files) > 1 else "", f.detail)
            kept.append(f)
    return kept, silenced
