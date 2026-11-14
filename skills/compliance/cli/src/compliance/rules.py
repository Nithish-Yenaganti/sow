"""Rule catalog. Every finding comes from one rule here.

who:  agent  = the skill can build the fix (after the user agrees)
      user   = only the user can do it (sign a DPA, register, decide)
      lawyer = needs a lawyer; the skill only flags it
Every rule cites source ids from references/sources.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}

GROUPS = {
    "privacy": "What data you collect and what your policy says",
    "cookies": "Cookies and tracking",
    "rights": "Can users see, fix and delete their data?",
    "terms": "Terms users agree to",
    "payments": "Payments, refunds and cancelling",
    "ai": "AI features",
    "licenses": "Code you didn't write (open-source licenses)",
    "assets": "Fonts, images and design assets",
    "claims": "What your marketing says",
    "content": "Advice, age limits and user content",
    "security": "Security basics",
    "access": "Accessibility and contact details",
    "vendors": "Services you share data with",
}


@dataclass(frozen=True)
class Rule:
    id: str
    group: str
    pack: str
    severity: str
    who: str
    title: str
    plain: str            # may contain {subject}, {detail}
    fix: str              # playbook / suggestions anchor
    sources: tuple[str, ...] = ()


def _r(*a, sources=()):
    return Rule(*a, sources=tuple(sources))


RULES: dict[str, Rule] = {r.id: r for r in [
    # privacy
    _r("privacy.policy_missing", "privacy", "baseline", "high", "agent", "No privacy policy",
       "There's no privacy policy page. Anyone who collects personal data (even an email address or analytics) needs one.",
       "playbooks/generic.md#legal-pages", sources=["gdpr-13", "caloppa", "cpra"]),
    _r("privacy.policy_outdated", "privacy", "baseline", "medium", "agent", "Privacy policy doesn't name a service you use",
       "Your privacy policy doesn't mention {subject}, which your code sends data to.",
       "playbooks/generic.md#legal-pages", sources=["gdpr-13"]),
    # cookies & tracking
    _r("cookies.no_consent", "cookies", "baseline", "high", "agent", "Tracker loads without consent",
       "{subject} loads for every visitor before they agree to tracking.",
       "playbooks/generic.md#consent-banner", sources=["eprivacy-5-3", "edpb-consent", "ico-cookies"]),
    _r("cookies.policy_missing", "cookies", "baseline", "medium", "agent", "No cookie policy",
       "There's no cookie policy listing the cookies and trackers your site uses.",
       "playbooks/generic.md#legal-pages", sources=["eprivacy-5-3", "ico-cookies"]),
    _r("cookies.session_replay", "cookies", "baseline", "high", "lawyer", "Session recording tool",
       "{subject} records what visitors do on the page. In the US this has led to wiretap-law lawsuits; in the EU/UK it needs consent first.",
       "suggestions.md#lawyer", sources=["cipa", "eprivacy-5-3"]),
    _r("cookies.ad_pixel", "cookies", "baseline", "high", "lawyer", "Advertising pixel",
       "{subject} shares visitor data with an ad network. That counts as 'selling or sharing' under California law and needs consent in the EU/UK.",
       "suggestions.md#lawyer", sources=["cpra", "eprivacy-5-3", "vppa"]),
    _r("cookies.gpc_missing", "cookies", "baseline", "medium", "agent", "Global Privacy Control not honored",
       "Your site doesn't respond to the browser's Global Privacy Control signal, which California treats as a valid opt-out.",
       "playbooks/generic.md#gpc", sources=["cppa-regs"]),
    _r("cookies.do_not_sell_missing", "cookies", "baseline", "medium", "agent", "No 'Do Not Sell or Share' link",
       "You share data with ad networks but have no 'Do Not Sell or Share My Personal Information' link for California users.",
       "playbooks/generic.md#gpc", sources=["cpra"]),
    _r("cookies.remote_google_fonts", "assets", "baseline", "medium", "agent", "Fonts load from Google's servers",
       "Your fonts load from Google's servers, which sends each visitor's IP address to Google. A German court fined a site for this; host the fonts yourself.",
       "playbooks/generic.md#self-host-fonts", sources=["lg-munich-fonts"]),
    # consent
    _r("consent.prechecked", "privacy", "baseline", "high", "agent", "Pre-ticked consent box",
       "A sign-up or marketing checkbox is ticked by default in {subject}. Consent only counts if the user ticks it themselves.",
       "playbooks/generic.md#consent-checkboxes", sources=["gdpr-7", "edpb-consent", "planet49"]),
    # rights
    _r("rights.delete_missing", "rights", "baseline", "high", "agent", "Users can't delete their account",
       "Users can create an account but there's no way to delete it.",
       "playbooks/generic.md#delete-account", sources=["gdpr-17", "cpra", "apple-5-1-1"]),
    _r("rights.export_missing", "rights", "baseline", "medium", "agent", "Users can't download their data",
       "Users can't download a copy of their data.",
       "playbooks/generic.md#export-data", sources=["gdpr-15", "gdpr-20", "cpra"]),
    _r("rights.correct_missing", "rights", "baseline", "low", "agent", "Users can't correct their details",
       "There's no page where users can update their own details.",
       "playbooks/generic.md#correct-data", sources=["gdpr-16", "cpra"]),
    # terms
    _r("terms.missing", "terms", "baseline", "high", "agent", "No terms of service",
       "There are no terms of service, so there's no agreement covering accounts, payments or acceptable use.",
       "playbooks/generic.md#legal-pages", sources=["clickwrap"]),
    _r("terms.no_clickwrap", "terms", "baseline", "medium", "agent", "Sign-up doesn't show the terms",
       "The sign-up form in {subject} doesn't link to your terms and privacy policy, so users never clearly agree to them.",
       "playbooks/generic.md#clickwrap", sources=["clickwrap"]),
    # payments
    _r("payments.raw_card_fields", "payments", "payments", "high", "agent", "Card numbers typed into your own form",
       "{subject} has its own card-number field. Use your payment provider's hosted checkout or card element so card data never touches your servers.",
       "playbooks/generic.md#hosted-checkout", sources=["pci-dss"]),
    _r("payments.refund_missing", "payments", "payments", "high", "agent", "No refund and cancellation policy",
       "You charge money but have no refund and cancellation policy.",
       "playbooks/generic.md#legal-pages", sources=["eu-crd", "ftc-rosca"]),
    _r("payments.renewal_disclosure", "payments", "payments", "high", "agent", "Checkout doesn't say it renews",
       "Your subscription checkout doesn't clearly say it renews automatically, how often, and how to cancel.",
       "playbooks/generic.md#renewal-disclosure", sources=["ca-arl", "ftc-rosca"]),
    _r("payments.cancel_missing", "payments", "payments", "high", "agent", "No online cancel",
       "Users can subscribe online but there's no way to cancel online.",
       "playbooks/generic.md#cancel-online", sources=["ca-arl", "ftc-rosca"]),
    _r("payments.tax", "payments", "payments", "medium", "user", "Sales tax / VAT",
       "You charge money, so you need a plan for sales tax and VAT: register where required, or use a merchant of record that handles it.",
       "suggestions.md#sales-tax", sources=["eu-vat-oss"]),
    # ai
    _r("ai.disclosure_missing", "ai", "ai", "high", "agent", "AI output isn't labeled",
       "Your app uses {subject} but nothing tells users they're seeing AI-generated content or talking to an AI.",
       "playbooks/generic.md#ai-disclosure", sources=["eu-ai-act-50"]),
    _r("ai.output_ip", "ai", "ai", "medium", "lawyer", "Who owns AI output",
       "Purely AI-generated content usually can't be copyrighted in the US, so your terms shouldn't promise users full ownership. A lawyer should word this.",
       "suggestions.md#lawyer", sources=["copyright-ai"]),
    _r("ai.provider_terms", "ai", "ai", "low", "user", "AI provider's usage policy",
       "Read {subject}'s usage policy and output terms: your users must follow them too, and they say whether your data is used for training.",
       "references/vendors.md", sources=["vendor-terms"]),
    # licenses
    _r("licenses.network_copyleft", "licenses", "baseline", "high", "user", "AGPL/SSPL dependency",
       "{subject} uses the {detail} license. If your app runs it on a server for users, you may have to publish your own source code.",
       "references/licenses.md#network-copyleft", sources=["spdx", "agpl"]),
    _r("licenses.strong_copyleft", "licenses", "baseline", "high", "user", "GPL dependency",
       "{subject} uses the {detail} license. Shipping it in your app's code can require releasing your code under the GPL.",
       "references/licenses.md#strong-copyleft", sources=["spdx", "gpl"]),
    _r("licenses.restricted", "licenses", "baseline", "high", "user", "Source-available license",
       "{subject} uses {detail}, which isn't open source and limits commercial or competing use.",
       "references/licenses.md#restricted", sources=["spdx"]),
    _r("licenses.unknown", "licenses", "baseline", "medium", "user", "Packages with no clear license",
       "{subject} package(s) have no clear license, which means you may not have permission to use them: {detail}.",
       "references/licenses.md#unknown", sources=["spdx"]),
    _r("licenses.unchecked", "licenses", "baseline", "low", "user", "Licenses couldn't be read",
       "Dependency licenses couldn't be read ({detail}). Install dependencies, then run the scan again.",
       "references/licenses.md#unchecked", sources=["spdx"]),
    _r("licenses.notices_missing", "licenses", "baseline", "low", "agent", "No third-party notices",
       "Most open-source licenses require keeping their copyright notice. There's no third-party licenses file or page.",
       "playbooks/generic.md#notices", sources=["spdx", "osi"]),
    # assets
    _r("assets.stock_watermark", "assets", "baseline", "high", "user", "Possibly unlicensed stock image",
       "{subject} looks like a stock-photo preview (the name mentions a stock site). Preview images aren't licensed for use.",
       "references/licenses.md#assets", sources=["copyright-basics"]),
    _r("assets.font_files", "assets", "baseline", "medium", "user", "Font files without a license",
       "The project ships {detail} font file(s) with no license file next to them. Desktop font licenses often don't cover websites or apps.",
       "references/licenses.md#fonts", sources=["copyright-basics"]),
    _r("assets.images_unknown", "assets", "baseline", "low", "user", "Images with unknown source",
       "The project has {detail} image(s). Make sure you made them, bought them, or their license allows this use.",
       "references/licenses.md#assets", sources=["copyright-basics"]),
    _r("assets.ui_kit", "assets", "baseline", "low", "user", "Paid template or UI kit",
       "{subject} mentions a paid template or UI kit. Check your license covers this project (many cover only one).",
       "references/licenses.md#assets", sources=["copyright-basics"]),
    # claims
    _r("claims.compliance_claim", "claims", "baseline", "high", "user", "Compliance or certification claim",
       "Your site says \"{detail}\" ({subject}). Only claim a certification or compliance you can prove; the FTC treats false ones as deceptive.",
       "references/claims.md", sources=["ftc-act-5"]),
    _r("claims.unverified", "claims", "baseline", "medium", "user", "Claim that needs evidence",
       "Your site says \"{detail}\" ({subject}). Keep it only if you have evidence today.",
       "references/claims.md", sources=["ftc-act-5", "ftc-endorsements", "ftc-reviews-rule"]),
    # content
    _r("advice.disclaimer_missing", "content", "regulated", "high", "agent", "High-risk advice without a disclaimer",
       "Your content talks about {detail} but there's no 'this isn't professional advice' notice where it appears.",
       "playbooks/generic.md#disclaimers", sources=["ftc-act-5"]),
    _r("regulated.sensitive", "content", "regulated", "high", "lawyer", "Sensitive data",
       "You handle {subject} data. That brings extra laws ({detail}) that a lawyer should review.",
       "suggestions.md#lawyer", sources=["gdpr-9", "hipaa", "mhmda", "bipa"]),
    _r("kids.age_gate_missing", "content", "kids", "high", "agent", "No age check",
       "Young people may use the app, but there's no age check at sign-up.",
       "playbooks/generic.md#age-gate", sources=["coppa", "gdpr-8", "uk-aadc"]),
    _r("kids.coppa", "content", "kids", "high", "lawyer", "Children under 13",
       "Children under 13 may use it. COPPA requires verified parental consent before collecting their data; get a lawyer before launch.",
       "suggestions.md#lawyer", sources=["coppa"]),
    _r("ugc.dmca_missing", "content", "ugc", "high", "agent", "No copyright takedown page",
       "Users can upload content but there's no copyright (DMCA) takedown page.",
       "playbooks/generic.md#legal-pages", sources=["dmca-512"]),
    _r("ugc.report_missing", "content", "ugc", "medium", "agent", "No way to report content",
       "Users can post content but there's no way to report harmful or illegal posts.",
       "playbooks/generic.md#report-content", sources=["eu-dsa"]),
    _r("ugc.aup_missing", "content", "ugc", "medium", "agent", "No content rules",
       "There's no acceptable-use policy saying what users may not post.",
       "playbooks/generic.md#legal-pages", sources=["eu-dsa"]),
    # security
    _r("security.secret_in_repo", "security", "baseline", "high", "agent", "Secret key in the code",
       "A {detail} is written into {subject}. Move it to an environment variable, then rotate it (anyone with the code has it).",
       "playbooks/generic.md#secrets", sources=["owasp-secrets"]),
    _r("security.env_tracked", "security", "baseline", "high", "agent", ".env file in git",
       "{subject} is committed to git, so every secret in it is in the repo history.",
       "playbooks/generic.md#secrets", sources=["owasp-secrets"]),
    _r("security.weak_hash", "security", "baseline", "high", "agent", "Weak password hashing",
       "{subject} hashes passwords with {detail}, which can be cracked fast. Use bcrypt, scrypt or Argon2.",
       "playbooks/generic.md#password-hashing", sources=["owasp-passwords"]),
    _r("security.txt_missing", "security", "baseline", "low", "agent", "No security.txt",
       "There's no /.well-known/security.txt telling researchers how to report a security problem.",
       "playbooks/generic.md#security-txt", sources=["rfc9116"]),
    # accessibility & identity
    _r("a11y.img_alt", "access", "baseline", "medium", "agent", "Images without alt text",
       "{detail} image(s) have no alt text, so screen-reader users can't tell what they show.",
       "playbooks/generic.md#accessibility", sources=["wcag22", "eaa", "ada"]),
    _r("a11y.html_lang", "access", "baseline", "low", "agent", "Page language not set",
       "{subject} doesn't set the page language (<html lang>), which screen readers need.",
       "playbooks/generic.md#accessibility", sources=["wcag22"]),
    _r("a11y.statement_missing", "access", "baseline", "low", "agent", "No accessibility statement",
       "You serve EU/UK consumers but have no accessibility statement.",
       "playbooks/generic.md#legal-pages", sources=["eaa"]),
    _r("identity.contact_missing", "access", "baseline", "medium", "agent", "No contact details",
       "The site shows no contact email or contact page. Privacy laws require a way to reach you.",
       "playbooks/generic.md#contact", sources=["gdpr-13", "eu-ecommerce-5"]),
    _r("identity.impressum_missing", "access", "baseline", "medium", "agent", "No Impressum",
       "You're based in Germany or Austria, which requires an Impressum page naming the business.",
       "playbooks/generic.md#legal-pages", sources=["de-ddg-5"]),
    # vendors & comms
    _r("vendors.dpa", "vendors", "baseline", "low", "user", "Data processing agreements",
       "You send personal data to {detail}. Accept or sign each one's data processing agreement (DPA) and list them in your privacy policy.",
       "references/vendors.md", sources=["gdpr-28"]),
    _r("email.unsubscribe_missing", "vendors", "baseline", "medium", "agent", "Marketing email without unsubscribe",
       "You send marketing email but there's no unsubscribe link in the code.",
       "playbooks/generic.md#email", sources=["can-spam", "pecr"]),
    _r("sms.consent", "vendors", "baseline", "medium", "lawyer", "Text messages",
       "You send SMS with {subject}. US law (TCPA) needs clear written consent for marketing texts, with heavy per-message fines.",
       "suggestions.md#lawyer", sources=["tcpa"]),
    _r("mobile.app_store", "vendors", "baseline", "medium", "user", "App store privacy rules",
       "There's a mobile app. Apple and Google require in-app account deletion and accurate privacy labels before review.",
       "suggestions.md#app-stores", sources=["apple-5-1-1", "play-deletion"]),
]}


@dataclass
class Finding:
    rule: str
    subject: str = ""
    detail: str = ""
    files: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    severity: str | None = None

    @property
    def fingerprint(self) -> str:
        return f"{self.rule}|{self.subject}" if self.subject else self.rule

    def to_dict(self) -> dict:
        r = RULES[self.rule]
        return {
            "fingerprint": self.fingerprint, "rule": r.id, "group": r.group, "group_title": GROUPS[r.group],
            "pack": r.pack, "severity": self.severity or r.severity, "who": r.who, "title": r.title,
            "plain": r.plain.format(subject=self.subject, detail=self.detail),
            "subject": self.subject, "detail": self.detail, "files": self.files[:10], "evidence": self.evidence[:5],
            "fix": r.fix, "sources": list(r.sources),
        }
