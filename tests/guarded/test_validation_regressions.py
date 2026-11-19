import json

import pytest
from typer.testing import CliRunner

from guarded import deps, store
from guarded.cli import app
from guarded.project import load
from guarded.rules import Finding
from guarded.scan import scan

runner = CliRunner()


@pytest.mark.parametrize("ids", ["typo.nonexistent", "inject.shell|app.py,typo.nonexistent", " , "])
def test_verify_rejects_invalid_explicit_targets(make, ids):
    root = make({"app.py": "import subprocess\nsubprocess.run(cmd, shell=True)\n"})
    runner.invoke(app, ["scan", "--path", str(root), "--json"])
    before = (root / ".guarded/findings.json").read_bytes()
    result = runner.invoke(app, ["verify", "--path", str(root), "--ids", ids, "--json"])
    assert result.exit_code != 0
    assert json.loads(result.output)["status"] == "error"
    assert (root / ".guarded/findings.json").read_bytes() == before


@pytest.mark.parametrize("link", [".", "cache.json", ".gitignore"])
def test_state_symlinks_are_rejected_before_reading_or_writing(make, tmp_path, link):
    root = make({"package.json": "{}"})
    outside = tmp_path / "outside"
    outside.mkdir()
    state = root / ".guarded"
    if link == ".":
        state.symlink_to(outside, target_is_directory=True)
    else:
        state.mkdir()
        (state / link).symlink_to(outside, target_is_directory=True)
    result = runner.invoke(app, ["scan", "--path", str(root), "--json"])
    assert result.exit_code != 0
    assert "symlink" in result.output.lower()
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("failure", [503, 429, "transport", "malformed", "partial"])
@pytest.mark.parametrize("command", ["scan", "verify"])
def test_failed_package_recheck_keeps_previous_vulnerability(make, monkeypatch, failure, command):
    root = make({"package.json": json.dumps({"dependencies": {"mcp-remote": "0.1.15"}})})
    finding = Finding("pkg.vulnerable", "mcp-remote 0.1.15", "known advisory", key="npm").to_dict()
    st = {}
    store.apply_run(st, [finding])
    store.save_findings(root, st)

    def fetch(method, url, body):
        if "downloads" in url:
            return 200, {"downloads": 90000}
        if failure == "transport":
            raise OSError("offline")
        if failure == "malformed":
            return 200, {"unexpected": []}
        if failure == "partial":
            return 200, {"results": []}
        return failure, None

    monkeypatch.setattr(deps.Net, "_http", staticmethod(fetch))
    args = [command, "--path", str(root), "--json", "--online"]
    if command == "verify":
        args += ["--ids", finding["fingerprint"]]
    result = runner.invoke(app, args)
    out = json.loads(result.output)
    assert store.load_findings(root)[finding["fingerprint"]]["status"] in ("new", "open")
    if command == "verify":
        assert result.exit_code == 2
        assert out["checked"][0]["result"].startswith("not re-checked")
    else:
        assert result.exit_code == 0
        assert out["counts"]["high"] == 1 and out["packages"]["errors"]


def test_monorepo_checks_each_version_and_uses_its_own_python_lock(make):
    root = make({"a/package.json": '{"dependencies":{"next":"16.0.0"}}',
                 "b/package.json": '{"dependencies":{"next":"15.0.0"}}',
                 "a/pyproject.toml": '[project]\ndependencies=["requests>=2"]\n',
                 "a/uv.lock": '[[package]]\nname="requests"\nversion="2.32.0"\n',
                 "b/pyproject.toml": '[project]\ndependencies=["requests>=2"]\n',
                 "b/uv.lock": '[[package]]\nname="requests"\nversion="2.19.0"\n'})
    inventory = {(d.name, d.version, d.source) for d in load(root).deps}
    assert inventory >= {("next", "16.0.0", "a/package.json"), ("next", "15.0.0", "b/package.json"),
                         ("requests", "2.32.0", "a/pyproject.toml"), ("requests", "2.19.0", "b/pyproject.toml")}
    queries = []

    def fetch(method, url, body):
        if url.endswith("/querybatch"):
            queries.extend(body["queries"])
            return 200, {"results": [{"vulns": [{"id": "GHSA-test"}]} if q["version"] == "15.0.0" else {}
                                     for q in body["queries"]]}
        return 200, {"id": "GHSA-test", "summary": "Synthetic advisory"}

    result = scan(root, online=True, fetch=fetch)
    assert {q["version"] for q in queries} == {"16.0.0", "15.0.0", "2.32.0", "2.19.0"}
    assert any(f.fingerprint == "pkg.vulnerable|next 15.0.0|npm" for f in result["findings"])


@pytest.mark.parametrize("mode", ["offline", "unversioned", "upgrade_failed", "upgrade_checked", "removed"])
def test_package_verification_requires_evidence_for_the_current_version(make, monkeypatch, mode):
    root = make({"package.json": '{"dependencies":{"next":"15.0.0"}}'})
    finding = Finding("pkg.vulnerable", "next 15.0.0", "known advisory", key="npm").to_dict()
    st = {}
    store.apply_run(st, [finding])
    store.save_findings(root, st)
    version = "^16" if mode == "unversioned" else "16.0.0"
    if mode != "offline":
        (root / "package.json").write_text(json.dumps({"dependencies": {} if mode == "removed" else {"next": version}}))
    calls = []

    def fetch(method, url, body):
        calls.append(url)
        if mode == "upgrade_failed":
            return 503, None
        return 200, {"results": [{} for _ in body["queries"]]}

    monkeypatch.setattr(deps.Net, "_http", staticmethod(fetch))
    result = runner.invoke(app, ["verify", "--path", str(root), "--ids", finding["fingerprint"], "--json",
                                 "--offline" if mode == "offline" else "--online"])
    fixed = mode in ("upgrade_checked", "removed")
    assert result.exit_code == (0 if fixed else 2), result.output
    status = json.loads(result.output)["checked"][0]["result"]
    assert status == "fixed" if fixed else status.startswith("not re-checked")
    if mode == "offline":
        assert calls == []


def test_partial_registry_failure_preserves_only_unchecked_packages(make, monkeypatch):
    root = make({"package.json": '{"dependencies":{"a-package":"1.0.0","b-package":"1.0.0"}}'})
    findings = [Finding("pkg.not_found", name, "npm", key="npm").to_dict() for name in ("a-package", "b-package")]
    st = {}
    store.apply_run(st, findings)
    store.save_findings(root, st)

    def fetch(method, url, body):
        if url.endswith("a-package"):
            return 503, None
        if "downloads" in url:
            return 200, {"downloads": 90000}
        return 200, {"results": [{} for _ in body["queries"]]}

    monkeypatch.setattr(deps.Net, "_http", staticmethod(fetch))
    result = runner.invoke(app, ["scan", "--path", str(root), "--json", "--online"])
    assert result.exit_code == 0, result.output
    st = store.load_findings(root)
    assert st[findings[0]["fingerprint"]]["status"] in ("open", "new")
    assert st[findings[1]["fingerprint"]]["status"] == "fixed"
