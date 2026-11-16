"""Rule catalog. Every finding comes from one rule here.

who:  agent = the skill can make the fix in the code (after the user agrees)
      user  = only the user can do it (rotate a key, change a dashboard setting, decide)
Every rule cites source ids from references/sources.md (OWASP, CWE, and the CVEs that show the pattern is real).
"""

from __future__ import annotations

from dataclasses import dataclass, field

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}

GROUPS = {
    "aitools": "Files that can take over AI coding tools",
    "secrets": "Secret keys",
    "data": "Who can read and change your data",
    "injection": "Commands and database queries built from outside text",
    "ai": "AI features that can be tricked (prompt injection)",
    "browser": "Code that runs in your users' browsers (XSS)",
    "server": "Server requests, files and loading data",
    "packages": "Packages you install",
}


@dataclass(frozen=True)
class Rule:
    id: str
    group: str
    severity: str
    who: str
    title: str
    plain: str            # may contain {subject}, {detail}
    fix: str              # playbook / suggestions anchor
    sources: tuple[str, ...] = ()


def _r(*a, sources=()):
    return Rule(*a, sources=tuple(sources))


PB = "playbooks/fixes.md"

RULES: dict[str, Rule] = {r.id: r for r in [
    # --- AI coding tools -----------------------------------------------------------------------------------
    _r("aitools.auto_approve", "aitools", "high", "agent", "AI tool set to run commands without asking",
       "{subject} turns on {detail}. Anyone who opens this repo with that AI tool lets it run commands without asking "
       "first, which is exactly what prompt-injection attacks need.",
       f"{PB}#auto-approve", sources=["CVE-2025-53773", "owasp-llm06"]),
    _r("aitools.mcp_suspicious", "aitools", "high", "agent", "AI tool server runs a risky command",
       "{subject} starts the MCP server '{detail}' with a command that downloads or runs code ({evidence}). "
       "AI tools may start it as soon as the repo is opened.",
       f"{PB}#mcp-config", sources=["CVE-2025-54135", "CVE-2025-54136", "owasp-llm03"]),
    _r("aitools.mcp_unpinned", "aitools", "low", "user", "AI tool server without a pinned version",
       "{subject} starts the MCP server '{detail}' from a package with no fixed version, so whatever its author "
       "publishes next runs on every developer's machine.",
       f"{PB}#mcp-config", sources=["CVE-2025-54136", "owasp-llm03"]),
    _r("aitools.autorun", "aitools", "medium", "user", "Command that runs when the project is opened",
       "{subject} runs '{detail}' automatically (a hook or a task that starts when the folder opens). "
       "Make sure everyone on the project knows it's there and what it does.",
       f"{PB}#autorun", sources=["CVE-2025-59536", "CVE-2025-65099"]),
    _r("aitools.hidden_text", "aitools", "high", "agent", "Invisible characters in a file",
       "{subject} contains {detail}. People can't see it, but AI tools read it, so it can carry hidden instructions.",
       f"{PB}#hidden-text", sources=["CVE-2025-59145", "trojan-source", "owasp-llm01"]),
    _r("aitools.hidden_instructions", "aitools", "medium", "agent", "Hidden comment that talks to AI tools",
       "{subject} has a hidden comment that gives instructions to AI tools: \"{detail}\". Check who added it.",
       f"{PB}#hidden-text", sources=["CVE-2025-53773", "CVE-2025-59145", "owasp-llm01"]),
    _r("aitools.tool_poisoning", "aitools", "high", "agent", "Tool text that gives the AI hidden orders",
       "{subject} defines AI tools, and the text of a tool description or result gives the model instructions "
       "(\"{detail}\"). The AI follows these, and the user never sees them (tool poisoning).",
       f"{PB}#tool-poisoning", sources=["owasp-llm01", "mcp-tool-poisoning"]),
    # --- secrets -------------------------------------------------------------------------------------------
    _r("secrets.hardcoded", "secrets", "high", "agent", "Secret key in the code",
       "{subject} contains what looks like a real {detail}. Anyone who can read the code can use it, so after it's moved "
       "out of the code it also needs replacing (rotating) at the provider.",
       f"{PB}#secrets", sources=["cwe-798", "owasp-a07"]),
    _r("secrets.env_tracked", "secrets", "high", "agent", ".env file in git",
       "{subject} is committed to git, so every secret in it is in the repo history{detail}.",
       f"{PB}#secrets", sources=["cwe-538", "owasp-a05"]),
    _r("secrets.public_env", "secrets", "high", "agent", "Secret key sent to the browser",
       "{detail} The variable {subject} has a public prefix, so its value is built into the code every visitor downloads.",
       f"{PB}#public-env", sources=["cwe-200", "CVE-2025-48757"]),
    _r("secrets.weak_hash", "secrets", "medium", "agent", "Weak password hashing",
       "{subject} hashes passwords with {detail}, which can be cracked quickly. Use bcrypt, scrypt or argon2.",
       f"{PB}#password-hash", sources=["cwe-916", "owasp-a02"]),
    # --- data access ---------------------------------------------------------------------------------------
    _r("data.rls_off", "data", "high", "agent", "Database table anyone can read and change",
       "The Supabase table '{subject}' never turns on row level security (RLS). With the public key that ships in "
       "your site, anyone can read and change every row.",
       f"{PB}#supabase-rls", sources=["CVE-2025-48757", "owasp-a01", "supabase-rls"]),
    _r("data.policy_open", "data", "high", "agent", "Database rule that lets anyone write",
       "A Supabase policy on '{subject}' lets anyone {detail} rows (its rule is just 'true').",
       f"{PB}#supabase-rls", sources=["CVE-2025-48757", "owasp-a01", "supabase-rls"]),
    _r("data.firebase_open", "data", "high", "agent", "Firebase rules open to everyone",
       "{subject} {detail}, so anyone on the internet can read or write that data.",
       f"{PB}#firebase-rules", sources=["owasp-a01", "firebase-rules"]),
    _r("data.route_no_auth", "data", "medium", "agent", "API route that changes data without checking who's calling",
       "{subject} changes data ({detail}) but doesn't seem to check who is calling. Make sure it's meant to be public.",
       f"{PB}#route-auth", sources=["owasp-a01", "cwe-862"]),
    # --- injection -----------------------------------------------------------------------------------------
    _r("inject.shell", "injection", "high", "agent", "Shell command built from outside text",
       "{subject} runs a shell command built from changing text ({detail}). If any of that text comes from a user, "
       "a web page or an AI model, it can run its own commands on your machine.",
       f"{PB}#shell", sources=["cwe-78", "CVE-2025-53107", "CVE-2025-53967", "CVE-2025-53818"]),
    _r("inject.eval", "injection", "high", "agent", "Text run as code",
       "{subject} runs changing text as code with {detail}. Whoever controls that text controls your server.",
       f"{PB}#eval", sources=["cwe-95", "CVE-2024-12366"]),
    _r("inject.sql", "injection", "high", "agent", "Database query built by joining text",
       "{subject} builds a SQL query by pasting values into the text ({detail}). That's SQL injection: "
       "a crafted value can read or delete any data.",
       f"{PB}#sql", sources=["cwe-89", "owasp-a03", "CVE-2025-1793"]),
    _r("inject.llm_sql", "injection", "high", "agent", "AI-written database queries run as is",
       "{subject} lets an AI model write database queries that run directly ({detail}). A prompt-injection can make "
       "it write a query that deletes or leaks data.",
       f"{PB}#llm-sql", sources=["p2sql", "CVE-2024-8309", "CVE-2024-12911", "owasp-llm05"]),
    _r("inject.llm_exec", "injection", "high", "agent", "AI output run as code",
       "{subject} lets an AI model run code or commands ({detail}). Anyone who can get text in front of the model can "
       "run code on your server.",
       f"{PB}#llm-exec", sources=["CVE-2024-12366", "owasp-llm05", "owasp-llm06"]),
    # --- AI features ---------------------------------------------------------------------------------------
    _r("ai.injection_risk", "ai", "medium", "user", "AI reads outside content and can use tools",
       "Your AI feature reads content you don't control ({detail}) and can also use tools. Hidden instructions in that "
       "content could make it use those tools against you or your users. No code check can rule this out; decide "
       "which tools need a person to confirm.",
       f"{PB}#prompt-injection", sources=["owasp-llm01", "owasp-llm06", "lethal-trifecta"]),
    _r("ai.markdown_images", "ai", "medium", "agent", "AI replies can load images from any website",
       "{subject} shows AI replies as markdown and allows images from any address. A prompt-injection can hide your "
       "users' data in an image link and send it to an attacker's server.",
       f"{PB}#markdown-images", sources=["gitlab-duo", "owasp-llm05"]),
    _r("ai.browser_key", "ai", "high", "agent", "AI provider key used in the browser",
       "{subject} calls the AI provider straight from the browser ({detail}), so visitors can copy your API key.",
       f"{PB}#public-env", sources=["cwe-200", "owasp-llm02"]),
    # --- browser -------------------------------------------------------------------------------------------
    _r("xss.raw_html", "browser", "medium", "agent", "Changing text inserted as raw HTML",
       "{subject} inserts changing text as raw HTML ({detail}). If that text comes from users or an AI model, "
       "it can run JavaScript in other people's browsers.",
       f"{PB}#xss", sources=["cwe-79", "owasp-a03", "CVE-2026-41318"]),
    _r("xss.markdown_html", "browser", "medium", "agent", "Markdown allowed to contain raw HTML",
       "{subject} renders markdown with raw HTML turned on and no sanitizer ({detail}), so a message can carry "
       "a script.",
       f"{PB}#xss", sources=["cwe-79", "CVE-2026-41318", "owasp-llm05"]),
    _r("xss.no_csp", "browser", "low", "agent", "No Content-Security-Policy",
       "The site sends no Content-Security-Policy header, the browser setting that blocks injected scripts and limits "
       "where data can be sent.",
       f"{PB}#csp", sources=["owasp-csp", "owasp-llm05"]),
    # --- server --------------------------------------------------------------------------------------------
    _r("server.ssrf", "server", "medium", "agent", "Server fetches an address the caller chooses",
       "{subject} fetches a URL that comes from the request ({detail}). Someone can point it at your internal "
       "systems or cloud metadata (SSRF).",
       f"{PB}#ssrf", sources=["cwe-918", "owasp-a10"]),
    _r("server.path", "server", "medium", "agent", "File path built from the request",
       "{subject} opens a file using a name from the request ({detail}). Names like ../../ can reach files outside "
       "the folder (path traversal).",
       f"{PB}#path", sources=["cwe-22", "CVE-2024-37032"]),
    _r("server.redirect", "server", "low", "agent", "Redirect to an address from the request",
       "{subject} redirects to an address taken from the request ({detail}), which lets phishing links borrow "
       "your domain.",
       f"{PB}#redirect", sources=["cwe-601"]),
    _r("server.deserialize", "server", "medium", "agent", "Loading data that can run code",
       "{subject} loads data with {detail}, which runs any code hidden inside the file. Only load files you made.",
       f"{PB}#deserialize", sources=["cwe-502", "CVE-2025-68664"]),
    _r("server.cors", "server", "medium", "agent", "Any website can call your API as the user",
       "{subject} allows requests from any website and sends cookies with them, so other sites can act as your "
       "logged-in users.",
       f"{PB}#cors", sources=["cwe-942"]),
    _r("server.model_exposed", "server", "medium", "user", "AI model server open to the network",
       "{subject} publishes {detail} to every network interface. That server has no login, and exposed instances "
       "have been attacked.",
       f"{PB}#model-server", sources=["CVE-2024-37032", "CVE-2026-7482"]),
    # --- packages ------------------------------------------------------------------------------------------
    _r("pkg.not_found", "packages", "high", "agent", "Package that doesn't exist",
       "{subject} doesn't exist on {detail}. AI tools often invent package names like this; if someone registers it, "
       "the next install runs their code (slopsquatting).",
       f"{PB}#packages", sources=["slopsquatting", "owasp-llm03"]),
    _r("pkg.suspicious", "packages", "medium", "user", "Package that is brand new or barely used",
       "{subject} {detail}. Check it's the package you meant before trusting it.",
       f"{PB}#packages", sources=["slopsquatting", "owasp-llm03"]),
    _r("pkg.lookalike", "packages", "medium", "user", "Package name one letter off a popular one",
       "{subject} is one letter away from the popular package '{detail}'. Make sure it isn't a typo or a fake.",
       f"{PB}#packages", sources=["typosquatting", "owasp-llm03"]),
    _r("pkg.vulnerable", "packages", "high", "agent", "Package with a known security hole",
       "{subject} has a published security hole: {detail}",
       f"{PB}#vulnerable-packages", sources=["osv", "owasp-a06"]),
]}


@dataclass
class Finding:
    rule: str
    subject: str = ""
    detail: str = ""
    files: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    severity: str | None = None
    key: str = ""

    @property
    def fingerprint(self) -> str:
        ident = "|".join(x for x in (self.subject, self.key) if x)
        return f"{self.rule}|{ident}" if ident else self.rule

    def to_dict(self) -> dict:
        r = RULES[self.rule]
        ev = self.evidence[0] if self.evidence else ""
        return {
            "fingerprint": self.fingerprint, "rule": r.id, "group": r.group, "group_title": GROUPS[r.group],
            "severity": self.severity or r.severity, "who": r.who, "title": r.title,
            "plain": r.plain.format(subject=self.subject, detail=self.detail, evidence=ev),
            "subject": self.subject, "detail": self.detail, "files": self.files[:10], "evidence": self.evidence[:5],
            "fix": r.fix, "sources": list(r.sources),
        }
