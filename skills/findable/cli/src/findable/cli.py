"""findable CLI.

Exit codes: 0 ok · 1 error · 3 needs input (JSON questions printed; agent asks the user, then re-runs).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from findable import __version__, ask, findings, report
from findable.detect import app_at, detect
from findable.verify import collect, fixable_scope, verify_targets

app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help="Can Google and AI engines find, read and cite your site? Scan, fix, verify.")

EXIT_NEEDS_INPUT = 3


def _root(path: str) -> Path:
    return Path(path).resolve()


def _print_json(obj) -> None:
    typer.echo(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(__version__)


@app.command()
def scan(
    app_: Optional[str] = typer.Option(None, "--app", help="App folder to scan (monorepos)"),
    url: Optional[str] = typer.Option(None, "--url", help="URL to scan live, or 'none' for code only"),
    max_pages: int = typer.Option(50, help="Live page budget"),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output for the agent"),
    path: str = typer.Option(".", help="Project root"),
) -> None:
    """Detect → (ask) → scan code + live site → findings → report."""
    root = _root(path)
    apps = detect(root)
    res = ask.resolve(root, apps, app_, url)
    if res.questions:
        _print_json({"status": "needs_input", "questions": [q.to_dict() for q in res.questions], "notes": res.notes,
                     "detected": [a.to_dict() | {"routes": len(a.routes)} for a in apps]})
        raise typer.Exit(EXIT_NEEDS_INPUT)
    if res.app is None:
        _print_json({"status": "error", "notes": res.notes}) if as_json else typer.echo("\n".join(res.notes))
        raise typer.Exit(1)
    ask.remember(root, res.app, res.url)

    data = collect(root, res.app, res.url, max_pages=max_pages)
    store = findings.load(root)
    previous = bool(store)
    scope = fixable_scope(store, res.app.root, data["live_ok"], bool(data["gsc"]))
    current = data["findings"]
    delta = findings.apply_run(store, current, scope)
    for f in current:
        store[f.fingerprint]["app"] = res.app.root
    findings.save(root, store)

    name = res.app.name if res.app.root != "." or res.app.name not in ("", ".") else root.name
    run = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "app": res.app.root, "name": name,
           "framework": res.app.framework, "url": res.url, "live_ok": data["live_ok"], "gsc": bool(data["gsc"]),
           "pages": data["pages"], "previous_run": previous, "notes": res.notes, "version": __version__}
    (root / ".findable" / "last-run.json").write_text(json.dumps(
        run | {"live_site": (data["live"] or {}).get("site"), "code_site": data["code"]["site"]},
        indent=2, default=str) + "\n")

    items = [r for r in findings.active(store) if r.get("app", res.app.root) == res.app.root]
    dismissed = [dict(r, fingerprint=fp) for fp, r in store.items() if r["status"] == "dismissed"]
    rp = report.write_html(root, report.html(run, items, delta, dismissed))
    if as_json:
        _print_json({"status": "ok", "run": run, "delta": delta, "do_first": report.do_first(items),
                     "findings": items, "report": str(rp)})
    else:
        for n in res.notes:
            typer.echo(f"note: {n}")
        typer.echo(report.terminal(run, items, delta, str(rp.relative_to(root))))


@app.command(name="report")
def report_cmd(
    as_json: bool = typer.Option(False, "--json"),
    path: str = typer.Option("."),
) -> None:
    """Show the latest results without re-scanning."""
    root = _root(path)
    try:
        run = json.loads((root / ".findable" / "last-run.json").read_text())
    except OSError:
        typer.echo("No scan yet. Run: findable scan")
        raise typer.Exit(1)
    store = findings.load(root)
    items = [r for r in findings.active(store) if r.get("app", run["app"]) == run["app"]]
    empty = {"new": [], "fixed": [], "regressed": [], "open": []}
    if as_json:
        _print_json({"status": "ok", "run": run, "findings": items, "do_first": report.do_first(items)})
    else:
        typer.echo(report.terminal(run | {"previous_run": False}, items, empty, ".findable/report.html"))


@app.command()
def verify(
    ids: Optional[str] = typer.Option(None, help="Comma-separated fingerprints (default: all open agent-fixable)"),
    url: Optional[str] = typer.Option(None, "--url", help="Override URL (e.g. local dev server)"),
    as_json: bool = typer.Option(False, "--json"),
    path: str = typer.Option("."),
) -> None:
    """Re-check only what the selected findings touch; mark fixed ones."""
    root = _root(path)
    cfg = ask.load_config(root)
    apps = {a.root: a for a in detect(root)}
    app_obj = apps.get(cfg.get("app", "")) or (app_at(root, cfg["app"]) if cfg.get("app") else None)
    if app_obj is None:
        typer.echo("No previous scan config. Run: findable scan")
        raise typer.Exit(1)
    store = findings.load(root)
    targets = verify_targets(store, [i.strip() for i in ids.split(",")] if ids else None)
    if not targets:
        _print_json({"status": "ok", "checked": [], "note": "nothing to verify"}) if as_json else typer.echo("Nothing to verify.")
        return
    paths = sorted({store[fp]["url"] for fp in targets if store[fp]["url"] != "site"})
    live_url = url if url is not None else cfg.get("url")
    live_url = None if live_url in (None, "none", "") else live_url
    data = collect(root, app_obj, live_url, only_paths=paths or ["/"])
    scope = fixable_scope(store, app_obj.root, data["live_ok"], bool(data["gsc"]), only_paths=paths) & set(targets)
    now = {f.fingerprint for f in data["findings"]}
    findings.apply_run(store, [f for f in data["findings"] if f.fingerprint in targets], scope)
    findings.save(root, store)
    results = []
    for fp in targets:
        if fp not in scope:
            state = "not re-checked (needs live URL or Search Console CSV)"
        elif fp in now:
            state = "still failing"
        else:
            state = "fixed"
        results.append({"fingerprint": fp, "title": store[fp]["title"], "result": state})
    if as_json:
        _print_json({"status": "ok", "checked": results})
    else:
        for r in results:
            mark = {"fixed": "✓", "still failing": "✗"}.get(r["result"], "·")
            typer.echo(f"{mark} {r['title']} — {r['result']}")
    if any(r["result"] == "still failing" for r in results):
        raise typer.Exit(2)


@app.command()
def dismiss(
    fingerprint: str = typer.Argument(..., help="e.g. seo.canonical|/pricing"),
    reason: str = typer.Option(..., "--reason", help="Why (kept in history)"),
    path: str = typer.Option("."),
) -> None:
    """Dismiss a finding so it isn't raised again."""
    root = _root(path)
    store = findings.load(root)
    if not findings.dismiss(store, fingerprint, reason):
        typer.echo(f"Unknown finding: {fingerprint}")
        raise typer.Exit(1)
    findings.save(root, store)
    typer.echo(f"✓ dismissed {fingerprint}")
