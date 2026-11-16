# guarded accuracy eval

guarded 0.1.0 · run 2026-11-15 · 14 open-source projects at pinned commits · scanned offline · 95 hand-verified checks · **14/14 projects pass**

A project passes when the scan reports every real problem verified by reading the code (`must`) and none of the false alarms checked the same way (`must_not`). Three MCP servers are scanned at the commit just before their CVE fix; two of them are also scanned at the fix commit, where the shell-injection finding has to be gone.

| Project | What it is | Findings (high) | Result |
|---|---|---|---|
| [git-mcp-server](https://github.com/cyanheads/git-mcp-server/tree/f30169ec3a25) | MCP server, commit before the CVE-2025-53107 fix | 23 (23) | ✅ pass |
| [git-mcp-server-fixed](https://github.com/cyanheads/git-mcp-server/tree/0dbd6995ccdf) | Same MCP server at the CVE-2025-53107 fix commit | 1 (1) | ✅ pass |
| [figma-context-mcp](https://github.com/GLips/Figma-Context-MCP/tree/5b0d10e76eaf) | MCP server, commit before the CVE-2025-53967 fix | 2 (2) | ✅ pass |
| [figma-context-mcp-fixed](https://github.com/GLips/Figma-Context-MCP/tree/7f4b5859454b) | Same MCP server at the CVE-2025-53967 fix commit | 1 (1) | ✅ pass |
| [github-kanban-mcp](https://github.com/Sunwood-ai-labs/github-kanban-mcp-server/tree/5c12cb403675) | MCP server named in CVE-2025-53818 (v0.4.0) | 4 (4) | ✅ pass |
| [juice-shop](https://github.com/juice-shop/juice-shop/tree/266448aba68c) | OWASP Juice Shop (deliberately insecure web shop) | 36 (16) | ✅ pass |
| [damn-vulnerable-llm-agent](https://github.com/ReversecLabs/damn-vulnerable-llm-agent/tree/c0cf9a14adad) | Deliberately vulnerable LangChain agent | 1 (1) | ✅ pass |
| [damn-vulnerable-mcp-server](https://github.com/harishsg993010/damn-vulnerable-MCP-server/tree/cdc4c6b5b763) | Deliberately vulnerable MCP servers (15 challenges) | 15 (12) | ✅ pass |
| [saas-starter](https://github.com/nextjs/saas-starter/tree/6e33e58b1e55) | Production template: Next.js, Stripe, Drizzle, own auth | 1 (0) | ✅ pass |
| [chatbot](https://github.com/vercel/chatbot/tree/a8989b522fa3) | Production template: AI chat app (Vercel AI SDK, tools, Postgres) | 3 (0) | ✅ pass |
| [chatbot-ui](https://github.com/mckaywrigley/chatbot-ui/tree/81328b61d2a4) | AI chat app: Supabase, file uploads, retrieval, custom tools | 3 (0) | ✅ pass |
| [nextjs-subscription-payments](https://github.com/vercel/nextjs-subscription-payments/tree/bdd0813206e4) | Production template: Supabase auth and tables, Stripe | 1 (0) | ✅ pass |
| [taxonomy](https://github.com/shadcn-ui/taxonomy/tree/298a8857c712) | Production template: Next.js, NextAuth, Prisma, Stripe | 1 (0) | ✅ pass |
| [commerce](https://github.com/vercel/commerce/tree/f7521d57d29f) | Production template: Shopify storefront | 2 (0) | ✅ pass |

## Known gaps (real problems the scan misses today; not counted as failures)

- juice-shop: `secrets.weak_hash`: lib/insecurity.ts hashes passwords with MD5, but the word 'password' only appears where hash() is called in another file (routes/login.ts), so the scan doesn't connect them.
- juice-shop: `inject.eval|routes/captcha.ts`: Also flagged (eval on a string), but the expression is built from random numbers on the server, so it isn't exploitable. Listed so nobody counts it as a catch.

## Limits

- This measures known bugs in these projects, not every bug they have. A clean result on the production templates means no false alarms on them, not that they're bug-free.
- Package checks (`pkg.*`) depend on live npm, PyPI and OSV data, so they run only with `--online` and aren't part of the weekly numbers.
- Every expectation was checked by reading the code at the pinned commit. A person should re-check them before relying on the numbers.

Expectations and the reason for each: [repos.json](repos.json). Re-run: `uv run --project skills/guarded/cli python evals/guarded/run.py`
