"""Finding lifecycle across runs (the only state machine in v1).

    new ──► open ──► fixed ──► (reappears) regressed ──► open
     │        │
     └────────┴──► dismissed   (user gave a reason; never re-raised)

Identity = fingerprint "rule|url", prefixed with the app folder in monorepos
("apps/web::rule|url") so the same issue in two apps stays two findings.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from findable import atomic
from findable.rules import Finding

ACTIVE = {"new", "open", "regressed"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def key(app_root: str, fingerprint: str) -> str:
    return fingerprint if app_root in ("", ".") else f"{app_root}::{fingerprint}"


def store_path(root: Path) -> Path:
    return root / ".findable" / "findings.json"


def load(root: Path) -> dict[str, dict]:
    try:
        return json.loads(store_path(root).read_text())
    except (OSError, ValueError):
        return {}


def save(root: Path, store: dict[str, dict]) -> None:
    atomic.write_json(store_path(root), store)


def _transition(rec: dict, to: str, why: str) -> None:
    if rec.get("status") == to:
        return
    rec.setdefault("history", []).append({"at": _now(), "from": rec.get("status"), "to": to, "why": why})
    rec["status"] = to


def apply_run(store: dict[str, dict], current: list[Finding], scope: set[str] | None = None,
              app: str = ".") -> dict:
    """Update the store with this run's findings for `app`. `scope` limits which store keys
    may be marked fixed (only what this run actually re-checked)."""
    seen = set()
    delta = {"new": [], "fixed": [], "regressed": [], "open": []}
    for f in current:
        fp = key(app, f.fingerprint)
        seen.add(fp)
        data = f.to_dict()
        rec = store.get(fp)
        if rec is None:
            rec = {"status": None, "first_seen": _now(), "history": []}
            store[fp] = rec
            _transition(rec, "new", "first seen")
            delta["new"].append(fp)
        elif rec["status"] == "fixed":
            _transition(rec, "regressed", "seen again after being fixed")
            delta["regressed"].append(fp)
        elif rec["status"] == "new":
            _transition(rec, "open", "still present")
            delta["open"].append(fp)
        elif rec["status"] == "regressed":
            _transition(rec, "open", "still present")
            delta["open"].append(fp)
        elif rec["status"] == "open":
            delta["open"].append(fp)
        rec.update({k: v for k, v in data.items() if k not in ("status", "history", "first_seen")})
        rec["fingerprint"] = fp
        rec["app"] = app
        rec["last_seen"] = _now()
    for fp, rec in store.items():
        if fp in seen or rec["status"] not in ACTIVE or rec.get("app", ".") != app:
            continue
        if scope is not None and fp not in scope:
            continue
        _transition(rec, "fixed", "no longer detected")
        delta["fixed"].append(fp)
    return delta


def dismiss(store: dict[str, dict], fp: str, reason: str) -> bool:
    rec = store.get(fp)
    if rec is None:
        return False
    _transition(rec, "dismissed", reason)
    rec["dismiss_reason"] = reason
    return True


def active(store: dict[str, dict]) -> list[dict]:
    from findable.rules import SEVERITY_RANK
    items = [dict(r, fingerprint=fp) for fp, r in store.items() if r["status"] in ACTIVE]
    return sorted(items, key=lambda r: (0 if r["status"] == "regressed" else 1, SEVERITY_RANK.get(r["severity"], 9),
                                        0 if r.get("who") == "user" else 1, r["url"]))
