import json

from typer.testing import CliRunner

from compliance.cli import app

runner = CliRunner()
INTAKE = ["categories=saas,ai", "regions=eu_uk,us_ca", "audience=consumers", "minors=adults", "charging=subscription",
          "sensitive=none", "business_name=Acme Ltd", "contact_email=privacy@acme.test", "business_address=skip",
          "business_country=Germany"]


def run(*args):
    return runner.invoke(app, list(args))


def answers(*pairs, flag="--answer"):
    out = []
    for p in pairs:
        out += [flag, p]
    return out


def intake(root):
    return run("plan", "--json", "--path", str(root), *answers(*INTAKE))


def test_plan_asks_first_and_recommends_from_code(project):
    root = project("saas-nextjs")
    r = run("plan", "--json", "--path", str(root))
    assert r.exit_code == 3
    qs = {q["id"]: q for q in json.loads(r.output)["questions"]}
    assert set(qs) == {"categories", "regions", "audience", "minors", "charging", "sensitive", "business"}
    rec = {o["value"] for o in qs["categories"]["options"] if o["recommended"]}
    assert rec == {"saas", "ai"}                                  # from next-auth + stripe subscription + openai
    assert [o["value"] for o in qs["charging"]["options"] if o["recommended"]] == ["subscription"]
    assert not (root / ".compliance").exists()                    # nothing written without answers


def test_bad_answer_is_reported(project):
    root = project("saas-nextjs")
    r = run("plan", "--json", "--path", str(root), "--answer", "regions=mars")
    assert r.exit_code == 3 and "regions" in json.loads(r.output)["errors"][0]


def test_full_flow(project):
    root = project("saas-nextjs")
    (root / "lib-config.ts").write_text('export const KEY = "sk_live_' + "a1B2c3D4e5F6g7H8i9J0" + '";\n')
    r = intake(root)
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["packs"] == ["baseline", "payments", "ai"]

    r = run("scan", "--json", "--path", str(root))
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    fps = {f["fingerprint"] for f in out["findings"]}
    for fp in ["privacy.policy_missing", "cookies.no_consent|PostHog", "cookies.remote_google_fonts", "cookies.gpc_missing",
               "consent.prechecked|app/signup/page.tsx", "rights.delete_missing", "terms.missing",
               "terms.no_clickwrap|app/signup/page.tsx", "payments.refund_missing", "payments.renewal_disclosure",
               "payments.cancel_missing", "ai.disclosure_missing|OpenAI", "licenses.strong_copyleft|gpl-thing",
               "licenses.unknown|1", "assets.stock_watermark|public/img/shutterstock_12345.jpg",
               "claims.compliance_claim|app/page.tsx|gdpr compliant", "claims.unverified|app/page.tsx|#1",
               "security.secret_in_repo|lib-config.ts:1", "identity.impressum_missing", "a11y.img_alt"]:
        assert fp in fps, fp
    assert "licenses.network_copyleft|agpl-devtool" not in fps        # dev-only dependency
    assert not any("dual" in fp for fp in fps)                         # MIT OR GPL -> permissive
    secret = next(f for f in out["findings"] if f["rule"] == "security.secret_in_repo")
    assert "a1B2c3D4" not in json.dumps(secret)                        # never print the secret
    assert {d["key"] for d in out["data_map"]} >= {"email", "password", "usage", "ai_inputs"}
    assert (root / ".compliance/report.md").read_text().count("not legal advice") == 1

    # decisions
    r = run("decide", "--json", "--path", str(root))
    assert r.exit_code == 3
    ids = {q["id"] for q in json.loads(r.output)["questions"]}
    assert {"data_map", "retention", "tracker:PostHog", "consent_style", "documents", "refunds", "ai_training",
            "license:gpl-thing", "governing_law"} <= ids
    r = run("changes", "--json", "--path", str(root))
    assert r.exit_code == 3                                            # no change list before decisions
    sets = ["data_map=confirm", "retention=account_plus_30", "tracker:PostHog=remove", "consent_style=built_in",
            "documents=privacy-policy,terms", "rights_style=self_serve", "refunds=14_days", "ai_training=no",
            "license:gpl-thing=keep", "images=owned", "fonts=owned", "governing_law=Germany"]
    sets += [f"{q}=reword" for q in ids if q.startswith("claim:")]
    r = run("decide", "--json", "--path", str(root), *answers(*sets, flag="--set"))
    assert r.exit_code == 0, r.output

    r = run("changes", "--json", "--path", str(root))
    ch = json.loads(r.output)
    plains = [c["plain"] for c in ch["build"]]
    assert "Remove PostHog from the code" in plains
    assert sum(1 for c in ch["build"] if c["kind"] == "legal page") == 2       # only the two chosen documents
    assert any("gpl-thing" in y["plain"] for y in ch["you"])                   # kept license -> user's job
    assert any("Rotate" in y["plain"] for y in ch["you"])
    assert any(l["fingerprint"] == "ai.output_ip" for l in ch["lawyer"])

    # drafts never guess unknown facts
    r = run("draft", "privacy-policy", "--json", "--path", str(root))
    d = json.loads(r.output)
    assert "postal address" in d["missing"]
    text = (root / ".compliance/drafts/privacy-policy.md").read_text()
    assert text.startswith("> **DRAFT: not legal advice.**")
    assert "Acme Ltd" in text and "OpenAI" in text and "We don't use your inputs" in text

    # the agent fixes two findings, verify confirms
    p = root / "app/signup/page.tsx"
    p.write_text(p.read_text().replace(" defaultChecked", ""))
    r = run("verify", "--json", "--path", str(root), "--ids", "consent.prechecked|app/signup/page.tsx,terms.missing")
    checked = {c["fingerprint"]: c["result"] for c in json.loads(r.output)["checked"]}
    assert checked == {"consent.prechecked|app/signup/page.tsx": "fixed", "terms.missing": "still failing"}
    assert r.exit_code == 2


def test_clean_site_has_little_to_say(project):
    root = project("clean-static")
    r = run("plan", "--json", "--path", str(root), *answers(
        "categories=content", "regions=us_other", "audience=consumers", "minors=adults", "charging=none", "sensitive=none",
        "business_name=Jo Doe", "contact_email=jo@example.test", "business_address=1 Road", "business_country=US"))
    assert r.exit_code == 0, r.output
    out = json.loads(run("scan", "--json", "--path", str(root)).output)
    assert out["findings"] == []                  # cookieless analytics, privacy page, alt text, lang, contact, security.txt
    assert out["vendors"][0]["cookieless"] is True


def test_dismiss_needs_reason_and_sticks(project):
    root = project("clean-static")
    run("plan", "--json", "--path", str(root), *answers(
        "categories=content", "regions=eu_uk", "audience=consumers", "minors=adults", "charging=none", "sensitive=none",
        "business_name=Jo", "contact_email=jo@example.test", "business_address=skip", "business_country=UK"))
    out = json.loads(run("scan", "--json", "--path", str(root)).output)
    assert [f["fingerprint"] for f in out["findings"]] == ["a11y.statement_missing"]
    assert run("dismiss", "a11y.statement_missing", "--path", str(root)).exit_code != 0     # --reason required
    assert run("dismiss", "a11y.statement_missing", "--reason", "personal site", "--path", str(root)).exit_code == 0
    assert json.loads(run("scan", "--json", "--path", str(root)).output)["findings"] == []
