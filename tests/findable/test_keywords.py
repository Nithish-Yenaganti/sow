import json

import pytest

from findable import keywords
from findable.report import terminal
from findable.rules import evaluate
from findable.verify import fixable_scope

RAW = {"engine": "test search", "keywords": [
    {"keyword": "best widget app", "intent": "commercial", "target_page": "/features",
     "result_urls": ["https://rival.test/a", "https://other.test/b"]},
    {"keyword": "widget vs gadget", "intent": "comparison",
     "result_urls": ["https://rival.test/c", "https://x.test", "https://y.test", "https://z.test", "https://q.test",
                     "https://www.acme.test/compare"]},
    {"keyword": "how to clean widgets", "intent": "informational", "target_page": "not a path",
     "result_urls": ["https://rival.test/d"]},
    {"keyword": "Best  widget app", "result_urls": []},                       # duplicate, ignored
]}
CODE = {"pages": {"/features": {"file": "app/features/page.tsx", "source": "code"}},
        "site": {"framework": "nextjs-app", "robots": "r", "sitemap": "s", "orphans": []}}
GSC = {"pages": [], "queries": [{"key": "best widget app", "clicks": 1, "impressions": 900, "position": 14.2}]}


def test_keywords_are_judged_by_domain_and_competitors_counted():
    k = keywords.evaluate_results(RAW, "acme.test")
    by = {x["keyword"]: x for x in k["keywords"]}
    assert len(k["keywords"]) == 3
    assert by["widget vs gadget"]["ranks"] and by["widget vs gadget"]["rank"] == 6
    assert not by["best widget app"]["ranks"] and by["best widget app"]["target_page"] == "/features"
    assert by["how to clean widgets"]["target_page"] is None                  # invalid path dropped
    assert k["top_competitors"][0] == {"domain": "rival.test", "keywords": 3}


@pytest.mark.parametrize("bad", [{}, {"keywords": []}, {"keywords": [{"keyword": ""}]}])
def test_bad_files_are_rejected(bad):
    with pytest.raises(ValueError):
        keywords.evaluate_results(bad, "acme.test")


def test_gaps_become_opportunities_with_gsc_and_page_file(tmp_path):
    f = tmp_path / "k.json"
    f.write_text(json.dumps(RAW))
    k = keywords.record(tmp_path, f, "https://acme.test")
    fs = {x.rule + x.url: x for x in evaluate(CODE, None, GSC, None, k)}
    gap = fs["seo.keyword_gap" + "kw:best-widget-app"]
    assert gap.severity == "medium" and gap.file == "app/features/page.tsx" and "900 impressions" in gap.evidence
    assert fs["seo.keyword_gap" + "kw:how-to-clean-widgets"].severity == "low"      # informational: folded as minor
    low = fs["seo.keyword_low" + "kw:widget-vs-gadget"]
    d = gap.to_dict()
    assert d["group"] == "grow" and "best widget app" in d["plain"] and "rival.test" in d["plain"]
    assert "#6" in low.to_dict()["plain"]
    d["status"] = "new"
    out = terminal({"url": "https://acme.test", "pages": 1, "live_ok": True, "app": "."}, [d],
                   {"fixed": [], "regressed": [], "new": [], "open": []}, "r.html")
    assert "Searches you could win" in out


def test_keyword_findings_need_new_research_to_be_fixed():
    store = {"seo.keyword_gap|kw:x": {"rule": "seo.keyword_gap", "url": "kw:x", "source": "keywords", "status": "open", "app": "."}}
    assert fixable_scope(store, ".", True, None, kw=False) == set()
    assert fixable_scope(store, ".", True, None, only_paths=["/"]) == set()
    assert fixable_scope(store, ".", True, None, kw=True) == set(store)
