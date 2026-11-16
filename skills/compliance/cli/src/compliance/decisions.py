"""After the scan: the per-module questions, the user's answers, and the agreed change list.

Flow: `compliance decide --json` prints open decisions (exit 3) → agent asks the user →
`compliance decide --json --set id=value ...` → when none are left, `compliance changes --json`
prints the one list of changes for the user's single "yes, build these".
"""

from __future__ import annotations

import json
from pathlib import Path

from compliance import atomic
from compliance.profile import Option, Question, state_dir

DOC_FOR_RULE = {
    "privacy.policy_missing": "privacy-policy", "privacy.policy_outdated": "privacy-policy",
    "cookies.policy_missing": "cookie-policy", "terms.missing": "terms", "payments.refund_missing": "refund-policy",
    "ugc.dmca_missing": "dmca", "ugc.aup_missing": "acceptable-use", "a11y.statement_missing": "accessibility",
    "identity.impressum_missing": "impressum", "licenses.notices_missing": "third-party-notices",
}
DOC_TITLES = {
    "privacy-policy": "Privacy policy", "cookie-policy": "Cookie policy", "terms": "Terms of service",
    "refund-policy": "Refund and cancellation policy", "dmca": "Copyright (DMCA) policy", "acceptable-use": "Acceptable use policy",
    "accessibility": "Accessibility statement", "impressum": "Impressum", "third-party-notices": "Third-party notices",
}


def load(root: Path) -> dict:
    try:
        return json.loads((state_dir(root) / "decisions.json").read_text())
    except (OSError, ValueError):
        return {}


def save(root: Path, d: dict) -> None:
    atomic.write_json(state_dir(root) / "decisions.json", d)


def _yes(fid, q, rec_label, alt_value, alt_label, alt_desc="", why=""):
    return Question(fid, q, [Option("yes", rec_label, "", True), Option(alt_value, alt_label, alt_desc)], why=why)


def questions(findings: list[dict], profile: dict, data_map: list[dict]) -> list[Question]:
    """Every decision this scan needs. Already-answered ones are filtered by the caller."""
    by_rule: dict[str, list[dict]] = {}
    for f in findings:
        by_rule.setdefault(f["rule"], []).append(f)
    qs: list[Question] = []
    eu = "eu_uk" in profile.get("regions", [])

    if data_map:
        rows = "; ".join(f"{d['data']}: {d['purpose']}" for d in data_map[:8])
        qs.append(Question("data_map", f"This is what your app collects and why: {rows}. Is that right?", [
            Option("confirm", "Yes, that's right", "", True),
            Option("edit", "Change something", "Tell the agent what to change; it edits .compliance/data-map.json")],
            why="Your privacy policy is written from this list, so it has to match reality."))
        qs.append(Question("retention", "How long should you keep a user's data after they stop using the product?", [
            Option("account_plus_30", "Until they delete their account, plus 30 days for backups", "", True),
            Option("inactive_2y", "Delete accounts inactive for 2 years"),
            Option("custom", "Something else", "Tell the agent the period")]))

    for f in by_rule.get("cookies.no_consent", []):
        qs.append(Question(f"tracker:{f['subject']}", f"{f['subject']} loads before visitors agree. What should happen to it?", [
            Option("consent", "Keep it, load only after consent", "", True),
            Option("remove", "Remove it", "Deletes the script or package from your code")]))
    if by_rule.get("cookies.no_consent"):
        qs.append(Question("consent_style", "How should visitors give consent?", [
            Option("built_in", "A small built-in banner (Accept / Reject / Settings)", "No new service; Reject is as easy as Accept", True),
            Option("cmp", "A consent platform (Cookiebot, Osano, Termly…)", "You sign up; the agent adds their script")]))

    missing_docs = sorted({DOC_FOR_RULE[f["rule"]] for f in findings if f["rule"] in DOC_FOR_RULE})
    if missing_docs:
        qs.append(Question("documents", "Which documents should the agent draft? Each one starts as a draft for a lawyer to review.",
                           [Option(d, DOC_TITLES[d], "", True) for d in missing_docs], multi=True))

    if by_rule.get("rights.delete_missing") or by_rule.get("rights.export_missing"):
        qs.append(Question("rights_style", "How should users delete or download their data?", [
            Option("self_serve", "Buttons in account settings", "Users do it themselves, instantly", True),
            Option("request_form", "A request form you handle by hand", "You must answer within 30 days (EU) / 45 days (California)")]))

    if by_rule.get("payments.refund_missing"):
        qs.append(Question("refunds", "What's your refund policy?", [
            Option("14_days", "Full refund within 14 days", "Matches the EU's 14-day withdrawal right", eu),
            Option("30_days", "Full refund within 30 days", "", not eu),
            Option("none", "No refunds, except where the law requires them"),
            Option("custom", "Something else", "Tell the agent the rule")]))

    if "ai" in {f["pack"] for f in findings}:
        qs.append(Question("ai_training", "Will you use what users type into AI features to train or improve models?", [
            Option("no", "No, never", "Simplest to explain; check your AI provider's setting matches", True),
            Option("opt_out", "Yes, but users can opt out"),
            Option("opt_in", "Only if users opt in")]))

    for f in by_rule.get("claims.compliance_claim", []) + by_rule.get("claims.unverified", []):
        qs.append(Question(f"claim:{f['fingerprint'].split('|', 1)[1]}", f"Your site says \"{f['detail']}\" ({f['subject']}). What should happen?", [
            Option("reword", "Reword it to something you can back up", "", True),
            Option("keep", "Keep it, I have evidence", "You'll be asked what the evidence is"),
            Option("remove", "Remove it")]))

    for rule in ("licenses.network_copyleft", "licenses.strong_copyleft", "licenses.restricted"):
        for f in by_rule.get(rule, []):
            qs.append(Question(f"license:{f['subject']}", f"{f['subject']} uses {f['detail']}. What should happen?", [
                Option("replace", "Find a permissively licensed alternative", "", True),
                Option("keep", "Keep it, I'll follow the license"),
                Option("lawyer", "Ask a lawyer first")]))

    for rule, qid, what in (("assets.images_unknown", "images", "images"), ("assets.font_files", "fonts", "font files")):
        f = (by_rule.get(rule) or [None])[0]
        if f:
            qs.append(Question(qid, f"Where do the {f['detail']} {what} in the project come from?", [
                Option("owned", "I made them or have licenses for all of them", "", True),
                Option("unsure", "Not sure about some", "The agent lists them so you can check or replace them"),
                Option("replace", "Replace with free-licensed ones")]))

    if by_rule.get("terms.missing"):
        qs.append(Question("governing_law", "Which country's (or US state's) law should your terms use?", kind="text",
                           fields=["governing_law"], why="Usually where your business is registered. A lawyer should confirm."))
    if by_rule.get("kids.age_gate_missing"):
        qs.append(Question("age_gate", "How should sign-up check age?", [
            Option("birthdate", "Ask for date of birth (neutral, no hint of the cut-off)", "", True),
            Option("checkbox", "A checkbox: 'I am 13 or older'", "Weaker; not enough if children are your audience")]))
    return qs


def open_questions(findings, profile, data_map, answered: dict) -> list[Question]:
    return [q for q in questions(findings, profile, data_map) if q.id not in answered and
            not (q.kind == "text" and all(answered.get(f) for f in q.fields))]


def apply(answered: dict, sets: list[str], valid: list[Question]) -> tuple[dict, list[str]]:
    errs = []
    by_id = {q.id: q for q in valid}
    text_fields = {f: q for q in valid if q.kind == "text" for f in q.fields}
    for s in sets:
        if "=" not in s:
            errs.append(f"'{s}' is not id=value")
            continue
        k, v = (x.strip() for x in s.split("=", 1))
        if k in text_fields:
            answered[k] = v
            continue
        q = by_id.get(k)
        if q is None:
            errs.append(f"no open decision '{k}'")
            continue
        vals = [x.strip() for x in v.split(",") if x.strip()]
        ok = {o.value for o in q.options}
        if not vals or any(x not in ok for x in vals):
            errs.append(f"{k}: choose from {', '.join(sorted(ok))}")
            continue
        answered[k] = vals if q.multi else vals[0]
    return answered, errs


KIND = {"legal page": "📄", "code": "🛠", "removal": "✂️"}


def changes(findings: list[dict], answered: dict) -> dict:
    """The agreed change list, plus what's left for the user and a lawyer."""
    build, you, lawyer, skipped = [], [], [], []
    docs = set(answered.get("documents", []))
    doc_added = set()
    for f in findings:
        r, s = f["rule"], f["subject"]
        if f["who"] == "lawyer":
            lawyer.append({"fingerprint": f["fingerprint"], "plain": f["plain"], "sources": f["sources"]})
            continue
        if r.startswith("claims."):
            a = answered.get(f"claim:{f['fingerprint'].split('|', 1)[1]}", "reword")
            if a == "keep":
                you.append({"fingerprint": f["fingerprint"], "plain": f"Keep proof for \"{f['detail']}\" on file.", "fix": f["fix"]})
            else:
                build.append({"fingerprint": f["fingerprint"], "kind": "code", "plain":
                              f"{'Remove' if a == 'remove' else 'Reword'} \"{f['detail']}\" in {s}", "files": f["files"], "fix": f["fix"]})
            continue
        if r.startswith("licenses.") and r != "licenses.notices_missing":
            a = answered.get(f"license:{s}")
            if a == "replace":
                build.append({"fingerprint": f["fingerprint"], "kind": "code", "plain": f"Replace {s} with a permissively licensed package",
                              "files": ["package.json"], "fix": f["fix"]})
            elif a == "lawyer":
                lawyer.append({"fingerprint": f["fingerprint"], "plain": f["plain"], "sources": f["sources"]})
            else:
                you.append({"fingerprint": f["fingerprint"], "plain": f["plain"], "fix": f["fix"]})
            continue
        if r == "assets.images_unknown" and answered.get("images") == "owned":
            skipped.append(f["fingerprint"])
            continue
        if r == "assets.font_files" and answered.get("fonts") == "owned":
            skipped.append(f["fingerprint"])
            continue
        if f["who"] == "user":
            you.append({"fingerprint": f["fingerprint"], "plain": f["plain"], "fix": f["fix"]})
            continue
        if r == "cookies.no_consent" and answered.get(f"tracker:{s}") == "remove":
            build.append({"fingerprint": f["fingerprint"], "kind": "removal", "plain": f"Remove {s} from the code",
                          "files": f["files"], "fix": f["fix"]})
            continue
        if r in DOC_FOR_RULE:
            doc = DOC_FOR_RULE[r]
            if doc not in docs:
                skipped.append(f["fingerprint"])
                continue
            if doc in doc_added:
                continue
            doc_added.add(doc)
            build.append({"fingerprint": f["fingerprint"], "kind": "legal page", "doc": doc,
                          "plain": (f"Add a {DOC_TITLES[doc].lower()} page (draft from `compliance draft {doc}`)"
                                    if doc != "third-party-notices" else
                                    "Add a third-party notices file and page (list from `compliance notices`)"), "fix": f["fix"]})
            continue
        build.append({"fingerprint": f["fingerprint"], "kind": "code", "plain": _code_plain(f, answered), "files": f["files"], "fix": f["fix"]})
        if r in ("security.secret_in_repo", "security.env_tracked"):
            you.append({"plain": f"Rotate (replace) the leaked key from {s} at the provider: moving it doesn't remove it from git history.",
                        "fix": "suggestions.md#rotate-secrets"})
    if answered.get("consent_style") == "cmp":
        you.append({"plain": "Sign up for your consent platform and send the agent its script snippet.", "fix": "suggestions.md#cmp"})
    return {"build": build, "you": you, "lawyer": lawyer, "skipped": skipped}


def _code_plain(f: dict, a: dict) -> str:
    r, s = f["rule"], f["subject"]
    return {
        "cookies.no_consent": f"Load {s} only after the visitor accepts ({'built-in banner' if a.get('consent_style', 'built_in') == 'built_in' else 'consent platform'})",
        "cookies.gpc_missing": "Treat the browser's Global Privacy Control signal as an opt-out",
        "cookies.do_not_sell_missing": "Add a 'Do Not Sell or Share My Personal Information' link to the footer",
        "cookies.remote_google_fonts": "Host your fonts on your own site instead of Google's servers",
        "consent.prechecked": f"Untick the consent checkbox in {s}",
        "rights.delete_missing": "Add 'Delete my account'" + (" to account settings" if a.get("rights_style", "self_serve") == "self_serve" else " request form"),
        "rights.export_missing": "Add 'Download my data'" + (" to account settings" if a.get("rights_style", "self_serve") == "self_serve" else " request form"),
        "rights.correct_missing": "Let users edit their name and email in account settings",
        "terms.no_clickwrap": f"Add 'By signing up you agree to the Terms and Privacy Policy' with links to {s}",
        "payments.raw_card_fields": f"Replace the card fields in {s} with the payment provider's hosted form",
        "payments.renewal_disclosure": "Say at checkout that the plan renews automatically, how often, the price, and how to cancel",
        "payments.cancel_missing": "Add an online 'Cancel subscription' button (or the provider's billing portal)",
        "ai.disclosure_missing": "Label AI-generated content and AI chat ('AI-generated, may be inaccurate')",
        "advice.disclaimer_missing": "Add a 'not professional advice' notice where that content appears",
        "kids.age_gate_missing": "Add an age check to sign-up",
        "ugc.report_missing": "Add a 'Report' button on user content",
        "security.secret_in_repo": f"Move the secret in {s} to an environment variable",
        "security.env_tracked": f"Stop tracking {s} in git and add it to .gitignore",
        "security.weak_hash": f"Switch password hashing in {s} to bcrypt or Argon2",
        "security.txt_missing": "Add /.well-known/security.txt with your security contact",
        "a11y.img_alt": "Add alt text to images that are missing it",
        "a11y.html_lang": f"Set the page language in {s}",
        "identity.contact_missing": "Add a contact email to the footer",
        "email.unsubscribe_missing": "Add an unsubscribe link to marketing emails",
    }.get(r, f["plain"])
