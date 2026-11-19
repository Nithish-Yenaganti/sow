import asyncio
import json

import httpx
import pytest
from typer.testing import CliRunner

from findable.cli import app
from findable.scan_live import OWN_UA, _get, _sitemap_urls

runner = CliRunner()


@pytest.mark.parametrize("ids", ["typo.nonexistent", "seo.title|/pricing.html,typo.nonexistent", " , "])
def test_verify_rejects_invalid_explicit_targets(project, ids):
    root = project("static-broken")
    runner.invoke(app, ["scan", "--path", str(root), "--url", "none", "--json"])
    before = (root / ".findable/findings.json").read_bytes()
    result = runner.invoke(app, ["verify", "--path", str(root), "--ids", ids, "--json"])
    assert result.exit_code != 0
    assert json.loads(result.output)["status"] == "error"
    assert (root / ".findable/findings.json").read_bytes() == before


@pytest.mark.parametrize("link", [".", "inputs", "findings.json"])
def test_state_symlinks_are_rejected_before_reading_or_writing(project, tmp_path, link):
    root = project("static-broken")
    outside = tmp_path / "outside"
    outside.mkdir()
    state = root / ".findable"
    if link == ".":
        state.symlink_to(outside, target_is_directory=True)
    else:
        state.mkdir()
        (state / link).symlink_to(outside, target_is_directory=True)
    result = runner.invoke(app, ["scan", "--path", str(root), "--url", "none", "--json"])
    assert result.exit_code != 0
    assert "symlink" in result.output.lower()
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("target", ["http://127.0.0.1:9876/internal", "https://other.test/page", "ftp://owned.test/file"])
def test_sitemap_redirect_never_requests_another_site(target):
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": target})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
            urls, info = await _sitemap_urls(client, "https://owned.test/sitemap.xml", "owned.test")
            assert urls == []
            assert info["error"]

    asyncio.run(run())
    assert requests == ["https://owned.test/sitemap.xml"]


def test_redirects_allow_www_https_and_relative_paths():
    requests = []

    def handler(request):
        requests.append(str(request.url))
        if len(requests) == 1:
            return httpx.Response(301, headers={"location": "https://www.owned.test/docs"})
        if len(requests) == 2:
            return httpx.Response(302, headers={"location": "/docs/"})
        return httpx.Response(200, text="hello", headers={"content-type": "text/html"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await _get(client, "http://owned.test/docs", OWN_UA)
            assert result["status"] == 200 and result["text"] == "hello"
            assert len(result["redirects"]) == 2

    asyncio.run(run())
    assert requests[-1] == "https://www.owned.test/docs/"
