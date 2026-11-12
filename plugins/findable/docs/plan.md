# findable — plan (lean v1)

Status: **v1 built (M1–M4), not yet published or tested on a real site** · 2026-11-11

> **Distribution changed (2026-11-12):** findable ships as a Claude Code plugin in the `stayonweb` marketplace repo, not on PyPI or npm. The Python CLI lives inside the skill folder (`skills/findable/cli/`) and the skill runs it with `uv run --project`. The `install` command and the npm wrapper were removed. The file tree in §5 shows the original packaging; see `../README.md` for the current layout.

## 1. One job

> **Can Google and AI engines find, read and cite my site? Fix what blocks it.**

findable is a Python tool plus a skill that installs into your coding agent (Claude Code, Codex). It runs inside your project and needs no accounts or API keys. It scans the code and the live site, asks you only when there's a real choice, fixes what you pick as a reviewable diff, and verifies the fix.

## 2. User flow

Install → `/findable` → answer ≤2 questions → scan → report → pick fixes → review diff → verify → deploy → the next run confirms.

```
/plugin marketplace add <github-owner>/stayonweb
/plugin install findable@stayonweb
```
Then type `/findable` in your agent.

## 3. What v1 does

### 3.1 Scans (no keys)

**Code scan:** reads the repo, offline.
| Rule id | Checks |
|---|---|
| `seo.title` / `seo.description` | Missing, duplicate, or wrong length, per route |
| `seo.canonical` | Missing, or pointing to another page by mistake |
| `seo.noindex_leak` | `noindex` on pages that should be indexed |
| `seo.robots` | robots.txt missing or blocking important paths |
| `seo.sitemap` | Sitemap missing, or missing routes / including dead ones |
| `aeo.schema` | JSON-LD missing or invalid (Organization, Article, Product, FAQ, Breadcrumb) |
| `aeo.headings` | No single H1; question-style headings without a direct answer below |
| `geo.client_rendered` | Page content only appears after JavaScript runs, so it's invisible to most AI crawlers |
| `seo.alt` | Content images without alt text |
| `seo.orphan` | Routes nothing links to |

**Live scan:** plain HTTP to the URL you choose (production or local dev).
| Rule id | Checks |
|---|---|
| `seo.status` | 4xx/5xx and redirect chains on sitemap and linked pages |
| `geo.bot_access` | Fetches as `GPTBot`, `OAI-SearchBot`, `PerplexityBot`, `ClaudeBot`, `Google-Extended`, `Bingbot`, and flags 403/challenge responses (CDN/WAF blocks) |
| `geo.no_js_view` | HTML returned without JS is empty or missing the main content |
| `seo.sitemap_live` | Sitemap URLs that redirect or 404 |

**Optional Search Console CSV:** drop an export into `.findable/inputs/`.
| Rule id | Checks |
|---|---|
| `seo.striking_distance` | Queries at position 8–20 with impressions, joined to the page's other findings |

### 3.2 Questions (asked only when there are ≥2 real options; recommended option first)

| # | When | Options |
|---|---|---|
| Q1 | Monorepo with several sites | Which app to scan |
| Q2 | Several URLs found, or the dev server isn't running | Production / staging / local (start dev server) / code scan only |
| Q3 | After the report | Which findings to fix (multi-select) |
| Q4 | A finding has more than one fix, or conflicts with existing setup | e.g. server-render vs. pre-render; patch your sitemap generator vs. replace it |

- Answers to Q1–Q2 are remembered in `.findable/config.json` and asked again only if the app or URL disappears.
- Claude Code uses its multiple-choice dialog; Codex uses a numbered list.

### 3.3 Missing → suggest

If something only you can do is missing, it goes to the top of the report as **"Do these first"**, with exact steps. The scan continues with everything else.

| Detected | Suggestion |
|---|---|
| No Search Console verification | How to verify (meta tag or DNS); the agent can add the meta tag |
| Sitemap not submitted | Submit it in Search Console and Bing Webmaster (Bing can import from GSC) |
| AI bots blocked at the CDN | The exact Cloudflare/Vercel/Netlify setting. You change it, since it's a security setting |
| No Search Console CSV | How to export one, to unlock striking distance |

### 3.4 Fix and verify

1. You pick findings (Q3) and variants (Q4).
2. The agent applies fixes using the playbooks and shows the diff.
3. `findable verify` re-runs only the affected checks; up to 2 retries, then it reports what still fails.
4. The agent never commits, deploys, signs in anywhere, or changes CDN/dashboard settings.

### 3.5 Output

**Terminal summary (≤ 6 lines):**
```
example.com · 84 pages · code + live scanned (no GSC CSV)
Since last run: 3 fixed ✓ · 1 regressed ✗ · 2 new
Do these first:
  1. ✗ Cloudflare returns 403 to OAI-SearchBot, PerplexityBot      — you, 2 min
  2. ✗ /pricing content is client-rendered (empty without JS)       — auto-fix
Report: .findable/report.html
```

**HTML report:** one page with "Do these first", then findings grouped by page. Each finding shows URL · file:line · current value → target value · evidence · fix · status.

**Finding format:**
```json
{"id":"geo.client_rendered","url":"/pricing","file":"app/pricing/page.tsx:12",
 "current":"0 words in HTML without JS","target":"main content server-rendered",
 "severity":"high","auto_fixable":true,"status":"new"}
```

### 3.6 State: one lifecycle only

Findings are tracked across runs by `rule id + URL`:

`new → open → fixed → (regressed → open)` · `open → dismissed` (you give a reason; it isn't raised again)

Everything else (whether the live site was reachable, whether a CSV was present) is a plain status field in the run output, not a state machine.

## 4. File structure

```
findable/                          # one repo
├── pyproject.toml                 # package metadata, deps, `findable` command entry point
├── README.md                      # what it does, install, quickstart
├── src/findable/
│   ├── __init__.py                # package version
│   ├── __main__.py                # allows `python -m findable`
│   ├── cli.py                     # commands: install | scan | report | verify | uninstall
│   ├── install.py                 # copies skill/ into .claude/skills/ and .agents/skills/ (+ AGENTS.md pointer)
│   ├── detect.py                  # framework, apps in a monorepo, routes → URLs
│   ├── ask.py                     # emits a question as JSON when there are ≥2 options
│   ├── scan_code.py               # code rules from §3.1
│   ├── scan_live.py               # live rules from §3.1 (httpx, polite, domain-limited)
│   ├── gsc_csv.py                 # optional Search Console CSV → striking distance
│   ├── rules.py                   # facts → findings, severity, priority
│   ├── findings.py                # lifecycle across runs (§3.6), stored in .findable/findings.json
│   ├── suggest.py                 # missing setup → "Do these first" items
│   ├── report.py                  # terminal summary + HTML page
│   ├── verify.py                  # re-runs only the checks a fix touched
│   ├── templates/report.html      # Jinja template for the report
│   └── skill/                     # shipped inside the package; `findable install` copies it
│       ├── SKILL.md               # trigger + flow: detect → ask → scan → report → fix/verify
│       ├── references/
│       │   ├── checks.md          # every rule: what, why, threshold
│       │   ├── ai-bots.md         # AI crawler user agents, search vs. training
│       │   ├── schema.md          # JSON-LD templates per page type
│       │   └── safety.md          # never commit, deploy, sign in or change settings
│       ├── playbooks/
│       │   ├── nextjs.md          # Next.js fix recipes
│       │   └── generic.md         # any-framework recipes the agent adapts
│       └── suggestions.md         # all user-only steps from §3.3
├── npm/
│   ├── package.json               # npm name `findable`, same version as pyproject
│   └── bin/findable.js            # checks for uv (suggests install if missing), runs `uvx <pypi-name>==<ver> …`
└── tests/
    ├── fixtures/                  # tiny sites: Next.js, plain HTML, monorepo, broken-on-purpose
    ├── test_rules.py              # each rule against the fixtures
    └── test_e2e.py                # scan → fix → verify on a fixture
```

**Per-project output:** `.findable/config.json` · `findings.json` · `report.html` · `last-run.json` · `inputs/` (optional CSV)

**Dependencies:** `typer`, `httpx`, `selectolax`, `extruct` (JSON-LD), `protego` (robots.txt), `jinja2`.

## 5. Milestones

| M | Scope | Done when |
|---|---|---|
| M1 | Package + npm wrapper + `install` + `detect` + `ask` | `npx findable install` puts the skill in Claude Code and Codex; a monorepo fixture triggers Q1 |
| M2 | Code scan + rules + report + findings store | Next.js fixture gives a report with file:line evidence; re-running marks fixed/regressed correctly |
| M3 | Live scan + suggestions | A fixture server that 403s AI bots is caught and shows up in "Do these first" |
| M4 | Fix + verify + playbooks + GSC CSV | End-to-end on a real site: scan → pick → diff → verify passes |

## 6. v2 roadmap (cut from v1 on purpose)

| Feature | Why later |
|---|---|
| Reading GSC/Bing dashboards through the agent's browser | Fragile when dashboards change; Codex has no browser. The CSV covers the main need |
| AI visibility via web search (who gets cited) | Noisy and directional; ship after the core works |
| Core Web Vitals (Playwright + web-vitals, optional Lighthouse) | Small ranking weight; adds Chromium to the install |
| IndexNow ping after deploy | Nice to have |
| More playbooks (Astro, Nuxt, SvelteKit, WordPress…) | The generic playbook covers them in v1 |
| Pillar scores (SEO/AEO/GEO 0–100) and trend history | Needs several runs of real data to be meaningful |
| Clarity, Google Alerts | Dropped: UX/brand monitoring, not findability. Alerts stays as one suggestion line |

## 7. Open decisions

- **D1 PyPI name:** resolved: no PyPI/npm package; findable ships in the stayonweb plugin marketplace.
- **D2 Agents:** Claude Code + Codex (recommended) · add Cursor later
- **D3 First real site** to test M4 on
