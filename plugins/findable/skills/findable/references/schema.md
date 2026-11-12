# JSON-LD templates

Fill values only from the site's real content. Leave out properties you can't source; don't invent them. Use one `<script type="application/ld+json">` per page, ideally a `@graph`.

## Organization + WebSite (homepage) {#organization}
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://example.com/#org",
      "name": "Example Inc.",
      "url": "https://example.com/",
      "logo": "https://example.com/logo.png",
      "sameAs": ["https://www.linkedin.com/company/example", "https://x.com/example"]
    },
    {
      "@type": "WebSite",
      "@id": "https://example.com/#website",
      "url": "https://example.com/",
      "name": "Example",
      "publisher": { "@id": "https://example.com/#org" }
    }
  ]
}
```

## Article / BlogPosting
```json
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "≤ 110 chars, matches the H1",
  "datePublished": "2026-01-15",
  "dateModified": "2026-02-01",
  "author": { "@type": "Person", "name": "Real Author" },
  "publisher": { "@id": "https://example.com/#org" },
  "mainEntityOfPage": "https://example.com/blog/post"
}
```

## Product (with an offer)
```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Product name",
  "description": "From the page",
  "brand": { "@id": "https://example.com/#org" },
  "offers": { "@type": "Offer", "price": "49.00", "priceCurrency": "USD", "availability": "https://schema.org/InStock" }
}
```

## FAQPage (only if the questions and answers are visible on the page)
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    { "@type": "Question", "name": "Visible question?", "acceptedAnswer": { "@type": "Answer", "text": "The same answer shown on the page." } }
  ]
}
```

## BreadcrumbList
```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://example.com/" },
    { "@type": "ListItem", "position": 2, "name": "Blog", "item": "https://example.com/blog" }
  ]
}
```

## Next.js placement
In a server component page or layout:
```tsx
<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
```
