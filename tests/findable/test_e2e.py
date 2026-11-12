import json

from typer.testing import CliRunner

from findable.cli import app

runner = CliRunner()


def scan(root, *extra):
    return runner.invoke(app, ["scan", "--json", "--path", str(root), *extra])


def test_scan_fix_verify_static(project):
    root = project("static-broken")
    r = scan(root, "--url", "none")
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    fps = {f["fingerprint"] for f in out["findings"]}
    assert "seo.title|/pricing.html" in fps
    assert (root / ".findable/report.html").read_text().count("seo.title|/pricing.html") == 1

    # the "agent" fixes one finding
    p = root / "pricing.html"
    p.write_text(p.read_text().replace("<head>", "<head><title>Acme pricing plans for teams</title>", 1))
    r = runner.invoke(app, ["verify", "--json", "--path", str(root), "--ids", "seo.title|/pricing.html,aeo.h1|/pricing.html"])
    checked = {c["fingerprint"]: c["result"] for c in json.loads(r.output)["checked"]}
    assert checked == {"seo.title|/pricing.html": "fixed", "aeo.h1|/pricing.html": "still failing"}
    assert r.exit_code == 2

    # next full scan reports the delta and keeps it fixed
    out = json.loads(scan(root).output)                      # url remembered from config
    assert out["run"]["previous_run"] is True
    assert "seo.title|/pricing.html" not in {f["fingerprint"] for f in out["findings"]}


def test_needs_input_exit_code(project):
    root = project("monorepo")
    r = scan(root)
    assert r.exit_code == 3
    payload = json.loads(r.output)
    assert payload["status"] == "needs_input" and payload["questions"][0]["id"] == "app"
    r = scan(root, "--app", "apps/docs", "--url", "none")
    assert r.exit_code == 0
    r = scan(root)                                           # answer remembered: no question now
    assert r.exit_code == 0


def test_live_scan_end_to_end(project, live_site):
    root = project("static-broken")
    out = json.loads(scan(root, "--url", live_site).output)
    assert out["run"]["live_ok"] is True
    top = out["do_first"][0]
    assert top["rule"] == "geo.bot_access" or top["severity"] == "critical"
