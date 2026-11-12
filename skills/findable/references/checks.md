# Checks

Each rule id appears in findings as `rule`. "Why" is what to tell the user when they ask.

## SEO

| Rule | Severity | Trigger | Why it matters |
|---|---|---|---|
| `seo.title` | high | No `<title>` | The title is the clickable headline in search results and the main relevance signal |
| `seo.title_inherited` | medium | Next.js page has no own title; uses the layout's | Every such page shows the same headline in results, so Google can't tell them apart |
| `seo.title_length` | low | < 15 or > 65 chars | Long titles get cut off; very short ones waste the headline |
| `seo.title_duplicate` | medium | Same title on several pages | Pages compete with each other; Google may pick the wrong one |
| `seo.description` | medium | No meta description | Google writes its own snippet, often a poor one; lower click-through |
| `seo.description_inherited` | low | Next.js page has no own description; uses the layout's | Same snippet for every page; generic results |
| `seo.description_duplicate` | low | Same description on several pages | Same as above |
| `seo.canonical` | low | No canonical link | Protects against duplicate URLs (params, trailing slash, www) splitting ranking |
| `seo.canonical_mismatch` | high | Canonical points to a different page | Tells Google to index *the other* page instead of this one |
| `seo.noindex_leak` | high | `noindex` on a public page | The page is removed from Google and can't be cited by AI search |
| `seo.robots` | medium | No robots.txt | Not fatal, but it's where you point crawlers at the sitemap |
| `seo.robots_blocks_all` | critical | `User-agent: *` + `Disallow: /` | Nothing on the site can be crawled; a common leftover from staging |
| `seo.sitemap` | high | No working sitemap | Crawlers discover pages more slowly; Bing (which feeds ChatGPT search/Copilot) relies on it heavily |
| `seo.sitemap_host` | high | Sitemap lists another host | Usually localhost/staging URLs baked in at build; crawlers ignore or follow the wrong URLs |
| `seo.sitemap_missing` | medium | Routes not in the sitemap | Those pages are discovered late or not at all |
| `seo.sitemap_dead` | medium | Sitemap URLs that 404/redirect | Wastes crawl budget and lowers trust in the sitemap |
| `seo.status` | high | Page returns 4xx/5xx or fails | Broken pages drop out of the index |
| `seo.redirect_chain` | low | > 1 redirect hop | Slower, and some crawlers give up after a few hops |
| `seo.alt` | low | Images without alt | Image search, accessibility, and context for AI |
| `seo.orphan` | low | Nothing links to a page | Crawlers find and rank pages through internal links |

### Striking distance
`seo.striking_distance` (from the Search Console CSV): a page averages position 8–20 with ≥ 50 impressions. It sits at the bottom of page 1 or on page 2, which is the cheapest traffic to win. The finding's `evidence` lists other issues on the same page; fix those first. Then strengthen the page: a clearer title for the query, an answer-first section, internal links from strong pages, and more depth than the pages ranking above it.

`seo.striking_queries`: queries in positions 8–20. Map each one to the single best page, then add an answer-first section for it there.

## AEO (answer engines)

| Rule | Severity | Trigger | Why |
|---|---|---|---|
| `aeo.h1` | medium/low | 0 or several `<h1>` | The H1 states what the page is about; answer engines use it to scope the page |
| `aeo.answer_first` | low | Question heading not followed by a short answer | Featured snippets and AI answers quote the paragraph right under a question |
| `aeo.schema` | medium | No JSON-LD anywhere | Structured data is how engines extract facts (who you are, products, FAQs) |
| `aeo.schema_org` | medium | Homepage lacks Organization/WebSite | Establishes your brand as an entity: name, logo, profiles |
| `aeo.schema_invalid` | high | JSON-LD doesn't parse | Invalid schema is ignored entirely |

## GEO (AI engines)

| Rule | Severity | Trigger | Why |
|---|---|---|---|
| `geo.no_js_view` | critical | Served HTML is an empty app shell | Most AI crawlers don't run JavaScript; they see a blank page and can't cite it |
| `geo.client_rendered` | high/medium | Next.js page file starts with `'use client'` | Risk of the above; content fetched in the browser is invisible to AI crawlers |
| `geo.robots_ai` | high | robots.txt blocks AI *search* bots | Those bots fetch pages to cite them in ChatGPT/Perplexity/Claude answers |
| `geo.bot_access` | critical/medium | Bots get 403/challenge while browsers get 200 | The CDN/WAF blocks them regardless of robots.txt; you're invisible to AI search. **User step** (see `playbooks/cdn.md`) |

## Setup (user steps)
`setup.live_url`, `setup.live_unreachable`, `setup.gsc_csv`, `setup.gsc_verify`, `setup.submit_sitemap`: see `suggestions.md`.
