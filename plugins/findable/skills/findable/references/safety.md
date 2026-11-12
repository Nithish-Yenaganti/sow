# Safety rules (always apply)

1. **Never commit, push, merge or deploy.** Leave changes in the working tree for the user to review.
2. **Never sign in, submit forms, or change settings** in Search Console, Bing Webmaster, CDN/WAF dashboards (Cloudflare, Vercel, Netlify), DNS, or analytics. Give the user the exact steps instead.
3. **Never pick between options for the user** when the CLI or this skill says to ask.
4. **Never invent content facts.** Titles, descriptions, FAQ answers and schema values come from the page's real content and the repo. If a value is unknown (logo URL, social profiles, prices), ask or leave it out.
5. **Don't weaken security** to let bots in (e.g. turning off bot protection globally). Recommend allowing specific verified bots only.
6. **Stay on the user's site.** The live scan is limited to the chosen host; don't point it at sites the user doesn't own.
7. **Dev server:** start it only if the user chose that option, and stop it when done if you started it.
8. **Dismissals need a reason** from the user, not one you made up.
