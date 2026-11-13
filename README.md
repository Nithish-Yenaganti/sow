<p align="center">
  <img src="assets/banner.svg" alt="SOW — Stay On Web" width="100%">
</p>

<p align="center">
  <a href="https://github.com/Nithish-Yenaganti/sow/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Nithish-Yenaganti/sow/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-5eead4"></a>
  <img alt="Works with Claude Code, Codex, Cursor" src="https://img.shields.io/badge/agents-Claude%20Code%20%C2%B7%20Codex%20%C2%B7%20Cursor-60a5fa">
  <img alt="No API keys" src="https://img.shields.io/badge/API%20keys-none-0e1a2b">
</p>

# SOW — Stay On Web

Skills for coding agents that keep your website findable and healthy on the web. Each one runs inside your project, asks you when there's a real choice, and never commits or deploys for you.

| Skill | What it does |
|---|---|
| [findable](skills/findable) | Checks whether Google and AI engines (ChatGPT, Perplexity, Claude, Gemini) can find, read and cite your site, fixes what blocks it, and verifies the fixes. |
| compliance *(coming soon)* | Compliance audit for your site. |

## Install

**Any agent** (Claude Code, Codex, Cursor and more):

```bash
npx skills add Nithish-Yenaganti/sow
```

**Claude Code plugin:**

```
/plugin marketplace add Nithish-Yenaganti/sow
/plugin install findable@sow
```

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/), which runs the skill's bundled CLI.

## Use

Ask your agent "check my site's SEO" or "run findable".

## Repo layout

```
skills/<name>/       # one folder per skill: SKILL.md + everything it needs
tests/<name>/        # tests and fixtures (not installed)
.claude-plugin/      # Claude Code marketplace manifest
```

## License

MIT
