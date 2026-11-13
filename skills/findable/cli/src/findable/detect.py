"""Detect apps in a project: framework, routes (route file -> URL path), site URL hints."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

IGNORE_DIRS = {
    "node_modules", ".git", ".next", ".nuxt", ".svelte-kit", ".astro", "dist", "build",
    "out", ".vercel", ".netlify", ".findable", ".venv", "venv", "__pycache__", "coverage",
    ".turbo", ".cache", ".output", "vendor",
}
PAGE_EXTS = (".tsx", ".jsx", ".ts", ".js", ".mdx", ".md")


@dataclass
class Route:
    path: str           # URL path, e.g. "/pricing" or "/blog/[slug]"
    file: str           # file relative to the project root
    dynamic: bool = False


@dataclass
class App:
    root: str                      # app dir relative to project root ("." for single app)
    name: str
    framework: str                 # nextjs-app | nextjs-pages | nextjs | astro | nuxt | sveltekit | remix | gatsby | hugo | jekyll | static | unknown
    routes: list[Route] = field(default_factory=list)
    site_urls: list[str] = field(default_factory=list)   # production URL hints found in code
    dev_port: int | None = None
    dev_command: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _walk(base: Path, max_depth: int = 6):
    stack = [(base, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = sorted(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.is_dir():
                if e.name in IGNORE_DIRS or e.name.startswith(".") and e.name not in {".well-known"}:
                    continue
                if depth < max_depth:
                    stack.append((e, depth + 1))
            else:
                yield e


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _deps(pkg: dict) -> set[str]:
    out: set[str] = set()
    # peerDependencies are left out: a shared UI package that peers on `next` is not a site.
    for k in ("dependencies", "devDependencies"):
        out |= set((pkg.get(k) or {}).keys())
    return out


def _framework(app_dir: Path) -> str:
    pkg = _read_json(app_dir / "package.json")
    deps = _deps(pkg)
    if "next" in deps:
        for base in (app_dir / "app", app_dir / "src" / "app"):
            if base.is_dir():
                return "nextjs-app"
        for base in (app_dir / "pages", app_dir / "src" / "pages"):
            if base.is_dir():
                return "nextjs-pages"
        return "nextjs"
    if "astro" in deps:
        return "astro"
    if "nuxt" in deps or "nuxt3" in deps:
        return "nuxt"
    if "@sveltejs/kit" in deps:
        return "sveltekit"
    if any(d.startswith("@remix-run/") for d in deps) or "@react-router/dev" in deps:
        return "remix"
    if "gatsby" in deps:
        return "gatsby"
    if (app_dir / "hugo.toml").exists() or (app_dir / "config.toml").exists() and (app_dir / "content").is_dir():
        return "hugo"
    if (app_dir / "_config.yml").exists():
        return "jekyll"
    if any(p.suffix == ".html" for p in _walk(app_dir, 3)):
        return "static"
    return "unknown"


def _next_app_routes(app_dir: Path, project_root: Path) -> list[Route]:
    routes: list[Route] = []
    for base in (app_dir / "app", app_dir / "src" / "app"):
        if not base.is_dir():
            continue
        for f in _walk(base, 12):
            if f.stem != "page" or f.suffix not in PAGE_EXTS:
                continue
            parts = []
            dynamic = False
            skip = False
            for seg in f.parent.relative_to(base).parts:
                if seg.startswith("(") and seg.endswith(")"):
                    continue                      # route group
                if seg.startswith("@"):
                    skip = True                   # parallel route slot
                    break
                if seg.startswith("_"):
                    skip = True                   # private folder
                    break
                if seg.startswith("["):
                    dynamic = True
                parts.append(seg)
            if skip:
                continue
            routes.append(Route("/" + "/".join(parts), str(f.relative_to(project_root)), dynamic))
    return routes


def _next_pages_routes(app_dir: Path, project_root: Path) -> list[Route]:
    routes: list[Route] = []
    for base in (app_dir / "pages", app_dir / "src" / "pages"):
        if not base.is_dir():
            continue
        for f in _walk(base, 12):
            if f.suffix not in PAGE_EXTS:
                continue
            rel = f.relative_to(base).with_suffix("")
            if rel.parts and rel.parts[0] == "api":
                continue
            if rel.name.startswith("_"):
                continue
            parts = list(rel.parts)
            if parts and parts[-1] == "index":
                parts = parts[:-1]
            routes.append(Route("/" + "/".join(parts), str(f.relative_to(project_root)),
                                any(p.startswith("[") for p in parts)))
    return routes


def _static_routes(app_dir: Path, project_root: Path) -> list[Route]:
    # Prefer a conventional public dir if it has HTML.
    roots = [app_dir / d for d in ("public", "site", "docs", "www") if (app_dir / d).is_dir()]
    roots.append(app_dir)
    for base in roots:
        files = [f for f in _walk(base, 8) if f.suffix == ".html"]
        if not files:
            continue
        routes = []
        for f in files:
            rel = f.relative_to(base)
            if rel.name in {"404.html", "500.html"}:
                continue
            if rel.name == "index.html":
                path = "/" + "/".join(rel.parts[:-1])
            else:
                path = "/" + "/".join(rel.parts)
            routes.append(Route(path.rstrip("/") or "/", str(f.relative_to(project_root))))
        return routes
    return []


URL_PATTERNS = [
    re.compile(r"metadataBase\s*:\s*new\s+URL\(\s*['\"](https?://[^'\"]+)['\"]"),
    re.compile(r"siteUrl\s*:\s*['\"](https?://[^'\"]+)['\"]"),
    re.compile(r"\bsite\s*:\s*['\"](https?://[^'\"]+)['\"]"),           # astro.config
    re.compile(r"(?:NEXT_PUBLIC_|PUBLIC_|VITE_)?SITE_URL\s*=\s*['\"]?(https?://[^\s'\"]+)"),
    re.compile(r"baseURL\s*=\s*['\"](https?://[^'\"]+)['\"]"),           # hugo
    re.compile(r"^url\s*:\s*['\"]?(https?://[^\s'\"]+)", re.M),          # jekyll _config.yml
]
URL_FILES = [
    "next.config.js", "next.config.mjs", "next.config.ts", "next-sitemap.config.js",
    "astro.config.mjs", "astro.config.ts", "nuxt.config.ts", "svelte.config.js",
    "hugo.toml", "config.toml", "_config.yml", ".env", ".env.production", ".env.example",
    "app/layout.tsx", "app/layout.jsx", "src/app/layout.tsx", "src/app/layout.jsx",
]


def _site_urls(app_dir: Path) -> list[str]:
    found: list[str] = []
    for name in URL_FILES:
        p = app_dir / name
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for pat in URL_PATTERNS:
            for m in pat.finditer(text):
                u = m.group(1).rstrip("/")
                if "localhost" not in u and "example.com" not in u and u not in found:
                    found.append(u)
    cname = app_dir / "CNAME"
    if cname.is_file():
        host = cname.read_text().strip()
        if host:
            u = f"https://{host}"
            if u not in found:
                found.append(u)
    pkg = _read_json(app_dir / "package.json")
    hp = pkg.get("homepage")
    if isinstance(hp, str) and hp.startswith("http") and "github.com" not in hp:
        if hp.rstrip("/") not in found:
            found.append(hp.rstrip("/"))
    return found


DEFAULT_PORTS = {"nextjs-app": 3000, "nextjs-pages": 3000, "nextjs": 3000, "astro": 4321,
                 "nuxt": 3000, "sveltekit": 5173, "remix": 5173, "gatsby": 8000}


def _dev(app_dir: Path, framework: str) -> tuple[int | None, str | None]:
    pkg = _read_json(app_dir / "package.json")
    script = (pkg.get("scripts") or {}).get("dev")
    port = DEFAULT_PORTS.get(framework)
    if script:
        m = re.search(r"(?:-p|--port)[ =](\d{2,5})", script)
        if m:
            port = int(m.group(1))
    return port, ("npm run dev" if script else None)


def _candidate_app_dirs(root: Path) -> list[Path]:
    """Return directories that look like separate sites (monorepo aware)."""
    pkg = _read_json(root / "package.json")
    globs: list[str] = []
    ws = pkg.get("workspaces")
    if isinstance(ws, list):
        globs = ws
    elif isinstance(ws, dict):
        globs = ws.get("packages", [])
    pnpm = root / "pnpm-workspace.yaml"
    if pnpm.is_file():
        globs += re.findall(r"^\s*-\s*['\"]?([^'\"\n]+)['\"]?\s*$", pnpm.read_text(), re.M)
    dirs: list[Path] = []
    for g in globs:
        g = g.strip().rstrip("/")
        if g.startswith("!"):
            continue
        for d in sorted(root.glob(g)):
            if d.is_dir() and (d / "package.json").is_file() and d.name not in IGNORE_DIRS:
                dirs.append(d)
    if not dirs:
        for parent in ("apps", "sites", "packages"):
            for d in sorted((root / parent).glob("*")) if (root / parent).is_dir() else []:
                if d.is_dir() and (d / "package.json").is_file():
                    dirs.append(d)
    if not dirs:
        # A site in a top-level folder such as web/, site/ or frontend/ (no workspaces).
        for d in sorted(root.iterdir()):
            if (d.is_dir() and not d.name.startswith(".") and d.name not in IGNORE_DIRS
                    and (d / "package.json").is_file() and _framework(d) not in ("unknown", "static")):
                dirs.append(d)
    return dirs


def detect(project_root: str | Path) -> list[App]:
    root = Path(project_root).resolve()
    apps: list[App] = []
    for d in _candidate_app_dirs(root):
        fw = _framework(d)
        if fw in {"unknown"}:
            continue
        apps.append(_build_app(d, root, fw))
    root_fw = _framework(root)
    # The root is a site too if it has a real framework, or if nothing else was found.
    if root_fw not in ("unknown", "static") or (not apps and root_fw == "static"):
        apps.insert(0, _build_app(root, root, root_fw))
    return apps


def app_at(project_root: str | Path, rel: str) -> App | None:
    """Build the app at an explicit folder (from --app), even if detection didn't list it."""
    root = Path(project_root).resolve()
    d = (root / rel).resolve()
    if not d.is_dir() or (d != root and root not in d.parents):
        return None
    fw = _framework(d)
    return None if fw == "unknown" else _build_app(d, root, fw)


def _build_app(d: Path, root: Path, fw: str) -> App:
    if fw == "nextjs-app":
        routes = _next_app_routes(d, root) + _next_pages_routes(d, root)
    elif fw == "nextjs-pages":
        routes = _next_pages_routes(d, root)
    elif fw == "static":
        routes = _static_routes(d, root)
    else:
        routes = []   # v1: other frameworks rely on the live scan for page discovery
    seen: dict[str, Route] = {}
    for r in routes:
        seen.setdefault(r.path, r)
    port, cmd = _dev(d, fw)
    rel = str(d.relative_to(root)) if d != root else "."
    name = _read_json(d / "package.json").get("name") or d.name
    return App(rel, name, fw, sorted(seen.values(), key=lambda r: r.path), _site_urls(d), port, cmd)
