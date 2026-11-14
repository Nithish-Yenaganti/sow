# AI visibility check

**Question it answers:** when people ask the questions your site should answer, do the sources AI answers draw on include you?

findable has no API keys, so it can't ask ChatGPT or Perplexity directly. AI answer engines cite pages from web search indexes: ChatGPT search and Copilot use Bing, Perplexity and Claude use their own search. So this check runs each question through **your own web search tool** and looks for the site among the results. It's a strong signal, not a copy of any one AI's answer. Say so when you report it.

## Run

1. **Ask first.** "Want me to check whether AI answers mention you? I'll run about 5 web searches." Only continue on yes. The questions are sent to your search tool, so don't include private details.
2. **Propose questions** the site's real customers would ask, from its actual content (homepage, product pages, question headings in the report):
   - 1 about the problem it solves, without the brand ("how to share whiteboard sketches with a team")
   - 1–2 about the category ("best open-source whiteboard app")
   - 1 comparison ("excalidraw vs miro")
   - 1–2 from the site's own question headings or docs ("how do I export a drawing as SVG")
   Show them as a multi-select with the option to edit. Use the user's choice. Never more than 10.
3. **Search** each question with your web search tool (Claude Code: WebSearch). If you have no web search tool, say so and stop; don't guess.
4. **Write the results** exactly as returned, in result order, to `.findable/inputs/visibility.json`:
   ```json
   {"engine": "Claude Code WebSearch",
    "results": [{"query": "best open-source whiteboard app", "result_urls": ["https://...", "https://..."]}]}
   ```
   Include every result URL (up to 20), not only the ones you think matter. findable decides whether the site appears.
5. **Record:** `findable visibility record --file .findable/inputs/visibility.json --json` (add `--site example.com` if it asks for the domain).
6. **Report** in plain language: "You show up for 2 of 5 questions." Then, for each miss, the question and who shows up instead.
7. Run `findable scan --json` again so the misses appear in the report under **Do AI answers mention you?**

## Improve

For each question where the site doesn't appear (`geo.ai_not_cited`), offer (with permission, like every fix):
- **A direct answer on the best-matching page**: a heading with the question and a 40–60 word answer right under it (see `aeo-content.md#answer-first`). Write it from the site's real content; never invent claims.
- **A new page** if no page covers the question. Ask before creating one.
- **Check the basics for that page first:** it must be indexable, in the sitemap, readable without JavaScript, and reachable by AI bots. Fix those before writing new content.

Results change over time. Suggest re-running the check a few weeks after changes are deployed.
