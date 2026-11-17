"""The HTML report style and severity wording are shared by all SOW skills; keep them in sync."""

import json
import re

from typer.testing import CliRunner

from compliance.cli import app
from conftest import SKILL

SKILLS = SKILL.parent
CSS = {s: SKILLS / s / "cli" / "src" / s / "templates" / "report.css" for s in ("findable", "compliance", "guarded")}


def test_stylesheet_is_identical_in_every_skill():
    texts = {s: p.read_text() for s, p in CSS.items()}
    assert len(set(texts.values())) == 1, "copy skills/findable/cli/src/findable/templates/report.css to the others"


def test_html_builder_is_identical_in_compliance_and_guarded():
    a = (SKILLS / "compliance/cli/src/compliance/report_html.py").read_text()
    b = (SKILLS / "guarded/cli/src/guarded/report_html.py").read_text()
    assert a == b


def test_severity_labels_match_everywhere():
    want = {"critical": "Fix now", "high": "Fix now", "medium": "Fix soon", "low": "When you can"}
    for f in ("findable/cli/src/findable/report.py", "compliance/cli/src/compliance/report_html.py"):
        m = re.search(r"ACTION_LABEL = (\{[^}]+\})", (SKILLS / f).read_text())
        assert m and eval(m.group(1)) == want, f


def test_style_is_white_black_and_10_12_14pt():
    css = CSS["compliance"].read_text()
    assert "--bg: #ffffff" in css and "--ink: #000000" in css and "color-scheme: light" in css
    assert "prefers-color-scheme: dark" not in css
    assert re.search(r"body \{[^}]*font: 12pt", css)
    assert re.search(r"h1, h2, h3 \{ font-size: 14pt", css)
    assert re.search(r"\.meta, \.who, \.pill[^{]*\{ font-size: 10pt", css)


def test_scan_writes_html_report_and_escapes_project_text(project):
    root = project("saas-nextjs")
    page = root / "app/page.tsx"
    page.write_text(page.read_text().replace("The #1 AI writing assistant", "The #1 <script>alert(1)</script> assistant"))
    runner = CliRunner()
    args = []
    for a in ["categories=saas,ai", "regions=eu_uk,us_ca", "audience=consumers", "minors=adults", "charging=subscription",
              "sensitive=none", "business_name=Acme", "contact_email=a@acme.test", "business_address=skip", "business_country=US"]:
        args += ["--answer", a]
    assert runner.invoke(app, ["plan", "--json", "--path", str(root), *args]).exit_code == 0
    out = json.loads(runner.invoke(app, ["scan", "--json", "--path", str(root)]).output)
    html = (root / ".compliance/report.html").read_text()
    assert out["report_html"].endswith("report.html")
    assert "<script>alert" not in html and "Fix now" in html and "What your app collects" in html
    assert "not legal advice" in html
