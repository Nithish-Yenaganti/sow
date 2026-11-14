# Keyword research (web search, no keyword tools)

**Question it answers:** what do people search that this site should win, who wins those searches today, and which page should go after each one?

There's no paid keyword data, so there are **no search volumes**. Never invent or estimate volumes. Rank keywords by search intent and by what you find in the results. If a Search Console Performance export is in `.findable/inputs/`, findable adds its real impressions and positions.

## Run

1. **Ask first.** "Want me to research keywords for your site? I'll run about 10–15 web searches." Continue only on yes. The searches go to your search tool, so don't include private details.
2. **Seed topics.** Read the site's real content: homepage, product and feature pages, docs and blog titles (the scan's pages and the code). Write down 3–5 seed topics, in the words a customer would use, not internal names.
3. **Expand with search.** Search each seed. Read the result titles and snippets for how people actually phrase it. Turn that into 10–15 candidate keywords across these intents:
   - **informational:** "how to …", "what is …"
   - **commercial:** "best … for …", "… tools"
   - **comparison:** "X vs Y", "X alternatives" (use competitors you saw in the results)
   - **transactional:** "… pricing", "… free trial"
   Leave out the brand name alone; you already rank for that.
4. **Let the user choose.** Show the candidates as a multi-select (they can edit or add). Use only what they pick, at most 30.
5. **Search each keyword** with your web search tool (Claude Code: WebSearch). If there's no web search tool, say so and stop.
6. **Pick the target page** for each keyword: the existing page that should rank for it (a path like `/features`), or leave it empty if no page fits (a new page is needed).
7. **Write the results** in result order to `.findable/inputs/keywords.json`:
   ```json
   {"engine": "Claude Code WebSearch",
    "keywords": [{"keyword": "best whiteboard for remote teams", "intent": "commercial",
                  "target_page": "/features", "result_urls": ["https://...", "https://..."]}]}
   ```
   Include every result URL (up to 20). findable decides whether the site appears.
8. **Record:** `findable keywords record --file .findable/inputs/keywords.json --json` (add `--site example.com` if asked).
9. **Report** in plain words:
   - "You show up for 3 of 12 searches."
   - The searches you're missing that matter most: commercial and comparison first, each with who shows up instead and the page that should target it.
   - The sites that show up across most of your searches: your real search competitors.
10. Run `findable scan --json` again so the misses appear in the report under **Searches you could win**.

## Act

Opportunities are content work, so they follow the same permission rules as every fix: ask, preview, then write.
- **Existing target page:** add a section that answers the search directly (the question as a heading, a 40–60 word answer under it, then details). Use the words people search in the title and the main heading, but only where it's true to the page.
- **No page fits:** propose a new page (title, main heading, outline) and ask before creating it. Comparison and "alternatives" pages must be fair and factual; never invent claims about competitors.
- **Check the basics first** for the target page: indexable, in the sitemap, readable without JavaScript, internal links pointing to it.
- Write from the site's real content. If a fact is missing (a price, a feature), ask; don't make it up.

Results change. Suggest re-running the research a few weeks after the changes are live.
