# Next.js recipes

Use these with `generic.md`. Match the project's router: App Router (`app/`) or Pages Router (`pages/`).

## Legal pages
- App Router: `app/(legal)/privacy/page.tsx` etc. If the project has MDX set up, use `page.mdx` with the draft's markdown; otherwise render the markdown with the markdown library already in the project, or convert it to JSX.
- Export `metadata = { title: "Privacy Policy" }`.
- Add the links to the footer component used by `app/layout.tsx`.

## Consent banner
- A client component `components/consent-banner.tsx` (`"use client"`) that reads/writes the consent cookie and exposes it through a small context (`useConsent()`).
- Wrap tracker providers so they render only when consent is given:
  ```tsx
  const { analytics } = useConsent();
  return analytics ? <PostHogProvider client={posthog}>{children}</PostHogProvider> : <>{children}</>;
  ```
  Move `posthog.init(...)` (or `<GoogleAnalytics gaId=…/>` from `@next/third-parties`) inside that branch; never call it at module top level.
- `next/script` tags for pixels: render them only when `marketing` is true.
- Footer "Cookie settings" button calls `openConsent()` from the context.

## Global Privacy Control
In the consent context, on first load: `if (navigator.globalPrivacyControl) setConsent({ analytics: false, marketing: false, gpc: true })`. Server side, read `headers().get("sec-gpc")` where you set ad cookies.

## Fonts
Replace `<link href="https://fonts.googleapis.com/…">` with `next/font/google` (`import { Inter } from "next/font/google"`). It downloads the font at build time and serves it from your domain.

## Delete account / download data
- Server actions in `app/(account)/settings/actions.ts`: `deleteAccount()` and `exportData()`. Get the user from the session (`auth()`, `getServerSession`, Clerk `auth()`), never from form input.
- Prisma: delete child rows first or rely on `onDelete: Cascade`; then `prisma.user.delete({ where: { id } })`.
- Clerk/Auth0/Supabase: also delete the user in the provider (`clerkClient.users.deleteUser(id)`, `supabase.auth.admin.deleteUser(id)`).
- Stripe: `stripe.subscriptions.cancel(subId)` before deleting.
- Export: a route handler `app/api/account/export/route.ts` returning `new Response(JSON.stringify(data, null, 2), { headers: { "Content-Disposition": "attachment; filename=my-data.json" } })`.

## Cancel online (Stripe)
Route handler that creates a portal session and redirects:
```ts
const session = await stripe.billingPortal.sessions.create({ customer: user.stripeCustomerId, return_url: `${origin}/settings` });
return Response.redirect(session.url, 303);
```
Enable cancellation in the Stripe dashboard's portal settings (a user step).

## security.txt
`public/.well-known/security.txt`.

## html lang
`app/layout.tsx`: `<html lang="en">`.
