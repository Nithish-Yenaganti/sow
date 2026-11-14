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

**Helpers for your AI coding assistant that make sure your website can be found, and is set up the right way.**

## Why we made this

Today anyone can build a website in an afternoon with an AI coding assistant. But two things often go wrong after that:

1. **Nobody can find it.** Google doesn't show it, and ChatGPT never mentions it.
2. **It's missing the rules.** No privacy policy, no cookie notice, no refund policy, or code you aren't allowed to use.

Most people only find out much later. SOW gives your coding assistant two skills that check for these problems, explain them in simple words, and fix them, but only when you say yes.

## The two skills

### findable: "Can people find my website?"

| Topic | What it checks |
|---|---|
| **Google** | Can Google find and list every page? |
| **AI** | Can ChatGPT, Claude and Perplexity read your pages? |
| **Blocked** | Is something accidentally keeping search engines out? |
| **Empty** | Do some pages look blank to robots? |
| **Titles** | Does every page have a clear name and summary? |
| **Answers** | Are there short answers AI tools can quote? |
| **Mentions** | Do AI answers mention you, or someone else? *(optional)* |
| **Keywords** | Which searches could you win? *(optional)* |

[Read more about findable →](skills/findable)

### compliance: "Is my website set up the right way?"

| Topic | What it checks |
|---|---|
| **Privacy** | Do you explain what personal data you collect and why? |
| **Cookies** | Do trackers wait until visitors say yes? |
| **Rights** | Can users delete or download their data? |
| **Payments** | Are refunds, renewals and cancelling clear? |
| **AI** | Do you tell people when they're talking to AI? |
| **Licenses** | Are you allowed to use your code, fonts and images? |
| **Claims** | Are you promising things you can't prove? |
| **Safety** | Are passwords and secret keys kept safe? |

[Read more about compliance →](skills/compliance)

> compliance is not a lawyer. Every policy it writes is a draft for a lawyer to check.

## How it works

1. You ask your coding assistant, like: "Why doesn't my site show up in Google?"
2. It looks at your website. Looking never changes anything.
3. It tells you what's wrong, in simple words.
4. You pick what to fix, and see every change first.
5. It fixes those things and checks that they worked.

It never publishes anything for you, and you don't need any accounts or keys.

## Install

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) installed first.

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

Open your website's project and ask:

- "Check if my site can be found" (findable)
- "Check if my site is set up right" (compliance)

## License

MIT, free to use.
