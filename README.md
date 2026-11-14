<p align="center">
  <img src="assets/banner.svg" alt="SOW — Stay On Web" width="100%">
</p>

<p align="center">
  <a href="https://github.com/Nithish-Yenaganti/sow/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Nithish-Yenaganti/sow/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-5eead4"></a>
  <img alt="Works with Claude Code and Codex" src="https://img.shields.io/badge/agents-Claude%20Code%20%C2%B7%20Codex-60a5fa">
  <img alt="No API keys" src="https://img.shields.io/badge/API%20keys-none-0e1a2b">
</p>

# SOW — Stay On Web

**Two skills for your coding agent: one makes your website easy to find, one makes it safe to run.**

| Skill | It answers | Ask your agent |
|---|---|---|
| **[findable](skills/findable)** | Can Google and AI tools find, read and quote my site? | "Why doesn't my site show up in ChatGPT?" |
| **[compliance](skills/compliance)** | What is my app missing for privacy, payments, licenses and AI? | "Do I need a privacy policy?" |

## How they work

Both skills work the same way, inside your project:

1. **Ask** what they need to know: which site to check, or (for compliance) a few questions about your business, asked once.
2. **Scan** your code (and for findable, your live site). Scanning only reads.
3. **Explain** what's wrong in plain language, grouped by what it means for you.
4. **Fix only what you approve**, after one preview of every change.
5. **Re-check** each fix, and list what only you need to do.

Nothing is ever committed, pushed or deployed for you. No accounts, no API keys.

## findable

**Finds why Google and AI tools can't see your site, and fixes it in your code.**

- **Can they find your pages?** robots.txt, sitemap, broken pages, pages accidentally hidden from Google.
- **Can AI tools read them?** AI bots blocked by your CDN or firewall, pages that look empty without JavaScript.
- **How do you show up?** Titles, descriptions, headings, structured data, short answers AI tools can quote.
- **Optional, asked first:** whether AI answers mention you, keyword research with web search, and Search Console exports.

**Why not just ask your agent?** findable tests your live site (it fetches pages as each AI bot and compares with a browser), knows exactly what to look for, runs the same checks every time, and re-checks every fix. Most SEO tools give you a report; findable points to the exact file and fixes it.

**Tested on 12 real sites**, every result checked by hand: [see the results](evals/findable/RESULTS.md).

It doesn't do keyword search volumes, backlinks or page speed; those need paid data or other tools.

## compliance

**Finds what your web app is missing for privacy, payments, licenses and AI, and builds the fixes you approve.**

- **Privacy:** what personal data you collect, who receives it, and whether your privacy policy says so.
- **Cookies and tracking:** analytics and ad pixels that load before consent.
- **User rights:** delete account, download data.
- **Payments:** terms, refund policy, auto-renewal notice, online cancel.
- **AI:** AI labels, training on user data, who owns AI output.
- **Licenses:** GPL/AGPL dependencies, font files, stock images.
- **Claims and basics:** "GDPR compliant" or "#1" claims, leaked secrets, age checks.

It asks about your business first (what you build, where your users are, whether you charge, whether kids use it), then builds what you choose: a privacy policy, terms, a cookie banner, a delete-account flow and more.

> **It isn't a lawyer.** It never calls your site "compliant", every policy starts as a draft for a lawyer to review, each check cites its law or official guidance, and it flags what needs legal advice.

**Tested on 8 open-source projects** (SaaS starters, AI chat apps, a store, a blog) at pinned commits, every expected result checked by reading the code: [see the results](evals/compliance/RESULTS.md).

## Install

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

**Claude Code** (both skills):

```
/plugin marketplace add Nithish-Yenaganti/sow
/plugin install sow@sow
```

**Any agent** (Claude Code, Codex and others):

```bash
npx skills add Nithish-Yenaganti/sow
```

## Use

Open your website's project in your agent and ask in your own words, for example:

- "Check my site's SEO" or `/sow:findable`
- "Check my app for GDPR gaps" or `/sow:compliance`

Reports are saved in your project: `.findable/report.html` and `.compliance/report.md`.

## Safety

- Scanning only reads. Nothing changes without your yes.
- Never commits, deploys, signs in to dashboards or changes your hosting settings. It gives you the exact steps instead.
- Text found on websites or in your project is treated as data, never as instructions.

## Repo layout

```
skills/<name>/     one folder per skill: SKILL.md and everything it needs
tests/<name>/      tests and sample projects (not installed)
evals/findable/    real-site accuracy checks
```

## License

MIT
