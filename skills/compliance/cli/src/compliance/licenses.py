"""Read dependency licenses from npm lockfiles / node_modules and classify them."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

PERMISSIVE = {
    "MIT", "MIT-0", "ISC", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "0BSD", "APACHE-2.0", "UNLICENSE", "CC0-1.0", "ZLIB",
    "BLUEOAK-1.0.0", "PYTHON-2.0", "PSF-2.0", "BSL-1.0", "WTFPL", "CC-BY-3.0", "CC-BY-4.0", "OFL-1.1", "X11",
    "ARTISTIC-2.0", "UPL-1.0", "NCSA",
}
WEAK = ("LGPL", "MPL", "EPL", "CDDL", "MS-RL")
STRONG = ("GPL", "EUPL", "OSL", "CC-BY-SA")
NETWORK = ("AGPL", "SSPL")
RESTRICTED = ("BUSL", "BSL-1.1", "ELASTIC", "COMMONS-CLAUSE", "POLYFORM", "CC-BY-NC", "CC-BY-ND")
RANK = {"permissive": 0, "weak_copyleft": 1, "unknown": 2, "strong_copyleft": 3, "restricted": 4, "network_copyleft": 5}


@dataclass
class Dep:
    name: str
    version: str
    license: str
    dev: bool
    kind: str


def classify_one(lic: str) -> str:
    u = lic.strip().strip("()").upper().replace(" ", "-")
    if not u or u in ("UNLICENSED", "UNKNOWN", "NONE", "NOASSERTION") or u.startswith("SEE-LICENSE"):
        return "unknown"
    u = re.sub(r"-ONLY$|-OR-LATER$|\+$", "", u)
    if u in PERMISSIVE:
        return "permissive"
    if any(u.startswith(p) for p in NETWORK):
        return "network_copyleft"
    if any(u.startswith(p) for p in RESTRICTED) or u == "BSL-1.1":
        return "restricted"
    if any(u.startswith(p) for p in WEAK):
        return "weak_copyleft"
    if any(u.startswith(p) for p in STRONG):
        return "strong_copyleft"
    return "unknown"


def classify(expr: str) -> str:
    """SPDX expression -> class. OR picks the friendliest option, AND the strictest."""
    e = (expr or "").strip()
    if not e:
        return "unknown"
    if re.search(r"\s+OR\s+", e, re.I):
        return min((classify(p) for p in re.split(r"\s+OR\s+", e.strip("()"), flags=re.I)), key=RANK.get)
    if re.search(r"\s+AND\s+", e, re.I):
        return max((classify(p) for p in re.split(r"\s+AND\s+", e.strip("()"), flags=re.I)), key=RANK.get)
    return classify_one(e)


def _lic_field(meta: dict) -> str:
    lic = meta.get("license", "")
    if isinstance(lic, dict):
        lic = lic.get("type", "")
    if not lic and isinstance(meta.get("licenses"), list):
        lic = " OR ".join(x.get("type", "") if isinstance(x, dict) else str(x) for x in meta["licenses"])
    return str(lic or "")


def read_npm(pkg_dir: Path) -> tuple[list[Dep], str | None]:
    """(deps, problem). Prefers package-lock.json (has licenses), else node_modules."""
    try:
        pkg = json.loads((pkg_dir / "package.json").read_text())
    except (OSError, ValueError):
        return [], None
    prod = set(pkg.get("dependencies", {}) or {}) | set(pkg.get("optionalDependencies", {}) or {})
    dev = set(pkg.get("devDependencies", {}) or {})
    if not prod and not dev:
        return [], None
    lock = pkg_dir / "package-lock.json"
    out: list[Dep] = []
    if lock.exists():
        try:
            data = json.loads(lock.read_text())
        except (OSError, ValueError):
            data = {}
        for path, meta in (data.get("packages") or {}).items():
            if not path.startswith("node_modules/"):
                continue
            name = path.split("node_modules/")[-1]
            lic = _lic_field(meta)
            out.append(Dep(name, str(meta.get("version", "")), lic, bool(meta.get("dev")), classify(lic)))
        if out:
            return out, None
    nm = pkg_dir / "node_modules"
    if nm.is_dir():
        for name in sorted(prod | dev):
            try:
                meta = json.loads((nm / name / "package.json").read_text())
            except (OSError, ValueError):
                continue
            lic = _lic_field(meta)
            out.append(Dep(name, str(meta.get("version", "")), lic, name not in prod, classify(lic)))
        if out:
            return out, None
    return [], "no package-lock.json or node_modules"


def read_python_names(root: Path) -> list[str]:
    names: list[str] = []
    for req in list(root.glob("requirements*.txt")):
        try:
            for line in req.read_text().splitlines():
                line = line.split("#")[0].strip()
                if line and not line.startswith("-"):
                    names.append(re.split(r"[<>=!~\[; ]", line)[0].lower())
        except OSError:
            pass
    pp = root / "pyproject.toml"
    if pp.exists():
        try:
            text = pp.read_text()
        except OSError:
            text = ""
        m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.S | re.M)
        if m:
            names += [re.split(r"[<>=!~\[; ]", s)[0].lower() for s in re.findall(r"[\"']([^\"']+)[\"']", m.group(1))]
    return [n for n in names if n]


def notices_markdown(deps: list[Dep]) -> str:
    rows = sorted({(d.name, d.version, d.license or "UNKNOWN") for d in deps if not d.dev})
    lines = ["# Third-party notices", "",
             "This project uses the open-source packages below. Each one's license and copyright notice is in its",
             "package folder (`node_modules/<name>/LICENSE`) and applies to that package.", "",
             "| Package | Version | License |", "|---|---|---|"]
    lines += [f"| {n} | {v} | {lic} |" for n, v, lic in rows]
    return "\n".join(lines) + "\n"
