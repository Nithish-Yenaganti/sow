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

**Your AI built the website. SOW makes sure it survives on the web.**

## The story

You build a website in an afternoon with your AI coding assistant. It looks great. You ship it.

Then, quietly, three things go wrong:

- **Nobody finds it.** Google doesn't list it, and ChatGPT never mentions it.
- **It's missing the rules.** No privacy policy, no cookie notice, or code you aren't allowed to use.
- **It has holes.** A leaked API key, a database anyone can read, or a package the AI made up.

Most people find out too late. SOW gives your assistant three skills to catch these early:

| Skill | The question it answers |
|---|---|
| [**findable**](skills/findable) | Can Google and AI tools find, read and quote my site? |
| [**compliance**](skills/compliance) | Do I have the policies, consent and licenses I need? |
| [**guarded**](skills/guarded) | Is my code safe from the usual attacks? |

Each one looks first, explains what's wrong in plain words, and fixes only what you say yes to. No accounts, no API keys, nothing published for you.

> compliance writes drafts, not legal advice. guarded checks code, it doesn't attack anything.

## Install

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) first.

**Claude Code:**

```
/plugin marketplace add Nithish-Yenaganti/sow
/plugin install sow@sow
```

**Other assistants (like Codex):**

```bash
npx skills add Nithish-Yenaganti/sow
```

## Use

Open your project and ask:

- "Check if my site can be found"
- "Check if my site is set up right"
- "Check my app for security holes"

## License

MIT, free to use.
