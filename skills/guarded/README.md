# guarded

**Find the security holes AI-built apps tend to ship, and fix them.**

guarded is a skill for your AI coding assistant (Claude Code, Codex). It reads your code and config, explains what looks risky in plain words, and fixes only what you agree to.

> **It is a code check, not a penetration test.** It looks for known risky patterns. It never attacks anything, never runs your code, and never says your app is "secure". Every finding says why it was flagged and which real incident or standard it's based on.

## Why it exists

AI writes most of the code in a lot of new apps now, and the same mistakes keep coming back:

- A database query built by pasting in what the user typed (**SQL injection**).
- Text from users or from the AI shown as raw HTML (**XSS**).
- A shell command built from a tool's input, so whoever controls the input runs commands (the bug behind several 2025 MCP server CVEs).
- An API key pasted into the code, or put in a `NEXT_PUBLIC_` variable that ships to every visitor.
- Supabase tables with **row level security** off, so anyone can read and change every row (CVE-2025-48757 hit about 170 Lovable apps).
- An AI feature that reads web pages or documents **and** can use tools, which is what **prompt injection** needs.
- AI replies shown as markdown with images allowed from anywhere, a known way to leak data.
- Files that take over AI coding tools: an auto-approve setting, a risky `.cursor/mcp.json`, a hook, or **invisible instructions** hidden in a README (Copilot, Cursor and Claude Code all had CVEs like this).
- **Made-up packages**: AI tools invent package names, and attackers register them (slopsquatting).

guarded catches these early.

## What it checks

| Topic | What it looks for |
|---|---|
| **AI coding tools** | Auto-approve settings, risky or unpinned MCP servers, hooks and tasks that run on their own, invisible characters and hidden comments that talk to AI tools, MCP tool descriptions with hidden orders (tool poisoning) |
| **Secret keys** | Keys in code, `.env` files in git, server secrets in browser variables, weak password hashing |
| **Your data** | Supabase tables without RLS, policies that let anyone write, open Firebase rules, API routes that change data without checking who's calling |
| **Injection** | SQL built from strings, shell commands built from input, `eval`, AI-written SQL or code run as is |
| **AI features** | Prompt-injection risk (outside content + tools), AI replies that can load any image, AI keys used in the browser |
| **Browser (XSS)** | Raw HTML from changing values, markdown with raw HTML on, no Content-Security-Policy |
| **Server** | Fetching any URL the caller gives (SSRF), file paths from the request, open redirects, `pickle`/`torch.load`, wide-open CORS, exposed Ollama ports |
| **Packages** *(optional, online)* | Packages that don't exist, are brand new or barely used, look one letter off a popular one, are known malware, or have published CVEs (via the free [OSV](https://osv.dev) database) |

Every check in plain words: [references/checks.md](references/checks.md). The source behind each one (OWASP, CWE and real CVEs): [references/sources.md](references/sources.md).

## How it works

1. **Ask:** "Is my app secure?" or "Check this repo for vulnerabilities".
2. **One question:** whether to also check your packages online. Only package names and versions are sent, to npm, PyPI and OSV. No accounts, no API keys.
3. **Scan:** it reads your code and config. Nothing runs and nothing changes.
4. **Report:** what it found, most serious first, in plain words, with the file and line.
5. **One approval:** one list of every fix. Nothing changes until you say yes.
6. **Fix and check:** it makes the smallest change in your code's own style, then re-scans to check each fix worked.
7. **Hand-over:** what's fixed, and what only you can do (like rotating a leaked key).

## Tested on real projects

Tested on 14 open-source projects at fixed versions, with 95 expected results checked by reading the code:
- 3 MCP servers at the commit just before their published CVE fix (CVE-2025-53107, CVE-2025-53967, CVE-2025-53818). It finds each bug. Two of them are also scanned at the fix commit, where the finding goes away.
- OWASP Juice Shop and two deliberately vulnerable AI projects (an LLM agent and 15 MCP server challenges).
- 6 production templates (Vercel's AI chatbot, Next.js SaaS starters, Supabase apps, a Shopify store), with no false alarms among the expected-clean checks.

[See the results](../../evals/guarded/RESULTS.md).

## What it won't do

- Attack, scan or log in to anything, or run your code. It only reads files.
- Say your app is "secure". A clean report means these checks found nothing, not that there's nothing to find.
- Change anything without your approval, or commit and publish anything for you.
- Rotate keys or change dashboards (Supabase, Firebase, hosting). It tells you the steps.
- Follow instructions it finds in your files. Finding hidden instructions is one of its checks.

## Install

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/). Then in Claude Code:

```
/plugin marketplace add Nithish-Yenaganti/sow
/plugin install sow@sow
```

Or for any assistant (needs Node.js 22.20 or newer): `npx skills add Nithish-Yenaganti/sow -g`

## Where results go

In your project, in `.guarded/` (git-ignored automatically):

| File | What's in it |
|---|---|
| `report.md` | The full report, with the file, line and source behind each finding |
| `findings.json` | Findings across runs (new, open, fixed, dismissed, suppressed) |
| `cache.json` | Package lookups from the last day (online mode only) |

<details>
<summary><b>Commands (for developers)</b></summary>

Your assistant runs these for you. To run them yourself, from your project folder: `uv run --project path/to/skills/guarded/cli guarded <command>`.

| Command | What it does |
|---|---|
| `guarded scan [--online] [--sarif FILE]` | Reads the project and writes the report (and SARIF, if asked) |
| `guarded report [--sarif FILE]` | Shows the latest results |
| `guarded verify --ids …` | Re-checks specific fixes (exit 2 if any still fail or were only silenced) |
| `guarded dismiss <id> --reason …` | Marks a finding as intentional or a false alarm |
| `guarded rules` | Lists every check |

Add `--json` for machine-readable output.

**Silence a false alarm for the whole team.** `dismiss` is stored in `.guarded/`, which is git-ignored, so it stays on
your machine. To record the decision in the code, where reviewers and CI see it, add a comment on the line, or the line
above, naming the rule (like `# nosemgrep` or `# nosec`):

```js
db.query(sql) // guarded-ignore[inject.sql] built from constants only
```

A rule id is required, and the comment is ignored for the `aitools.*` checks, because whoever plants instructions
for AI tools in a file could plant the comment too. Silenced places are still listed in the scan output.

**GitHub code scanning.** `guarded scan --sarif guarded.sarif` writes SARIF 2.1.0, ready for
`github/codeql-action/upload-sarif`, so findings show up as alerts on pull requests.

**Develop:**

```bash
cd skills/guarded/cli
uv run pytest
```

Tests build their sample projects at runtime, so the repo never holds fake keys or risky AI-tool configs.

**Evals:** [evals/guarded](../../evals/guarded) scans 14 open-source projects at pinned commits and checks hand-verified expectations (`must`, `must_not`, `online_must`, and `known_gaps`). It runs weekly in CI and on demand, from the repo root:

```bash
uv run --project skills/guarded/cli python evals/guarded/run.py           # summary
uv run --project skills/guarded/cli python evals/guarded/run.py --show    # every finding
uv run --project skills/guarded/cli python evals/guarded/run.py --online  # also packages (npm, PyPI, OSV)
```

When the eval finds a false alarm or a miss, fix the scanner and add a test to `tests/guarded/`.

To release, bump the version in `cli/pyproject.toml`, `cli/src/guarded/__init__.py` and the root `.claude-plugin/marketplace.json`.

</details>
