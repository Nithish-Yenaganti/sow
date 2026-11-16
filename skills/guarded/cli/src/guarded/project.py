"""Reading the project: files, text, dependencies, and small parsing helpers. Reads only."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = {"node_modules", ".git", ".next", ".nuxt", ".svelte-kit", ".astro", "dist", "build", "out", ".venv", "venv",
             "vendor", "coverage", ".guarded", ".compliance", ".findable", ".turbo", ".vercel", ".output", "__pycache__",
             ".cache", "target", "Pods", ".expo", "site-packages", ".pnpm-store", "bower_components", ".angular"}
CODE_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro", ".py", ".php", ".rb", ".go"}
JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro"}
UI_EXT = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro"}
TEXT_EXT = CODE_EXT | {".html", ".htm", ".md", ".mdx", ".mdc", ".json", ".jsonc", ".yml", ".yaml", ".toml", ".txt", ".sql",
                       ".sh", ".rules", ".env", ".j2", ".jinja", ".ejs", ".hbs", ".erb"}
MAX_BYTES = 600_000
TEST_RE = re.compile(r"(^|/)(tests?|__tests__|spec|specs|e2e|cypress|fixtures|__mocks__|mocks?|stories|examples?|"
                     r"test[-_]?data|testdata|demo|samples?|docs?)(/|$)|\.(test|spec|stories|e2e)\.", re.I)
MINIFIED_RE = re.compile(r"\.min\.(js|css)$|[-.]bundle\.js$|\.chunk\.js$", re.I)


@dataclass
class Dep:
    name: str
    ecosystem: str            # "npm" | "PyPI"
    version: str | None       # exact installed/pinned version when known
    spec: str = ""            # what the manifest asked for
    dev: bool = False
    source: str = ""          # file it came from


@dataclass
class Project:
    root: Path
    files: list[Path] = field(default_factory=list)
    _text: dict = field(default_factory=dict)
    deps: list[Dep] = field(default_factory=list)
    local_names: set = field(default_factory=set)   # workspace package names (never looked up)

    def text(self, rel: Path) -> str:
        if rel not in self._text:
            p = self.root / rel
            try:
                self._text[rel] = p.read_text(errors="ignore") if p.stat().st_size <= MAX_BYTES else ""
            except OSError:
                self._text[rel] = ""
        return self._text[rel]

    def code(self, exts: set[str] = CODE_EXT, tests: bool = False) -> list[Path]:
        return [f for f in self.files if f.suffix.lower() in exts and not MINIFIED_RE.search(f.name)
                and (tests or not TEST_RE.search(f.as_posix()))]

    def named(self, *globs: str) -> list[Path]:
        return [f for f in self.files if any(f.match(g) or f.as_posix() == g for g in globs)]

    @property
    def npm(self) -> set[str]:
        return {d.name for d in self.deps if d.ecosystem == "npm"}

    @property
    def py(self) -> set[str]:
        return {d.name for d in self.deps if d.ecosystem == "PyPI"}

    def has_pkg(self, *names: str) -> bool:
        have = self.npm | self.py
        return any(n in have for n in names)


def load(root: Path) -> Project:
    pj = Project(root)
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.is_symlink():
                continue
            if e.is_dir():
                if e.name not in SKIP_DIRS:
                    stack.append(e)
            elif e.is_file():
                pj.files.append(e.relative_to(root))
    pj.files.sort()
    _read_deps(pj)
    return pj


# --- dependencies -------------------------------------------------------------------------------------------------
_EXACT = re.compile(r"^v?(\d+\.\d+\.\d+(?:[-+][\w.]+)?)$")
_NON_REGISTRY = ("workspace:", "file:", "link:", "git", "github:", "http:", "https:", "npm:", "portal:", "patch:", "catalog:")


def norm_py(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _read_deps(pj: Project) -> None:
    seen: dict[tuple[str, str], Dep] = {}

    def add(d: Dep) -> None:
        k = (d.ecosystem, d.name)
        if k in seen:
            old = seen[k]
            old.version = old.version or d.version
            old.dev = old.dev and d.dev
        else:
            seen[k] = d

    for f in pj.files:
        if TEST_RE.search(f.parent.as_posix() + "/") and f.parent != Path("."):
            continue
        n = f.name
        if n == "package.json":
            try:
                pkg = json.loads(pj.text(f))
            except ValueError:
                continue
            if isinstance(pkg.get("name"), str):
                pj.local_names.add(pkg["name"])
            lock = _npm_lock(pj, f.parent)  # relative folder
            for section, dev in (("dependencies", False), ("devDependencies", True), ("optionalDependencies", False)):
                for name, spec in (pkg.get(section) or {}).items():
                    if not isinstance(spec, str) or spec.startswith(_NON_REGISTRY):
                        continue
                    m = _EXACT.match(spec.strip())
                    ver = lock.get((name, spec)) or lock.get(name) or (m.group(1) if m else None)
                    add(Dep(name, "npm", ver, spec, dev, f.as_posix()))
        elif re.fullmatch(r"requirements[\w.-]*\.txt", n):
            for line in pj.text(f).splitlines():
                line = line.split("#", 1)[0].strip()
                m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(==\s*([\w.+-]+))?", line)
                if not m or line.startswith("-"):
                    continue
                add(Dep(norm_py(m.group(1)), "PyPI", m.group(4), line, "dev" in n, f.as_posix()))
        elif n == "pyproject.toml":
            for name, ver, spec, dev in _pyproject(pj.text(f)):
                add(Dep(name, "PyPI", ver, spec, dev, f.as_posix()))
    # Lock files fill in exact versions for Python.
    for f in pj.files:
        if f.name in ("uv.lock", "poetry.lock"):
            for m in re.finditer(r'\[\[package\]\]\s*\nname\s*=\s*"([^"]+)"\s*\nversion\s*=\s*"([^"]+)"', pj.text(f)):
                d = seen.get(("PyPI", norm_py(m.group(1))))
                if d and not d.version:
                    d.version = m.group(2)
        elif f.name == "Pipfile.lock":
            try:
                lock = json.loads(pj.text(f))
            except ValueError:
                continue
            for section in ("default", "develop"):
                for name, info in (lock.get(section) or {}).items():
                    v = str((info or {}).get("version", "")).lstrip("=")
                    add(Dep(norm_py(name), "PyPI", v or None, "", section == "develop", f.as_posix()))
    pj.deps = sorted(seen.values(), key=lambda d: (d.ecosystem, d.name))


def _npm_lock(pj: Project, folder: Path) -> dict:
    """Exact versions of a package.json's direct dependencies, from whichever lock file sits next to it.
    Returns {name: version} and, for yarn, {(name, spec): version}."""
    out: dict = {}
    rel = (folder.relative_to(pj.root) if folder.is_absolute() else folder)
    files = set(pj.files)
    if rel / "package-lock.json" in files:
        try:
            lock = json.loads(pj.text(rel / "package-lock.json"))
        except ValueError:
            lock = {}
        for key, info in (lock.get("packages") or {}).items():
            if key.startswith("node_modules/") and key.count("node_modules/") == 1 and isinstance(info, dict):
                if info.get("version") and not info.get("link"):
                    out[key.removeprefix("node_modules/")] = info["version"]
        for name, info in (lock.get("dependencies") or {}).items():   # lockfile v1
            if isinstance(info, dict) and info.get("version"):
                out.setdefault(name, info["version"])
    if rel / "pnpm-lock.yaml" in files:
        t = pj.text(rel / "pnpm-lock.yaml")
        for m in re.finditer(r"^\s+('?)(@?[^\s:']+)\1:\n\s+specifier: [^\n]+\n\s+version: ([0-9][^\s(]*)", t, re.M):
            out.setdefault(m.group(2), m.group(3))
    if rel / "yarn.lock" in files:
        t = pj.text(rel / "yarn.lock")
        for m in re.finditer(r'^("?[^\s#][^\n]*?):\n(?:[ \t]+[^\n]*\n)*?[ \t]+version:? "?([^"\s]+)"?', t, re.M):
            for desc in m.group(1).split(","):
                desc = desc.strip().strip('"')
                at = desc.rfind("@")
                if at > 0:
                    name, spec = desc[:at], desc[at + 1:].removeprefix("npm:")
                    out[(name, spec)] = m.group(2)
                    out.setdefault(name, m.group(2))
    return out


def _pyproject(text: str):
    """[project].dependencies and optional/dev groups, read without a TOML parser (Python 3.10 has none)."""
    for m in re.finditer(r"^(dependencies|dev|test|docs|[\w-]+)\s*=\s*\[(.*?)\]", text, re.M | re.S):
        header = ("\n" + text[:m.start()]).rsplit("\n[", 1)[-1].split("]", 1)[0]
        if not (header in ("project", "project.optional-dependencies", "dependency-groups")
                or header.startswith("tool.uv")):
            continue
        dev = header != "project"
        for s in re.findall(r"[\"']([^\"']+)[\"']", m.group(2)):
            mm = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(==\s*([\w.+-]+))?", s.strip())
            if mm:
                yield norm_py(mm.group(1)), mm.group(4), s, dev


# --- git -----------------------------------------------------------------------------------------------------------
def git_tracked(root: Path) -> list[str] | None:
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode:
        return None
    return [x for x in r.stdout.split("\0") if x]


# --- text helpers --------------------------------------------------------------------------------------------------
def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def line_text(text: str, idx: int) -> str:
    s = text.rfind("\n", 0, idx) + 1
    e = text.find("\n", idx)
    return text[s: e if e != -1 else len(text)]


def is_comment(text: str, idx: int) -> bool:
    ln = line_text(text, idx).lstrip()
    return ln.startswith(("//", "#", "*", "/*", "<!--", "--"))


def in_pattern(text: str, idx: int) -> bool:
    """The match sits in a regex pattern (re.compile / RegExp / a raw-string line), e.g. in a scanner's own rules."""
    ln = line_text(text, idx).lstrip()
    return ("re.compile(" in ln or "new RegExp(" in ln or ln.startswith(('r"', "r'", 'rf"', "rf'", 'r"""'))
            or bool(re.match(r"^\(\s*[\"'][\w .()-]+[\"']\s*,\s*re\.compile", ln)))


def call_args(text: str, open_idx: int, limit: int = 4000) -> str:
    """The text between the '(' at open_idx and its matching ')'. Skips over strings and template literals."""
    depth, i, n = 0, open_idx, min(len(text), open_idx + limit)
    quote, tmpl_depth = "", []
    while i < n:
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if quote == "`" and c == "$" and text[i + 1: i + 2] == "{":
                tmpl_depth.append(depth)
                quote = ""
                depth += 1
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "\"'`":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if tmpl_depth and c == "}" and depth == tmpl_depth[-1]:
                tmpl_depth.pop()
                quote = "`"
            elif depth == 0:
                return text[open_idx + 1: i]
        i += 1
    return text[open_idx + 1: n]


def split_args(args: str) -> list[str]:
    out, depth, quote, cur, i = [], 0, "", [], 0
    while i < len(args):
        c = args[i]
        if quote:
            if c == "\\":
                cur.append(args[i: i + 2])
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "\"'`":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return out


_STATIC = re.compile(r"""^\s*(?:r|b|rb|br|u)?(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\$]|\\.|\$(?!\{))*`)\s*$""",
                     re.S)


def is_static(arg: str) -> bool:
    """True for a plain string literal with nothing pasted in (no ${}, f-string, +, % or .format)."""
    a = arg.strip()
    if a.startswith(("f\"", "f'", "rf\"", "fr\"", "rf'", "fr'")):
        return False
    if a.startswith("[") and a.endswith("]"):         # argument lists like ["git", "status"] are safe for exec
        return True
    return bool(_STATIC.match(a))


def interpolates(arg: str) -> bool:
    a = arg.strip()
    return ("${" in a and "`" in a) or bool(re.match(r"^(r?f|fr)[\"']", a)) or bool(re.search(r"[\"'`]\s*\+|\+\s*[\"'`]", a)) \
        or bool(re.search(r"[\"']\s*%\s*[\w(]", a)) or ".format(" in a


def window(text: str, idx: int, before: int = 20, after: int = 2) -> str:
    """The lines around idx (to spot where a variable came from)."""
    lines = text.split("\n")
    ln = line_of(text, idx) - 1
    return "\n".join(lines[max(0, ln - before): ln + after + 1])


def mask(secret: str) -> str:
    return secret[:6] + "…" if len(secret) > 6 else "…"
