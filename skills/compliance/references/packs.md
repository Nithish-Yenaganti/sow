# Packs: what each business category adds

Every project gets the **baseline** pack. The intake's category answer, and what the scan finds in the code, switch on more packs. A business can have several (an AI SaaS gets baseline + payments + ai).

| Pack | Switched on by | Adds checks for |
|---|---|---|
| baseline | always | privacy policy, data map, cookie consent, tracking pixels, Google Fonts, pre-ticked boxes, delete/export/correct data, terms and sign-up agreement, open-source licenses, fonts/images/UI kits, marketing claims, secrets, password hashing, security.txt, alt text, page language, accessibility statement, contact details, Impressum, vendor DPAs, email unsubscribe, SMS consent, app stores |
| payments | SaaS or store category, "we charge" answer, or Stripe/Paddle/etc. in the code | card fields on your own form, refund and cancellation policy, auto-renewal disclosure, online cancel, sales tax/VAT |
| ai | AI category or an AI SDK in the code | AI labels, who owns AI output, AI provider's usage policy, training on user inputs (asked), AI sections in the privacy policy and terms |
| ugc | marketplace/community category or file uploads in the code | copyright (DMCA) page, report button, acceptable-use policy |
| regulated | health/finance/legal category or any sensitive data | "not professional advice" notices, sensitive-data laws (flagged for a lawyer) |
| kids | kids/education category or users under 18 | age check at sign-up, COPPA (flagged for a lawyer) |

## Who does what
- **agent**: the skill can build it after the user approves.
- **user**: only the user can do it (sign a DPA, register a DMCA agent, decide on a license).
- **lawyer**: the skill flags it and explains why; a lawyer decides.

## Regions
- **EU / UK**: GDPR and UK GDPR, ePrivacy/PECR cookie consent (opt-in, Reject as easy as Accept), 14-day withdrawal right, EU AI Act transparency, European Accessibility Act.
- **US: California**: CCPA/CPRA (notice, rights, "Do Not Sell or Share", Global Privacy Control), auto-renewal law, CalOPPA.
- **US: other states**: federal FTC rules, COPPA, CAN-SPAM, TCPA, ROSCA, plus state privacy laws similar to California's.
- **Somewhere else**: not checked in detail; the skill says so.

The source for every rule is in `sources.md`, under the ids shown in each finding's `sources`.
