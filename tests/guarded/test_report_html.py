import json

from typer.testing import CliRunner

from guarded.cli import app


def test_scan_writes_html_report_with_labels(tmp_path):
    (tmp_path / "app.js").write_text('const q = "SELECT * FROM users WHERE id = " + req.query.id;\ndb.query(q);\n')
    out = json.loads(CliRunner().invoke(app, ["scan", "--json", "--path", str(tmp_path)]).output)
    html = (tmp_path / ".guarded" / "report.html").read_text()
    assert out["report_html"].endswith("report.html")
    assert "#ffffff" in html and "not a penetration test" in html
    assert any(label in html for label in ("Fix now", "Fix soon", "When you can"))
    assert "req.query.id;\ndb" not in html          # quoted code is escaped/plain, never raw markup
