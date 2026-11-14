"""Intake: the profile questions that decide which packs run.

The CLI never prompts. When it needs answers it prints a `needs_input` payload with
questions; the agent asks the user and re-runs with `--answer id=value` (repeatable,
comma-separated values for multi-select). Answers are saved in .compliance/profile.json
so later runs don't ask again.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

STATE_DIR = ".compliance"


def state_dir(root: Path) -> Path:
    return root / STATE_DIR


def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def _save(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_profile(root: Path) -> dict:
    return _load(state_dir(root) / "profile.json")


def save_profile(root: Path, profile: dict) -> None:
    _save(state_dir(root) / "profile.json", profile)


@dataclass
class Option:
    value: str
    label: str
    description: str = ""
    recommended: bool = False


@dataclass
class Question:
    id: str
    question: str
    options: list[Option] = field(default_factory=list)
    multi: bool = False
    kind: str = "choice"            # choice | text
    fields: list[str] = field(default_factory=list)   # for kind=text
    why: str = ""

    def to_dict(self) -> dict:
        d = {"id": self.id, "question": self.question, "kind": self.kind, "multi": self.multi, "why": self.why,
             "answer_with": (f"--answer {self.id}=<value>" if self.kind == "choice" and not self.multi
                             else f"--answer {self.id}=<v1>,<v2>" if self.kind == "choice"
                             else " ".join(f'--answer "{f}=<text>"' for f in self.fields)),
             "options": [o.__dict__ for o in self.options]}
        if self.kind == "text":
            d["fields"] = self.fields
        return d


CATEGORIES = {
    "saas": ("Software / SaaS app", "Accounts, a product people log into, often subscriptions"),
    "ecommerce": ("Online store", "Selling physical or digital goods"),
    "ai": ("AI product or AI features", "Generates text, images, code or answers with AI"),
    "marketplace": ("Marketplace or community", "Users post, upload or sell to each other"),
    "content": ("Content or marketing site", "Blog, portfolio, docs, landing pages"),
    "regulated": ("Health, finance or legal", "Gives or touches health, money or legal advice or data"),
    "kids": ("Kids or education", "Used by children, students or schools"),
}

REGIONS = {
    "eu_uk": ("EU / UK", "GDPR, ePrivacy cookie rules, UK GDPR, EU AI Act, accessibility act"),
    "us_ca": ("US: California", "CCPA/CPRA, auto-renewal law, CalOPPA"),
    "us_other": ("US: other states", "Federal rules (FTC, COPPA, CAN-SPAM) plus state privacy laws"),
    "other": ("Somewhere else", "Flagged only: the skill doesn't cover other countries' rules in detail"),
}

BUSINESS_FIELDS = ["business_name", "contact_email", "business_address", "business_country"]


def questions(profile: dict, signals: dict) -> list[Question]:
    """Unanswered intake questions. `signals` (from a quick scan) pick the recommended options."""
    qs: list[Question] = []
    if "categories" not in profile:
        rec = set(signals.get("suggested_categories", [])) or {"content"}
        qs.append(Question(
            "categories", "What kind of product is this? Pick every one that fits.",
            [Option(k, v[0], v[1], k in rec) for k, v in CATEGORIES.items()], multi=True,
            why="Each category adds its own checks on top of the baseline every site gets."))
    if "regions" not in profile:
        qs.append(Question(
            "regions", "Where are your users? Pick every one that applies.",
            [Option(k, v[0], v[1], k in ("eu_uk", "us_ca")) for k, v in REGIONS.items()], multi=True,
            why="Cookie consent, privacy rights and refund rules depend on where users live, not where you are."))
    if "audience" not in profile:
        qs.append(Question("audience", "Who uses it?", [
            Option("consumers", "Individual people", "Consumer protection rules apply in full", True),
            Option("businesses", "Businesses only", "Fewer consumer rules; contracts matter more"),
            Option("both", "Both")]))
    if "minors" not in profile:
        kids = "kids" in signals.get("suggested_categories", [])
        qs.append(Question("minors", "Could anyone under 18 use it?", [
            Option("adults", "No, adults only (18+)", "Add a minimum age to your terms", not kids),
            Option("teens", "Teens 13-17 may use it", "Extra privacy defaults for teens"),
            Option("under13", "Children under 13 may use it", "COPPA in the US: needs parental consent and a lawyer", kids)],
            why="Children's data has the strictest rules (COPPA, GDPR age of consent, UK Children's Code)."))
    if "charging" not in profile:
        pay = signals.get("payments", False)
        sub = signals.get("subscription", False)
        qs.append(Question("charging", "Do you charge users money?", [
            Option("none", "No, it's free", "", not pay),
            Option("one_time", "Yes, one-time payments", "", pay and not sub),
            Option("subscription", "Yes, subscriptions (with or without a free trial)",
                   "Auto-renewal and online-cancellation rules apply", pay and sub)]))
    if "sensitive" not in profile:
        qs.append(Question("sensitive", "Do you handle any of these? Pick all that apply.", [
            Option("none", "None of these", "", True),
            Option("health", "Health or medical data"),
            Option("financial", "Bank, income or financial account data"),
            Option("biometric", "Face, fingerprint or voice data"),
            Option("location", "Precise location")], multi=True,
            why="Sensitive data brings extra laws (HIPAA, BIPA, Washington's health data act) and needs a lawyer."))
    missing_biz = [f for f in BUSINESS_FIELDS if not profile.get(f)]
    if missing_biz:
        qs.append(Question(
            "business", "What legal name, contact email, address and country should your policies show?",
            kind="text", fields=missing_biz,
            why="Policies must name who runs the site. These are never guessed; type 'skip' to leave a blank to fill in later."))
    return qs


def apply_answers(profile: dict, answers: list[str]) -> tuple[dict, list[str]]:
    """Parse `id=value` answers into the profile. Returns (profile, errors)."""
    errors: list[str] = []
    allowed = {"categories": set(CATEGORIES), "regions": set(REGIONS), "audience": {"consumers", "businesses", "both"},
               "minors": {"adults", "teens", "under13"}, "charging": {"none", "one_time", "subscription"},
               "sensitive": {"none", "health", "financial", "biometric", "location"}}
    multi = {"categories", "regions", "sensitive"}
    for a in answers:
        if "=" not in a:
            errors.append(f"'{a}' is not id=value")
            continue
        k, v = a.split("=", 1)
        k, v = k.strip(), v.strip()
        if k in BUSINESS_FIELDS:
            profile[k] = "" if v.lower() == "skip" else v
            if v.lower() == "skip":
                profile.setdefault("skipped", [])
                if k not in profile["skipped"]:
                    profile["skipped"].append(k)
                profile[k] = "[TO FILL IN]"
            continue
        if k not in allowed:
            errors.append(f"unknown question '{k}'")
            continue
        vals = [x.strip() for x in v.split(",") if x.strip()]
        bad = [x for x in vals if x not in allowed[k]]
        if bad or not vals:
            errors.append(f"{k}: {', '.join(bad) or 'empty'} not one of {', '.join(sorted(allowed[k]))}")
            continue
        if k in multi:
            if k == "sensitive" and len(vals) > 1:
                vals = [x for x in vals if x != "none"]
            profile[k] = vals
        else:
            profile[k] = vals[0]
    return profile, errors


def packs(profile: dict, signals: dict) -> list[str]:
    """Which packs run. Baseline always; others from the user's categories plus what the code shows."""
    cats = set(profile.get("categories", []))
    out = ["baseline"]
    if "ecommerce" in cats or profile.get("charging") in ("one_time", "subscription") or signals.get("payments"):
        out.append("payments")
    if "ai" in cats or signals.get("ai"):
        out.append("ai")
    # Uploads alone (e.g. private chat attachments) aren't public user content: the intake recommends
    # "marketplace" when uploads are found, and the user decides.
    if "marketplace" in cats:
        out.append("ugc")
    if "regulated" in cats or [s for s in profile.get("sensitive", []) if s != "none"]:
        out.append("regulated")
    if "kids" in cats or profile.get("minors") in ("teens", "under13"):
        out.append("kids")
    return out
