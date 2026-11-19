"""Project config (remembered answers) and the questions findable asks when there are >=2 real options.

The CLI never prompts interactively. When it needs a decision it prints a JSON
`needs_input` payload; the agent shows the question (Claude Code: multiple-choice
dialog, Codex: numbered list) and re-runs the command with the answer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from urllib.parse import urlparse

from findable import atomic
from findable.detect import App, app_at

CONFIG_DIR = ".findable"


def config_path(root: Path) -> Path:
    return atomic.state_dir(root) / "config.json"


def load_config(root: Path) -> dict:
    p = config_path(root)
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def save_config(root: Path, cfg: dict) -> None:
    atomic.write_json(config_path(root), cfg)


@dataclass
class Option:
    value: str
    label: str
    description: str = ""
    recommended: bool = False


@dataclass
class Question:
    id: str
    question: str
    options: list[Option]
    multi: bool = False
    answer_with: str = ""
    why: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "question": self.question, "multi": self.multi, "why": self.why,
            "answer_with": self.answer_with,
            "options": [o.__dict__ for o in self.options],
        }


@dataclass
class Resolution:
    app: App | None = None
    url: str | None = None          # None = code scan only
    questions: list[Question] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


NO_URL = ("", "none", "code")


def normalize_url(value: str) -> tuple[str | None, str | None]:
    """--url value -> (url or None for code-only, error message or None)."""
    v = (value or "").strip()
    if v.lower() in NO_URL:
        return None, None
    if v.lower() == "ask":
        return None, "Ask the user for the production URL, then re-run with --url https://…"
    if "://" not in v:
        v = "https://" + v                      # "example.com" -> "https://example.com"
    pu = urlparse(v)
    if pu.scheme not in ("http", "https") or not pu.netloc or " " in v:
        return None, f"'{value}' is not a valid http(s) URL."
    return v.rstrip("/"), None


def reachable(url: str, timeout: float = 3.0) -> bool:
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=True,
                      headers={"User-Agent": "findable/0.1 (+preflight)"})
        return r.status_code < 500
    except httpx.HTTPError:
        return False


def resolve(root: Path, apps: list[App], app_arg: str | None, url_arg: str | None,
            check=reachable) -> Resolution:
    """Decide app + URL from args, remembered config, or detection; else return questions."""
    cfg = load_config(root)
    res = Resolution()

    # ---- Q1: which app -------------------------------------------------------
    by_root = {a.root: a for a in apps}
    if app_arg:
        # An explicit --app always wins; never fall back to another folder.
        key = app_arg.strip().strip("/") or "."
        if key not in by_root:
            explicit = app_at(root, key)
            if explicit is None:
                res.notes.append(f"'{app_arg}' is not a website folder findable recognises "
                                 "(no Next.js/Astro/Nuxt/SvelteKit/Remix/Gatsby/Hugo/Jekyll/HTML found there).")
                return res
            by_root[explicit.root] = explicit
            apps = apps + [explicit]
            key = explicit.root
        chosen = key
    else:
        chosen = cfg.get("app")
        if chosen and chosen not in by_root:
            explicit = app_at(root, chosen)
            if explicit is not None:
                by_root[explicit.root] = explicit
                apps = apps + [explicit]
            else:
                res.notes.append(f"Remembered app '{chosen}' no longer exists; asking again.")
                chosen = None
    if not apps:
        res.notes.append("No website found in this folder (no Next.js/Astro/Nuxt/SvelteKit/static HTML).")
        return res
    if chosen is None and len(apps) == 1:
        chosen = apps[0].root
    if chosen is None:
        ranked = sorted(apps, key=lambda a: len(a.routes), reverse=True)
        res.questions.append(Question(
            id="app",
            question=f"Which site should I scan? (found {len(apps)} apps in this repo)",
            why="This repo contains more than one website.",
            answer_with="findable scan --app <value>",
            options=[Option(a.root, f"{a.root} ({a.framework})",
                            f"{len(a.routes)} route{'s' if len(a.routes) != 1 else ''}" + (f", {a.site_urls[0]}" if a.site_urls else ""),
                            recommended=(i == 0)) for i, a in enumerate(ranked)],
        ))
        return res
    res.app = by_root[chosen]

    # ---- Q2: which URL -------------------------------------------------------
    if url_arg is not None:
        res.url, err = normalize_url(url_arg)
        if err:
            res.app = None
            res.notes.append(err)
        return res
    if "url" in cfg and cfg.get("app") == chosen:
        remembered = cfg["url"]
        if remembered is None and cfg.get("code_only"):
            res.notes.append("Code scan only (you chose this before; pass --url to scan the live site).")
            return res
        if remembered and check(remembered):
            res.url = remembered
            res.notes.append(f"Using the remembered URL {remembered} (from .findable/config.json).")
            return res
        if remembered:
            res.notes.append(f"Remembered URL {remembered} is not reachable; asking again.")

    app = res.app
    local = f"http://localhost:{app.dev_port}" if app.dev_port else None
    local_up = bool(local and check(local))
    real: list[Option] = [Option(u, u, "production URL found in your code") for u in app.site_urls]
    if local_up:
        real.append(Option(local, f"{local} (running now)", "local dev server"))

    if len(real) == 1:
        res.url = real[0].value
        return res
    if len(real) >= 2:
        real[0].recommended = True
        real.append(Option("none", "Code scan only", "skip the live checks (bot access, status codes)"))
        res.questions.append(Question(
            id="url", question="Which URL should I scan live?",
            why="More than one URL is available.",
            answer_with="findable scan --url <value>", options=real))
        return res
    # No production URL and no running dev server.
    if app.dev_command and local:
        res.questions.append(Question(
            id="url", question="I couldn't find a production URL and the dev server isn't running. What should I scan?",
            why="The live checks need a reachable URL.",
            answer_with="findable scan --url <value>  (for 'start', run the dev server first, then use the localhost URL)",
            options=[
                Option(local, f"Start the dev server ({app.dev_command}) and scan {local}",
                       "agent starts it in the background, then re-runs the scan", recommended=True),
                Option("ask", "I'll give you the production URL", "reply with the URL"),
                Option("none", "Code scan only", "skip the live checks"),
            ]))
        return res
    res.url = None
    res.notes.append("No URL to scan live; running the code scan only.")
    return res


def remember(root: Path, app: App | None, url: str | None, url_arg: str | None = None) -> None:
    """Save the answers. Code-only is remembered only when the user chose it (--url none);
    otherwise the next run looks for a URL again (a dev server may be running by then)."""
    cfg = load_config(root)
    if app is not None:
        cfg["app"] = app.root
    cfg["url"] = url
    cfg["code_only"] = url is None and url_arg is not None and url_arg.strip().lower() in NO_URL
    save_config(root, cfg)
