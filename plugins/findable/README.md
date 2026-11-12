# findable

**Can Google and AI engines find, read and cite your site? findable shows what blocks them and fixes it.**

findable is a skill for your coding agent (Claude Code, Codex) with a bundled CLI. It runs inside your project with **no accounts and no API keys**:

- **Code scan:** titles, descriptions, canonicals, `noindex` leaks, robots.txt, sitemap, JSON-LD, headings, alt text, orphan pages, client-rendered pages (invisible to most AI crawlers)
- **Live scan:** status codes, redirect chains, sitemap health, empty-without-JavaScript pages, and an **AI-bot access test** (GPTBot, OAI-SearchBot, PerplexityBot, ClaudeBot, Bingbot…) that catches CDN/WAF blocks
- **Optional Search Console CSV:** striking-distance pages (positions 8–20), joined with each page's other issues

When there's more than one reasonable option, it asks. When something only you can do is missing, it tells you exactly how. It applies fixes as a reviewable diff and verifies them. It never commits or deploys.

Needs [uv](https://docs.astral.sh/uv/) (the skill runs the bundled CLI with `uv run`).

## Install

**Claude Code** (from the stayonweb marketplace, see the repo README):

```
/plugin install findable@stayonweb
```

**Codex:** copy `skills/findable/` into your project's `.agents/skills/` (or `~/.agents/skills/` for all projects).

## Use

In Claude Code type `/findable:findable`, or just ask "check my SEO" / "run findable". In Codex ask "run findable".

The CLI also runs on its own, from your project root:

```bash
CLI=path/to/skills/findable/cli
uv run --project $CLI findable scan                     # asks (exit 3 + JSON) if it needs a choice
uv run --project $CLI findable scan --url https://example.com
uv run --project $CLI findable scan --url none          # code scan only
uv run --project $CLI findable verify --ids "seo.title|/pricing"
uv run --project $CLI findable report
uv run --project $CLI findable dismiss "seo.canonical|/tag" --reason "tag pages are intentionally canonicalised"
```

Results go to `.findable/` in your project:
- `report.html`: the report
- `findings.json`: findings with their state across runs (new → open → fixed / regressed / dismissed)
- `config.json`: your remembered answers
- `last-run.json`: raw facts from the last scan
- `inputs/`: drop a Search Console export here

## Layout

```
plugins/findable/
├── .claude-plugin/plugin.json
├── skills/findable/       # what gets installed: SKILL.md, references, playbooks
│   └── cli/               # the Python CLI (pyproject, uv.lock, src/findable)
├── tests/                 # pytest + fixture sites (not used at runtime)
└── docs/plan.md           # plan and v2 roadmap
```

## Develop

```bash
cd skills/findable/cli
uv sync
uv run pytest
uv run findable scan --path ../../../tests/fixtures/static-broken --url none
```

Release: bump `version` in `.claude-plugin/plugin.json`, `skills/findable/cli/pyproject.toml` and `skills/findable/cli/src/findable/__init__.py` (all three must match), and the plugin's entry in the root `.claude-plugin/marketplace.json`.
