"""Collect → evaluate pipeline, shared by `scan` and `verify`.

verify re-runs the code scan (cheap) and the live scan only for the pages the
selected findings touch, then reports which of those findings are gone.
"""

from __future__ import annotations

from pathlib import Path

from findable import gsc_csv
from findable.detect import App
from findable.rules import Finding, evaluate
from findable.scan_code import scan_code
from findable.scan_live import scan_live
from findable.suggest import suggestions

LIVE_SOURCES = {"live", "code+live"}


def collect(root: Path, app: App, url: str | None, max_pages: int = 50,
            only_paths: list[str] | None = None) -> dict:
    code = scan_code(app, root)
    live = None
    if url:
        code_paths = [r.path for r in app.routes if not r.dynamic]
        live = scan_live(url, code_paths, max_pages=max_pages, only_paths=only_paths)
    gsc = gsc_csv.load(root / ".findable" / "inputs")
    findings: list[Finding] = evaluate(code, live, gsc)
    findings = suggestions(code["site"], live, url, gsc, app.dev_command) + findings
    live_ok = bool(live) and live["site"].get("reachable", False)
    pages = set(code["pages"]) | set((live or {}).get("pages", {}))
    return {"code": code, "live": live, "gsc": gsc, "findings": findings, "live_ok": live_ok, "pages": len(pages)}


def fixable_scope(store: dict, app_root: str, live_ok: bool, gsc: bool, only_paths: list[str] | None = None) -> set[str]:
    """Fingerprints this run is allowed to mark as fixed (only what it actually re-checked)."""
    scope = set()
    for fp, rec in store.items():
        if rec.get("app", app_root) != app_root:
            continue
        src = rec.get("source", "code")
        if src in LIVE_SOURCES and not live_ok:
            continue
        if src == "gsc" and not gsc:
            continue
        if only_paths is not None and rec.get("url") not in set(only_paths) | {"site"}:
            continue
        scope.add(fp)
    return scope


def verify_targets(store: dict, fingerprints: list[str] | None) -> list[str]:
    if fingerprints:
        return [fp for fp in fingerprints if fp in store]
    return [fp for fp, r in store.items() if r.get("status") in ("new", "open", "regressed") and r.get("who") != "user"]
