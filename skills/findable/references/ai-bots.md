# AI crawlers

| Token (robots.txt) | Company | Purpose | Effect of blocking |
|---|---|---|---|
| `OAI-SearchBot` | OpenAI | **Search**: ChatGPT search results and citations | Not shown or cited in ChatGPT search |
| `ChatGPT-User` | OpenAI | **Search**: fetches a page when a user asks ChatGPT about it | ChatGPT can't open your pages on request |
| `GPTBot` | OpenAI | Training | Not used for training; search is unaffected |
| `PerplexityBot` | Perplexity | **Search**: index and citations | Not cited in Perplexity |
| `Claude-SearchBot` | Anthropic | **Search**: Claude's search results | Not cited in Claude search |
| `ClaudeBot` | Anthropic | Training | Not used for training |
| `Google-Extended` | Google | Training for Gemini (robots.txt token only; crawling is done by Googlebot) | AI Overviews still use Googlebot's index |
| `Bingbot` | Microsoft | **Search**: Bing, which also feeds Copilot and ChatGPT search | Big loss; never block it |
| `Googlebot` | Google | **Search**: Google + AI Overviews / AI Mode | Never block it |
| `CCBot` | Common Crawl | Training datasets used by many models | — |
| `Applebot-Extended` | Apple | Training (Apple Intelligence) | — |

**Recommended default** (the `search_only` option): allow every search bot and leave training bots as the user prefers.

```txt
User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

# Training crawlers: remove these blocks to allow training use
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: *
Allow: /

Sitemap: https://YOUR-DOMAIN/sitemap.xml
```

Notes:
- robots.txt groups don't merge. A bot uses the *most specific* `User-agent` group that matches it. If the bot has its own group, the `*` rules don't apply to it.
- robots.txt is a request, not a block. If bots still get 403s, the CDN/WAF is blocking them (`geo.bot_access`, see `playbooks/cdn.md`).
- Bot tokens change. Check the vendor docs (OpenAI, Anthropic, Perplexity) if a new bot shows up in server logs.
