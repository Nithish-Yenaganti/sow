"""Run every check. Reads the project only; network only when online=True (package names and versions)."""

from __future__ import annotations

from pathlib import Path

from guarded import checks_code, checks_config, deps
from guarded.project import load
from guarded.rules import RULES, Finding


def scan(root: Path, online: bool = False, fetch=None) -> dict:
    pj = load(root)
    findings: list[Finding] = checks_config.run(pj) + checks_code.run(pj)
    pkg_findings, pkg_meta = deps.check(pj, online, fetch)
    findings += pkg_findings
    # Same fingerprint twice (two rules can land on one line) → keep the first.
    seen, unique = set(), []
    for f in findings:
        if f.fingerprint not in seen:
            seen.add(f.fingerprint)
            unique.append(f)
    online_rules = {"pkg.not_found", "pkg.suspicious", "pkg.vulnerable"}
    scope = {r for r in RULES if online or r not in online_rules}
    return {"findings": unique, "files_scanned": len(pj.files), "packages": pkg_meta, "scope": scope,
            "stack": _stack(pj)}


def _stack(pj) -> list[str]:
    s = []
    for name, pkgs in (("Next.js", ("next",)), ("React", ("react",)), ("Vue", ("vue",)), ("Svelte", ("svelte",)),
                       ("Express", ("express",)), ("Supabase", ("@supabase/supabase-js", "supabase")),
                       ("Firebase", ("firebase", "firebase-admin")), ("Prisma", ("prisma", "@prisma/client")),
                       ("LangChain", ("langchain", "@langchain/core", "langchain-core")),
                       ("MCP server", ("@modelcontextprotocol/sdk", "mcp", "fastmcp")),
                       ("Flask", ("flask",)), ("Django", ("django",)), ("FastAPI", ("fastapi",)),
                       ("OpenAI", ("openai",)), ("Anthropic", ("@anthropic-ai/sdk", "anthropic")),
                       ("Vercel AI SDK", ("ai",))):
        if pj.has_pkg(*pkgs):
            s.append(name)
    return s
