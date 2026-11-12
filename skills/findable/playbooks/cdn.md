# CDN / WAF bot blocking: user steps

`geo.bot_access` means AI or search bots got 401/403/429/503 or a challenge page while a normal browser got 200. robots.txt is not the cause, so this is a **security setting only the user should change**. Give them the steps for their host. The finding's `current` field often names the server (e.g. `cloudflare`, `Vercel`).

Recommend allowing **verified search bots** specifically, not turning bot protection off.

## Cloudflare
1. Dashboard → your domain → **Security → Bots**.
2. If **"Block AI bots"** / AI Scrapers and Crawlers is on: turn it off, or switch to managing it per crawler. Under **AI Crawl Control** (formerly AI Audit), set the search crawlers (`OAI-SearchBot`, `ChatGPT-User`, `PerplexityBot`, `Claude-SearchBot`) to **Allow**. Training crawlers can stay blocked if the user prefers.
3. **Bot Fight Mode / Super Bot Fight Mode:** if it challenges verified bots, set "Verified bots" to **Allow**.
4. **Security → WAF → Custom rules:** look for rules blocking by user agent or by "known bots"; add an exception for `cf.client.bot` (verified bots).
5. Re-run `/findable` to confirm.

## Vercel
1. Project → **Firewall**. Check for **Bot Protection / Attack Challenge Mode** and custom rules that deny by user agent.
2. Turn off Attack Challenge Mode when you're not under attack. Add a bypass rule for verified bots or for the specific user agents.
3. Check `middleware.ts` in the repo for user-agent blocking. *That* part the agent can fix in code.

## Netlify
1. Site → **Security / Firewall traffic rules** (or the edge function/WAF add-on). Look for bot or user-agent rules.
2. Check `netlify.toml` and `_headers`/`_redirects` in the repo for user-agent conditions.

## AWS CloudFront + WAF / Akamai / Fastly / others
- Look for managed bot-control rule groups (e.g. AWS WAF Bot Control). Set **verified bots → allow**, or add an allow rule for the specific user agents above.

## Self-hosted (nginx / Apache)
- Search the server config for `$http_user_agent` / `BrowserMatch` rules blocking `GPTBot|ClaudeBot|PerplexityBot|…`. If that config lives in the repo, the agent can propose the edit; otherwise give the user the lines to change.

After any change, the user re-runs `/findable` and `geo.bot_access` should move to **fixed**.
