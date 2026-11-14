# findable

**Can Google and AI engines find, read and cite your site? findable shows what blocks them and fixes it.**

No accounts, no API keys. It scans:

- **Your code:** titles, descriptions, canonicals, `noindex` leaks, robots.txt, sitemap, JSON-LD, headings, alt text, orphan pages, and client-rendered pages that AI crawlers can't read
- **Your live site:** status codes, redirects, sitemap health, pages that are empty without JavaScript, and whether AI bots (GPTBot, PerplexityBot, ClaudeBot…) get blocked by your CDN
- **Search Console export** *(optional)*: pages ranking 8–20 that are close to page one
- **AI visibility** *(optional, asks first)*: runs your key questions through your agent's web search and shows whether you appear, and who appears instead

Then it asks which fixes you want, applies them as a diff you review, and re-checks them. It never commits or deploys.

## Install

See the [repo README](../../README.md). Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

## Results

Saved in `.findable/` in your project:
- `report.html`: the full report, page by page
- `findings.json`: each finding's state across runs (new, open, fixed, regressed, dismissed)
- `config.json`: your remembered answers
- `inputs/`: put a Search Console export here

## Develop

```bash
cd skills/findable/cli   # from the repo root
uv run pytest
uv run findable scan --path ../../../tests/findable/fixtures/static-broken --url none
```

To release, bump the version in `cli/pyproject.toml`, `cli/src/findable/__init__.py` and the root `.claude-plugin/marketplace.json`.

## Roadmap

Core Web Vitals, AI citation checks, IndexNow, more framework playbooks (Astro, Nuxt, SvelteKit, WordPress).
