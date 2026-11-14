"""Optional Search Console export reader (no API, no sign-in: the user downloads the files).

Two kinds of export are understood. Drop zips or CSVs into `.findable/inputs/`:

- Performance (Performance → Export): Queries.csv / Pages.csv with Impressions and Position.
- Page indexing (Indexing → Pages): a table of reasons ("Reason", "Pages"), and, when you open
  one reason and export it, the list of affected URLs ("URL", "Last crawled"). The reason for a
  URL list comes from a reason column, the export's metadata file, or the zip/file name.

Google doesn't document the exact file layouts, so matching is by column names, not file names.
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from urllib.parse import urlparse


MAX_CSV_BYTES = 50_000_000


def _num(v: str) -> float:
    v = (v or "").strip().replace(",", "").replace("%", "")
    try:
        return float(v)
    except ValueError:
        return 0.0


def _rows(text: str) -> tuple[list[str], list[dict]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    return [h.strip() for h in (reader.fieldnames or [])], list(reader)


def _classify(headers: list[str]) -> str | None:
    low = [h.lower() for h in headers]
    if not {"impressions", "position"} <= set(low):
        return None
    first = low[0]
    if "page" in first:
        return "pages"
    if "quer" in first:
        return "queries"
    return None


def _index_kind(headers: list[str]) -> str | None:
    low = {h.lower() for h in headers}
    if "reason" in low and "pages" in low:
        return "reasons"
    if ("url" in low or "page" in low) and "impressions" not in low:
        return "urls"
    return None


def _metadata_issue(text: str) -> str | None:
    """Exports of one reason ship a small metadata CSV; find the issue/reason name in it."""
    for row in csv.reader(io.StringIO(text.lstrip("\ufeff"))):
        if len(row) >= 2 and row[0].strip().lower() in ("issue", "reason", "status"):
            return row[1].strip() or None
    return None


def _path(u: str) -> str:
    return urlparse(u.strip()).path.rstrip("/") or "/"


def load(inputs_dir: Path) -> dict | None:
    """Return {"pages", "queries", "index": {"reasons", "urls"}, "files", "skipped"} or None if no export found."""
    if not inputs_dir.is_dir():
        return None
    texts: list[tuple[str, str]] = []
    skipped: list[str] = []
    for f in sorted(inputs_dir.iterdir()):
        if f.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(f) as z:
                    for info in z.infolist():
                        if info.filename.lower().endswith(".csv") and info.file_size <= MAX_CSV_BYTES:
                            texts.append((f"{f.name}:{info.filename}", z.read(info).decode("utf-8", errors="ignore")))
            except (zipfile.BadZipFile, OSError):
                skipped.append(f.name)      # broken or half-downloaded export: skip it, don't crash
                continue
        elif f.suffix.lower() == ".csv" and f.stat().st_size <= MAX_CSV_BYTES:
            texts.append((f.name, f.read_text(encoding="utf-8", errors="ignore")))
    out: dict = {"pages": [], "queries": [], "index": {"reasons": [], "urls": []}, "files": [], "skipped": skipped}
    # issue names from metadata files, per zip (or per folder for loose CSVs)
    issue_for: dict[str, str] = {}
    for name, text in texts:
        issue = _metadata_issue(text) if "metadata" in name.lower() else None
        if issue:
            issue_for[name.split(":")[0]] = issue
    seen_urls: set[tuple[str, str]] = set()
    for name, text in texts:
        headers, rows = _rows(text)
        kind = _classify(headers)
        ikind = None if kind else _index_kind(headers)
        if ikind == "reasons":
            out["files"].append(name)
            h = {x.lower(): x for x in headers}
            for r in rows:
                reason = (r.get(h["reason"]) or "").strip()
                if reason:
                    out["index"]["reasons"].append({
                        "reason": reason, "pages": int(_num(r.get(h["pages"], ""))),
                        "source": (r.get(h.get("source", ""), "") or "").strip(),
                        "validation": (r.get(h.get("validation", ""), "") or "").strip()})
            continue
        if ikind == "urls":
            h = {x.lower(): x for x in headers}
            col = h.get("url") or h.get("page")
            rcol = h.get("reason") or h.get("status") or h.get("issue")
            default = issue_for.get(name.split(":")[0]) or Path(name.split(":")[0]).stem.replace("_", " ")
            added = False
            for r in rows:
                u = (r.get(col) or "").strip()
                if not u.startswith("http"):
                    continue
                reason = ((r.get(rcol) or "").strip() if rcol else "") or default
                if (u, reason) in seen_urls:
                    continue
                seen_urls.add((u, reason))
                out["index"]["urls"].append({"url": u, "path": _path(u), "reason": reason,
                                             "last_crawled": (r.get(h.get("last crawled", ""), "") or "").strip()})
                added = True
            if added:
                out["files"].append(name)
            continue
        if not kind:
            continue
        out["files"].append(name)
        key = headers[0]
        h = {x.lower(): x for x in headers}
        for r in rows:
            item = {
                "key": (r.get(key) or "").strip(),
                "clicks": _num(r.get(h.get("clicks", ""), "")),
                "impressions": _num(r.get(h["impressions"], "")),
                "position": _num(r.get(h["position"], "")),
            }
            if kind == "pages":
                item["path"] = urlparse(item["key"]).path.rstrip("/") or "/"
            out[kind].append(item)
    return out if out["files"] else None
