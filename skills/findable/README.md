# findable

**Your coding agent finds why Google and AI tools can't see your site, and fixes it in your code.**

For the overview (how it works, what it catches, how it's different, real-site tests) see the [repo README](../../README.md). This page is the reference.

## What it checks

| Group | Checks |
|---|---|
| **Can Google and AI find your pages?** | robots.txt (missing, blocks everyone), `noindex` leaks (page or layout), sitemap (missing, wrong domain, missing pages, dead or redirecting URLs), broken pages, redirect chains, canonicals, pages nothing links to, pages Google isn't indexing (Search Console export) |
| **Can AI tools read your pages?** | AI search bots blocked in robots.txt, AI and search bots blocked by your CDN or firewall (tested with each bot's user agent against a browser), pages empty without JavaScript, `'use client'` pages |
| **How you show up in results** | titles and descriptions (missing, length, duplicated, inherited from the layout), main heading, short direct answers under question headings, structured data (missing, invalid, no Organization/WebSite on the homepage), image text descriptions, pages close to page one (Search Console export) |
| **Do AI answers mention you?** *(optional)* | your customers' questions run through your agent's web search: do you appear, and who appears instead |
| **Searches you could win** *(optional)* | keyword research with web search: searches you're missing, who wins them, the page that should target each |
| **Things only you can do** | Search Console setup, sitemap submission, CDN settings, with exact steps |

Low-impact items are folded into "Minor improvements" so the important ones stand out.

## Inputs

- **Your code:** Next.js (App and Pages Router) in depth; Astro, Nuxt, SvelteKit, Remix, Gatsby, Hugo, Jekyll and plain HTML through the live scan and generic fix guides. Monorepos and sites in folders like `web/` are detected.
- **Your live site:** up to 50 pages, 4 at a time, respecting robots.txt.
- **Optional, in `.findable/inputs/`:** Search Console exports (Page indexing, Performance), plus the results files the agent writes for AI visibility and keyword research.

## Results

Saved in `.findable/` in your project:
- `report.html`: the full report, grouped in plain language, with technical details per issue
- `findings.json`: each issue's state across runs (new, open, fixed, came back, dismissed)
- `config.json`: your confirmed site and URL
- `visibility.json`, `keywords.json`: the latest optional checks and their history
- `inputs/`: Search Console exports and search results

## Commands

The agent runs these for you. They're listed for reference and for running findable by hand from your project root (`CLI=path/to/skills/findable/cli`, then `uv run --project $CLI findable …`).

| Command | What it does |
|---|---|
| `findable plan` | Says which site and URL a scan would check, without scanning |
| `findable scan` | Scans code and live site, updates findings, writes the report |
| `findable report` | Shows the latest results without scanning |
| `findable verify --ids …` | Re-checks only what the given findings touch |
| `findable dismiss <id> --reason …` | Marks a finding as intentional |
| `findable visibility record\|show` | Stores or shows the AI visibility check |
| `findable keywords record\|show` | Stores or shows the keyword research |

Add `--json` for machine-readable output. Exit codes: `0` ok, `1` error, `2` verify found failures, `3` needs your input.

## Develop

```bash
cd skills/findable/cli   # from the repo root
uv run pytest
uv run findable scan --path ../../../tests/findable/fixtures/static-broken --url none
```

Real-site evals: `uv run --project skills/findable/cli python evals/findable/run.py` from the repo root.

To release, bump the version in `cli/pyproject.toml`, `cli/src/findable/__init__.py` and the root `.claude-plugin/marketplace.json`.

## Roadmap

A rendered-page check (what a real browser shows vs. the raw HTML), page speed, IndexNow, and more framework fix guides (Astro, Nuxt, SvelteKit, WordPress).
