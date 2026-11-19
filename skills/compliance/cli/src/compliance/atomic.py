"""Crash-safe writes for the state folder: write a temp file next to the target, then rename over it.

A rename is atomic on POSIX and Windows, so an interrupted run leaves the old file, never half of a new one
(a half-written findings.json would otherwise load as "no findings" and silently drop the user's dismissals).
"""

import json
import os
import tempfile
from pathlib import Path


STATE_NAME = ".compliance"


def state_dir(root: Path) -> Path:
    """Reject links before reading or writing state, including nested files/folders."""
    return validate_state(Path(root).resolve() / STATE_NAME)


def validate_state(state: Path) -> Path:
    if state.is_symlink():
        raise ValueError(f"Refusing symlink in {STATE_NAME}: {state}")
    if state.exists():
        for folder, dirs, files in os.walk(state, followlinks=False):
            for name in dirs + files:
                entry = Path(folder) / name
                if entry.is_symlink():
                    raise ValueError(f"Refusing symlink in {STATE_NAME}: {entry}")
    return state


def write_text(path: Path, text: str) -> Path:
    for parent in (path, *path.parents):
        if parent.name == STATE_NAME:
            validate_state(parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path


def write_json(path: Path, data, **kw) -> Path:
    return write_text(path, json.dumps(data, indent=2, ensure_ascii=False, **kw) + "\n")
