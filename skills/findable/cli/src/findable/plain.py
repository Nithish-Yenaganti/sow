"""Plain-language layer: what each finding means for someone who isn't an SEO expert.

Every rule gets
- a group (the question it answers for the site owner),
- a one-sentence plain explanation ({page} is filled in),
- a change kind, which decides how the agent previews the fix before asking permission:
    text      – changes words visitors and search results show (titles, descriptions, answers)
    access    – changes who may crawl or index the site (robots.txt, noindex)
    structure – changes how a page is built (server vs. client rendering)
    technical – invisible plumbing (sitemap, canonical, alt text, schema)
    none      – nothing for the agent to change (the user does it)
"""

from __future__ import annotations

GROUPS = {
    "find": "Can Google and AI find your pages?",
    "read": "Can AI tools read your pages?",
    "show": "How you show up in results",
    "you": "Things only you can do",
}

PLAIN: dict[str, tuple[str, str, str]] = {
    # rule: (group, plain sentence, change kind)
    "seo.robots_blocks_all": ("find", "Your site tells every search engine and AI tool to stay away. Nothing can be found.", "access"),
    "seo.robots": ("find", "There's no robots.txt file, the standard note that tells search engines what they may visit.", "access"),
    "seo.noindex_leak": ("find", "{page} is hidden from Google on purpose by a setting in the code.", "access"),
    "seo.sitemap": ("find", "There's no working sitemap, the list that tells search engines which pages exist.", "technical"),
    "seo.sitemap_host": ("find", "Your sitemap points to a different website address (often a test or local address).", "technical"),
    "seo.sitemap_missing": ("find", "Some pages are missing from your sitemap, so search engines may not discover them.", "technical"),
    "seo.sitemap_dead": ("find", "Your sitemap lists pages that are broken or redirect elsewhere.", "technical"),
    "seo.status": ("find", "{page} is broken: visitors and search engines get an error instead of the page.", "technical"),
    "seo.redirect_chain": ("find", "{page} sends visitors through several redirects before it loads, which wastes crawl time.", "technical"),
    "seo.canonical": ("find", "{page} doesn't say which address is its official one, so duplicates can compete with it.", "technical"),
    "seo.canonical_mismatch": ("find", "{page} tells Google that a different page is the real one, so this page may not show up.", "technical"),
    "seo.orphan": ("find", "Some pages have no links pointing to them, so search engines rarely find them.", "technical"),
    "geo.robots_ai": ("read", "Your robots.txt blocks AI search tools (ChatGPT, Perplexity, Claude) from visiting your site.", "access"),
    "geo.bot_access": ("read", "Your hosting or firewall blocks AI and search tools, even though browsers get through.", "none"),
    "geo.no_js_view": ("read", "{page} looks empty to AI tools, because its content only appears after JavaScript runs.", "structure"),
    "geo.client_rendered": ("read", "{page} is built in the browser, so AI tools may see little or none of its content.", "structure"),
    "seo.title": ("show", "{page} has no title, so search results show something generic or nothing useful.", "text"),
    "seo.title_length": ("show", "The title of {page} is too short or too long for search results.", "text"),
    "seo.title_duplicate": ("show", "{page} has the same title as other pages, so they look identical in search results.", "text"),
    "seo.title_inherited": ("show", "{page} uses the site-wide title instead of its own.", "text"),
    "seo.description": ("show", "{page} has no description, the short summary shown under the title in search results.", "text"),
    "seo.description_duplicate": ("show", "{page} has the same description as other pages.", "text"),
    "seo.description_inherited": ("show", "{page} uses the site-wide description instead of its own.", "text"),
    "seo.alt": ("show", "Images on {page} have no text description, so search engines and screen readers can't tell what they show.", "text"),
    "aeo.h1": ("show", "{page} doesn't have exactly one main heading saying what the page is about.", "text"),
    "aeo.answer_first": ("show", "Questions on {page} aren't followed by a short, direct answer that AI tools can quote.", "text"),
    "aeo.schema": ("show", "No page carries structured facts about your business (name, logo, what you offer) for Google and AI.", "technical"),
    "aeo.schema_org": ("show", "Your homepage doesn't describe your business in the structured format Google and AI read.", "technical"),
    "aeo.schema_invalid": ("show", "The structured facts on {page} are broken, so Google and AI ignore them.", "technical"),
    "seo.striking_distance": ("show", "{page} is almost on Google's first page; a few fixes could push it up.", "text"),
    "seo.striking_queries": ("show", "Some searches show your site on page 2 of Google; a short answer for each could move it up.", "text"),
    "setup.live_url": ("you", "Only your code was checked. Share your website address to also test the live site.", "none"),
    "setup.live_unreachable": ("you", "Your website couldn't be reached, so the live checks were skipped.", "none"),
    "setup.gsc_csv": ("you", "Optional: add a Google Search Console export to find pages that are close to page one.", "none"),
    "setup.gsc_verify": ("you", "Make sure your site is connected to Google Search Console, so you can see how Google sees it.", "none"),
    "setup.submit_sitemap": ("you", "Submit your sitemap to Google and Bing (Bing also powers ChatGPT search and Copilot).", "none"),
}

CHANGE_LABEL = {
    "text": "changes your words",
    "access": "changes who can visit or index your site",
    "structure": "changes how the page is built",
    "technical": "behind-the-scenes fix",
    "none": "you do this",
}


def describe(rule: str, url: str, who: str) -> dict:
    group, sentence, kind = PLAIN.get(rule, ("show", "", "technical"))
    if who == "user":
        group, kind = "you", "none"
    page = "your homepage" if url == "/" else ("your site" if url == "site" else f"the page {url}")
    text = sentence.replace("{page}", page)
    if text:
        text = text[0].upper() + text[1:]
    return {"group": group, "plain": text, "change_kind": kind}
