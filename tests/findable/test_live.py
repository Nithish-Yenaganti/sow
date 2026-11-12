from findable.rules import evaluate
from findable.scan_live import scan_live


def test_live_scan_finds_blocks_and_shells(live_site):
    live = scan_live(live_site, ["/about"], max_pages=10, concurrency=2)
    site = live["site"]
    assert site["bot_access"]["GPTBot"]["blocked"]
    assert site["bot_access"]["OAI-SearchBot"]["results"][0]["challenged"]
    assert not site["bot_access"]["Bingbot"]["blocked"]
    assert site["robots_ai"]["PerplexityBot"]["allowed_home"] is False

    code = {"pages": {}, "site": {"framework": "static", "orphans": []}}
    f = {x.fingerprint: x for x in evaluate(code, live, None)}
    access = f["geo.bot_access|site"]
    assert access.severity == "critical" and access.who == "user"
    assert "cloudflare" in access.title
    assert "geo.robots_ai|site" in f                       # PerplexityBot disallowed in robots.txt
    assert "geo.no_js_view|/pricing" in f                  # empty app shell
    assert "seo.canonical_mismatch|/pricing" in f          # canonical points to /
    assert "seo.status|/gone" in f
    assert "seo.sitemap_host|site" in f                    # localhost URL in sitemap
    assert "seo.sitemap_dead|site" in f
    assert "seo.description_duplicate|/about" in f
    assert "seo.title|/" not in f


def test_unreachable_site():
    live = scan_live("http://127.0.0.1:9", [], max_pages=3)
    assert live["site"]["reachable"] is False
