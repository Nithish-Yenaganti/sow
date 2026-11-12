# stayonweb

Skills for coding agents that keep your website findable and healthy on the web. Each one runs inside your project, asks you when there's a real choice, and never commits or deploys for you.

| Skill | What it does |
|---|---|
| [findable](skills/findable) | Checks whether Google and AI engines (ChatGPT, Perplexity, Claude, Gemini) can find, read and cite your site, fixes what blocks it, and verifies the fixes. |
| compliance *(coming soon)* | Compliance audit for your site. |

## Install

**Any agent** (Claude Code, Codex, Cursor and more):

```bash
npx skills add Nithish-Yenaganti/stayonweb
```

**Claude Code plugin:**

```
/plugin marketplace add Nithish-Yenaganti/stayonweb
/plugin install findable@stayonweb
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
