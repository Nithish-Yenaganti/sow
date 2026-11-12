# Next.js fix recipes

App Router first, then Pages Router. Match the project's existing style (TS/JS, path aliases, where shared config lives). Check `next --version` in package.json: everything here works on Next 13.4+ App Router.

## title {#title}
**App Router:** give each page its own title. Set a template once in the root layout:
```tsx
// app/layout.tsx
export const metadata: Metadata = {
  metadataBase: new URL("https://example.com"),
  title: { default: "Brand: what you do", template: "%s | Brand" },
};
// app/pricing/page.tsx
export const metadata: Metadata = { title: "Pricing", description: "…" };
```
For dynamic pages, use `export async function generateMetadata({ params })`.
**A client page can't export metadata.** Put the metadata in a sibling `layout.tsx`, or split the page (see client-rendered below).
**Pages Router:** `<Head><title>…</title></Head>` from `next/head` in each page.

## description {#description}
Same place as the title: `description: "…"`. 70–160 characters, written from the page's actual content, unique per page.

## canonical {#canonical}
Set `metadataBase` in the root layout (above), then on each page:
```tsx
export const metadata: Metadata = { alternates: { canonical: "/pricing" } };
```
For dynamic routes, set it in `generateMetadata`. Never point every page at `/`; that's the usual cause of `seo.canonical_mismatch`.

## noindex {#noindex}
Look for `robots: { index: false }` in metadata (page *or* layout; a layout's applies to every child), `<meta name="robots" content="noindex">`, or an `X-Robots-Tag` header in `next.config.*`/middleware. These often come from a staging-only guard; make it environment-aware:
```tsx
robots: process.env.VERCEL_ENV === "production" ? { index: true, follow: true } : { index: false }
```

## client-rendered {#client-rendered}
Cause: `'use client'` at the top of `page.tsx`, so the whole page (and its data) renders in the browser.
**Option `server` (recommended):**
1. Remove `'use client'` from `page.tsx`.
2. Move hooks, state, event handlers and browser APIs into a new `components/<Name>Client.tsx` with `'use client'`.
3. Fetch the data in the server page (`async function Page()`) and pass it to the client component as props.
4. Keep the headings and main text in the server part, so they appear in the initial HTML.

**Option `prerender`:** keep the client component but make the content static. Pass the text as props from a server parent, or use `generateStaticParams` + static data for dynamic routes.
Verify with `curl -s URL | grep "<h1"`: the content must be in the raw HTML.

## headings {#headings}
Exactly one `<h1>` per page, stating the page's topic. Components rendering `<h1>` (heroes) are a frequent cause of duplicates. Make the level a prop.

## alt {#alt}
`<Image alt="…">` or `<img alt="…">`. Describe the image's content or purpose; use `alt=""` for purely decorative images.

## robots {#robots}
```ts
// app/robots.ts
import type { MetadataRoute } from "next";
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/" }],
    sitemap: "https://example.com/sitemap.xml",
  };
}
```
For AI bots, add per-bot rules from `references/ai-bots.md` (the option the user chose). Delete `public/robots.txt` if both exist: the static file wins and hides `app/robots.ts`.

## sitemap {#sitemap}
```ts
// app/sitemap.ts
import type { MetadataRoute } from "next";
const BASE = "https://example.com";
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes = ["", "/pricing", "/about"].map((p) => ({ url: `${BASE}${p}`, lastModified: new Date() }));
  // const posts = await getPosts(); …posts.map(p => ({ url: `${BASE}/blog/${p.slug}`, lastModified: p.updatedAt }))
  return [...staticRoutes];
}
```
- Build the route list from the same data source the pages use (CMS, MDX folder), not a hand-written list that goes stale.
- If `next-sitemap` is already used, patch its config (`siteUrl`, `exclude`) instead of adding `app/sitemap.ts`. Ask the user first (conflict rule).
- `seo.sitemap_host`: the base URL comes from an env var that is unset at build. Hardcode the production URL or make the env var required.

## broken-page {#broken-page}
A 404 that's linked or in the sitemap: fix the link, add a redirect in `next.config.*` (`redirects()`), or remove the sitemap entry. Ask which one if it's unclear whether the page should exist.

## redirects {#redirects}
Point links and the sitemap at the final URL. Collapse chains in `next.config.*` so each old URL redirects once to the final one.

## internal-links {#internal-links}
Add at least one contextual `<Link href="/page">` from a related, already-linked page (nav, footer, related posts, or in-body). Use descriptive anchor text, not "click here".
