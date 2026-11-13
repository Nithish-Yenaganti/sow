"""Optional Search Console export reader.

Search Console → Performance → Export → "Download CSV" gives a zip with
Queries.csv and Pages.csv. Drop the zip (or the CSVs) into `.findable/inputs/`.
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


def load(inputs_dir: Path) -> dict | None:
    """Return {"pages": [...], "queries": [...], "files": [...]} or None if no export found."""
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
    out: dict = {"pages": [], "queries": [], "files": [], "skipped": skipped}
    for name, text in texts:
        headers, rows = _rows(text)
        kind = _classify(headers)
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
