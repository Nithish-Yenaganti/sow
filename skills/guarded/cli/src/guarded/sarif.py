"""SARIF 2.1.0 output, the format GitHub code scanning (and most CI security dashboards) read.

Upload with github/codeql-action/upload-sarif. Field choices follow GitHub's SARIF support page:
- every rule carries `properties.security-severity` (0.1–10), which GitHub maps to critical/high/medium/low;
- `partialFingerprints` carries our own stable fingerprint, so alerts keep their identity when lines move;
- a finding with no file (for example "no Content-Security-Policy") is anchored to a real project file, because
  code scanning drops results that have no location. URIs are relative to the repo root, as GitHub expects.
"""

import hashlib
import re

from guarded import __version__
from guarded.rules import GROUPS, RULES

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
LEVEL = {"high": "error", "medium": "warning", "low": "note"}
SCORE = {"high": "8.0", "medium": "5.5", "low": "3.0"}
INFO_URI = "https://github.com/Nithish-Yenaganti/sow/tree/main/skills/guarded"
_LOC = re.compile(r"^(?P<path>.+?)(?::(?P<line>\d+))?$")


def _location(loc: str) -> dict:
    m = _LOC.match(loc)
    phys: dict = {"artifactLocation": {"uri": m["path"]}}
    if m["line"]:
        phys["region"] = {"startLine": int(m["line"])}
    return {"physicalLocation": phys}


def build(items: list[dict], anchor: str) -> dict:
    """items: active findings as the store returns them (dicts with rule, severity, plain, files, fingerprint).
    anchor: a real project file (package.json, say) for findings that have no file of their own."""
    used = sorted({i["rule"] for i in items})
    rules = [{
        "id": r.id,
        "name": "".join(w.capitalize() for w in re.split(r"[._]", r.id)),
        "shortDescription": {"text": r.title},
        "fullDescription": {"text": GROUPS[r.group]},
        "helpUri": f"{INFO_URI}/{r.fix.split('#')[0]}",
        "defaultConfiguration": {"level": LEVEL[r.severity]},
        "properties": {"security-severity": SCORE[r.severity], "tags": ["security", r.group, *r.sources]},
    } for r in (RULES[u] for u in used)]
    index = {rid: n for n, rid in enumerate(used)}
    results = []
    for i in items:
        locs = [_location(loc) for loc in i.get("files") or []] or [_location(anchor)]
        results.append({
            "ruleId": i["rule"],
            "ruleIndex": index[i["rule"]],
            "level": LEVEL[i["severity"]],
            "message": {"text": i["plain"]},
            "locations": locs[:1],
            **({"relatedLocations": [dict(loc, id=n) for n, loc in enumerate(locs[1:10], 1)]} if len(locs) > 1 else {}),
            "partialFingerprints": {"guarded/v1": hashlib.sha256(i["fingerprint"].encode()).hexdigest()[:32]},
            "properties": {"who": i["who"], "fingerprint": i["fingerprint"]},
        })
    return {
        "$schema": SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "guarded", "version": __version__, "informationUri": INFO_URI, "rules": rules}},
            "results": results,
        }],
    }
