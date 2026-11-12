# stayonweb

Skills for coding agents that keep your website findable and healthy on the web. Each one runs inside your project, asks when there's a real choice, and never commits or deploys for you.

| Plugin | What it does |
|---|---|
| [findable](plugins/findable) | Can Google and AI engines find, read and cite your site? Scans code + live site, fixes SEO/AEO/GEO issues, verifies them. |
| compliance *(coming)* | Compliance audit for your site. |

## Install (Claude Code)

```
/plugin marketplace add <github-owner>/stayonweb
/plugin install findable@stayonweb
```

Most skills need [uv](https://docs.astral.sh/uv/) to run their bundled CLI.

## Adding a plugin

1. Create `plugins/<name>/` with `.claude-plugin/plugin.json` and `skills/<name>/SKILL.md`.
2. Put anything the skill runs inside its skill folder, so it also works when copied on its own (Codex).
3. Add an entry to `.claude-plugin/marketplace.json`.
4. Check it: `claude plugin validate .`
