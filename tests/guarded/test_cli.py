import json

from typer.testing import CliRunner

from guarded.cli import app

runner = CliRunner()
VULN = {"src/db.ts": "await pool.query(`SELECT * FROM users WHERE email = '${req.body.email}'`)\n",
        "src/run.js": "const { exec } = require('child_process')\nexec(`convert ${file} out.png`)\n"}


def run(*args):
    return runner.invoke(app, list(args))


def test_scan_writes_only_inside_state_dir(make):
    root = make(VULN)
    before = {p.relative_to(root) for p in root.rglob("*")}
    r = run("scan", "--json", "--path", str(root))
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    after = {p.relative_to(root) for p in root.rglob("*")}
    assert {p for p in after - before if p.parts[0] != ".guarded"} == set()
    assert (root / ".guarded" / ".gitignore").read_text().strip().endswith("*")
    assert out["counts"]["high"] == 2 and out["run"]["online"] is False
    assert "not a penetration test" in out["not_a_pentest"]
    assert any("--online" in n for n in out["notes"])
    report = (root / ".guarded" / "report.md").read_text()
    assert "Commands and database queries" in report and "not a penetration test" in report


def test_verify_and_dismiss_flow(make):
    root = make(VULN)
    run("scan", "--json", "--path", str(root))
    (root / "src/db.ts").write_text("await pool.query('SELECT * FROM users WHERE email = $1', [req.body.email])\n")
    r = run("verify", "--ids", "inject.sql|src/db.ts,inject.shell|src/run.js", "--path", str(root))
    assert r.exit_code == 2
    checked = {c["fingerprint"]: c["result"] for c in json.loads(r.output)["checked"]}
    assert checked == {"inject.sql|src/db.ts": "fixed", "inject.shell|src/run.js": "still failing"}
    r = run("dismiss", "inject.shell|src/run.js", "--reason", "file name comes from our own build step", "--path", str(root))
    assert r.exit_code == 0
    left = json.loads(run("report", "--path", str(root)).output)["findings"]
    assert left == []
    # A dismissed finding stays dismissed on the next scan.
    out = json.loads(run("scan", "--json", "--path", str(root)).output)
    assert out["findings"] == []


def test_offline_scan_keeps_online_findings(make):
    root = make({"package.json": json.dumps({"dependencies": {"x": "1.0.0"}})})
    state = root / ".guarded"
    state.mkdir()
    (state / "findings.json").write_text(json.dumps({"pkg.not_found|x|npm": {
        "status": "open", "rule": "pkg.not_found", "group": "packages", "severity": "high", "who": "agent", "plain": "",
        "files": []}}))
    run("scan", "--json", "--path", str(root))
    assert json.loads((state / "findings.json").read_text())["pkg.not_found|x|npm"]["status"] == "open"


def test_rules_and_bad_path(make, tmp_path):
    r = run("rules")
    ids = {x["id"] for x in json.loads(r.output)}
    assert "aitools.hidden_text" in ids and "pkg.not_found" in ids
    r = run("scan", "--json", "--path", str(tmp_path / "nope"))
    assert r.exit_code == 1
