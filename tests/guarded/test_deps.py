"""Package checks with the network replaced by a fake, so tests never call npm, PyPI or OSV."""

import json

from guarded import deps
from guarded.project import load
from guarded.scan import scan


def fake_net(npm=None, pypi=None, osv=None, vulns=None, calls=None):
    npm, pypi, osv, vulns = npm or {}, pypi or {}, osv or {}, vulns or {}

    def fetch(method, url, body):
        if calls is not None:
            calls.append((method, url, body))
        if "downloads/point" in url:
            name = url.rsplit("/last-week/", 1)[1]
            return (200, {"downloads": npm[name]["weekly"]}) if name in npm else (404, None)
        if "registry.npmjs.org" in url:
            name = url.rsplit("/", 1)[1].replace("%2f", "/")
            return (200, {"time": {"created": npm[name]["created"]}}) if name in npm else (404, None)
        if "pypi.org" in url:
            name = url.split("/pypi/")[1].split("/")[0]
            if name not in pypi:
                return 404, None
            return 200, {"releases": {"1": [{"upload_time_iso_8601": pypi[name]}]}}
        if url.endswith("/querybatch"):
            return 200, {"results": [{"vulns": [{"id": i} for i in osv.get(f"{q['package']['name']}@{q['version']}", [])]}
                                     for q in body["queries"]]}
        if "/v1/vulns/" in url:
            return 200, vulns.get(url.rsplit("/", 1)[1], {"id": url.rsplit("/", 1)[1]})
        raise AssertionError(url)
    return fetch


def test_lock_files_give_exact_versions(make):
    root = make({
        "package.json": json.dumps({"name": "app", "dependencies": {"next": "^15.0.0", "mylib": "workspace:*", "zod": "3.24.2"}}),
        "package-lock.json": json.dumps({"packages": {"node_modules/next": {"version": "15.1.0"}}}),
        "web/package.json": json.dumps({"dependencies": {"express": "^4.21.0", "@scope/pkg": "^1.0.0"}}),
        "web/pnpm-lock.yaml": "importers:\n\n  .:\n    dependencies:\n      express:\n        specifier: ^4.21.0\n"
                              "        version: 4.21.2\n      '@scope/pkg':\n        specifier: ^1.0.0\n        version: 1.2.0(react@19.0.0)\n",
        "api/package.json": json.dumps({"dependencies": {"lodash": "^4.17.0"}}),
        "api/yarn.lock": "lodash@^4.17.0, lodash@^4.17.20:\n  version \"4.17.21\"\n  resolved \"https://x\"\n",
        "requirements.txt": "requests==2.19.0\nflask>=2\n# comment\n-r other.txt\n",
        "pyproject.toml": "[project]\nname = \"x\"\ndependencies = [\n  \"langchain-core==0.3.10\",\n  \"Pydantic_Core\",\n]\n",
        "uv.lock": "[[package]]\nname = \"pydantic-core\"\nversion = \"2.27.0\"\n",
    })
    pj = load(root)
    v = {(d.ecosystem, d.name): d.version for d in pj.deps}
    assert v[("npm", "next")] == "15.1.0" and v[("npm", "zod")] == "3.24.2"
    assert v[("npm", "express")] == "4.21.2" and v[("npm", "@scope/pkg")] == "1.2.0"
    assert v[("npm", "lodash")] == "4.17.21"
    assert v[("PyPI", "requests")] == "2.19.0" and v[("PyPI", "flask")] is None
    assert v[("PyPI", "langchain-core")] == "0.3.10" and v[("PyPI", "pydantic-core")] == "2.27.0"
    assert ("npm", "mylib") not in v


def test_pyproject_read_with_a_real_toml_parser(make):
    root = make({
        "pyproject.toml": (
            "[project]\nname = 'x'\ndependencies = ['fastapi>=0.110', \"httpx==0.28.1\"]  # trailing comment\n"
            "[project.optional-dependencies]\nai = ['openai']\n"
            "[dependency-groups]\ndev = ['pytest==8.3.0', {include-group = 'lint'}]\nlint = ['ruff']\n"
            "[tool.poetry.dependencies]\npython = '^3.11'\nrequests = '2.32.3'\nlocal = {path = '../local'}\n"
            "[tool.poetry.group.test.dependencies]\nhypothesis = {version = '^6.0'}\n"),
        # Key order in lock files isn't fixed; the old regex needed `version` right after `name`.
        "uv.lock": "version = 1\n[[package]]\nsource = { registry = 'https://pypi.org/simple' }\nname = 'fastapi'\n"
                   "version = '0.115.6'\n",
    })
    deps_ = {d.name: d for d in load(root).deps}
    assert deps_["fastapi"].version == "0.115.6" and not deps_["fastapi"].dev
    assert deps_["httpx"].version == "0.28.1"
    assert deps_["openai"].dev and deps_["pytest"].version == "8.3.0" and "ruff" in deps_
    assert deps_["requests"].version == "2.32.3" and deps_["hypothesis"].version is None
    assert "python" not in deps_ and "local" not in deps_


def test_broken_toml_is_skipped_not_fatal(make):
    root = make({"pyproject.toml": "[project\ndependencies = [", "uv.lock": "not toml ["})
    assert load(root).deps == []


def test_lookalike_offline():
    assert deps.lookalike("lodahs", "npm") == "lodash"
    assert deps.lookalike("reqeusts", "PyPI") == "requests"
    for ok in ("lodash", "preact", "motion", "react-dom", "@types/node", "express-session", "requests-oauthlib"):
        assert deps.lookalike(ok, "npm" if not ok.startswith("requests") else "PyPI") is None


def test_offline_makes_no_requests(make):
    root = make({"package.json": json.dumps({"dependencies": {"made-up-pkg-zz": "1.0.0"}})})
    calls = []
    res = scan(root, online=False, fetch=fake_net(calls=calls))
    assert calls == [] and not any(f.rule.startswith("pkg.not_found") for f in res["findings"])


def test_online_flags_missing_new_and_vulnerable(make):
    root = make({"package.json": json.dumps({"dependencies": {"huggingface-utils-zz": "1.0.0", "fresh-pkg": "0.0.1",
                                                              "mcp-remote": "0.1.15", "react": "18.2.0"}}),
                 "requirements.txt": "flask-gpt-helper-qq==0.1\nlangchain-core==0.3.10\n"})
    net = fake_net(
        npm={"fresh-pkg": {"weekly": 3, "created": "2099-01-01T00:00:00Z"},
             "mcp-remote": {"weekly": 90000, "created": "2024-01-01T00:00:00Z"}},
        pypi={"langchain-core": "2023-01-01T00:00:00Z"},
        osv={"mcp-remote@0.1.15": ["GHSA-6xpm-ggf7-wc3p"], "langchain-core@0.3.10": ["GHSA-c67j-w6g6-q2cm"]},
        vulns={"GHSA-6xpm-ggf7-wc3p": {"id": "GHSA-6xpm-ggf7-wc3p", "aliases": ["CVE-2025-6514"], "summary": "OS command injection",
                                        "database_specific": {"severity": "CRITICAL"},
                                        "affected": [{"package": {"name": "mcp-remote"},
                                                      "ranges": [{"events": [{"introduced": "0.0.5"}, {"fixed": "0.1.16"}]}]}]}})
    found = {f.fingerprint: f for f in scan(root, online=True, fetch=net)["findings"]}
    assert "pkg.not_found|huggingface-utils-zz|npm" in found
    assert "pkg.not_found|flask-gpt-helper-qq|PyPI" in found
    assert "pkg.suspicious|fresh-pkg|npm" in found
    v = found["pkg.vulnerable|mcp-remote 0.1.15|npm"].to_dict()
    assert "CVE-2025-6514" in v["plain"] and "0.1.16" in v["plain"] and v["severity"] == "high"
    assert "pkg.vulnerable|langchain-core 0.3.10|PyPI" in found
    assert not any("react" in k for k in found)


def test_malware_is_called_out(make):
    root = make({"package.json": json.dumps({"dependencies": {"lodahs": "1.0.0"}})})
    net = fake_net(npm={"lodahs": {"weekly": 0, "created": "2019-01-01T00:00:00Z"}}, osv={"lodahs@1.0.0": ["MAL-2025-25502"]})
    found = {f.fingerprint: f for f in scan(root, online=True, fetch=net)["findings"]}
    assert "malware" in found["pkg.vulnerable|lodahs 1.0.0|npm"].to_dict()["plain"]


def test_network_errors_are_reported_not_guessed(make):
    root = make({"package.json": json.dumps({"dependencies": {"some-pkg": "1.0.0"}})})

    def broken(method, url, body):
        raise OSError("offline")
    res = scan(root, online=True, fetch=broken)
    assert not any(f.rule in ("pkg.not_found", "pkg.suspicious") for f in res["findings"])
    assert res["packages"]["errors"]


def test_rate_limited_downloads_are_unknown(make):
    root = make({"package.json": json.dumps({"dependencies": {"@types/node": "^22.0.0"}}),
                 "package-lock.json": json.dumps({"packages": {"node_modules/@types/node": {"version": "22.1.0"}}})})

    def limited(method, url, body):
        if "downloads" in url:
            return 429, None
        if url.endswith("/querybatch"):
            return 200, {"results": [{}]}
        raise AssertionError(url)
    assert not any(f.rule == "pkg.suspicious" for f in scan(root, online=True, fetch=limited)["findings"])
