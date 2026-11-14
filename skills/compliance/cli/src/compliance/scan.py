"""Read-only project scan: what the code collects, loads, ships and says.

Everything here reads files. Nothing is written except by the caller (cli.py) into .compliance/.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from compliance import licenses as lic
from compliance.rules import Finding

SKIP_DIRS = {"node_modules", ".git", ".next", ".nuxt", ".svelte-kit", ".astro", "dist", "build", "out", ".venv", "venv",
             "vendor", "coverage", ".compliance", ".findable", ".turbo", ".vercel", ".output", "__pycache__", ".cache",
             "target", "Pods", ".expo"}
TEXT_EXT = {".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro", ".md", ".mdx",
            ".php", ".erb", ".liquid", ".njk", ".hbs", ".py", ".rb", ".go", ".json", ".prisma", ".sql", ".yml", ".yaml",
            ".toml", ".txt", ".env", ".sh"}
UI_EXT = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".md", ".mdx", ".php", ".erb", ".liquid",
          ".njk", ".hbs", ".js", ".ts"}
CONTENT_EXT = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".md", ".mdx", ".php", ".erb", ".liquid",
               ".njk", ".hbs"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}
FONT_EXT = {".woff", ".woff2", ".ttf", ".otf", ".eot"}
MAX_BYTES = 400_000
TEST_RE = re.compile(r"(^|/)(tests?|__tests__|spec|e2e|fixtures|__mocks__|stories)(/|$)|\.(test|spec|stories)\.", re.I)

# --- vendors -----------------------------------------------------------------------------------------------
# kind: analytics | replay | ads | payments | ai | email | sms | auth | chat | errors | storage | consent
VENDORS: dict[str, dict] = {
    "google_analytics": dict(name="Google Analytics / Tag Manager", kind="analytics",
                             pkgs=["react-ga4", "vue-gtag", "@next/third-parties", "ga-4-react", "react-gtm-module"],
                             pats=[r"googletagmanager\.com", r"google-analytics\.com", r"\bgtag\(", r"<GoogleAnalytics\b", r"<GoogleTagManager\b"]),
    "posthog": dict(name="PostHog", kind="analytics", pkgs=["posthog-js", "posthog-node"], py=["posthog"],
                    pats=[r"posthog\.init\(", r"i\.posthog\.com"]),
    "mixpanel": dict(name="Mixpanel", kind="analytics", pkgs=["mixpanel-browser", "mixpanel"], py=["mixpanel"], pats=[r"mixpanel\.init\("]),
    "segment": dict(name="Segment", kind="analytics", pkgs=["@segment/analytics-next", "@segment/analytics-node", "analytics-node"],
                    pats=[r"cdn\.segment\.com"]),
    "amplitude": dict(name="Amplitude", kind="analytics", pkgs=["@amplitude/analytics-browser", "amplitude-js"], pats=[]),
    "plausible": dict(name="Plausible", kind="analytics", cookieless=True, pkgs=["next-plausible", "plausible-tracker"], pats=[r"plausible\.io/js"]),
    "fathom": dict(name="Fathom", kind="analytics", cookieless=True, pkgs=["fathom-client"], pats=[r"cdn\.usefathom\.com"]),
    "vercel_analytics": dict(name="Vercel Analytics", kind="analytics", cookieless=True, pkgs=["@vercel/analytics", "@vercel/speed-insights"], pats=[]),
    "umami": dict(name="Umami", kind="analytics", cookieless=True, pkgs=[], pats=[r"umami\.is/script", r"cloud\.umami\.is"]),
    "hotjar": dict(name="Hotjar", kind="replay", pkgs=["@hotjar/browser", "react-hotjar"], pats=[r"static\.hotjar\.com"]),
    "fullstory": dict(name="FullStory", kind="replay", pkgs=["@fullstory/browser"], pats=[r"fullstory\.com/s/fs\.js", r"edge\.fullstory\.com"]),
    "clarity": dict(name="Microsoft Clarity", kind="replay", pkgs=["@microsoft/clarity", "react-microsoft-clarity"], pats=[r"clarity\.ms/tag"]),
    "logrocket": dict(name="LogRocket", kind="replay", pkgs=["logrocket"], pats=[r"cdn\.logrocket"]),
    "sentry_replay": dict(name="Sentry Session Replay", kind="replay", pkgs=[], pats=[r"replayIntegration\(", r"new\s+Sentry\.Replay\("]),
    "meta_pixel": dict(name="Meta (Facebook) Pixel", kind="ads", pkgs=["react-facebook-pixel"], pats=[r"connect\.facebook\.net", r"\bfbq\(\s*['\"]init"]),
    "tiktok_pixel": dict(name="TikTok Pixel", kind="ads", pkgs=[], pats=[r"analytics\.tiktok\.com", r"\bttq\.load\("]),
    "linkedin_insight": dict(name="LinkedIn Insight Tag", kind="ads", pkgs=[], pats=[r"snap\.licdn\.com", r"_linkedin_partner_id"]),
    "google_ads": dict(name="Google Ads", kind="ads", pkgs=[], pats=[r"googleadservices\.com", r"['\"]AW-\d{6,}"]),
    "x_pixel": dict(name="X (Twitter) Pixel", kind="ads", pkgs=[], pats=[r"static\.ads-twitter\.com", r"\btwq\(\s*['\"]config"]),
    "intercom": dict(name="Intercom", kind="chat", pkgs=["@intercom/messenger-js-sdk", "react-use-intercom"], pats=[r"widget\.intercom\.io"]),
    "crisp": dict(name="Crisp", kind="chat", pkgs=["crisp-sdk-web"], pats=[r"client\.crisp\.chat"]),
    "sentry": dict(name="Sentry", kind="errors", pkgs=["@sentry/nextjs", "@sentry/browser", "@sentry/react", "@sentry/node", "@sentry/vue"],
                   py=["sentry-sdk"], pats=[]),
    "stripe": dict(name="Stripe", kind="payments", pkgs=["stripe", "@stripe/stripe-js", "@stripe/react-stripe-js"], py=["stripe"], pats=[r"js\.stripe\.com"]),
    "paddle": dict(name="Paddle", kind="payments", pkgs=["@paddle/paddle-js", "@paddle/paddle-node-sdk"], pats=[r"cdn\.paddle\.com"]),
    "lemonsqueezy": dict(name="Lemon Squeezy", kind="payments", pkgs=["@lemonsqueezy/lemonsqueezy.js"], pats=[r"app\.lemonsqueezy\.com"]),
    "polar": dict(name="Polar", kind="payments", pkgs=["@polar-sh/sdk", "@polar-sh/nextjs"], pats=[]),
    "shopify": dict(name="Shopify", kind="payments", pkgs=["@shopify/hydrogen", "@shopify/shopify-api", "@shopify/storefront-api-client"],
                    pats=[r"SHOPIFY_STORE_DOMAIN", r"\.myshopify\.com"]),
    "paypal": dict(name="PayPal", kind="payments", pkgs=["@paypal/react-paypal-js", "@paypal/paypal-js"], pats=[r"paypal\.com/sdk/js"]),
    "openai": dict(name="OpenAI", kind="ai", pkgs=["openai", "@ai-sdk/openai"], py=["openai"], pats=[]),
    "anthropic": dict(name="Anthropic (Claude)", kind="ai", pkgs=["@anthropic-ai/sdk", "@ai-sdk/anthropic"], py=["anthropic"], pats=[]),
    "google_ai": dict(name="Google Gemini", kind="ai", pkgs=["@google/generative-ai", "@google/genai", "@ai-sdk/google"],
                      py=["google-generativeai", "google-genai"], pats=[]),
    "mistral": dict(name="Mistral", kind="ai", pkgs=["@mistralai/mistralai", "@ai-sdk/mistral"], py=["mistralai"], pats=[]),
    "groq": dict(name="Groq", kind="ai", pkgs=["groq-sdk", "@ai-sdk/groq"], py=["groq"], pats=[]),
    "replicate": dict(name="Replicate", kind="ai", pkgs=["replicate"], py=["replicate"], pats=[]),
    "cohere": dict(name="Cohere", kind="ai", pkgs=["cohere-ai"], py=["cohere"], pats=[]),
    "resend": dict(name="Resend", kind="email", pkgs=["resend"], py=["resend"], pats=[]),
    "sendgrid": dict(name="SendGrid", kind="email", pkgs=["@sendgrid/mail"], py=["sendgrid"], pats=[]),
    "postmark": dict(name="Postmark", kind="email", pkgs=["postmark"], py=["postmarker"], pats=[]),
    "mailchimp": dict(name="Mailchimp", kind="email", marketing=True, pkgs=["@mailchimp/mailchimp_marketing"], pats=[r"list-manage\.com/subscribe"]),
    "convertkit": dict(name="Kit (ConvertKit)", kind="email", marketing=True, pkgs=[], pats=[r"app\.convertkit\.com", r"app\.kit\.com"]),
    "twilio": dict(name="Twilio", kind="sms", pkgs=["twilio"], py=["twilio"], pats=[]),
    "clerk": dict(name="Clerk", kind="auth", pkgs=["@clerk/nextjs", "@clerk/clerk-react", "@clerk/remix", "@clerk/astro"], pats=[]),
    "auth0": dict(name="Auth0", kind="auth", pkgs=["@auth0/nextjs-auth0", "@auth0/auth0-react", "auth0"], pats=[]),
    "firebase": dict(name="Firebase", kind="auth", pkgs=["firebase", "firebase-admin"], py=["firebase-admin"], pats=[]),
    "supabase": dict(name="Supabase", kind="auth", pkgs=["@supabase/supabase-js", "@supabase/ssr"], py=["supabase"], pats=[]),
    "uploadthing": dict(name="UploadThing", kind="storage", pkgs=["uploadthing", "@uploadthing/react"], pats=[]),
    "vercel_blob": dict(name="Vercel Blob", kind="storage", pkgs=["@vercel/blob"], pats=[]),
    "aws_s3": dict(name="Amazon S3", kind="storage", pkgs=["@aws-sdk/client-s3"], py=["boto3"], pats=[]),
    "cloudinary": dict(name="Cloudinary", kind="storage", pkgs=["cloudinary", "next-cloudinary"], py=["cloudinary"], pats=[]),
}
CONSENT_PKGS = {"vanilla-cookieconsent", "cookieconsent", "react-cookie-consent", "@cookiehub/cookiehub-react", "klaro",
                "@osano/cookieconsent", "react-cookienotice", "@iubenda/cookie-solution", "cookies-eu-banner", "c15t", "@c15t/nextjs"}
CONSENT_PATS = [r"cdn\.cookielaw\.org", r"consent\.cookiebot\.com", r"app\.termly\.io", r"cdn-cookieyes\.com",
                r"cdn\.iubenda\.com", r"app\.usercentrics\.eu", r"cmp\.osano\.com", r"\bcookieConsent\b", r"\bCookieConsent\b",
                r"\bConsentBanner\b", r"\bCookieBanner\b", r"gtag\(\s*['\"]consent['\"]", r"analytics_storage"]
AUTH_SELF_PKGS = {"next-auth", "@auth/core", "better-auth", "lucia", "passport", "@node-rs/argon2", "devise", "django-allauth"}
HASH_PKGS = {"bcrypt", "bcryptjs", "argon2", "@node-rs/argon2", "@node-rs/bcrypt", "passlib", "bcrypt-ts", "scrypt-js"}
UPLOAD_PKGS = {"multer", "formidable", "busboy", "uploadthing", "@uploadthing/react", "react-dropzone", "@vercel/blob", "filepond"}
MOBILE_PKGS = {"react-native", "expo", "@capacitor/core", "@ionic/core"}

LEGAL_PAGES = {
    "privacy": r"privacy|datenschutz|gdpr",
    "terms": r"terms|tos\b|conditions|legal/terms|agb",
    "cookies": r"cookie",
    "refund": r"refund|cancellation|returns?\b|withdrawal",
    "impressum": r"impressum|imprint|legal-notice",
    "accessibility": r"accessibility|a11y-statement",
    "dmca": r"dmca|copyright-policy|copyright\b|takedown",
    "notices": r"third[-_]?party|notices|licenses|credits|attributions?|open-?source",
    "aup": r"acceptable[-_]?use|aup\b|community[-_]?guidelines|content[-_]?policy",
    "subprocessors": r"sub-?processors",
    "ai_policy": r"ai[-_](policy|disclosure|use)",
}

FIELD_PATS = {
    "email": r"type=[\"'{]*email|name=[\"'{]*email|autocomplete=[\"']email|register\(\s*[\"']email",
    "password": r"type=[\"'{]*password",
    "phone": r"type=[\"'{]*tel\b|name=[\"'{]*(phone|mobile|tel)\b|autocomplete=[\"']tel",
    "name": r"name=[\"'{]*(full_?name|first_?name|last_?name|name)[\"'}]|autocomplete=[\"'](name|given-name|family-name)|register\(\s*[\"'](first_?name|last_?name|name)",
    "address": r"autocomplete=[\"'](street-address|address-line1|postal-code)|name=[\"'{]*(address|street|zip|postcode|postal_?code)[\"'}]",
    "birthdate": r"name=[\"'{]*(dob|birth\w*|birthday|date_?of_?birth)|autocomplete=[\"']bday",
    "card": r"autocomplete=[\"']cc-number|name=[\"'{]*(card_?number|cc_?number|cardnumber|ccnum)",
    "upload": r"type=[\"'{]*file\b",
}
SCHEMA_FIELDS = {
    "email": r"\bemail\b", "phone": r"\b(phone|phone_?number|mobile)\b", "name": r"\b(full_?name|first_?name|last_?name)\b",
    "address": r"\b(address|street|postal_?code|zip_?code)\b", "birthdate": r"\b(dob|birth_?date|date_?of_?birth|birthday)\b",
    "ip_address": r"\b(ip|ip_?address|ipAddress)\b", "location": r"\b(latitude|longitude|lat|lng|geo_?location)\b",
    "password": r"\b(password|password_?hash|hashed_?password)\b", "payment_ref": r"\b(stripe_?customer_?id|stripeCustomerId|customer_?id)\b",
}
DATA_DEFAULTS = {
    "email": ("Email address", "Create and log in to your account, send service messages", "contract"),
    "password": ("Password (stored hashed)", "Log in securely", "contract"),
    "name": ("Name", "Show your account and address you", "contract"),
    "phone": ("Phone number", "Contact you about your account or order", "contract"),
    "address": ("Postal address", "Ship orders and send invoices", "contract"),
    "birthdate": ("Date of birth", "Check you meet the minimum age", "legal_obligation"),
    "card": ("Card details", "Take payment (handled by the payment provider)", "contract"),
    "payment_ref": ("Payment customer reference", "Link your account to billing", "contract"),
    "ip_address": ("IP address", "Security and abuse prevention", "legitimate_interests"),
    "location": ("Location", "Location features", "consent"),
    "upload": ("Files you upload", "Provide the upload feature", "contract"),
    "usage": ("Usage and device data", "Analytics to improve the product", "consent"),
    "replay": ("Session recordings (clicks, scrolls, typing)", "See how people use the product", "consent"),
    "ads": ("Ad and conversion data", "Measure and target advertising", "consent"),
    "ai_inputs": ("What you type into AI features, and the replies", "Provide the AI feature", "contract"),
    "messages": ("Email or SMS delivery data", "Send you emails or texts", "contract"),
}

CLAIM_HIGH = re.compile(r"\b((?:GDPR|HIPAA|CCPA|SOC\s?2|ISO\s?27001|PCI(?:[- ]DSS)?)[- ](?:compliant|certified|ready|approved)|fully compliant)\b", re.I)
CLAIM_MED = re.compile(
    r"(100% secure|bank[- ](?:level|grade) (?:security|encryption)|military[- ]grade|unhackable|completely secure|zero risk"
    r"|#1\b|number one\b|world'?s (?:first|best|leading|fastest)|\bfree forever\b"
    r"|\bguaranteed (?:results|returns|uptime|delivery|approval|income|to (?:work|rank|grow|increase))|\b100% guaranteed"
    r"|\b(?:trusted|used|loved) by (?:over |more than )?[\d,.]+\s*[kKmM]?\+?\s*(?:users|customers|teams|companies|developers|people|businesses)"
    r"|\b\d+(?:\.\d+)?[xX%]\s+(?:faster|cheaper|more|better|increase))", re.I)
ADVICE = {
    "medical topics": re.compile(r"\b(diagnos\w+|symptoms?|treatments?|medications?|dosage|prescriptions?|mental health|therapy)\b", re.I),
    "financial or investment topics": re.compile(r"\b(investment advice|investing|stock picks?|trading signals?|portfolio|tax advice|financial advice|retirement planning|crypto)\b", re.I),
    "legal topics": re.compile(r"\b(legal advice|lawsuit|contract review|immigration)\b", re.I),
}
DISCLAIMER = re.compile(r"not (?:medical|financial|legal|investment|tax|professional) advice|for (?:informational|educational) purposes only"
                        r"|consult (?:a|your) (?:doctor|physician|lawyer|attorney|financial advis[eo]r|professional|qualified)"
                        r"|does not (?:provide|constitute) (?:medical|financial|legal)", re.I)
SECRETS = [
    ("Stripe live secret key", r"\b[sr]k_live_[0-9a-zA-Z]{16,}"),
    ("AWS access key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("private key", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ("GitHub token", r"\b(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{40,})"),
    ("Slack token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    ("Anthropic API key", r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    ("OpenAI API key", r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
]
STOCK_RE = re.compile(r"shutterstock|istock|gettyimages|getty_|adobestock|adobe_stock|depositphotos|dreamstime|123rf|alamy", re.I)


@dataclass
class Project:
    root: Path
    files: list[Path] = field(default_factory=list)          # relative paths, all files
    _text: dict = field(default_factory=dict)
    npm_prod: set = field(default_factory=set)
    npm_dev: set = field(default_factory=set)
    py: set = field(default_factory=set)
    pkg_dirs: list[Path] = field(default_factory=list)

    def text(self, rel: Path) -> str:
        if rel not in self._text:
            p = self.root / rel
            try:
                self._text[rel] = p.read_text(errors="ignore") if p.stat().st_size <= MAX_BYTES else ""
            except OSError:
                self._text[rel] = ""
        return self._text[rel]

    def by_ext(self, exts: set[str], tests: bool = False) -> list[Path]:
        return [f for f in self.files if f.suffix.lower() in exts and (tests or not TEST_RE.search(f.as_posix()))]

    @property
    def all_pkgs(self) -> set:
        return self.npm_prod | self.npm_dev


def load(root: Path) -> Project:
    pj = Project(root)
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.is_dir():
                if e.name not in SKIP_DIRS and not e.is_symlink():
                    stack.append(e)
            elif e.is_file():
                pj.files.append(e.relative_to(root))
    pj.files.sort()
    for f in pj.files:
        if f.name == "package.json":
            try:
                pkg = json.loads(pj.text(f))
            except ValueError:
                continue
            pj.pkg_dirs.append(root / f.parent)
            pj.npm_prod |= set((pkg.get("dependencies") or {}).keys())
            pj.npm_dev |= set((pkg.get("devDependencies") or {}).keys())
    pj.py = set(lic.read_python_names(root))
    return pj


def _grep(pj: Project, pattern: str | re.Pattern, files: list[Path], flags=re.I) -> list[tuple[Path, int, str]]:
    rx = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, flags)
    hits = []
    for f in files:
        t = pj.text(f)
        if not t:
            continue
        for m in rx.finditer(t):
            line = t.count("\n", 0, m.start()) + 1
            hits.append((f, line, m.group(0)))
    return hits


def _imgs_without_alt(text: str) -> list[int]:
    """Line numbers of <img>/<Image> tags with a src but no alt. Skips over {...} so JSX arrow functions don't end the tag."""
    out = []
    for m in re.finditer(r"<(img|Image)\b", text):
        i, depth, quote = m.end(), 0, ""
        while i < len(text) and i - m.end() < 2000:
            c = text[i]
            if quote:
                quote = "" if c == quote else quote
            elif c in "\"'`" and depth == 0:
                quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == ">" and depth == 0:
                break
            i += 1
        tag = text[m.start(): i + 1]
        if re.search(r"\bsrc\s*=", tag) and not re.search(r"\balt\s*=", tag) and "{...props}" not in tag:
            out.append(text.count("\n", 0, m.start()) + 1)
    return out


def _loc(h: tuple[Path, int, str]) -> str:
    return f"{h[0].as_posix()}:{h[1]}"


def detect_vendors(pj: Project) -> dict[str, dict]:
    code = pj.by_ext(UI_EXT | {".py", ".rb", ".php"})
    found: dict[str, dict] = {}
    for key, v in VENDORS.items():
        where = [f"package.json: {p}" for p in v["pkgs"] if p in pj.npm_prod]
        where += [f"python: {p}" for p in v.get("py", []) if p in pj.py]
        for pat in v["pats"]:
            where += [_loc(h) for h in _grep(pj, pat, code)[:3]]
        if where:
            found[key] = {"key": key, "name": v["name"], "kind": v["kind"], "cookieless": v.get("cookieless", False),
                          "marketing": v.get("marketing", False), "where": where[:5]}
    return found


def legal_pages(pj: Project) -> dict[str, list[str]]:
    pages: dict[str, list[str]] = {k: [] for k in LEGAL_PAGES}
    for f in pj.files:
        if f.suffix.lower() not in CONTENT_EXT | {".ts", ".js", ".txt"}:
            continue
        p = f.as_posix().lower()
        if TEST_RE.search(p) or "/components/" in p:
            continue
        stem_path = re.sub(r"\.[a-z]+$", "", p)
        tail = "/".join(stem_path.split("/")[-2:])   # e.g. "privacy/page" or "legal/privacy"
        for k, rx in LEGAL_PAGES.items():
            if re.search(rf"(^|[/_.-])({rx})", tail):
                pages[k].append(f.as_posix())
    if any(f.as_posix().upper().startswith(("THIRD_PARTY", "THIRD-PARTY", "NOTICE")) for f in pj.files):
        pages["notices"].append("THIRD_PARTY_NOTICES")
    return {k: v for k, v in pages.items() if v}


def signals(pj: Project, vendors: dict | None = None) -> dict:
    vendors = vendors if vendors is not None else detect_vendors(pj)
    kinds = {v["kind"] for v in vendors.values()}
    ui = pj.by_ext(UI_EXT)
    payments = "payments" in kinds
    sub = payments and bool(_grep(pj, r"mode:\s*['\"]subscription|subscriptions\.create|trial_period_days|trialPeriodDays"
                                      r"|recurring:\s*\{|\binterval:\s*['\"](month|year)", pj.by_ext(UI_EXT | {".py"})))
    uploads = bool(pj.all_pkgs & UPLOAD_PKGS) or "storage" in kinds or bool(_grep(pj, FIELD_PATS["upload"], ui))
    accounts = "auth" in kinds or bool(pj.all_pkgs & AUTH_SELF_PKGS) or bool(_grep(pj, FIELD_PATS["password"], ui))
    ai = "ai" in kinds or bool(pj.all_pkgs & {"ai", "langchain", "@langchain/core", "llamaindex"}) or "langchain" in pj.py
    kids = bool(_grep(pj, r"\bfor (kids|children|students|schools|teachers|parents|classrooms)\b|\bkids'? (app|learning|games)\b", pj.by_ext(CONTENT_EXT)[:200]))
    cats = []
    if accounts or sub:
        cats.append("saas")
    if payments and not sub:
        cats.append("ecommerce")
    if ai:
        cats.append("ai")
    if uploads:
        cats.append("marketplace")
    if not cats:
        cats.append("content")
    if kids:
        cats.append("kids")
    return {"payments": payments, "subscription": sub, "uploads": uploads, "accounts": accounts, "ai": ai,
            "mobile": bool(pj.all_pkgs & MOBILE_PKGS) or (pj.root / "ios").is_dir() or (pj.root / "android").is_dir(),
            "suggested_categories": cats}


def data_map(pj: Project, vendors: dict, sig: dict) -> list[dict]:
    ui = pj.by_ext(UI_EXT)
    found: dict[str, list[str]] = {}
    for key, pat in FIELD_PATS.items():
        hits = _grep(pj, pat, ui)
        if hits:
            found.setdefault(key, []).extend(_loc(h) for h in hits[:3])
    schema_files = [f for f in pj.files if f.suffix in (".prisma", ".sql") or
                    (f.suffix in (".ts", ".js", ".py") and re.search(r"(schema|models?)\b", f.as_posix(), re.I))]
    schema_files = [f for f in schema_files if not TEST_RE.search(f.as_posix())]
    for key, pat in SCHEMA_FIELDS.items():
        hits = _grep(pj, pat, schema_files)
        if hits:
            found.setdefault(key, []).extend(_loc(h) for h in hits[:2])
    kinds = {}
    for v in vendors.values():
        kinds.setdefault(v["kind"], []).append(v["name"])
    if [v for v in vendors.values() if v["kind"] == "analytics"]:
        found.setdefault("usage", []).extend(v["name"] for v in vendors.values() if v["kind"] == "analytics")
    if "replay" in kinds:
        found["replay"] = kinds["replay"]
    if "ads" in kinds:
        found["ads"] = kinds["ads"]
    if sig.get("ai"):
        found["ai_inputs"] = kinds.get("ai", ["AI provider"])
    if "email" in kinds or "sms" in kinds:
        found["messages"] = kinds.get("email", []) + kinds.get("sms", [])
    share = {
        "usage": "analytics", "replay": "replay", "ads": "ads", "ai_inputs": "ai", "messages": "email",
        "card": "payments", "payment_ref": "payments", "upload": "storage",
    }
    out = []
    for key, where in found.items():
        label, purpose, basis = DATA_DEFAULTS[key]
        shared = kinds.get(share.get(key, ""), [])
        if key == "messages":
            shared = kinds.get("email", []) + kinds.get("sms", [])
        if key in ("email", "name", "password") and "auth" in kinds:
            shared = shared + kinds["auth"]
        out.append({"key": key, "data": label, "found_in": sorted(set(where))[:5], "purpose": purpose,
                    "lawful_basis": basis, "retention": "", "shared_with": sorted(set(shared))})
    order = list(DATA_DEFAULTS)
    return sorted(out, key=lambda d: order.index(d["key"]))


def _git_tracked(root: Path) -> list[str] | None:
    if not (root / ".git").exists():
        return None
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.splitlines() if r.returncode == 0 else None


def scan(root: Path, profile: dict) -> dict:
    pj = load(root)
    vendors = detect_vendors(pj)
    sig = signals(pj, vendors)
    from compliance.profile import packs as pick_packs
    packs = pick_packs(profile, sig)
    regions = set(profile.get("regions", []))
    eu, ca = "eu_uk" in regions, "us_ca" in regions
    pages = legal_pages(pj)
    ui = pj.by_ext(UI_EXT)
    content = pj.by_ext(CONTENT_EXT)
    F: list[Finding] = []

    # ---- consent & trackers
    consent = bool(pj.all_pkgs & CONSENT_PKGS) or any(_grep(pj, p, ui, 0) for p in CONSENT_PATS)
    tracking = [v for v in vendors.values() if v["kind"] in ("analytics", "replay", "ads", "chat") and not v["cookieless"]]
    if not consent:
        for v in tracking:
            F.append(Finding("cookies.no_consent", v["name"], files=v["where"], severity="high" if eu else "medium"))
    for v in vendors.values():
        if v["kind"] == "replay":
            F.append(Finding("cookies.session_replay", v["name"], files=v["where"]))
        if v["kind"] == "ads":
            F.append(Finding("cookies.ad_pixel", v["name"], files=v["where"]))
    if (tracking or consent) and "cookies" not in pages:
        F.append(Finding("cookies.policy_missing"))
    ads = [v for v in vendors.values() if v["kind"] == "ads"]
    if ca and tracking and not _grep(pj, r"globalPrivacyControl|Sec-GPC", pj.by_ext(UI_EXT | {".py"})):
        F.append(Finding("cookies.gpc_missing"))
    if ca and ads and not _grep(pj, r"do not sell|don'?t sell|your privacy choices|opt[- ]out of (sale|sharing)", ui):
        F.append(Finding("cookies.do_not_sell_missing"))
    gf = _grep(pj, r"fonts\.googleapis\.com|fonts\.gstatic\.com", ui + pj.by_ext({".css", ".scss"}))
    if gf and eu:
        F.append(Finding("cookies.remote_google_fonts", files=sorted({_loc(h) for h in gf})))

    # ---- privacy policy
    dmap = data_map(pj, vendors, sig)
    if "privacy" not in pages:
        F.append(Finding("privacy.policy_missing", severity="high" if (dmap or tracking) else "medium"))
    else:
        policy_text = " ".join(pj.text(Path(p)) for p in pages["privacy"]).lower()
        for v in vendors.values():
            first = v["name"].split(" (")[0].split(" / ")[0].lower()
            if v["kind"] != "consent" and first.split()[0] not in policy_text:
                F.append(Finding("privacy.policy_outdated", v["name"], files=pages["privacy"]))

    # ---- pre-ticked boxes
    box = re.compile(r"<input\b[^>]{0,400}?type=[\"'{]*checkbox[^>]{0,400}?>", re.I | re.S)
    pre = re.compile(r"\bdefaultChecked\b(?!\s*=\s*\{\s*false)|\bchecked(?:\s*=\s*(?:\{\s*true\s*\}|[\"']checked[\"']|[\"']true[\"']))?(?=[\s/>])", re.I)
    ctx = re.compile(r"newsletter|marketing|updates|offers|promo|consent|subscribe|partners|emails?", re.I)
    for f in ui:
        t = pj.text(f)
        for m in box.finditer(t):
            near = t[max(0, m.start() - 200): m.end() + 200]
            if pre.search(m.group(0)) and ctx.search(near):
                F.append(Finding("consent.prechecked", f.as_posix(), files=[f"{f.as_posix()}:{t.count(chr(10), 0, m.start()) + 1}"]))
                break

    # ---- accounts: rights & terms
    if sig["accounts"]:
        code = pj.by_ext(UI_EXT | {".py", ".rb", ".php"})
        # Clerk's <UserButton>/<UserProfile> include "Delete account" and profile editing out of the box
        hosted_account = "clerk" in vendors and bool(_grep(pj, r"<(UserButton|UserProfile)\b", ui))
        if not hosted_account and not _grep(pj, r"delete[\s_-]?(my[\s_-]?|your[\s_-]?)?account|deleteAccount|deleteUser|account/delete|close[\s_-]?account"
                         r"|user\.delete\(|users\.delete|deleteMany\(\s*\{\s*where:\s*\{\s*userId", code):
            F.append(Finding("rights.delete_missing"))
        if not _grep(pj, r"export[\s_-]?(my[\s_-]?|your[\s_-]?|user[\s_-]?)?data|download[\s_-](my|your)[\s_-]data|exportUserData|dataExport", code):
            F.append(Finding("rights.export_missing"))
        if not hosted_account and not _grep(pj, r"(edit|update)[\s_-]?(profile|account)|account[\s_-]settings|settings/(profile|account)|updateUser|user\.update\(", code):
            F.append(Finding("rights.correct_missing"))
        signup = [f for f in ui if _grep(pj, FIELD_PATS["email"] + "|" + FIELD_PATS["password"], [f]) and (
                  re.search(r"sign-?up|register|join|create-account|onboarding", f.as_posix(), re.I) or
                  re.search(r"\bsignUp\b|sign_up\(|createUser\b|mode\s*={2,3}\s*['\"]signup", pj.text(f)) or
                  re.search(r"create (?:an |your )?account", pj.text(f), re.I))]
        no_terms = [f.as_posix() for f in signup if not re.search(r"terms|privacy|agree", pj.text(f), re.I)]
        if no_terms:
            F.append(Finding("terms.no_clickwrap", no_terms[0], files=no_terms))
    if "terms" not in pages and (sig["accounts"] or "payments" in packs or "ugc" in packs or "ai" in packs):
        F.append(Finding("terms.missing"))

    # ---- payments
    card = _grep(pj, FIELD_PATS["card"], ui)
    if card:
        F.append(Finding("payments.raw_card_fields", card[0][0].as_posix(), files=[_loc(h) for h in card]))
    charging = profile.get("charging") in ("one_time", "subscription") or sig["payments"]
    if "payments" in packs and charging:
        if "refund" not in pages:
            F.append(Finding("payments.refund_missing"))
        if profile.get("charging") == "subscription" or sig["subscription"]:
            if not _grep(pj, r"renews? (automatically|monthly|annually|every|each)|auto-?renew|recurring (charge|billing)|billed (monthly|annually|yearly) until", content):
                F.append(Finding("payments.renewal_disclosure"))
            if not _grep(pj, r"billingPortal|billing_portal|cancel_at_period_end|subscriptions\.(cancel|del)\(|cancelSubscription|cancel[\s_-]subscription|customer[\s_-]portal",
                         pj.by_ext(UI_EXT | {".py"})):
                F.append(Finding("payments.cancel_missing"))
        F.append(Finding("payments.tax"))

    # ---- AI
    ai_v = [v for v in vendors.values() if v["kind"] == "ai"]
    if "ai" in packs and sig["ai"]:
        names = ", ".join(v["name"] for v in ai_v) or "an AI model"
        if not _grep(pj, r"\bAI[- ]generated\b|generated (by|with|using) AI|powered by (AI|GPT|Claude|Gemini)|AI can make mistakes"
                         r"|\bAI\b.{0,40}\b(may|can) (make mistakes|be (wrong|inaccurate))|(may|can) (be inaccurate|contain errors)"
                         r"|you'?re (chatting|talking) (with|to) an? AI", content):
            F.append(Finding("ai.disclosure_missing", names))
        F.append(Finding("ai.output_ip"))
        for v in ai_v:
            F.append(Finding("ai.provider_terms", v["name"]))

    # ---- licenses
    deps: list[lic.Dep] = []
    problems = []
    for d in pj.pkg_dirs:
        got, prob = lic.read_npm(d)
        deps += got
        if prob:
            problems.append(f"{(d.relative_to(root).as_posix() or '.')}: {prob}")
    seen = set()
    unknown = []
    for d in deps:
        if d.dev or d.name in seen:
            continue
        seen.add(d.name)
        if d.kind == "network_copyleft":
            F.append(Finding("licenses.network_copyleft", d.name, d.license))
        elif d.kind == "strong_copyleft":
            F.append(Finding("licenses.strong_copyleft", d.name, d.license))
        elif d.kind == "restricted":
            F.append(Finding("licenses.restricted", d.name, d.license))
        elif d.kind == "unknown":
            unknown.append(d.name)
    if unknown:
        F.append(Finding("licenses.unknown", str(len(unknown)), ", ".join(sorted(unknown)[:15])))
    if problems:
        F.append(Finding("licenses.unchecked", detail="; ".join(problems)))
    if pj.py and not deps:
        F.append(Finding("licenses.unchecked", "python", "Python packages: run `uvx pip-licenses` in your environment"))
    if (deps or pj.npm_prod) and "notices" not in pages:
        F.append(Finding("licenses.notices_missing"))

    # ---- assets
    imgs = [f for f in pj.files if f.suffix.lower() in IMG_EXT and not TEST_RE.search(f.as_posix())]
    for f in imgs:
        if STOCK_RE.search(f.name):
            F.append(Finding("assets.stock_watermark", f.as_posix(), files=[f.as_posix()]))
    photos = [f for f in imgs if f.suffix.lower() in (".jpg", ".jpeg", ".webp", ".avif") or
              ((root / f).stat().st_size > 40_000 if (root / f).exists() else False)]
    if photos:
        F.append(Finding("assets.images_unknown", detail=str(len(photos)), files=[f.as_posix() for f in photos]))
    fonts = [f for f in pj.files if f.suffix.lower() in FONT_EXT]
    unlicensed = [f for f in fonts if not any(re.search(r"(ofl|license|licence)", g.name, re.I)
                                              for g in pj.files if g.parent == f.parent)]
    if unlicensed:
        F.append(Finding("assets.font_files", detail=str(len(unlicensed)), files=[f.as_posix() for f in unlicensed]))
    for h in _grep(pj, r"tailwindui\.com|\btailwind plus\b|themeforest\.net|\benvato\b|creative-tim\.com|\buideck\b|templatemo\.com", ui + pj.by_ext({".css"}))[:3]:
        F.append(Finding("assets.ui_kit", h[0].as_posix(), files=[_loc(h)]))

    # ---- claims
    seen_claims = set()
    for rx, rule in ((CLAIM_HIGH, "claims.compliance_claim"), (CLAIM_MED, "claims.unverified")):
        for h in _grep(pj, rx, content):
            key = h[2].lower().strip()
            if (h[0], key) in seen_claims or len(seen_claims) >= 25:
                continue
            seen_claims.add((h[0], key))
            F.append(Finding(rule, h[0].as_posix(), h[2].strip(), files=[_loc(h)], key=key))

    # ---- high-risk advice
    topics = []
    for label, rx in ADVICE.items():
        hit_files = {h[0] for h in _grep(pj, rx, content)}
        if len(hit_files) >= 2 or (hit_files and "regulated" in packs):
            topics.append(label)
    if topics and ("regulated" in packs or len(topics) and sig["ai"]) and not _grep(pj, DISCLAIMER, content):
        F.append(Finding("advice.disclaimer_missing", detail=" and ".join(topics)))
    laws = {"health": "HIPAA, Washington's My Health My Data Act, GDPR special-category rules",
            "financial": "GLBA, state privacy laws, GDPR", "biometric": "Illinois BIPA, Texas and Washington biometric laws, GDPR",
            "location": "state privacy laws treat precise location as sensitive; GDPR"}
    for s in profile.get("sensitive", []):
        if s in laws:
            F.append(Finding("regulated.sensitive", s, laws[s]))

    # ---- kids
    if "kids" in packs:
        if not _grep(pj, r"(are you|i am|confirm (that )?you are|must be) (at least |over )?(13|16|18)|date of birth|birthdate|ageGate|age_gate"
                         r"|age[\s_-]?verification|minimum age|isOver(13|16|18)", ui):
            F.append(Finding("kids.age_gate_missing"))
        if profile.get("minors") == "under13" or "kids" in profile.get("categories", []):
            F.append(Finding("kids.coppa"))

    # ---- user content
    if "ugc" in packs and sig["uploads"]:
        if "dmca" not in pages:
            F.append(Finding("ugc.dmca_missing"))
        if not _grep(pj, r"report (this|post|comment|content|user|abuse)|reportContent|flagContent|report-content", ui):
            F.append(Finding("ugc.report_missing"))
        if "aup" not in pages:
            F.append(Finding("ugc.aup_missing"))

    # ---- security
    tracked = _git_tracked(root)
    for label, pat in SECRETS:
        for h in _grep(pj, pat, [f for f in pj.files if f.suffix.lower() in TEXT_EXT or f.name.startswith(".env")], 0):
            name = h[0].name
            if name.endswith((".example", ".sample", ".template")) or (tracked is not None and h[0].as_posix() not in tracked):
                continue
            F.append(Finding("security.secret_in_repo", _loc(h), label, files=[_loc(h)], evidence=[h[2][:8] + "…(hidden)"]))
    if tracked is not None:
        for t in tracked:
            if re.search(r"(^|/)\.env(\.[\w.-]+)?$", t) and not re.search(r"\.(example|sample|template)$", t):
                F.append(Finding("security.env_tracked", t, files=[t]))
    weak = _grep(pj, r"(md5|sha1)[^\n]{0,80}password|password[^\n]{0,80}\b(md5|sha1)\b", pj.by_ext(UI_EXT | {".py", ".php", ".rb"}))
    for h in weak[:2]:
        F.append(Finding("security.weak_hash", _loc(h), "MD5/SHA-1", files=[_loc(h)]))
    if not any(f.as_posix().endswith(".well-known/security.txt") for f in pj.files):
        F.append(Finding("security.txt_missing"))

    # ---- accessibility & identity
    noalt = [(f, line, "") for f in ui if f.suffix in CONTENT_EXT for line in _imgs_without_alt(pj.text(f))]
    if noalt:
        F.append(Finding("a11y.img_alt", detail=str(len(noalt)), files=sorted({_loc(h) for h in noalt})))
    for f in [f for f in ui if f.suffix in (".html", ".htm") or re.search(r"(^|/)(app/)?layout\.(t|j)sx$|_document\.(t|j)sx$", f.as_posix())]:
        t = pj.text(f)
        if re.search(r"<html\b", t, re.I) and not re.search(r"<html\b[^>]*\blang\s*=", t, re.I):
            F.append(Finding("a11y.html_lang", f.as_posix(), files=[f.as_posix()]))
    if eu and profile.get("audience") in ("consumers", "both") and "accessibility" not in pages:
        F.append(Finding("a11y.statement_missing"))
    if not _grep(pj, r"mailto:|\b[\w.+-]+@[\w-]+\.[\w.]+\b|href=[\"'{]*/contact", content):
        F.append(Finding("identity.contact_missing"))
    if str(profile.get("business_country", "")).strip().lower() in ("germany", "deutschland", "de", "austria", "österreich", "at") \
            and "impressum" not in pages:
        F.append(Finding("identity.impressum_missing"))

    # ---- vendors & comms
    personal = [v["name"] for v in vendors.values() if v["kind"] not in ("consent",) and not v["cookieless"]]
    if personal:
        F.append(Finding("vendors.dpa", detail=", ".join(personal)))
    email_v = [v for v in vendors.values() if v["kind"] == "email"]
    marketing = any(v["marketing"] for v in email_v) or bool(email_v and _grep(pj, r"newsletter", ui))
    if marketing and not _grep(pj, r"unsubscribe|List-Unsubscribe", pj.by_ext(UI_EXT | {".py", ".html"}, tests=False)):
        F.append(Finding("email.unsubscribe_missing"))
    for v in vendors.values():
        if v["kind"] == "sms":
            F.append(Finding("sms.consent", v["name"]))
    if sig["mobile"]:
        F.append(Finding("mobile.app_store"))

    return {"findings": F, "data_map": dmap, "vendors": list(vendors.values()), "signals": sig, "packs": packs,
            "legal_pages": pages, "consent_tool": consent, "deps": deps,
            "files_scanned": len(pj.files)}
