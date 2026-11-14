# compliance accuracy eval

compliance 0.1.0 · run 2026-11-13 · 8 open-source projects at pinned commits · 57 hand-verified checks · **8/8 projects pass**

Each project is scanned with a fixed intake profile. A project passes when the scan reports every real gap verified by reading the code (`must`) and none of the false alarms checked the same way (`must_not`).

| Project | Kind | Packs | Findings | Result |
|---|---|---|---|---|
| [saas-starter](https://github.com/nextjs/saas-starter/tree/6e33e58b1e55) | SaaS starter: Stripe subscriptions, Drizzle, own auth | baseline, payments | 12 | ✅ pass |
| [nextjs-subscription-payments](https://github.com/vercel/nextjs-subscription-payments/tree/bdd0813206e4) | SaaS: Stripe subscriptions, Supabase auth | baseline, payments | 14 | ✅ pass |
| [taxonomy](https://github.com/shadcn-ui/taxonomy/tree/298a8857c712) | SaaS + blog: Stripe, NextAuth, Prisma | baseline, payments | 15 | ✅ pass |
| [chatbot](https://github.com/vercel/chatbot/tree/a8989b522fa3) | AI chat app with accounts | baseline, ai | 13 | ✅ pass |
| [chatbot-ui](https://github.com/mckaywrigley/chatbot-ui/tree/81328b61d2a4) | AI chat app, Supabase, file uploads | baseline, ai | 17 | ✅ pass |
| [commerce](https://github.com/vercel/commerce/tree/f7521d57d29f) | Store (Shopify headless) | baseline, payments | 11 | ✅ pass |
| [tailwind-nextjs-starter-blog](https://github.com/timlrx/tailwind-nextjs-starter-blog/tree/b45bef66b40c) | Blog with optional analytics | baseline | 6 | ✅ pass |
| [precedent](https://github.com/steven-tey/precedent/tree/3be40205d7cd) | Landing-page starter | baseline | 10 | ✅ pass |

## Known gaps (real problems the scan misses today; not counted as failures)

- chatbot: `terms.no_clickwrap`: app/(auth)/register/page.tsx shows a sign-up form with no terms link, but its inputs live in components/chat/auth-form.tsx, so the scan doesn't see it.

## Limits

- The scan reads code, so pages managed in a CMS or a hosted platform (Shopify policies, for example) can't be seen.
- Dependency licenses are only read from `package-lock.json` license fields or an installed `node_modules`. These projects are scanned without installing, so most report `licenses.unchecked`.
- Every expectation was checked by reading the code at the pinned commit. A person should re-check them before relying on the numbers.

Expectations and the reason for each: [repos.json](repos.json). Re-run: `uv run --project skills/compliance/cli python evals/compliance/run.py`
