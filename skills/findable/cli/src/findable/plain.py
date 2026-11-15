"""The rule catalog: one entry per rule, the single place its wording and defaults live.

Each rule has
- group: the question it answers for the site owner (see GROUPS)
- severity: the default (a rule may raise or lower it with evidence)
- kind: how the agent previews the fix before asking permission
    text      changes words visitors and search results show
    access    changes who may crawl or index the site
    structure changes how a page is built (server vs. client rendering)
    technical invisible plumbing (sitemap, canonical, schema)
    none      nothing for the agent to change (the user does it)
- fix: a fix guide; "@anchor" means the framework playbook (nextjs.md or generic.md)
- target: what good looks like
- plain: one sentence for someone who isn't an SEO expert; {page}, {query}, {others},
  {rank} and {why} are filled in from the finding
"""

from __future__ import annotations

from typing import NamedTuple

GROUPS = {
    "find": "Can Google and AI find your pages?",
    "read": "Can AI tools read your pages?",
    "show": "How you show up in results",
    "cite": "Do AI answers mention you?",
    "grow": "Searches you could win",
    "you": "Things only you can do",
}

CHANGE_LABEL = {
    "text": "changes your words",
    "access": "changes who can visit or index your site",
    "structure": "changes how the page is built",
    "technical": "behind-the-scenes fix",
    "none": "you do this",
}


class Rule(NamedTuple):
    group: str
    severity: str
    kind: str
    fix: str
    target: str
    plain: str


R = Rule
CATALOG: dict[str, Rule] = {
    # Can Google and AI find your pages?
    "seo.robots_blocks_all": R("find", "critical", "access", "@robots", "Allow crawling of public pages",
                               "Your site tells every search engine and AI tool to stay away. Nothing can be found."),
    "seo.robots": R("find", "medium", "access", "@robots", "robots.txt that allows crawling and lists the sitemap",
                    "There's no robots.txt file, the standard note that tells search engines what they may visit."),
    "seo.noindex_leak": R("find", "high", "access", "@noindex", "indexable, unless the page is meant to be hidden",
                          "{page} is hidden from Google by a setting in the code."),
    "seo.sitemap": R("find", "high", "technical", "@sitemap", "sitemap.xml listing every indexable page, referenced in robots.txt",
                     "There's no working sitemap, the list that tells search engines which pages exist."),
    "seo.sitemap_host": R("find", "high", "technical", "@sitemap", "only URLs on your own domain",
                          "Your sitemap points to a different website address (often a test or local address)."),
    "seo.sitemap_missing": R("find", "medium", "technical", "@sitemap", "every indexable page listed in the sitemap",
                             "Some pages are missing from your sitemap, so search engines may not discover them."),
    "seo.sitemap_dead": R("find", "medium", "technical", "@sitemap", "only final, 200-status URLs in the sitemap",
                          "Your sitemap lists pages that are broken or redirect elsewhere."),
    "seo.status": R("find", "high", "technical", "@broken-page", "HTTP 200, or remove links and sitemap entries pointing here",
                    "{page} is broken: visitors and search engines get an error instead of the page."),
    "seo.redirect_chain": R("find", "low", "technical", "@redirects", "a single redirect, or a link straight to the final URL",
                            "{page} sends visitors through several redirects before it loads, which wastes crawl time."),
    "seo.canonical": R("find", "low", "technical", "@canonical", "a canonical link pointing to this page's own address",
                       "{page} doesn't say which address is its official one, so duplicates can compete with it."),
    "seo.canonical_mismatch": R("find", "high", "technical", "@canonical", "a canonical pointing to this page, unless it's a deliberate copy",
                                "{page} tells Google that a different page is the real one, so this page may not show up."),
    "seo.not_indexed": R("find", "medium", "technical", "references/checks.md#not-indexed", "indexed by Google (or deliberately excluded)",
                         "Google isn't indexing {page}: {why}."),
    "seo.index_summary": R("find", "medium", "technical", "suggestions.md#gsc-index-export", "every page you want found is indexed",
                           "Google isn't indexing some of your pages. Search Console lists the reasons."),
    "seo.orphan": R("find", "low", "technical", "@internal-links", "at least one internal link to each page",
                    "Some pages have no links pointing to them, so search engines rarely find them."),
    # Can AI tools read your pages?
    "geo.robots_ai": R("read", "high", "access", "references/ai-bots.md", "allow AI search bots (they fetch pages to cite them)",
                       "Your robots.txt blocks AI search tools (ChatGPT, Perplexity, Claude) from visiting your site."),
    "geo.bot_access": R("read", "critical", "none", "playbooks/cdn.md", "HTTP 200 for AI search bots",
                        "Your hosting or firewall blocks AI and search tools, even though browsers get through."),
    "geo.no_js_view": R("read", "critical", "structure", "@client-rendered", "main content in the initial HTML",
                        "{page} looks empty to AI tools, because its content only appears after JavaScript runs."),
    "geo.client_rendered": R("read", "high", "structure", "@client-rendered", "server-rendered page; interactive parts in small client components",
                             "{page} is built in the browser, so AI tools may see little or none of its content."),
    # How you show up in results
    "seo.title": R("show", "high", "text", "@title", "a unique title, 15–60 characters",
                   "{page} has no title, so search results show something generic or nothing useful."),
    "seo.title_length": R("show", "low", "text", "@title", "15–60 characters",
                          "The title of {page} is too short or too long for search results."),
    "seo.title_duplicate": R("show", "medium", "text", "@title", "a unique title per page",
                             "{page} has the same title as other pages, so they look identical in search results."),
    "seo.title_inherited": R("show", "medium", "text", "@title", "a page-specific title in this page's metadata",
                             "{page} uses the site-wide title instead of its own."),
    "seo.description": R("show", "medium", "text", "@description", "a unique description, 70–160 characters",
                         "{page} has no description, the short summary shown under the title in search results."),
    "seo.description_duplicate": R("show", "low", "text", "@description", "a unique description per page",
                                   "{page} has the same description as other pages."),
    "seo.description_inherited": R("show", "low", "text", "@description", "a page-specific description in this page's metadata",
                                   "{page} uses the site-wide description instead of its own."),
    "seo.alt": R("show", "low", "text", "@alt", 'descriptive alt text (alt="" for decorative images)',
                 "Images on {page} have no text description, so search engines and screen readers can't tell what they show."),
    "aeo.h1": R("show", "medium", "text", "@headings", "exactly one <h1> saying what the page is about",
                "{page} doesn't have exactly one main heading saying what the page is about."),
    "aeo.answer_first": R("show", "low", "text", "references/aeo-content.md#answer-first", "a 40–60 word direct answer under each question heading",
                          "Questions on {page} aren't followed by a short, direct answer that AI tools can quote."),
    "aeo.schema": R("show", "medium", "technical", "references/schema.md", "Organization + WebSite on the homepage; Article/Product/FAQPage where they apply",
                    "No page carries structured facts about your business (name, logo, what you offer) for Google and AI."),
    "aeo.schema_org": R("show", "medium", "technical", "references/schema.md#organization", "Organization + WebSite JSON-LD on the homepage",
                        "Your homepage doesn't describe your business in the structured format Google and AI read."),
    "aeo.schema_invalid": R("show", "high", "technical", "references/schema.md", "valid JSON-LD",
                            "The structured facts on {page} are broken, so Google and AI ignore them."),
    "seo.striking_distance": R("show", "medium", "text", "references/checks.md#striking-distance", "page 1 (position ≤ 7)",
                               "{page} is almost on Google's first page; a few fixes could push it up."),
    "seo.striking_queries": R("show", "medium", "text", "references/aeo-content.md#answer-first", "each query mapped to one page with an answer-first section",
                              "Some searches show your site on page 2 of Google; a short answer for each could move it up."),
    # Optional web-search checks
    "seo.keyword_gap": R("grow", "low", "text", "references/keyword-research.md#act", "a page that answers this search",
                         "People search “{query}” and find {others}, but not you."),
    "seo.keyword_low": R("grow", "low", "text", "references/keyword-research.md#act", "top 5 for this search",
                         "You show up for “{query}”, but only at #{rank}."),
    "geo.ai_not_cited": R("cite", "medium", "text", "references/ai-visibility.md#improve", "your site among the sources for this question",
                          "When people ask “{query}”, answers draw on {others}, not your site."),
    # Things only you can do
    "setup.live_url": R("you", "medium", "none", "suggestions.md#live-url", "a reachable production URL or a running dev server",
                        "Only your code was checked. Share your website address to also test the live site."),
    "setup.live_unreachable": R("you", "high", "none", "suggestions.md#live-url", "a reachable URL",
                                "Your website couldn't be reached, so the live checks were skipped."),
    "setup.gsc_csv": R("you", "low", "none", "suggestions.md#gsc-index-export", "Page indexing and Performance exports in .findable/inputs/",
                       "Optional: add Google Search Console exports to see which pages Google isn't indexing and which are close to page one."),
    "setup.gsc_index": R("you", "low", "none", "suggestions.md#gsc-index-export", "Page indexing export in .findable/inputs/",
                         "Optional: add the Search Console Page indexing export to see which pages Google isn't indexing, and why."),
    "setup.gsc_verify": R("you", "low", "none", "suggestions.md#gsc-verify", "site verified in Search Console",
                          "Make sure your site is connected to Google Search Console, so you can see how Google sees it."),
    "setup.submit_sitemap": R("you", "low", "none", "suggestions.md#submit-sitemap", "sitemap submitted in Search Console and Bing Webmaster Tools",
                              "Submit your sitemap to Google and Bing (Bing also powers ChatGPT search and Copilot)."),
}
UNKNOWN = Rule("show", "medium", "technical", "", "", "")


class _Vars(dict):
    def __missing__(self, key: str) -> str:
        return "?"


def describe(rule: str, url: str, who: str = "agent", **values) -> dict:
    """Group, plain sentence and change kind for a finding."""
    r = CATALOG.get(rule, UNKNOWN)
    group, kind = ("you", "none") if who == "user" else (r.group, r.kind)
    page = "your homepage" if url == "/" else ("your site" if url == "site" else f"the page {url}")
    text = r.plain.format_map(_Vars(page=page, **values)) if r.plain else ""
    return {"group": group, "plain": text[:1].upper() + text[1:], "change_kind": kind}
