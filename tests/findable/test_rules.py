from findable.detect import detect
from findable.rules import evaluate
from findable.scan_code import scan_code


def rules_for(root):
    [app] = detect(root)
    return {f.fingerprint: f for f in evaluate(scan_code(app, root), None, None)}


def test_nextjs_code_rules(project):
    f = rules_for(project("nextjs-app"))
    assert f["geo.client_rendered|/pricing"].file == "app/pricing/page.tsx:1"
    assert f["geo.client_rendered|/pricing"].fix_options[0]["recommended"]
    assert "seo.title_inherited|/pricing" in f
    assert "seo.title_inherited|/" not in f            # homepage may use the layout default
    assert "seo.title_inherited|/about" not in f       # has its own metadata
    assert "seo.description_inherited|/features" in f
    assert "seo.sitemap|site" in f and "seo.robots|site" in f
    assert f["seo.orphan|site"].current == "/about"    # /pricing and /features are linked in the layout
    assert f["seo.alt|/"].current == "app/page.tsx:2"


def test_static_code_rules(project):
    f = rules_for(project("static-broken"))
    assert f["seo.robots_blocks_all|site"].severity == "critical"
    assert "seo.noindex_leak|/blog" in f
    assert "aeo.schema_invalid|/pricing.html" in f
    assert "aeo.schema|site" not in f                  # there IS schema, it's just invalid
    assert "seo.title|/pricing.html" in f
    assert f["aeo.h1|/pricing.html"].current == "2 <h1>"
    assert f["aeo.answer_first|/"].current == "How much does Acme cost?"
    assert "seo.description|/" in f
