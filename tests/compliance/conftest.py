import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SKILL = Path(__file__).parents[2] / "skills" / "compliance"


@pytest.fixture
def project(tmp_path):
    def make(name: str) -> Path:
        dest = tmp_path / name
        shutil.copytree(FIXTURES / name, dest)
        return dest
    return make
