# Vendors: terms and data processing agreements

When the scan finds a service that receives personal data, the user should (1) read its terms and usage policy and (2) accept or sign its DPA, then list it in the privacy policy. Many DPAs are already part of the terms you accepted at sign-up; some need a click in the dashboard.

Links change. If one is dead, search "<vendor> DPA" on the vendor's own site. Never accept anything for the user.

| Service | Terms / usage policy | DPA |
|---|---|---|
| Stripe | https://stripe.com/legal/ssa | https://stripe.com/legal/dpa |
| OpenAI | https://openai.com/policies/usage-policies/ | https://openai.com/policies/data-processing-addendum/ |
| Anthropic (Claude) | https://www.anthropic.com/legal/commercial-terms · https://www.anthropic.com/legal/aup | part of the commercial terms |
| Google Gemini API | https://ai.google.dev/gemini-api/terms | in the Gemini API terms |
| PostHog | https://posthog.com/terms | https://posthog.com/dpa |
| Google Analytics | https://marketingplatform.google.com/about/analytics/terms/us/ | https://business.safety.google/adsprocessorterms/ |
| Mixpanel | https://mixpanel.com/legal/terms-of-use/ | https://mixpanel.com/legal/dpa/ |
| Hotjar | https://www.hotjar.com/legal/policies/terms-of-service/ | https://www.hotjar.com/legal/support/dpa/ |
| Meta Pixel | https://www.facebook.com/legal/terms/businesstools | https://www.facebook.com/legal/terms/dataprocessing |
| Sentry | https://sentry.io/terms/ | https://sentry.io/legal/dpa/ |
| Vercel | https://vercel.com/legal/terms | https://vercel.com/legal/dpa |
| Supabase | https://supabase.com/terms | https://supabase.com/legal/dpa |
| Clerk | https://clerk.com/legal/terms | https://clerk.com/legal/dpa |
| Resend | https://resend.com/legal/terms-of-service | https://resend.com/legal/dpa |
| Twilio | https://www.twilio.com/en-us/legal/tos | https://www.twilio.com/en-us/legal/data-protection-addendum |

## What to look for in an AI provider's terms
- **Training:** is your API data used to train models? (Most API terms say no by default; check the account setting matches what your privacy policy says.)
- **Output ownership and indemnity:** who owns outputs, and does the provider defend you against copyright claims about them?
- **Usage policy:** what users may not generate. Your terms must pass this on to your users.
- **Retention:** how long prompts are kept, and whether zero-retention is available.
