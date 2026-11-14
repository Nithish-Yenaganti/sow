# Build recipes (any framework)

Make the smallest change that fixes the finding, in the project's existing style and components. For Next.js, `nextjs.md` has framework-specific versions of these.

## Legal pages {#legal-pages}
1. `compliance draft <doc> --json`, ask the user for each `missing` fact, re-run.
2. Add the page where the project keeps pages: `/privacy`, `/terms`, `/cookies`, `/refunds`, `/acceptable-use`, `/copyright`, `/accessibility`, `/impressum`, `/ai`. Render the markdown with the project's existing markdown setup, or convert it to the project's page format.
3. **Keep the DRAFT notice at the top.**
4. Link every legal page from the site footer (and the Impressum from every page if in Germany/Austria).
5. Privacy policy already exists but is outdated: add only the missing service(s) to its "who we share with" section, matching its wording. Don't rewrite the user's policy.

## Consent banner and gated scripts {#consent-banner}
Goal: optional trackers load only **after** the visitor clicks Accept; Reject is as visible and as easy as Accept; the choice can be changed later.
1. Add a small banner component with three buttons of equal weight: **Accept all**, **Reject all**, **Settings** (per-category toggles: analytics, marketing). No pre-ticked toggles.
2. Store the choice in a first-party cookie or localStorage (`consent = {analytics: bool, marketing: bool, at: ISO date, version: 1}`) for at most 12 months.
3. Move each tracker's loader (script tag, `init()` call, provider component) behind the check: load it only when the relevant category is true, and also right after the visitor accepts.
4. Add a **Cookie settings** link in the footer that reopens the banner.
5. Google tags: also set Consent Mode defaults to `denied` before the tag loads and update to `granted` on accept.
6. If the user chose a consent platform (`consent_style=cmp`), add the platform's snippet instead and gate scripts with its categories.
7. Trackers the user chose to remove: delete the package, its init code and its env vars.

## Global Privacy Control and "Do Not Sell or Share" {#gpc}
- Treat `navigator.globalPrivacyControl === true` (browser) or the `Sec-GPC: 1` request header (server) as "reject marketing" automatically, and don't show a pre-accepted state.
- If the site shares data with ad networks, add a footer link **"Do Not Sell or Share My Personal Information"** that opens the consent settings with marketing off.

## Self-host fonts {#self-host-fonts}
Download the font files (or use `@fontsource/<font>`), serve them from the site, replace the `fonts.googleapis.com` link with a local `@font-face`, and delete the remote `<link>`/`@import`.

## Consent checkboxes {#consent-checkboxes}
Remove `checked`/`defaultChecked` from marketing or consent checkboxes. Each purpose gets its own unticked box (newsletter ≠ terms). Store the consent: user id, purpose, true/false, timestamp, policy version.

## Delete account {#delete-account}
- **Self-serve:** "Delete my account" in account settings → confirm dialog (type email or "DELETE") → server action that deletes or anonymises the user's rows (cascade), cancels any subscription at the payment provider, deletes their customer record there if appropriate, deletes uploaded files, and signs them out. Log the deletion (user id + date only).
- **Request form:** a form that emails the request to the contact address, and a note of the response deadline (EU 1 month, California 45 days).
- Don't forget third parties: remove the user from email lists and analytics (most analytics tools have a delete-person API).

## Download my data {#export-data}
"Download my data" in account settings → server route that gathers the user's own rows (profile, content, orders, consents) as JSON (and CSV for tables) and returns a file. Require a signed-in session; never accept a user id from the request.

## Correct data {#correct-data}
A profile form where users edit their name and email (re-verify a new email).

## Sign-up agreement (clickwrap) {#clickwrap}
Under the sign-up button: "By creating an account, you agree to our [Terms](/terms) and [Privacy Policy](/privacy)." Links open the pages. Optional but stronger: an unticked "I agree" box that's required. Save the accepted terms version and time on the user record.

## Hosted checkout {#hosted-checkout}
Replace card inputs with the provider's hosted checkout (Stripe Checkout, Paddle overlay) or embedded element (Stripe Payment Element). Delete the custom card fields and any code that sends card numbers to your server.

## Renewal disclosure {#renewal-disclosure}
Next to the subscribe button, in plain text (not a tooltip): "**Renews automatically** every month at $X until you cancel. Cancel anytime in Account → Billing." Trials: "Free for 14 days, then $X/month. We'll remind you before it ends." Use the real price and interval from the code.

## Cancel online {#cancel-online}
Add "Cancel subscription" in account billing: either link to the provider's customer portal (Stripe Billing Portal, Paddle, Lemon Squeezy) or call the API to set `cancel_at_period_end`. No "call us to cancel". Send a confirmation email.

## AI disclosure {#ai-disclosure}
- Chat: a line above the input: "You're chatting with an AI. It can make mistakes."
- Generated content: a small "AI-generated" label on the output, and a "Report" or thumbs-down link.
- Generated images/audio/video that look real: label them and keep the provider's metadata/watermark.
- Add the `ai-disclosure` page from `compliance draft ai-disclosure` and link it from the footer.

## Disclaimers {#disclaimers}
Show the notice where the advice appears (not only in the footer): "This is general information, not medical/financial/legal advice. Talk to a qualified professional about your situation." For AI answers in these areas, show it with every answer.

## Age gate {#age-gate}
Ask for date of birth at sign-up without hinting the cut-off. Under the minimum age: don't create the account, and don't keep the date. For teens: private-by-default settings, no ads profiling.

## Report content {#report-content}
A "Report" button on each post/comment/upload → small form (reason, details) → saved to a reports table and emailed to the contact address. Tell the reporter you received it.

## Secrets {#secrets}
Move the value to an environment variable (`process.env.X`, `os.environ["X"]`), add it to `.env.example` with a placeholder, make sure `.env*` is in `.gitignore`, and `git rm --cached` any tracked `.env`. Then tell the user to rotate the key.

## Password hashing {#password-hashing}
Use bcrypt (cost ≥ 12) or Argon2id via a maintained library. Re-hash old MD5/SHA-1 hashes when each user next signs in.

## security.txt {#security-txt}
Add `/.well-known/security.txt`:
```
Contact: mailto:<the user's security email>
Expires: <one year from today, ISO 8601>
Preferred-Languages: en
```

## Accessibility {#accessibility}
- `alt` text on every meaningful image (describe it); `alt=""` for decorative ones.
- `<html lang="en">` (the site's real language).
- Accessibility statement from `compliance draft accessibility`.

## Contact details {#contact}
Add the contact email (from the profile) to the footer and the privacy policy.

## Email {#email}
Every marketing email gets a working one-click unsubscribe link and the `List-Unsubscribe` header, plus the sender's postal address. Newsletter sign-up: unticked box, and double opt-in (confirmation email) for EU/UK.

## Third-party notices {#notices}
`compliance notices --json` writes the list. Copy it to `THIRD_PARTY_NOTICES.md` at the repo root and add a `/licenses` page (or footer link) that shows it.
