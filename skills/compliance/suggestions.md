# User steps

Things only the user (or their lawyer) can do. Give the exact steps, then say what it unlocks.

## Install uv {#install-uv}
The skill's CLI runs with uv: https://docs.astral.sh/uv/getting-started/installation/ (macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`). Then run `/compliance` again.

## Take it to a lawyer {#lawyer}
Bring: `.compliance/report.md`, the drafts in `.compliance/drafts/`, and `references/sources.md` (what each check is based on). Ask them to (1) review every page marked DRAFT, (2) answer each ⚖️ item, (3) write the liability and AI-output clauses in the terms. A privacy or tech lawyer can usually do this as a fixed-fee review.

## Sales tax and VAT {#sales-tax}
Pick one:
- **Merchant of record** (Paddle, Lemon Squeezy, Polar): they sell to the customer and handle tax worldwide. Simplest.
- **Do it yourself** (Stripe): turn on Stripe Tax, register where you pass thresholds (EU VAT One-Stop Shop for EU consumers, US states by economic nexus), and file returns. An accountant should confirm.

## Data processing agreements {#dpa}
For each service in `references/vendors.md`: open its DPA, accept it (often a dashboard toggle or it's part of the terms), and save a copy. List every service in your privacy policy.

## Consent platform {#cmp}
Sign up (Cookiebot, Osano, Termly, Usercentrics…), add your domain, run its cookie scan, then give the agent the script snippet and the category names.

## Rotate leaked secrets {#rotate-secrets}
In the provider's dashboard (Stripe → Developers → API keys, AWS IAM, GitHub tokens…) create a new key, put it in your environment variables and hosting settings, then delete the old key. Moving the key in code doesn't remove it from git history.

## Register a DMCA agent {#dmca-agent}
https://www.copyright.gov/dmca-directory/: register your designated agent (small fee, renew every 3 years). Use the same details as your copyright page.

## App stores {#app-stores}
- Apple: in-app account deletion (Guideline 5.1.1(v)), the privacy "nutrition label" in App Store Connect, and the privacy manifest.
- Google Play: the Data safety form and an account deletion link/URL in Play Console.

## Things outside the code
Register a legal entity, run a trademark search on your name, get IP assignment agreements from anyone who built the product, keep evidence for marketing claims, and consider cyber/E&O insurance once you have paying customers.
