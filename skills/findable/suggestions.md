# User steps

Things only the user can do. Give the exact steps, then say what it unlocks.

## Give findable a URL {#live-url}
The live checks need a reachable site: AI-bot access, status codes, sitemap, empty-without-JS.
- **Production:** `findable scan --url https://your-domain.com`
- **Local:** start the dev server (e.g. `npm run dev`), then `findable scan --url http://localhost:3000`
- The answer is remembered in `.findable/config.json`.

## Search Console: Page indexing export {#gsc-index-export}
Unlocks which pages Google isn't indexing, and why. No sign-in for findable: you download the files.
1. Open https://search.google.com/search-console → pick the property.
2. **Indexing → Pages**. Top right: **Export → Download CSV**. This gives the list of reasons ("Why pages aren't indexed") with page counts.
3. For the page list: click a reason in that table (e.g. **Crawled – currently not indexed**), then **Export → Download CSV** again. Repeat for each reason you care about.
4. Put the zips (or CSVs) in `.findable/inputs/` in this project. Keep each zip as downloaded: findable reads the reason from it.
5. Run `/findable` again.

## Search Console: Performance export {#gsc-export}
Unlocks striking-distance pages and queries (positions 8–20).
1. Open https://search.google.com/search-console → pick the property.
2. **Performance → Search results** → set the date range to the **last 3 months**.
3. Top right: **Export → Download CSV**. You get a zip with `Queries.csv`, `Pages.csv`, …
4. Put the zip (or the CSVs) in `.findable/inputs/` in this project.
5. Run `/findable` again.

## Verify in Search Console {#gsc-verify}
1. https://search.google.com/search-console → **Add property**.
2. **Domain** property (recommended; covers http/https and all subdomains): add the TXT record at your DNS provider.
3. Or a **URL-prefix** property with the **HTML tag** method: copy the `google-site-verification` meta tag. The agent can add it to the site's `<head>` (Next.js: `metadata.verification.google`), then you click **Verify** after deploying.

## Submit the sitemap {#submit-sitemap}
1. **Google:** Search Console → **Sitemaps** → enter `sitemap.xml` → Submit.
2. **Bing:** https://www.bing.com/webmasters → **Import from Google Search Console** (2 clicks), or add the site and submit the sitemap under **Sitemaps**. Bing's index also feeds ChatGPT search and Copilot.
3. Then dismiss this: `findable dismiss "setup.submit_sitemap|site" --reason "submitted"`.

## Install uv {#install-uv}
findable runs on `uv` (a fast Python runner).
- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Or: `brew install uv`
Then re-run the command.

## Brand mentions (optional)
Create Google Alerts (https://www.google.com/alerts) for `"Your Brand"` and `"yourdomain.com" -site:yourdomain.com`. Unlinked mentions you find are good candidates to turn into links. Mentions on Reddit and review sites also shape what AI engines say about you.
