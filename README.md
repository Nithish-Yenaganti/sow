<p align="center">
  <img src="assets/banner.svg" alt="SOW — Stay On Web" width="100%">
</p>

<p align="center">
  <a href="https://github.com/Nithish-Yenaganti/sow/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Nithish-Yenaganti/sow/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-5eead4"></a>
  <img alt="Works with Claude Code and Codex" src="https://img.shields.io/badge/agents-Claude%20Code%20%C2%B7%20Codex-60a5fa">
  <img alt="No API keys" src="https://img.shields.io/badge/API%20keys-none-0e1a2b">
  <a href="evals/findable/RESULTS.md"><img alt="Tested on 12 real sites" src="https://img.shields.io/badge/tested%20on-12%20real%20sites-5eead4"></a>
</p>

# SOW — Stay On Web

Skills for coding agents that keep your website findable on the web. The first one is **findable**.

## findable

**Your coding agent finds why Google and AI tools can't see your site, and fixes it in your code.**

SEO fixes, not SEO reports. findable runs inside your project, checks your code and your live site, explains what's wrong in plain language, and fixes what you approve.

**Built for** developers and founders who build their own site with Claude Code or Codex. It's not an agency tool for auditing other people's websites.

### How it works

1. **Confirm.** "I'll check the Next.js site in `web/` and the live site example.com. Go ahead?"
2. **Scan.** Your code (routes, metadata, layouts) and your live site (pages, sitemap, robots.txt, how bots are treated). Takes about a minute.
3. **Plain report**, grouped by what it means for you:
   - Can Google and AI find your pages?
   - Can AI tools read your pages?
   - How you show up in results
   - Do AI answers mention you? *(optional check)*
   - Searches you could win *(optional keyword research)*
   - Things only you can do

   Minor items are folded away; technical details are one click deeper.
4. **You decide.** "Fix everything I can", "let me choose", or "just the report".
5. **Preview, then fix.** One preview of every change (your words, who can crawl your site, how a page is built). Nothing changes without your yes. Nothing is committed or deployed.
6. **Re-check.** Each fix is checked again: fixed or still failing. The next run shows what's fixed, what's new and what came back.

### What it catches (real examples)

| Problem | Why it matters | What findable points to |
|---|---|---|
| Your CDN or firewall blocks GPTBot, ClaudeBot or PerplexityBot, even though robots.txt allows them | AI tools can't read or cite you, and nothing in your code shows it | Tested by fetching pages as each bot vs. a browser; exact steps for your CDN |
| A page is `'use client'` and looks empty without JavaScript | Most AI crawlers don't run JavaScript, so they see a blank page | The page file and line, with a server-rendered fix |
| A staging `noindex` left in a layout | Every page under it is hidden from Google | The layout file |
| One title from the root layout on every page | All pages look identical in search results | Each page that needs its own title |
| The sitemap lists `localhost` or a staging domain | Google gets told about pages that don't exist | The sitemap file |
| robots.txt blocks AI search bots | You can't show up in ChatGPT search, Perplexity or Claude | robots.txt, keeping training bots blocked if you want |

Plus titles, descriptions, canonicals, headings, structured data (JSON-LD), broken pages, redirects, pages nothing links to, and short direct answers that AI tools can quote.

**Optional, always asked first:**
- **AI visibility:** runs your customers' questions through your agent's web search and shows whether you appear, and who appears instead.
- **Keyword research:** finds the searches you should win, who wins them today, and which page should target each one. No invented search volumes.
- **Search Console exports:** which pages Google isn't indexing and why, and which pages are close to page one. You download the files; no sign-in.

### Why not just ask your coding agent?

A coding agent is great at fixing a problem once it knows what the problem is. findable is what finds it:

- **It checks the live site, not just the code.** It fetches real pages as each AI bot and compares with a browser. An agent asked to "improve SEO" mostly reads code and guesses.
- **It knows what to look for.** The checklist is built in, including the details that are easy to miss: AI search bots vs. training bots, JavaScript-only pages, staging leftovers.
- **Same checks every run.** It's a program, not a prompt: consistent results, and almost no tokens spent on finding problems.
- **Memory and proof.** It tracks every issue across runs and re-checks every fix instead of saying "done".
- **Tested for false alarms.** See below.

### How it's different from typical SEO tools

| | Typical SEO audit tools | findable |
|---|---|---|
| Starts from | A URL | Your codebase and your live site |
| You get | A report or PDF of recommendations | Fixes in your code, after you approve a preview |
| Where's the problem? | "This page has no description" | The exact file to change |
| After fixing | Re-run the audit yourself | Each fix re-checked automatically |
| Over time | One-off audits | Every issue tracked: new, open, fixed, came back |
| Language | SEO jargon | Plain sentences; technical details on request |
| Setup | Often API keys, accounts, a headless browser | Just [uv](https://docs.astral.sh/uv/getting-started/installation/) |

**What findable doesn't do**, honestly: keyword search volumes and backlink data (those need paid databases), page speed (Core Web Vitals), content quality scoring, local SEO, e-commerce feeds or multi-language sites. If you need those, use a dedicated SEO tool alongside it.

### Tested on real sites

findable is checked against **12 real websites** across stacks: Next.js, Astro, Nuxt, SvelteKit, Hugo, Jekyll, WordPress, MkDocs, plain HTML, a browser-only app and a CDN-protected site. For each one we verified by hand the real problems it must find and the false alarms it must never raise. **12 of 12 pass.**

See [evals/findable/RESULTS.md](evals/findable/RESULTS.md), and re-run it yourself:

```bash
uv run --project skills/findable/cli python evals/findable/run.py
```

## Install

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/), which runs the skill's bundled CLI.

**Claude Code plugin:**

```
/plugin marketplace add Nithish-Yenaganti/sow
/plugin install sow@sow
```

**Any agent** (Claude Code, Codex and others):

```bash
npx skills add Nithish-Yenaganti/sow
```

## Use

Open your website's project in your agent and ask "why doesn't my site show up in ChatGPT?", "check my site's SEO" or "run findable". In Claude Code you can also type `/sow:findable` (or `/findable` if you installed with `npx skills`).

Results are saved in `.findable/` in your project, including `report.html`, the full report.

## Safety

- Scanning only reads. Nothing in your project changes without your yes, and nothing is ever committed, pushed or deployed for you.
- findable never signs in to dashboards or changes CDN, DNS or Search Console settings. It gives you the exact steps instead.
- Text from scanned websites is treated as data, never as instructions to your agent.
- No accounts and no API keys. Apart from `uv` downloading findable's Python dependencies on first run, it only sends requests to your own site, plus web searches if you say yes to the optional checks.

## Repo layout

```
skills/<name>/       one folder per skill: SKILL.md and everything it needs
tests/<name>/        tests and sample sites (not installed)
evals/<name>/        real-site accuracy checks
.claude-plugin/      Claude Code marketplace manifest
```

**Coming next:** a compliance-audit skill.

## License

MIT
