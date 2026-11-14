import zipfile

from findable.gsc_csv import load
from findable.rules import evaluate
from findable.suggest import suggestions
from findable.verify import fixable_scope

CODE = {"pages": {"/pricing": {"file": "app/pricing/page.tsx", "source": "code", "title": "present", "description": "present"}},
        "site": {"framework": "nextjs-app", "robots": "app/robots.ts", "sitemap": "app/sitemap.ts", "orphans": []}}


def _reason_zip(path, issue, urls):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Table.csv", "URL,Last crawled\n" + "".join(f"{u},2026-11-01\n" for u in urls))
        z.writestr("Chart.csv", "Date,Affected pages\n2026-11-01,3\n")
        z.writestr("Metadata.csv", f"Property,Value\nIssue,{issue}\n")


def test_reason_list_exports_become_not_indexed_findings(tmp_path):
    _reason_zip(tmp_path / "a.zip", "Crawled - currently not indexed",
                ["https://acme.test/pricing", "https://acme.test/blog/old/"])
    _reason_zip(tmp_path / "b.zip", "Page with redirect", ["https://acme.test/old"])
    g = load(tmp_path)
    assert {u["reason"] for u in g["index"]["urls"]} == {"Crawled - currently not indexed", "Page with redirect"}
    fs = [f for f in evaluate(CODE, None, g) if f.rule == "seo.not_indexed"]
    assert sorted(f.url for f in fs) == ["/blog/old", "/pricing"]          # redirect is normal: skipped
    pricing = next(f for f in fs if f.url == "/pricing")
    assert pricing.file == "app/pricing/page.tsx" and pricing.severity == "medium"
    d = pricing.to_dict()
    assert d["group"] == "find" and "chose not to index it" in d["plain"]


def test_reasons_table_alone_gives_one_site_finding(tmp_path):
    (tmp_path / "Critical issues.csv").write_text(
        "Reason,Source,Validation,Pages\nNot found (404),Website,Not Started,4\n"
        "Crawled – currently not indexed,Google systems,Not Started,9\nPage with redirect,Website,N/A,50\n")
    g = load(tmp_path)
    fs = [f for f in evaluate(CODE, None, g) if f.rule == "seo.index_summary"]
    assert len(fs) == 1 and "13 page" in fs[0].title and "Crawled" in fs[0].current
    assert not any(s.rule == "setup.gsc_index" for s in suggestions(CODE["site"], None, "https://acme.test", g, None))


def test_performance_only_suggests_the_indexing_export_and_scopes_stay_separate(tmp_path):
    (tmp_path / "Pages.csv").write_text("Top pages,Clicks,Impressions,CTR,Position\nhttps://acme.test/x,1,100,1%,9\n")
    g = load(tmp_path)
    assert any(s.rule == "setup.gsc_index" for s in suggestions(CODE["site"], None, "https://acme.test", g, None))
    store = {"seo.not_indexed|/x": {"rule": "seo.not_indexed", "url": "/x", "source": "gsc_index", "status": "open", "app": "."}}
    assert fixable_scope(store, ".", True, g) == set()     # no indexing export this run: can't claim it's fixed
