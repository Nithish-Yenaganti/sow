"""Checks that read config files: AI coding tool settings, hidden text, Supabase/Firebase rules, .env, Docker."""

from __future__ import annotations

import json
import re
from pathlib import Path

from guarded.project import Project, git_tracked, line_of
from guarded.rules import Finding

# --- AI coding tool configs ---------------------------------------------------------------------------------------
MCP_FILES = (".mcp.json", ".cursor/mcp.json", ".vscode/mcp.json", ".claude/settings.json",
             ".gemini/settings.json", ".roo/mcp.json", ".kiro/settings/mcp.json", ".amazonq/mcp.json", ".windsurf/mcp.json",
             "mcp.json", ".continue/config.json")
RISKY_CMD = re.compile(r"\bcurl\b|\bwget\b|Invoke-WebRequest|\biwr\b|\|\s*(ba|z)?sh\b|\b(ba|z)?sh\s+-c\b|\bcmd(\.exe)?\s+/c\b|"
                       r"powershell|pwsh|base64|\beval\b|\bnc\b|\bncat\b|/dev/tcp|~/\.ssh|\.aws/credentials|\bpython3?\s+-c\b|"
                       r"\bnode\s+-e\b|\brm\s+-rf\b|\bchmod\s+\+x\b|\bdd\s+if=|osascript", re.I)


def _json(text: str):
    """JSON or JSONC (comments and trailing commas, as VS Code allows)."""
    try:
        return json.loads(text)
    except ValueError:
        pass
    t = re.sub(r"(?m)^\s*//.*$", "", text)
    t = re.sub(r"/\*[\s\S]*?\*/", "", t)
    t = re.sub(r",(\s*[}\]])", r"\1", t)
    try:
        return json.loads(t)
    except ValueError:
        return None


def _servers(data) -> dict:
    if not isinstance(data, dict):
        return {}
    for key in ("mcpServers", "servers", "mcp_servers"):
        v = data.get(key)
        if isinstance(v, dict):
            return v
        if isinstance(v, list):                                # Continue's list form
            return {s.get("name", f"server{i}"): s for i, s in enumerate(v) if isinstance(s, dict)}
    mcp = data.get("mcp")
    if isinstance(mcp, dict):
        return _servers(mcp)
    return {}


def _cmd(server: dict) -> str:
    parts = [str(server.get("command", ""))] + [str(a) for a in server.get("args", []) if isinstance(a, (str, int))]
    return " ".join(p for p in parts if p).strip()


def _unpinned(cmd: str) -> bool:
    m = re.match(r"^(npx|bunx|pnpm\s+dlx|yarn\s+dlx|uvx|pipx\s+run)\s+(.*)$", cmd)
    if not m:
        return False
    pkg = next((a for a in m.group(2).split() if not a.startswith("-")), "")
    if not pkg or pkg.startswith((".", "/")):
        return False
    if m.group(1) in ("uvx", "pipx run"):
        return "==" not in pkg and "@" not in pkg
    return not re.search(r"@\d", pkg.lstrip("@"))


def check_ai_tools(pj: Project, out: list[Finding]) -> None:
    files = set(pj.files)
    for name in MCP_FILES:
        f = Path(name)
        if f not in files:
            continue
        data = _json(pj.text(f))
        for sname, s in _servers(data).items():
            if not isinstance(s, dict):
                continue
            cmd = _cmd(s)
            env = " ".join(f"{k}={v}" for k, v in (s.get("env") or {}).items()) if isinstance(s.get("env"), dict) else ""
            if cmd and RISKY_CMD.search(cmd + " " + env) and not re.match(r"^(npx|uvx|bunx)\s+(-y\s+)?[@\w./-]+(\s+--?[\w-]+(=\S+)?)*$", cmd):
                out.append(Finding("aitools.mcp_suspicious", f.as_posix(), sname, files=[f.as_posix()],
                                   evidence=[cmd[:200]], key=sname))
            elif cmd and _unpinned(cmd):
                out.append(Finding("aitools.mcp_unpinned", f.as_posix(), sname, files=[f.as_posix()],
                                   evidence=[cmd[:200]], key=sname))
    auto = [
        (".vscode/settings.json", re.compile(r"\"chat\.tools\.(global\.)?autoApprove\"\s*:\s*true|\"chat\.tools\.autoApprove\"\s*:\s*\{|"
                                             r"\"chat\.agent\.autoApprove\"\s*:\s*true|\"github\.copilot\.chat\.agent\.autoApprove\"\s*:\s*true|"
                                             r"\"chat\.tools\.terminal\.autoApprove\"\s*:\s*\{[^}]*\"/\.\*/\"\s*:\s*true"),
         "auto-approve for Copilot agent tools"),
        (".claude/settings.json", re.compile(r"\"defaultMode\"\s*:\s*\"bypassPermissions\"|\"(Bash|Bash\(\*\)|Bash\(\*:\*\))\""),
         "Claude Code permission to run any shell command"),
        (".cursor/cli.json", re.compile(r"\"Shell\(\*\)\"|\"Shell\(\*:\*\)\""), "Cursor permission to run any shell command"),
        (".cursor/cli-config.json", re.compile(r"\"Shell\(\*\)\"|\"Shell\(\*:\*\)\""), "Cursor permission to run any shell command"),
        (".gemini/settings.json", re.compile(r"\"autoAccept\"\s*:\s*true|\"yolo\"\s*:\s*true|\"approvalMode\"\s*:\s*\"yolo\""),
         "Gemini CLI auto-accept (YOLO mode)"),
        (".codex/config.toml", re.compile(r"approval_policy\s*=\s*\"never\"|sandbox_mode\s*=\s*\"danger-full-access\""),
         "Codex with no approvals or no sandbox"),
        (".windsurf/settings.json", re.compile(r"\"autoExecution\"\s*:\s*\"(turbo|auto)\""), "Windsurf auto-run of terminal commands"),
    ]
    for name, rx, what in auto:
        f = Path(name)
        if f in files:
            t = pj.text(f)
            m = rx.search(t)
            if m:
                out.append(Finding("aitools.auto_approve", name, what, files=[f"{name}:{line_of(t, m.start())}"],
                                   evidence=[m.group(0)[:120]]))
    # Commands that run on their own: Claude Code hooks, Cursor hooks, VS Code tasks that run on folder open.
    for name in (".claude/settings.json", ".cursor/hooks.json", ".gemini/settings.json"):
        f = Path(name)
        if f not in files:
            continue
        data = _json(pj.text(f)) or {}
        hooks = data.get("hooks") if isinstance(data, dict) else None
        for cmd in _hook_commands(hooks):
            sev = "high" if RISKY_CMD.search(cmd) else None
            out.append(Finding("aitools.autorun", name, cmd[:80], files=[name], evidence=[cmd[:200]], severity=sev, key=cmd[:60]))
    f = Path(".vscode/tasks.json")
    if f in files:
        data = _json(pj.text(f)) or {}
        for task in data.get("tasks", []) if isinstance(data, dict) else []:
            if isinstance(task, dict) and (task.get("runOptions") or {}).get("runOn") == "folderOpen":
                cmd = " ".join([str(task.get("command", ""))] + [str(a) for a in task.get("args", []) if isinstance(a, str)])
                out.append(Finding("aitools.autorun", f.as_posix(), cmd[:80].strip(), files=[f.as_posix()], evidence=[cmd[:200]],
                                   severity="high" if RISKY_CMD.search(cmd) else None, key=str(task.get("label", cmd[:40]))))


def _hook_commands(hooks) -> list[str]:
    out = []
    if isinstance(hooks, dict):
        for v in hooks.values():
            out += _hook_commands(v)
    elif isinstance(hooks, list):
        for v in hooks:
            out += _hook_commands(v)
    elif isinstance(hooks, str):
        pass
    if isinstance(hooks, dict) and isinstance(hooks.get("command"), str):
        out.append(hooks["command"])
    return list(dict.fromkeys(out))


# --- hidden text --------------------------------------------------------------------------------------------------
INSTRUCTION_FILES = re.compile(r"(^|/)(AGENTS|CLAUDE|GEMINI|COPILOT|CONVENTIONS|README|CONTRIBUTING|SKILL)[\w.-]*\.md$|"
                               r"(^|/)\.(cursorrules|windsurfrules|clinerules|roorules|goosehints)$|\.mdc$|"
                               r"(^|/)\.github/(copilot-instructions\.md|instructions/|prompts/|chatmodes/)|(^|/)\.cursor/rules/|"
                               r"(^|/)\.claude/(commands|agents|skills)/|(^|/)\.(kiro|windsurf|clinerules|roo)/", re.I)
TAG_CHARS = re.compile("[\U000E0000-\U000E007F]+")
BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")
ZERO_WIDTH = re.compile("[\u200b\u200c\u2060-\u2064\u180e]|(?<!^)\ufeff")
AI_TALK = re.compile(r"(ignore|disregard|forget)\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier|other)\s+(instructions|rules|context|prompts?)|"
                     r"\b(you are|as an?)\s+(an?\s+)?(AI|assistant|agent|LLM|language model|coding agent)|"
                     r"\b(AI|coding|code)\s+(assistant|agent|model)s?\b[^\n]{0,80}\b(must|should|always|never|need to)\b|"
                     r"\b(Claude|Copilot|Cursor|ChatGPT|Gemini|Codex|Windsurf|Cline)\b[^\n]{0,60}\b(must|should|always|never|please)\b|"
                     r"(curl|wget)\s+\S+\s*\|\s*(ba)?sh|do not (tell|inform|mention|show|alert|reveal)\s+(this\s+)?(to\s+)?(the\s+)?(user|human|developer)|"
                     r"\b(run|execute)\s+(this|the following)\s+(command|script)|\bsystem prompt\b|<\s*/?\s*(system|instructions?|IMPORTANT)\s*>",
                     re.I)
HIDDEN_BLOCK = re.compile(r"<!--([\s\S]*?)-->|<(details|div|span|p)[^>]*(display\s*:\s*none|hidden)[^>]*>([\s\S]*?)</\2>", re.I)


def _decode_tags(s: str) -> str:
    return "".join(chr(ord(ch) - 0xE0000) for ch in s if 0xE0020 <= ord(ch) <= 0xE007E)


def check_hidden(pj: Project, out: list[Finding]) -> None:
    for f in pj.files:
        posix = f.as_posix()
        ext = f.suffix.lower()
        instr = bool(INSTRUCTION_FILES.search(posix))
        text_like = ext in {".md", ".mdx", ".mdc", ".txt", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".go", ".rb",
                            ".php", ".vue", ".svelte", ".astro", ".html", ".json", ".yml", ".yaml", ".toml", ".sh"} or instr
        if not text_like:
            continue
        t = pj.text(f)
        if not t:
            continue
        m = TAG_CHARS.search(t)
        if m:
            hidden = _decode_tags(m.group(0))
            out.append(Finding("aitools.hidden_text", posix, "invisible 'tag' characters that spell out hidden text"
                               + (f": \"{hidden[:80]}\"" if hidden else ""), files=[f"{posix}:{line_of(t, m.start())}"],
                               evidence=[hidden[:200]], key="tags"))
            continue
        if ext not in {".json", ".yml", ".yaml", ".txt", ".po"}:
            m = BIDI.search(t)
            if m:
                code = ext not in {".md", ".mdx", ".mdc", ".html"}
                out.append(Finding("aitools.hidden_text", posix,
                                   f"invisible text-direction characters (U+{ord(m.group(0)):04X}) that can make "
                                   + ("code look different from what runs" if code else "text read differently than shown"),
                                   files=[f"{posix}:{line_of(t, m.start())}"], key="bidi",
                                   severity="high" if code or instr else "medium"))
                continue
        if instr:
            zw = ZERO_WIDTH.findall(t)
            if len(zw) >= 3:
                m = ZERO_WIDTH.search(t)
                out.append(Finding("aitools.hidden_text", posix, f"{len(zw)} zero-width characters",
                                   files=[f"{posix}:{line_of(t, m.start())}"], key="zw", severity="medium"))
        if ext in {".md", ".mdx", ".mdc", ".html"} or instr:
            for hm in HIDDEN_BLOCK.finditer(t):
                body = hm.group(1) if hm.group(1) is not None else hm.group(4) or ""
                am = AI_TALK.search(body)
                if am:
                    snippet = re.sub(r"\s+", " ", body.strip())[:140]
                    out.append(Finding("aitools.hidden_instructions", posix, snippet,
                                       files=[f"{posix}:{line_of(t, hm.start())}"], evidence=[snippet], key=str(line_of(t, hm.start()))))
                    break


# --- Supabase / Firebase ------------------------------------------------------------------------------------------
CREATE_TABLE = re.compile(r"create\s+table\s+(if\s+not\s+exists\s+)?((\"?\w+\"?)\.)?\"?(\w+)\"?\s*\(", re.I)
ENABLE_RLS = re.compile(r"alter\s+table\s+(if\s+exists\s+)?(only\s+)?((\"?\w+\"?)\.)?\"?(\w+)\"?\s+(enable|disable|force)\s+row\s+level\s+security", re.I)
POLICY = re.compile(r"create\s+policy\s+(\"[^\"]*\"|\w+)\s+on\s+((\"?\w+\"?)\.)?\"?(\w+)\"?([\s\S]*?);", re.I)


def check_supabase(pj: Project, out: list[Finding]) -> None:
    sql = [f for f in pj.files if f.suffix.lower() == ".sql" and not re.search(r"(^|/)(tests?|seed)", f.as_posix())]
    if not sql or not (pj.has_pkg("@supabase/supabase-js", "@supabase/ssr", "supabase")
                       or any(p.startswith("supabase") for p in (f.as_posix() for f in sql))):
        return
    tables: dict[str, str] = {}
    status: dict[str, str] = {}
    for f in sorted(sql, key=lambda p: p.as_posix()):
        t = pj.text(f)
        for m in CREATE_TABLE.finditer(t):
            schema = (m.group(3) or "public").strip('"').lower()
            if schema == "public":
                tables.setdefault(m.group(4).lower(), f"{f.as_posix()}:{line_of(t, m.start())}")
        for m in ENABLE_RLS.finditer(t):
            schema = (m.group(4) or "public").strip('"').lower()
            if schema == "public":
                status[m.group(5).lower()] = m.group(6).lower()
        for m in POLICY.finditer(t):
            body = re.sub(r"\s+", " ", m.group(5).lower())
            cmd = re.search(r"\bfor\s+(all|insert|update|delete|select)\b", body)
            cmd = cmd.group(1) if cmd else "all"
            if cmd == "select":
                continue
            if re.search(r"(using|with\s+check)\s*\(\s*true\s*\)", body) and not re.search(r"\bto\s+service_role\b", body):
                verb = {"all": "read, add, change and delete", "insert": "add", "update": "change", "delete": "delete"}[cmd]
                out.append(Finding("data.policy_open", m.group(4).lower(), verb, files=[f"{f.as_posix()}:{line_of(t, m.start())}"],
                                   evidence=[m.group(0)[:200]], key=m.group(1).strip('"')[:40]))
    for name, loc in sorted(tables.items()):
        if status.get(name) not in ("enable", "force"):
            out.append(Finding("data.rls_off", name, files=[loc]))


def check_firebase(pj: Project, out: list[Finding]) -> None:
    for f in pj.files:
        if f.name in ("firestore.rules", "storage.rules") or f.suffix == ".rules":
            t = pj.text(f)
            m = re.search(r"allow\s+(read\s*,\s*write|write\s*,\s*read|write|read|create|update|delete)[^;:]*(:\s*if\s+true\s*;|;)", t)
            if m:
                out.append(Finding("data.firebase_open", f.as_posix(), f"allows '{m.group(1)}' with no condition",
                                   files=[f"{f.as_posix()}:{line_of(t, m.start())}"], evidence=[m.group(0)]))
                continue
            m = re.search(r"request\.time\s*<\s*timestamp\.date\(", t)
            if m:
                out.append(Finding("data.firebase_open", f.as_posix(), "still uses the 'test mode' rules (open to everyone until a date)",
                                   files=[f"{f.as_posix()}:{line_of(t, m.start())}"], evidence=[m.group(0)]))
        elif f.name in ("database.rules.json",):
            t = pj.text(f)
            m = re.search(r"\"\.(read|write)\"\s*:\s*(true|\"true\")", t)
            if m:
                out.append(Finding("data.firebase_open", f.as_posix(), f"sets \".{m.group(1)}\": true",
                                   files=[f"{f.as_posix()}:{line_of(t, m.start())}"], evidence=[m.group(0)]))


# --- .env in git --------------------------------------------------------------------------------------------------
def check_env_tracked(pj: Project, out: list[Finding]) -> None:
    tracked = git_tracked(pj.root)
    if tracked is None:
        return
    for name in tracked:
        base = name.rsplit("/", 1)[-1]
        if not re.fullmatch(r"\.env(\.[\w-]+)?", base) or re.search(r"example|sample|template|dist|defaults?|schema", base, re.I):
            continue
        p = pj.root / name
        try:
            t = p.read_text(errors="ignore")
        except OSError:
            continue
        secretish = re.search(r"(?m)^\s*\w*(KEY|SECRET|TOKEN|PASSWORD|PASS|DATABASE_URL|DSN)\w*\s*=\s*['\"]?[^\s'\"#]{8,}", t)
        out.append(Finding("secrets.env_tracked", name, "" if secretish else " (it has no obvious secrets right now)",
                           files=[name], severity=None if secretish else "low"))


# --- local model servers -------------------------------------------------------------------------------------------
def check_model_servers(pj: Project, out: list[Finding]) -> None:
    for f in pj.files:
        if not re.search(r"(docker-)?compose[\w.-]*\.ya?ml$|Dockerfile[\w.-]*$|\.env$|fly\.toml$", f.name, re.I):
            continue
        t = pj.text(f)
        hit = False
        for port, what in (("11434", "Ollama (port 11434)"), ("1234", "LM Studio (port 1234)")):
            m = re.search(rf"^\s*-\s*['\"]?(0\.0\.0\.0:)?{port}:{port}['\"]?\s*$", t, re.M)
            if m:
                out.append(Finding("server.model_exposed", f.as_posix(), what, files=[f"{f.as_posix()}:{line_of(t, m.start())}"],
                                   evidence=[m.group(0).strip()]))
                hit = True
                break
        if not hit:
            m = re.search(r"OLLAMA_HOST\s*[=:]\s*['\"]?0\.0\.0\.0", t)
            if m:
                out.append(Finding("server.model_exposed", f.as_posix(), "Ollama (OLLAMA_HOST=0.0.0.0)",
                                   files=[f"{f.as_posix()}:{line_of(t, m.start())}"], evidence=[m.group(0)]))


def run(pj: Project) -> list[Finding]:
    out: list[Finding] = []
    for fn in (check_ai_tools, check_hidden, check_supabase, check_firebase, check_env_tracked, check_model_servers):
        fn(pj, out)
    return out
