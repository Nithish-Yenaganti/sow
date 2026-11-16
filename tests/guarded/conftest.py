import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def make(tmp_path):
    """Write a project from {relative path: text}. Fixtures live here, not as files in the repo, so the repo never holds
    fake secrets or risky AI-tool configs that other scanners (or AI tools opening this repo) would trip over."""
    def _make(files: dict[str, str], git: bool = False) -> Path:
        root = tmp_path / "proj"
        for rel, text in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        if git:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        return root
    return _make
