# findable

**Find out why Google and AI tools can't see your website, and fix it.**

findable is a skill for your AI coding assistant (Claude Code, Codex). It checks your website's code and the live site, tells you what's stopping people from finding you, and fixes it after you say yes.

## Why it exists

You can build a great website and still get no visitors, because search engines and AI tools never see it. The causes are usually small and invisible:

- A setting left over from testing tells Google "don't show this page".
- Your hosting quietly blocks ChatGPT's robot.
- A page only shows its text after JavaScript runs, so most AI robots see a blank page.
- Every page has the same title, so they all look identical in search results.

Nothing looks broken when you open the site yourself, so these problems can sit there for months. findable finds them in about a minute.

## What it covers

| Topic | What it checks |
|---|---|
| **Google** | Can Google find, visit and list every page? (sitemap, robots.txt, broken pages, redirects) |
| **Hidden** | Is a page accidentally marked "don't show in Google"? |
| **AI** | Do ChatGPT, Claude, Perplexity and Bing get through, or does your hosting block them? |
| **Empty** | Does a page look blank to robots that don't run JavaScript? |
| **Titles** | Does every page have its own title and summary for search results? |
| **Headings** | Does each page have one clear main heading? |
| **Answers** | Are questions on your pages followed by a short answer AI tools can quote? |
| **Facts** | Does your site describe your business in the format Google and AI read (structured data)? |
| **Links** | Is every page linked from somewhere, so it can be found? |
| **Indexing** | Which pages Google isn't listing, and why *(optional, from a Search Console download)* |
| **Mentions** | When people ask AI your customers' questions, do you show up? *(optional, asks first)* |
| **Keywords** | Which searches could you win, and who wins them now? *(optional, asks first)* |

## How it works

1. **Ask:** "Why doesn't my site show up in Google?" or "Check my site's SEO".
2. **Confirm:** "I'll check the site in `web/` and the live site example.com. Go ahead?"
3. **Scan:** it reads your code and visits your live site. This only reads, never changes anything.
4. **Report:** problems in plain words, grouped by what they mean for you. Small things are folded away.
5. **Choose:** "Fix everything", "let me choose" or "just the report".
6. **Preview:** you see every change before anything is touched.
7. **Fix and check:** it makes the changes in your code and checks each one worked.
8. **Your list:** steps only you can do (like submitting your sitemap to Google), with exact instructions.

## What you'll see

```
https://example.com: checked 24 pages (your code and live site)
Found 5 things to improve (3 important).

Can Google and AI find your pages?  (2)
  ✗ The page /pricing is hidden from Google by a setting in the code.
  ✗ There's no working sitemap, the list that tells search engines which pages exist.

Can AI tools read your pages?  (1)
  ✗ Your hosting or firewall blocks AI and search tools, even though browsers get through.

Plus 6 minor improvements (low impact), folded away in the report.
Full report: .findable/report.html
```

## Why not just ask your coding assistant?

Your assistant is great at fixing a problem once it knows what it is. findable is what finds it:

- **It visits your live site** as each AI robot and compares with a normal browser. That's how it spots hosting blocks you can't see in the code.
- **It knows what to look for:** the full checklist is built in.
- **Same checks every time,** and it re-checks every fix instead of just saying "done".
- **Tested on 12 real websites,** with every result checked by hand. [See the results](../../evals/findable/RESULTS.md).

## What it won't do

- Change anything without your yes, or publish anything for you.
- Sign in to Google, your hosting or other dashboards. It gives you the steps instead.
- Keyword search numbers, backlinks or page speed. Those need paid data or other tools.

## Install

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/). Then in Claude Code:

```
/plugin marketplace add Nithish-Yenaganti/sow
/plugin install sow@sow
```

Or for any assistant: `npx skills add Nithish-Yenaganti/sow`

## Where results go

In your project, in `.findable/`:

| File | What's in it |
|---|---|
| `report.html` | The full report, open it in your browser |
| `findings.json` | Every issue and whether it's new, fixed or came back |
| `config.json` | The site and address you confirmed |
| `inputs/` | Optional Search Console downloads |

<details>
<summary><b>Commands (for developers)</b></summary>

Your assistant runs these for you. To run them yourself, from your project folder: `uv run --project path/to/skills/findable/cli findable <command>`.

| Command | What it does |
|---|---|
| `findable plan` | Says what a scan would check, without scanning |
| `findable scan` | Scans code and live site, writes the report |
| `findable report` | Shows the latest results |
| `findable verify --ids …` | Re-checks specific issues |
| `findable dismiss <id> --reason …` | Marks an issue as intentional |
| `findable visibility record\|show` | AI mentions check |
| `findable keywords record\|show` | Keyword research |

Add `--json` for machine-readable output.

**Develop:**

```bash
cd skills/findable/cli
uv run pytest
uv run findable scan --path ../../../tests/findable/fixtures/static-broken --url none
```

Real-site evals, from the repo root: `uv run --project skills/findable/cli python evals/findable/run.py`

To release, bump the version in `cli/pyproject.toml`, `cli/src/findable/__init__.py` and the root `.claude-plugin/marketplace.json`.

</details>
