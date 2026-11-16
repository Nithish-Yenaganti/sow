"""Checks that read source code: injection, XSS, secrets, server-side request handling, AI features."""

from __future__ import annotations

import base64
import json
import re
from collections import defaultdict
from pathlib import Path

from guarded.project import (JS_EXT, UI_EXT, Project, call_args, in_pattern, interpolates, is_comment, is_static, line_of,
                             mask, split_args, window)
from guarded.rules import Finding

PY = {".py"}

# Where outside text enters a request handler or a tool call.
REQ_SRC = (r"req\.(query|body|params|headers|cookies)|request\.(query|body|params|args|form|files|values|GET|POST|json)"
           r"|searchParams\.get\(|\bquery\.get\(|formData\.get\(|await\s+req(uest)?\.json\(\)|ctx\.(query|params|request)"
           r"|event\.(body|queryStringParameters|pathParameters)|\$_(GET|POST|REQUEST)|params\[|\bparams\.\w+|\bquery\.\w+"
           r"|\b(args|input|arguments)\.\w+|\barguments\[")

LLM_CALL = re.compile(r"chat\.completions\.create|responses\.create|messages\.create|generateText\(|streamText\(|generateObject\("
                      r"|streamObject\(|ChatOpenAI|ChatAnthropic|ChatLiteLLM|ChatGoogleGenerativeAI|ChatOllama|"
                      r"generate_content\(|generateContent\(|ollama\.(chat|generate)|litellm\.completion|ChatCompletion\.create")
LLM_PKGS = {"openai", "@anthropic-ai/sdk", "anthropic", "ai", "@ai-sdk/openai", "@ai-sdk/anthropic", "@ai-sdk/google",
            "@ai-sdk/react", "langchain", "@langchain/core", "@langchain/openai", "langchain-core", "langchain-openai",
            "langchain-community", "llama-index", "llamaindex", "@google/generative-ai", "@google/genai", "google-genai",
            "google-generativeai", "groq-sdk", "groq", "@mistralai/mistralai", "mistralai", "ollama", "litellm", "cohere",
            "cohere-ai", "replicate", "together-ai", "@openrouter/ai-sdk-provider", "pandasai", "crewai", "autogen",
            "pyautogen", "@modelcontextprotocol/sdk", "mcp", "fastmcp", "langgraph", "@langchain/langgraph"}


def _hits(pj: Project, rx: re.Pattern, files: list[Path]):
    for f in files:
        t = pj.text(f)
        if not t:
            continue
        for m in rx.finditer(t):
            if not is_comment(t, m.start()) and not in_pattern(t, m.start()):
                yield f, t, m


def has(rx: re.Pattern, t: str) -> bool:
    """rx occurs in t outside comments and regex patterns."""
    return any(not is_comment(t, m.start()) and not in_pattern(t, m.start()) for m in rx.finditer(t))


def _loc(f: Path, t: str, idx: int) -> str:
    return f"{f.as_posix()}:{line_of(t, idx)}"


class Collector:
    """Groups occurrences into one finding per (rule, file)."""

    def __init__(self) -> None:
        self.items: dict[tuple[str, str], Finding] = {}

    def add(self, rule: str, f: Path | str, loc: str, detail: str, evidence: str = "", severity: str | None = None,
            subject: str | None = None) -> None:
        subj = subject or (f.as_posix() if isinstance(f, Path) else f)
        k = (rule, subj)
        if k not in self.items:
            self.items[k] = Finding(rule, subj, detail, severity=severity)
        fd = self.items[k]
        if loc not in fd.files:
            fd.files.append(loc)
        if evidence and len(fd.evidence) < 5:
            fd.evidence.append(evidence.strip()[:200])
        if severity == "high":
            fd.severity = "high"

    def findings(self) -> list[Finding]:
        out = []
        for f in self.items.values():
            if len(f.files) > 1 and "place" not in f.detail:
                f.detail = f"{f.detail}, in {len(f.files)} places"
            out.append(f)
        return out


# --- shell commands -----------------------------------------------------------------------------------------------
def _exec_names(t: str) -> set[str]:
    names = set()
    if re.search(r"""(require\(\s*['"](node:)?child_process['"]\s*\)|from\s+['"](node:)?child_process['"])""", t):
        names |= {"exec", "execSync"}
        for m in re.finditer(r"\{([^}]*)\}\s*(=\s*require\(\s*['\"](node:)?child_process|from\s+['\"](node:)?child_process)", t):
            for part in m.group(1).split(","):
                bits = [b.strip() for b in re.split(r"\s+as\s+|:", part)]
                if bits[0] in ("exec", "execSync") and len(bits) > 1 and bits[1]:
                    names.add(bits[1])
        for m in re.finditer(r"(\w+)\s*=\s*require\(\s*['\"](node:)?child_process['\"]\s*\)|import\s+\*\s+as\s+(\w+)\s+from\s+['\"](node:)?child_process", t):
            mod = m.group(1) or m.group(3)
            names |= {f"{mod}.exec", f"{mod}.execSync"}
    for m in re.finditer(r"(\w+)\s*=\s*(util\.)?promisify\(\s*(\w+\.)?exec\s*\)", t):
        names.add(m.group(1))
    for m in re.finditer(r"import\s*\{([^}]*)\}\s*from\s*['\"][^'\"]*['\"]", t):    # a local wrapper like utils/exec
        for part in m.group(1).split(","):
            nm = part.strip().split(" as ")[-1].strip()
            if re.fullmatch(r"(exec|run|sh)(Async|Promise|P|Command|Shell|Cmd)\w*|execa?Command\w*", nm):
                names.add(nm)
    if re.search(r"""['"]shelljs['"]""", t):
        names.add("shell.exec")
    return names


PY_SHELL = re.compile(r"\b(subprocess\.(run|call|Popen|check_output|check_call)|os\.system|os\.popen|subprocess\.getoutput"
                      r"|subprocess\.getstatusoutput|asyncio\.create_subprocess_shell|commands\.getoutput)\s*\(")


def check_shell(pj: Project, c: Collector) -> None:
    for f in pj.code(JS_EXT):
        t = pj.text(f)
        names = _exec_names(t)
        if not names:
            continue
        alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
        for m in re.finditer(rf"(?<![\w.$])({alt})\s*\(", t):
            if is_comment(t, m.start()):
                continue
            args = split_args(call_args(t, m.end() - 1))
            if not args or is_static(args[0]):
                continue
            how = "text pasted into the command" if interpolates(args[0]) else f"the command comes from `{args[0][:40]}`"
            c.add("inject.shell", f, _loc(f, t, m.start()), how, m.group(0) + args[0][:120])
        for m in re.finditer(r"(?<![\w.])(spawn|spawnSync|execFile|execFileSync)\s*\(", t):
            a = call_args(t, m.end() - 1)
            if re.search(r"shell\s*:\s*true", a):
                args = split_args(a)
                if args and not is_static(args[0]):
                    c.add("inject.shell", f, _loc(f, t, m.start()), "a command run with shell: true", m.group(0) + args[0][:120])
    for f, t, m in _hits(pj, PY_SHELL, pj.code(PY)):
        a = call_args(t, m.end() - 1)
        args = split_args(a)
        if not args or is_static(args[0]):
            continue
        fn = m.group(1)
        if fn.startswith("subprocess.") and fn.split(".")[1] in ("run", "call", "Popen", "check_output", "check_call") \
                and not re.search(r"shell\s*=\s*True", a):
            continue
        how = "text pasted into the command" if interpolates(args[0]) else f"the command comes from `{args[0][:40]}`"
        c.add("inject.shell", f, _loc(f, t, m.start()), how, fn + "(" + args[0][:120])


# --- eval ---------------------------------------------------------------------------------------------------------
JS_EVAL = re.compile(r"(?<![\w.$])(eval|new\s+Function|setTimeout|setInterval)\s*\(|\bvm\.(runInNewContext|runInContext|runInThisContext)\s*\(|new\s+vm\.Script\s*\(")
PY_EVAL = re.compile(r"(?<![\w.])(eval|exec)\s*\(")


def check_eval(pj: Project, c: Collector) -> None:
    for f, t, m in _hits(pj, JS_EVAL, pj.code(JS_EXT)):
        args = split_args(call_args(t, m.end() - 1))
        if not args or is_static(args[0]):
            continue
        fn = re.sub(r"\s+", " ", m.group(0).rstrip("( "))
        if fn in ("setTimeout", "setInterval") and not re.match(r"^[\"'`]", args[0]):
            continue                                     # a function, not a string of code
        if fn == "new Function" and all(is_static(a) for a in args[:-1]) and is_static(args[-1]):
            continue
        c.add("inject.eval", f, _loc(f, t, m.start()), f"`{fn}()`", fn + "(" + args[0][:120])
    for f, t, m in _hits(pj, PY_EVAL, pj.code(PY)):
        args = split_args(call_args(t, m.end() - 1))
        if not args or is_static(args[0]) or re.match(r"^compile\(\s*[\"']", args[0]):
            continue
        c.add("inject.eval", f, _loc(f, t, m.start()), f"`{m.group(1)}()`", m.group(1) + "(" + args[0][:120])


# --- SQL ----------------------------------------------------------------------------------------------------------
SQL_SHAPE = re.compile(r"\b(SELECT\s[\s\S]{1,300}?\sFROM\s|INSERT\s+INTO\s|UPDATE\s+[\w.\"`\[\]]+\s+SET\s|DELETE\s+FROM\s"
                       r"|DROP\s+TABLE\s|ALTER\s+TABLE\s|WHERE\s+[\w.\"`]+\s*(=|LIKE|IN)\s)", re.I)
TEMPLATE = re.compile(r"(?<![\w$.\]])`((?:[^`\\]|\\.)*)`", re.S)
PY_FSTR = re.compile(r"\b[rR]?[fF][rR]?(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\"\n]*\"|'[^'\n]*')")
PY_FMT = re.compile(r"(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\"\n]*\"|'[^'\n]*')\s*(%\s*[\w(]|\.format\(|\+\s*\w)")
JS_CONCAT = re.compile(r"(\"[^\"\n]*\"|'[^'\n]*')\s*\+\s*[\w(]")
RAW_UNSAFE = re.compile(r"\$(queryRawUnsafe|executeRawUnsafe)\s*\(|\bsql\.raw\s*\(|\bknex\.raw\s*\(|\.whereRaw\s*\(|\.unsafe\s*\(")
SQL_SINK = re.compile(r"\.(query|execute|exec|raw|run|all|get|prepare|executescript|executemany|unsafe|text)\s*\(|\btext\(|\bsql\s*=|query\s*=|stmt\s*=|Raw\(")


def _sql_context(t: str, start: int, end: int) -> bool:
    """The string is used as a query: passed to a query call, or assigned to a variable that is."""
    before = t[max(0, start - 120): start]
    return bool(re.search(r"(\.(query|execute|exec|raw|run|all|get|prepare|unsafe|executescript|executemany)|\btext|\bRaw|"
                          r"Unsafe)\s*\(\s*$|(sql|query|stmt|statement|q)\w*\s*[:=]\s*$|\+=\s*$", before, re.I))


def check_sql(pj: Project, c: Collector) -> None:
    for f in pj.code(JS_EXT):
        t = pj.text(f)
        if not t:
            continue
        for m in TEMPLATE.finditer(t):
            body = m.group(1)
            if "${" not in body or not SQL_SHAPE.search(re.sub(r"\$\{[^}]*\}", "x", body)):
                continue
            if not _sql_context(t, m.start(), m.end()) or is_comment(t, m.start()):
                continue
            c.add("inject.sql", f, _loc(f, t, m.start()), "values pasted into the query text", "`" + body[:150] + "`")
        for m in JS_CONCAT.finditer(t):
            if SQL_SHAPE.search(m.group(1)) and not is_comment(t, m.start()) and _sql_context(t, m.start(), m.end()):
                c.add("inject.sql", f, _loc(f, t, m.start()), "values joined onto the query with +", m.group(0)[:150])
        for m in RAW_UNSAFE.finditer(t):
            args = split_args(call_args(t, m.end() - 1))
            if args and not is_static(args[0]) and not is_comment(t, m.start()):
                c.add("inject.sql", f, _loc(f, t, m.start()), f"`{m.group(0).rstrip('( ')}` with changing text",
                      m.group(0) + args[0][:120])
    for f in pj.code(PY | {".php", ".rb", ".go"}):
        t = pj.text(f)
        if not t:
            continue
        for rx, how in ((PY_FSTR, "an f-string query"), (PY_FMT, "a query built with % / .format / +")):
            for m in rx.finditer(t):
                s = m.group(1)
                inner = re.sub(r"\{[^}]*\}", "x", s) if rx is PY_FSTR else s
                if rx is PY_FSTR and "{" not in s:
                    continue
                if not SQL_SHAPE.search(inner) or is_comment(t, m.start()):
                    continue
                if not _sql_context(t, m.start(), m.end()):
                    continue
                c.add("inject.sql", f, _loc(f, t, m.start()), how, m.group(0)[:150])
        if f.suffix == ".php":
            for m in re.finditer(r"(mysqli_query|->query|->exec)\s*\([^;]*\$_(GET|POST|REQUEST|COOKIE)", t):
                c.add("inject.sql", f, _loc(f, t, m.start()), "request values in the query", m.group(0)[:150])


# --- AI-written queries and code ----------------------------------------------------------------------------------
LLM_SQL_TOOLS = re.compile(r"\b(SQLDatabaseChain|create_sql_agent|create_sql_query_chain|SQLDatabaseToolkit|NLSQLTableQueryEngine"
                           r"|SQLTableRetrieverQueryEngine|NLSQLRetriever|GraphCypherQAChain|JSONalyzeQueryEngine|"
                           r"PandasQueryEngine|SmartDataframe|SmartDatalake|createSqlQueryChain|SqlDatabaseChain|"
                           r"SqlToolkit|createSqlAgent)\b")
LLM_EXEC_TOOLS = re.compile(r"\b(PythonREPLTool|PythonAstREPLTool|PythonREPL\(|ShellTool\(|BashProcess|create_python_agent|"
                            r"create_pandas_dataframe_agent|create_csv_agent|LLMMathChain|allow_dangerous_code\s*=\s*True|"
                            r"allow_dangerous_requests\s*=\s*True|code_execution_config|LocalCommandLineCodeExecutor)")
AI_VALUE = r"(completion|response|resp|output|result|generated|llm\w*|ai\w*|model\w*|answer|reply|choices|message|content|text|tool_?input|toolCall|args)"


def check_llm_flows(pj: Project, c: Collector) -> None:
    files = pj.code()
    for f, t, m in _hits(pj, LLM_SQL_TOOLS, files):
        c.add("inject.llm_sql", f, _loc(f, t, m.start()), f"`{m.group(1)}`", m.group(0))
    for f, t, m in _hits(pj, LLM_EXEC_TOOLS, files):
        c.add("inject.llm_exec", f, _loc(f, t, m.start()), f"`{m.group(1).split('=')[0].strip()}`", m.group(0))
    for f in files:
        t = pj.text(f)
        if not t or not has(LLM_CALL, t):
            continue
        for m in re.finditer(r"\.(query|execute|raw|\$queryRawUnsafe|\$executeRawUnsafe|unsafe)\s*\(", t):
            args = split_args(call_args(t, m.end() - 1))
            if args and not is_static(args[0]) and re.search(rf"(^|[\s.(\[]){AI_VALUE}\b", args[0], re.I) \
                    and not is_comment(t, m.start()):
                c.add("inject.llm_sql", f, _loc(f, t, m.start()), "the model's reply passed to a query", m.group(0) + args[0][:100])
        for m in re.finditer(r"(?<![\w.$])(eval|exec|execSync|new\s+Function)\s*\(|\bvm\.run\w*\(|subprocess\.\w+\(|os\.system\(", t):
            args = split_args(call_args(t, m.end() - 1))
            if args and not is_static(args[0]) and re.search(rf"(^|[\s.(\[]){AI_VALUE}\b", args[0], re.I) \
                    and not is_comment(t, m.start()):
                c.add("inject.llm_exec", f, _loc(f, t, m.start()), "the model's reply run as code", m.group(0) + args[0][:100])


# --- XSS ----------------------------------------------------------------------------------------------------------
SANITIZER = re.compile(r"DOMPurify|sanitize-html|sanitizeHtml|\bsanitize\(|xss\(|isomorphic-dompurify|rehype-sanitize|bleach\.clean|"
                       r"escapeHtml|escape_html|he\.encode|sanitizer\.sanitize\(", re.I)


def check_xss(pj: Project, c: Collector) -> None:
    rx = re.compile(r"dangerouslySetInnerHTML\s*=\s*\{\{\s*__html\s*:|\.(innerHTML|outerHTML)\s*(?<![=!])=(?!=)|"
                    r"\binsertAdjacentHTML\s*\(|\bdocument\.write(ln)?\s*\(|\bv-html\s*=|\{@html\s|"
                    r"bypassSecurityTrust(Html|Script|Url|ResourceUrl)\s*\(|\b(mark_safe|Markup)\s*\(|\|\s*safe\b")
    for f in pj.code(JS_EXT | PY | {".html", ".htm", ".j2", ".jinja", ".ejs", ".hbs"}):
        t = pj.text(f)
        if not t:
            continue
        sanitized = bool(SANITIZER.search(t))

        def safe_value(val: str) -> bool:
            v = val.strip().rstrip(",;")
            if is_static(v) or v in ('""', "''", "``") or re.search(r"sanitize|purify|escape|renderToString|renderToStaticMarkup", v, re.I):
                return True
            if re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", v):
                return True                                  # a constant
            if re.fullmatch(r"[A-Za-z_$][\w$]*", v):
                src = re.search(rf"\b{re.escape(v)}\s*(:\s*[\w<>| ]+)?=\s*(?!=)([^\n;]*)", t)
                if src and (is_static(src.group(2)) or re.search(r"renderToString|renderToStaticMarkup|sanitize|purify|escape",
                                                                   src.group(2), re.I)):
                    return True
            return False

        for m in rx.finditer(t):
            if is_comment(t, m.start()):
                continue
            tok = m.group(0)
            rest = t[m.end(): m.end() + 300]
            if tok.startswith("dangerouslySetInnerHTML"):
                val = rest.split("}}", 1)[0].strip()
                if safe_value(val) or val.startswith("JSON.stringify"):
                    continue
                what = "dangerouslySetInnerHTML"
            elif tok.startswith("."):
                val = rest.split(";", 1)[0].split("\n", 1)[0].strip()
                if safe_value(val):
                    continue
                what = tok.strip("=. ")
            elif tok.startswith(("insertAdjacentHTML", "document.write", "bypassSecurityTrust", "mark_safe", "Markup")):
                args = split_args(call_args(t, m.end() - 1))
                val = args[-1] if args else ""
                if not args or safe_value(val):
                    continue
                what = tok.rstrip("( ")
            elif tok.startswith("|"):
                if f.suffix not in (".html", ".htm", ".j2", ".jinja"):
                    continue
                val, what = "", "the |safe filter"
            else:
                val, what = rest[:80], tok.strip("={ ")
            if sanitized and what in ("dangerouslySetInnerHTML", "innerHTML", "outerHTML", "v-html", "@html"):
                continue
            c.add("xss.raw_html", f, _loc(f, t, m.start()), f"`{what}`", tok + val[:100])
    # Markdown with raw HTML turned on.
    md_raw = pj.has_pkg("rehype-raw") and not pj.has_pkg("rehype-sanitize", "dompurify", "isomorphic-dompurify")
    for f in pj.code(JS_EXT):
        t = pj.text(f)
        if not t:
            continue
        if md_raw and re.search(r"""from\s+['"]rehype-raw['"]|require\(['"]rehype-raw""", t):
            m = re.search(r"rehype-raw", t)
            c.add("xss.markdown_html", f, _loc(f, t, m.start()), "`rehype-raw` without `rehype-sanitize`", "rehype-raw")
        m = re.search(r"markdownit\(\s*\{[^}]*html\s*:\s*true|new\s+MarkdownIt\(\s*\{[^}]*html\s*:\s*true", t)
        if m and not SANITIZER.search(t):
            c.add("xss.markdown_html", f, _loc(f, t, m.start()), "markdown-it with `html: true`", m.group(0)[:120])
        m = re.search(r"\bmarked(\.parse)?\s*\(", t)
        if m and re.search(r"innerHTML|dangerouslySetInnerHTML|v-html|\{@html", t) and not SANITIZER.search(t):
            c.add("xss.markdown_html", f, _loc(f, t, m.start()), "`marked()` output inserted as HTML", m.group(0))


def check_csp(pj: Project, findings: list[Finding], ai_markdown: bool) -> None:
    ui = pj.code(UI_EXT)
    web = ui and (pj.has_pkg("next", "react-dom", "vue", "svelte", "@sveltejs/kit", "astro", "nuxt", "@remix-run/react",
                             "express", "fastify", "hono", "flask", "django", "fastapi", "vite", "@angular/core")
                  or any(f.suffix in (".html", ".htm") for f in ui))
    if not web:
        return
    rx = re.compile(r"Content-Security-Policy|contentSecurityPolicy|helmet\(|\bcsp\s*[:=(]|CSP_|django-csp|flask_talisman|"
                    r"Talisman\(|secure_headers|nonce=", re.I)
    cfg = [f for f in pj.files if f.suffix.lower() in JS_EXT | PY | {".html", ".htm", ".json", ".toml", ".yml", ".yaml", ".conf"}
           or f.name in ("_headers", "nginx.conf", "Caddyfile")]
    for f in cfg:
        if rx.search(pj.text(f)):
            return
    findings.append(Finding("xss.no_csp", severity="medium" if ai_markdown else None))


# --- secrets ------------------------------------------------------------------------------------------------------
SECRET_PATS = [
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}T3BlbkFJ[A-Za-z0-9_-]{20,}\b|\bsk-proj-[A-Za-z0-9_-]{40,}")),
    ("Anthropic API key", re.compile(r"\bsk-ant-(?:api|admin)\d{2}-[A-Za-z0-9_-]{30,}")),
    ("Stripe live secret key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{50,}")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{34,}\b")),
    ("Groq API key", re.compile(r"\bgsk_[A-Za-z0-9]{48,}\b")),
    ("Replicate token", re.compile(r"\br8_[A-Za-z0-9]{37,}\b")),
    ("Google API key (Gemini, Maps or Firebase)", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("Supabase service_role key", re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")),
]
PLACEHOLDER = re.compile(r"x{6,}|X{6,}|your[_-]|example|placeholder|dummy|fake|<|0{10,}|1234567890|\.\.\.", re.I)


def _jwt_role(tok: str) -> str:
    try:
        part = tok.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))).get("role", "")
    except (ValueError, IndexError, AttributeError):
        return ""


def check_secrets(pj: Project, c: Collector) -> None:
    files = pj.code(set(JS_EXT) | PY | {".php", ".rb", ".go", ".json", ".yml", ".yaml", ".toml", ".html", ".env", ".sh", ".txt"})
    files += [f for f in pj.files if f.name.startswith(".env") and f not in files]
    for f in files:
        if re.search(r"\.(example|sample|template|dist|defaults?)$|example|lock\.json$|\.lock$", f.name, re.I):
            continue
        t = pj.text(f)
        if not t:
            continue
        for kind, rx in SECRET_PATS:
            for m in rx.finditer(t):
                tok = m.group(0)
                if PLACEHOLDER.search(tok):
                    continue
                if kind.startswith("Supabase"):
                    if _jwt_role(tok) != "service_role":
                        continue
                if kind.startswith("Google") and re.search(r"authDomain|firebaseConfig|messagingSenderId", t):
                    continue                                     # Firebase web config: public by design
                c.add("secrets.hardcoded", f, _loc(f, t, m.start()), kind, f"{kind}: {mask(tok)}",
                      severity="medium" if kind.startswith("Google") else None)


PUBLIC_PREFIX = r"(?:NEXT_PUBLIC|VITE|REACT_APP|EXPO_PUBLIC|NUXT_PUBLIC|GATSBY|PUBLIC|VUE_APP)"
PUBLIC_SECRET = re.compile(rf"\b({PUBLIC_PREFIX}_[A-Z0-9_]*?(?:SECRET|SERVICE_ROLE|SERVICE_KEY|PRIVATE_KEY|DATABASE_URL|DB_PASSWORD|"
                           r"(?:OPENAI|ANTHROPIC|CLAUDE|GROQ|GEMINI|GOOGLE_AI|MISTRAL|COHERE|REPLICATE|DEEPSEEK|XAI|PERPLEXITY|"
                           r"TOGETHER|FIREWORKS|OPENROUTER|ELEVENLABS|RESEND|SENDGRID|POSTMARK|TWILIO|HF|HUGGINGFACE)_?\w*?"
                           r"(?:KEY|TOKEN))[A-Z0-9_]*)\b")
BROWSER_AI = re.compile(r"dangerouslyAllowBrowser\s*:\s*true|anthropic-dangerous-direct-browser-access")


def check_public_env(pj: Project, c: Collector) -> None:
    files = pj.code(JS_EXT) + [f for f in pj.files if f.name.startswith(".env") or f.name in ("vercel.json", "netlify.toml")]
    for f in files:
        t = pj.text(f)
        for m in PUBLIC_SECRET.finditer(t):
            name = m.group(1)
            if "PUBLISHABLE" in name or "ANON" in name:
                continue
            why = ("A Supabase service_role key skips every database rule." if "SERVICE" in name else
                   "This looks like a server-only secret.")
            c.add("secrets.public_env", f, _loc(f, t, m.start()), why, name, subject=name)
    for f, t, m in _hits(pj, BROWSER_AI, pj.code(JS_EXT)):
        c.add("ai.browser_key", f, _loc(f, t, m.start()), f"`{m.group(0)}`", m.group(0))


def check_weak_hash(pj: Project, c: Collector) -> None:
    rx = re.compile(r"createHash\(\s*['\"](md5|sha1|sha256|sha512)['\"]|hashlib\.(md5|sha1|sha256|sha512)\(|\bmd5\(|"
                    r"CryptoJS\.(MD5|SHA1|SHA256)\(")
    for f, t, m in _hits(pj, rx, pj.code()):
        near = window(t, m.start(), 6, 6)
        if not re.search(r"passw(or)?d|pwd\b", near, re.I) and not re.search(r"passw(or)?d", t[:m.start()][-2000:], re.I):
            continue
        if re.search(r"bcrypt|argon2|scrypt|pbkdf2", t, re.I):
            continue
        algo = next(g for g in m.groups() if g)
        c.add("secrets.weak_hash", f, _loc(f, t, m.start()), algo.upper(), m.group(0))


# --- server -------------------------------------------------------------------------------------------------------
FETCH = re.compile(r"(?<![\w.])(fetch|axios(\.(get|post|put|request|head))?|got(\.(get|post))?|needle|superagent\.get|ky(\.get)?)\s*\(|"
                   r"\brequests\.(get|post|put|head|request)\s*\(|\bhttpx\.(get|post|request)\s*\(|\bclient\.(get|post)\s*\(|"
                   r"urlopen\s*\(|\burllib\.request\.urlopen\s*\(")
URLISH = r"(url|uri|link|href|src|target|endpoint|webhook|callback|image|img|feed|site|domain|host|address|remote)"
FS_CALL = re.compile(r"(?<![\w])(fs\.|fsp\.|fs/promises|)(readFile|readFileSync|createReadStream|writeFile|writeFileSync|unlink|"
                     r"unlinkSync|rm|rmSync|readdir|appendFile)\s*\(|\.(sendFile|download)\s*\(|\b(send_file|send_from_directory|"
                     r"FileResponse)\s*\(|(?<![\w.])open\s*\(")
PATH_GUARD = re.compile(r"path\.basename|\.startsWith\(|secure_filename|safe_join|realpath|is_relative_to|commonpath|"
                        r"normalize\([^)]*\)\.startsWith|sanitize[-_]?filename|\.\.[/\\]?['\"]\s*\)|includes\(['\"]\.\.", re.I)


SKIP_IDENT = {"path", "join", "resolve", "__dirname", "__filename", "process", "cwd", "os", "String", "encodeURIComponent",
              "new", "URL", "await", "this", "const", "let", "var", "return", "true", "false", "null", "undefined", "env",
              "toString", "trim", "replace", "toLowerCase", "baseDir", "BASE_DIR", "ROOT", "root", "as", "string"}


def _from_request(t: str, idx: int, arg: str, keys: str | None = None) -> bool:
    if re.search(REQ_SRC, arg):
        return True
    idents = [v for v in re.findall(r"(?<![\w$.'\"`])([A-Za-z_$][\w$]*)", re.sub(r"(['\"`])(?:(?!\1).)*\1", "", arg))
              if v not in SKIP_IDENT]
    if not idents or any(re.search(r"saniti[sz]|safe|clean|valid|allowed", v, re.I) for v in idents):
        return False
    return any(_var_from_request(t, idx, v, arg, keys) for v in dict.fromkeys(idents[:4]))


def _var_from_request(t: str, idx: int, name: str, arg: str, keys: str | None) -> bool:
    w = window(t, idx, 25, 0)
    v = re.escape(name)
    if re.search(rf"\b{v}\b(\s*:\s*[\w<>\[\]| .]+)?\s*[:=](?!=)[^=\n]*({REQ_SRC})", w):
        return True
    if re.search(rf"\{{[^}}]*\b{v}\b[^}}]*\}}\s*=\s*[^\n]*({REQ_SRC}|await\s+req\w*\.json\(\)|\breq\.\w+|\brequest\b)", w):
        return True
    return bool(keys and re.search(rf"({REQ_SRC})[^\n]*{keys}", w, re.I) and re.search(rf"\b{v}\b\s*=", w))


def check_server(pj: Project, c: Collector) -> None:
    files = pj.code()
    for f, t, m in _hits(pj, FETCH, files):
        args = split_args(call_args(t, m.end() - 1))
        if not args or is_static(args[0]):
            continue
        a = args[0]
        if re.match(r"^[`'\"]https?://[^$'\"`{]+/", a) or re.match(r"^[`'\"]/", a):
            continue                                     # fixed host or own path; only the path changes
        if re.match(r"^f[\"']https?://[^{]+/", a):
            continue
        if _from_request(t, m.start(), a, URLISH):
            c.add("server.ssrf", f, _loc(f, t, m.start()), f"`{a[:40]}`", m.group(0) + a[:100])
    for f, t, m in _hits(pj, FS_CALL, files):
        if PATH_GUARD.search(t):
            continue
        args = split_args(call_args(t, m.end() - 1))
        if not args or is_static(args[0]):
            continue
        a = args[0]
        if m.group(0).strip().startswith("open") and f.suffix not in PY:
            continue
        if _from_request(t, m.start(), a):
            c.add("server.path", f, _loc(f, t, m.start()), f"`{a[:40]}`", m.group(0) + a[:100])
    rx = re.compile(r"(?<![\w])(res\.redirect|redirect|NextResponse\.redirect|Response\.redirect|HttpResponseRedirect|"
                    r"RedirectResponse|reply\.redirect|ctx\.redirect)\s*\(")
    for f, t, m in _hits(pj, rx, files):
        args = split_args(call_args(t, m.end() - 1))
        if not args:
            continue
        a = args[-1] if m.group(1) == "res.redirect" and len(args) == 2 and args[0].isdigit() else args[0]
        if is_static(a) or re.match(r"^[`'\"]/", a) or "new URL(" in a or re.match(r"^[\w.]*origin\s*(\+|$)|^`\$\{[\w.]*origin\}", a):
            continue
        if _from_request(t, m.start(), a, r"(to|next|url|redirect\w*|return\w*|callback\w*|continue|dest\w*|goto)"):
            c.add("server.redirect", f, _loc(f, t, m.start()), f"`{a[:40]}`", m.group(0) + a[:100])
    deser = re.compile(r"\b(pickle|cPickle|dill|cloudpickle)\.loads?\s*\(|\bjoblib\.load\s*\(|\bshelve\.open\s*\(|\btorch\.load\s*\(|"
                       r"\byaml\.(load|load_all|unsafe_load)\s*\(|\bjsonpickle\.decode\s*\(|\bnp\.load\s*\(|\bnumpy\.load\s*\(|"
                       r"\bpd\.read_pickle\s*\(|from\s+langchain(_core)?\.load\s+import\s+loads?\b|\bunserialize\s*\(")
    for f, t, m in _hits(pj, deser, pj.code(PY | JS_EXT | {".php"})):
        tok = m.group(0)
        a = call_args(t, m.end() - 1) if tok.endswith("(") else ""
        if "torch.load" in tok and re.search(r"weights_only\s*=\s*True", a):
            continue
        if "yaml." in tok and (f.suffix not in PY or re.search(r"SafeLoader|CSafeLoader|BaseLoader", a)):
            continue
        if ("np.load" in tok or "numpy.load" in tok) and not re.search(r"allow_pickle\s*=\s*True", a):
            continue
        if "unserialize" in tok and f.suffix != ".php" and "node-serialize" not in t:
            continue
        what = re.sub(r"\s*\($", "", tok).replace("from ", "").strip()
        c.add("server.deserialize", f, _loc(f, t, m.start()), f"`{what}`", tok + a[:80])
    for f in files:
        t = pj.text(f)
        any_origin = re.search(r"origin\s*:\s*(['\"]\*['\"]|true)\b|Access-Control-Allow-Origin['\"]?\s*[,:]\s*['\"]\*|"
                               r"allow_origins\s*=\s*\[\s*['\"]\*['\"]|CORS_ALLOW_ALL_ORIGINS\s*=\s*True|"
                               r"origin\s*:\s*\(\s*\w*\s*,\s*(cb|callback)\s*\)\s*=>\s*(cb|callback)\(\s*null\s*,\s*true", t)
        creds = re.search(r"credentials\s*:\s*true|Allow-Credentials['\"]?\s*[,:]\s*['\"]?true|allow_credentials\s*=\s*True|"
                          r"CORS_ALLOW_CREDENTIALS\s*=\s*True|supports_credentials\s*=\s*True", t)
        if any_origin and creds:
            c.add("server.cors", f, _loc(f, t, any_origin.start()), "", any_origin.group(0))


# --- API routes without an auth check ------------------------------------------------------------------------------
ROUTE_FILE = re.compile(r"(^|/)app/(.*/)?route\.(ts|js|mjs)$|(^|/)pages/api/.*\.(ts|js)$|(^|/)src/routes/.*\+server\.(ts|js)$")
WRITE_VERB = re.compile(r"export\s+(async\s+)?function\s+(POST|PUT|PATCH|DELETE)\b|export\s+const\s+(POST|PUT|PATCH|DELETE)\b|"
                        r"req\.method\s*===?\s*['\"](POST|PUT|PATCH|DELETE)['\"]")
DB_WRITE = re.compile(r"\.(insert|insertMany|update|updateMany|upsert|delete|deleteMany|create|createMany|destroy|remove|save)\s*\(|"
                      r"\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b|\bDELETE\s+FROM\b|\.from\(\s*['\"]\w+['\"]\s*\)\s*\.(insert|update|upsert|delete)")
AUTH_HINT = re.compile(r"\bauth\(|getServerSession|getSession|currentUser|getUser\b|getAuth|clerk|requireAuth|withAuth|ensureAuth|"
                       r"isAuthenticated|verify\w*\(|jwt|session|authorization|x-api-key|api[_-]?key|apiKey|signature|"
                       r"constructEvent|webhook|validateRequest|lucia|unauthori[sz]ed|\b401\b|\b403\b|getToken|bearer|"
                       r"protectedProcedure|requireUser|auth\.api|supabase\.auth\.getUser|cron_secret|CRON_SECRET|secret", re.I)


def check_routes(pj: Project, c: Collector) -> None:
    mw = [f for f in pj.files if re.search(r"(^|/)(src/)?(middleware|proxy)\.(ts|js)$", f.as_posix())]
    mw_protects = any(AUTH_HINT.search(pj.text(f)) and re.search(r"api", pj.text(f)) for f in mw)
    if mw_protects:
        return
    for f in pj.code(JS_EXT):
        if not ROUTE_FILE.search(f.as_posix()):
            continue
        t = pj.text(f)
        verb, write = WRITE_VERB.search(t), DB_WRITE.search(t)
        if not verb or not write or AUTH_HINT.search(t):
            continue
        name = next(g for g in verb.groups()[1:] if g)
        c.add("data.route_no_auth", f, _loc(f, t, verb.start()), f"a {name} request writes to the database", verb.group(0))


# --- AI features --------------------------------------------------------------------------------------------------
TOOL_USE = re.compile(r"\btools\s*:\s*[\[{\w]|\btool\(\s*\{|bind_tools\(|@tool\b|\bTool\(|StructuredTool|DynamicTool|tool_choice|"
                      r"functions\s*=\s*\[|AgentExecutor|initialize_agent|create_react_agent|createReactAgent|"
                      r"experimental_createMCPClient|createMCPClient|MultiServerMCPClient|function_call|"
                      r"\bAgent\(\s*(name|model|tools|llm)\s*=|server\.tool\(|registerTool\(|@mcp\.tool")
UNTRUSTED_SRC = [
    ("web pages", re.compile(r"""from\s+['"](cheerio|puppeteer|playwright|playwright-core|jsdom|@mozilla/readability|"""
                             r"""@mendable/firecrawl-js|firecrawl|@tavily/core|tavily|serpapi|exa-js|node-html-parser)['"]|"""
                             r"""require\(['"](cheerio|puppeteer|jsdom)['"]\)|^\s*(from|import)\s+(bs4|trafilatura|tavily|serpapi|"""
                             r"""firecrawl|exa_py|duckduckgo_search|newspaper|playwright)\b|BeautifulSoup\(|WebBaseLoader|"""
                             r"""SeleniumURLLoader|AsyncHtmlLoader|TavilySearch|DuckDuckGoSearch|\bweb_?search\s*[:=(]|"""
                             r"""\b(browse|fetch|scrape|read)_(url|page|webpage|website)\b|\b(scrapeUrl|browseUrl|fetchWebpage|readWebpage|"""
                             r"""scrapeWebsite|crawlUrl)\s*\(""", re.M)),
    ("uploaded or shared documents", re.compile(r"""from\s+['"](pdf-parse|pdfjs-dist|pdf2json|mammoth|unpdf|officeparser)['"]|"""
                                                r"""^\s*(from|import)\s+(pypdf|PyPDF2|unstructured|docx|pdfplumber|fitz)\b|"""
                                                r"""(PyPDF|PDF|CSV|Text|Unstructured|Docx|Directory|S3|Notion|Confluence|"""
                                                r"""GitHub|Gmail)\w*Loader\(|SimpleDirectoryReader""", re.M)),
    ("search results from your own data (RAG)", re.compile(r"""from\s+['"](@pinecone-database/pinecone|chromadb|"""
                                                           r"""weaviate-client|@qdrant/js-client-rest|@upstash/vector)['"]|"""
                                                           r"""^\s*(from|import)\s+(pinecone|chromadb|weaviate|qdrant_client|"""
                                                           r"""pgvector|faiss)\b|match_documents|similarity_search|"""
                                                           r"""as_retriever|\w*Retriever\(|getRelevantDocuments""", re.M)),
    ("emails or messages", re.compile(r"""from\s+['"](imapflow|node-imap|@slack/web-api|discord\.js|telegraf)['"]|"""
                                      r"""^\s*(from|import)\s+(imaplib|slack_sdk|discord)\b|gmail\.users\.messages""", re.M)),
    ("GitHub issues, pull requests or repos", re.compile(r"""from\s+['"](@octokit/rest|octokit|@octokit/core)['"]|"""
                                                         r"""^\s*(from|import)\s+github\b|issues\.(listComments|get)\(|"""
                                                         r"""\bgh\s+(issue|pr)\s+view""", re.M)),
]


def check_ai(pj: Project, findings: list[Finding]) -> bool:
    """Prompt-injection risk (untrusted content + tools) and markdown image exfiltration. Returns True when AI replies
    are rendered as markdown (used to raise the CSP finding)."""
    uses_llm = bool(pj.has_pkg(*LLM_PKGS)) or any(has(LLM_CALL, pj.text(f)) for f in pj.code())
    if not uses_llm:
        return False
    code = [f for f in pj.code() if not re.search(r"\.config\.|setup\.|\.d\.ts$", f.name)]
    tool_files = [f for f in code if has(TOOL_USE, pj.text(f))]
    is_mcp_server = pj.has_pkg("@modelcontextprotocol/sdk", "mcp", "fastmcp") and any(
        re.search(r"McpServer|Server\(|FastMCP|server\.tool\(|registerTool\(|@mcp\.tool", pj.text(f)) for f in code)
    if tool_files:
        found = []
        files = []
        for label, rx in UNTRUSTED_SRC:
            hit = next((f for f in code if has(rx, pj.text(f))), None)
            if hit is not None:
                found.append(label)
                if hit is not None:
                    files.append(hit.as_posix())
        if is_mcp_server:
            found.append("whatever the AI client passes to your tools")
        if found:
            findings.append(Finding("ai.injection_risk", detail=", ".join(found),
                                    files=list(dict.fromkeys(files + [f.as_posix() for f in tool_files[:3]])),
                                    severity="high" if is_mcp_server else None))
    md_rx = re.compile(r"""from\s+['"](react-markdown|streamdown|marked|markdown-it|@uiw/react-markdown-preview|"""
                       r"""react-markdown-renderer|markdown-to-jsx|@mdx-js/mdx|showdown|remark-html)['"]""")
    guard = re.compile(r"urlTransform|transformImageUri|disallowedElements|allowedElements|allowedImagePrefixes|"
                       r"allowElement|\bimg\s*:\s*[\w(]|skipHtml|defaultOrigin")
    md_files = [f for f in pj.code(JS_EXT) if md_rx.search(pj.text(f))]
    if not md_files:
        return False
    csp_img = any(re.search(r"img-src", pj.text(f)) for f in pj.files
                  if re.search(r"next\.config|middleware|vercel\.json|_headers|netlify\.toml|nginx", f.as_posix()))
    md_files = [f for f in md_files if not guard.search(pj.text(f))]
    if csp_img or not md_files:
        return True
    chatty = [f for f in md_files if re.search(r"message|chat|assistant|completion|response|reply|answer", pj.text(f), re.I)
              or re.search(r"message|chat", f.as_posix(), re.I)]
    for f in (chatty or [])[:3]:
        findings.append(Finding("ai.markdown_images", f.as_posix(), files=[f.as_posix()]))
    return bool(chatty)


POISON = re.compile(r"<\s*/?\s*(IMPORTANT|SYSTEM|HIDDEN|instructions?)\s*>|(ignore|disregard)\s+(all\s+)?(previous|prior|above)\s+"
                    r"instructions|do not (tell|reveal|mention|show)\s+(this\s+)?(to\s+)?the\s+user|"
                    r"before (responding|answering)[^\n]{0,40}\byou must\b", re.I)


def check_tool_poisoning(pj: Project, c: Collector) -> None:
    from guarded.checks_config import AI_TALK                     # one list of "talks to an AI" phrases
    for f in pj.code(JS_EXT | PY):
        t = pj.text(f)
        if not t or not has(TOOL_USE, t):
            continue
        for m in POISON.finditer(t):
            if is_comment(t, m.start()) or in_pattern(t, m.start()):
                continue
            near = t[m.start(): m.start() + 300]
            if not (AI_TALK.search(near) or re.search(r"\byou (must|should|need to)\b|\bmandatory\b", near, re.I)):
                continue
            snippet = re.sub(r"\s+", " ", near)[:120].strip()
            c.add("aitools.tool_poisoning", f, _loc(f, t, m.start()), snippet, snippet)
            break


def run(pj: Project) -> list[Finding]:
    c = Collector()
    for fn in (check_shell, check_eval, check_sql, check_llm_flows, check_xss, check_secrets, check_public_env,
               check_weak_hash, check_server, check_routes, check_tool_poisoning):
        fn(pj, c)
    out = c.findings()
    ai_md = check_ai(pj, out)
    check_csp(pj, out, ai_md)
    return out
