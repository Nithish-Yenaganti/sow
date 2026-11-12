# Generic fix recipes (any framework)

Find where the framework sets `<head>` content, then apply the recipe there:

| Framework | Head / metadata | robots / sitemap |
|---|---|---|
| Astro | `<head>` in the layout (`src/layouts/*.astro`), props per page | `public/robots.txt`, `@astrojs/sitemap` |
| Nuxt | `useHead()` / `useSeoMeta()` in pages, `app.head` in nuxt.config | `@nuxtjs/sitemap`, `@nuxtjs/robots` or `public/robots.txt` |
| SvelteKit | `<svelte:head>` in `+page.svelte` | `static/robots.txt`, a `src/routes/sitemap.xml/+server.ts` |
| Remix / React Router | `export const meta` per route | `public/robots.txt`, a `sitemap[.]xml` resource route |
| Gatsby | Head API (`export const Head`) | `gatsby-plugin-sitemap`, `static/robots.txt` |
| Hugo | `layouts/partials/head.html` | built-in sitemap; `enableRobotsTXT = true` |
| Jekyll | `_includes/head.html`, `jekyll-seo-tag` | `jekyll-sitemap` |
| Plain HTML | each `.html` file's `<head>` | `robots.txt`, `sitemap.xml` at the web root |
| WordPress | SEO plugin (Yoast/RankMath) settings or theme `header.php` | plugin-generated |

## title {#title}
`<title>Page topic | Brand</title>`: unique, 15–60 characters, the main topic first.

## description {#description}
`<meta name="description" content="…">`: 70–160 characters, from the page's real content.

## canonical {#canonical}
`<link rel="canonical" href="https://example.com/this-page">`: absolute, self-referencing, using the same trailing-slash style as the sitemap.

## noindex {#noindex}
Remove `<meta name="robots" content="noindex">` or the `X-Robots-Tag: noindex` header (server/CDN config) from pages that should be found. If it's a staging guard, make it environment-specific.

## client-rendered {#client-rendered}
Make the main content part of the initial HTML: use the framework's SSR/SSG mode for that page (Astro: avoid `client:only` for content; Nuxt: `ssr: true` / route rules; SvelteKit: `export const ssr = true`, `prerender = true`; plain SPA: pre-render with a static build step). Keep interactivity as islands/components.

## headings {#headings}
One `<h1>` per page. Make the heading level of reused hero components configurable.

## alt {#alt}
Add `alt` to every `<img>`. Use `alt=""` for decorative ones.

## robots {#robots}
```txt
User-agent: *
Allow: /

Sitemap: https://example.com/sitemap.xml
```
Add AI-bot groups from `references/ai-bots.md` per the user's choice.

## sitemap {#sitemap}
Prefer the framework's sitemap plugin (table above). Otherwise write a static `sitemap.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/pricing</loc></url>
</urlset>
```
List only final, indexable, 200-status URLs on the production host. Reference it in robots.txt.

## broken-page {#broken-page}
Fix the link, add a 301 redirect (server/host config: `_redirects`, `vercel.json`, `.htaccess`, nginx), or remove it from the sitemap. Ask the user if it's unclear whether the page should exist.

## redirects {#redirects}
Link straight to final URLs; make each legacy URL redirect once.

## internal-links {#internal-links}
Link to the page from at least one related page with descriptive anchor text.
