import json

import pytest
from typer.testing import CliRunner

from compliance import draft
from compliance.cli import app

runner = CliRunner()


@pytest.mark.parametrize("ids", ["typo.nonexistent", "terms.missing,typo.nonexistent", " , "])
def test_verify_rejects_invalid_explicit_targets(project, ids):
    root = project("saas-nextjs")
    result = runner.invoke(app, ["verify", "--path", str(root), "--ids", ids, "--json"])
    assert result.exit_code != 0
    assert json.loads(result.output)["status"] == "error"
    assert not (root / ".compliance/findings.json").exists()


@pytest.mark.parametrize("link", [".", "drafts", "profile.json"])
def test_state_symlinks_are_rejected_before_reading_or_writing(project, tmp_path, link):
    root = project("saas-nextjs")
    outside = tmp_path / "outside"
    outside.mkdir()
    state = root / ".compliance"
    if link == ".":
        state.symlink_to(outside, target_is_directory=True)
    else:
        state.mkdir()
        (state / link).symlink_to(outside, target_is_directory=True)
    result = runner.invoke(app, ["plan", "--path", str(root), "--json", "--answer", "business_name=Test"])
    assert result.exit_code != 0
    assert "symlink" in result.output.lower()
    assert list(outside.iterdir()) == []


def test_clean_scan_finishes_decision_flow(project):
    root = project("clean-static")
    args = ["plan", "--json", "--path", str(root)]
    for answer in ["categories=content", "regions=us_other", "audience=consumers", "minors=adults",
                   "charging=none", "sensitive=none", "business_name=Test", "contact_email=test@example.test",
                   "business_address=1 Test St", "business_country=US"]:
        args += ["--answer", answer]
    assert runner.invoke(app, args).exit_code == 0
    result = runner.invoke(app, ["decide", "--json", "--path", str(root)])
    assert result.exit_code == 1  # intake alone is not a completed scan
    result = runner.invoke(app, ["scan", "--json", "--path", str(root)])
    assert result.exit_code == 0 and json.loads(result.output)["findings"] == []
    result = runner.invoke(app, ["decide", "--json", "--path", str(root)])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["changes", "--json", "--path", str(root)])
    assert result.exit_code == 0 and json.loads(result.output)["build"] == []


@pytest.mark.parametrize("training", [None, "no", "opt_in", "opt_out"])
def test_privacy_draft_does_not_invent_operational_facts(training):
    answers = {} if training is None else {"ai_training": training}
    ctx = draft.context({"regions": ["eu_uk"], "minors": "adults"}, [],
                        [{"name": "OpenAI", "kind": "ai"}], ["baseline", "ai"], answers)
    text, missing = draft.render("privacy-policy", ctx)
    assert "They process data for us under contract" not in text
    assert "We protect your data with encryption in transit, access controls and hashed passwords" not in text
    assert "we rely on the EU-US Data Privacy Framework or Standard Contractual Clauses" not in text
    assert "our providers are set not to either" not in text
    assert {"security controls actually in use", "provider contracts and processing purposes",
            "international transfer safeguards", "AI provider data-use and training settings"} <= set(missing)
    if training is None:
        assert "whether you use AI inputs or outputs for training" in missing
    else:
        assert "whether you use AI inputs or outputs for training" not in missing
