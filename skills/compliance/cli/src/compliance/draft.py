"""Render a legal document draft from the templates, the profile, the data map and the user's decisions.

Unknown facts are never guessed: they render as [TO FILL IN: ...] and are listed in `missing`.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from compliance.profile import state_dir

TEMPLATES = Path(__file__).parent / "templates"
DOCS = ["privacy-policy", "cookie-policy", "terms", "refund-policy", "acceptable-use", "dmca", "accessibility",
        "impressum", "ai-disclosure"]
BASIS = {"contract": "to provide the service you asked for (contract)", "consent": "your consent",
         "legitimate_interests": "our legitimate interests", "legal_obligation": "a legal obligation"}
RETENTION = {"account_plus_30": "until you delete your account, then up to 30 more days in backups",
             "inactive_2y": "until you delete your account, or 2 years after your last sign-in"}
REFUNDS = {"14_days": "a full refund if you ask within 14 days of purchase", "30_days": "a full refund if you ask within 30 days of purchase",
           "none": "no refunds, except where the law gives you a right to one"}


def _fill(label: str) -> str:
    return f"[TO FILL IN: {label}]"


def context(profile: dict, data_map: list[dict], vendors: list[dict], packs: list[str], answers: dict) -> dict:
    def biz(k, label):
        v = profile.get(k, "")
        return v if v and v != "[TO FILL IN]" else _fill(label)
    regions = set(profile.get("regions", []))
    retention = answers.get("retention")
    return {
        "business_name": biz("business_name", "legal business name"),
        "contact_email": biz("contact_email", "contact email"),
        "business_address": biz("business_address", "postal address"),
        "business_country": biz("business_country", "country"),
        "governing_law": answers.get("governing_law") or _fill("governing law (country or US state)"),
        "effective_date": date.today().isoformat(),
        "eu": "eu_uk" in regions, "california": "us_ca" in regions, "us": bool(regions & {"us_ca", "us_other"}),
        "consumers": profile.get("audience", "consumers") in ("consumers", "both"),
        "minors": profile.get("minors", "adults"), "min_age": 13 if profile.get("minors") == "under13" else (13 if profile.get("minors") == "teens" else 18),
        "data": [d | {"basis_text": BASIS.get(d["lawful_basis"], d["lawful_basis"]),
                      "retention_text": d.get("retention") or RETENTION.get(retention, _fill("how long you keep this"))} for d in data_map],
        "vendors": vendors,
        "trackers": [v for v in vendors if v["kind"] in ("analytics", "replay", "ads", "chat")],
        "has": {p: True for p in packs},
        "subscription": profile.get("charging") == "subscription",
        "charging": profile.get("charging") in ("one_time", "subscription"),
        "refund_text": REFUNDS.get(answers.get("refunds", ""), _fill("your refund rule")),
        "ai_training": answers.get("ai_training", "no"),
        "ai_vendors": [v["name"] for v in vendors if v["kind"] == "ai"],
        "sells_or_shares": any(v["kind"] == "ads" for v in vendors),
    }


def render(doc: str, ctx: dict) -> tuple[str, list[str]]:
    env = Environment(loader=FileSystemLoader(TEMPLATES), undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True,
                      keep_trailing_newline=True)
    text = env.get_template(f"{doc}.md.j2").render(**ctx)
    text = re.sub(r"\n{3,}", "\n\n", text)
    missing = sorted(set(re.findall(r"\[TO FILL IN: ([^\]]+)\]", text)))
    return text, missing


def write(root: Path, doc: str, text: str) -> Path:
    p = state_dir(root) / "drafts" / f"{doc}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p
