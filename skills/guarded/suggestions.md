# Steps only you can do

The skill never signs in anywhere, rotates keys or changes dashboards. These are yours.

## install-uv
The skill runs its checker with [uv](https://docs.astral.sh/uv/getting-started/installation/). Install it (`curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS/Linux, or `brew install uv`), then run the skill again.

## rotate-keys
A key that was ever in git, or sent to the browser, should be treated as leaked, even after the code change.
1. Create a new key at the provider (OpenAI, Anthropic, Stripe, AWS, GitHub, Supabase: API settings).
2. Put the new key in your hosting provider's environment variables (Vercel, Netlify, Fly, Railway, Render) and in your local `.env`.
3. Delete the old key at the provider.
4. Check the provider's usage or billing page for anything you didn't do.
5. Optional: remove the old key from git history (`git filter-repo` or GitHub's guide). Only after rotating, and only if you understand it rewrites history for everyone.

## supabase
1. Apply the new migration: `supabase db push` (or paste it into the SQL editor).
2. In the dashboard, open **Database → Tables** and check every table in `public` shows RLS enabled.
3. Open **Advisors → Security Advisor** and fix anything it lists.
4. With the app logged out, try reading a table with the anon key (the Supabase API docs page shows how). It should return nothing.

## firebase
Deploy the new rules (`firebase deploy --only firestore:rules,storage`), then use the **Rules Playground** in the Firebase console to check a logged-out user can't read private data.

## read-only-db
Create a database user for AI-generated queries that can only `SELECT` from the tables the feature needs, and use its connection string for that feature only. Postgres:
```sql
create role ai_reader login password '…';
grant usage on schema public to ai_reader;
grant select on public.<table> to ai_reader;
```

## model-server
Keep Ollama (or any local model server) updated, and don't open its port to the internet. If you need remote access, use a VPN or an authenticating proxy.

## malware
If a package was listed as malware and was ever installed:
1. Remove it and reinstall dependencies from a clean lock file.
2. Treat every secret on machines and CI runners that installed it as leaked: rotate them (see rotate-keys).
3. Check those machines for unknown startup items or processes, or ask your security team.

## ai-tools
If a risky MCP server, hook or hidden instruction was in the repo, ask everyone who opened it with an AI coding tool whether the tool ran anything unexpected, and check their machines' shell history. Turn on your AI tool's "ask before running commands" setting.
