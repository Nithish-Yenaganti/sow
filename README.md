# stayonweb

Skills for coding agents that keep your website findable and healthy on the web. Each one runs inside your project, asks you when there's a real choice, and never commits or deploys for you.

| Skill | What it does |
|---|---|
| [findable](plugins/findable) | Checks whether Google and AI engines (ChatGPT, Perplexity, Claude, Gemini) can find, read and cite your site, fixes what blocks it, and verifies the fixes. |
| compliance *(coming soon)* | Compliance audit for your site. |

## Install

**Claude Code**

```
/plugin marketplace add Nithish-Yenaganti/stayonweb
/plugin install findable@stayonweb
```

**Codex and other agents:** copy `plugins/findable/skills/findable/` into your project's `.agents/skills/`.

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/), which runs the skill's bundled CLI.

## Use

Ask your agent "check my site's SEO" or "run findable" (in Claude Code: `/findable:findable`).

## License

MIT
