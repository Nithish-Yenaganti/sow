import json

import pytest

from findable import findings, visibility
from findable.rules import evaluate
from findable.report import terminal
from findable.verify import fixable_scope

RAW = {"engine": "test search", "results": [
    {"query": "best widget app", "result_urls": ["https://rival.test/x", "https://www.acme.test/widgets", "https://other.test"]},
    {"query": "how to   fix widgets", "result_urls": ["https://rival.test/fix", "https://blog.rival.test/y"]},
    {"query": "acme vs rival", "result_urls": ["https://docs.acme.test/compare"]},
]}
CODE = {"pages": {}, "site": {"framework": "static", "robots": "robots.txt", "sitemap": "sitemap.xml", "orphans": []}}


def test_cited_is_decided_by_domain_not_by_the_agent():
    v = visibility.evaluate_results(RAW, "https://acme.test")
    by_q = {r["query"]: r for r in v["results"]}
    assert by_q["best widget app"]["cited"] and by_q["best widget app"]["rank"] == 2      # www. matches
    assert by_q["acme vs rival"]["cited"]                                                  # subdomain matches
    assert not by_q["how to fix widgets"]["cited"]                                         # whitespace normalised
    assert by_q["how to fix widgets"]["others"] == ["rival.test", "blog.rival.test"]
    assert (v["cited"], v["total"]) == (2, 3)


@pytest.mark.parametrize("bad", [{}, {"results": []}, {"results": [{"query": " "}]}])
def test_bad_results_are_rejected(bad):
    with pytest.raises(ValueError):
        visibility.evaluate_results(bad, "https://acme.test")


def test_record_keeps_history_and_misses_become_plain_findings(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps(RAW))
    visibility.record(tmp_path, f, "acme.test")
    latest = visibility.record(tmp_path, f, "acme.test")
    assert len(json.loads(visibility.store_path(tmp_path).read_text())["history"]) == 2
    fs = [x for x in evaluate(CODE, None, None, latest) if x.rule == "geo.ai_not_cited"]
    assert [x.url for x in fs] == ["q:how-to-fix-widgets"]
    d = fs[0].to_dict()
    assert d["group"] == "cite" and "how to fix widgets" in d["plain"] and "rival.test" in d["plain"]
    d["status"] = "new"
    out = terminal({"url": "https://acme.test", "pages": 1, "live_ok": True, "app": "."}, [d],
                   {"fixed": [], "regressed": [], "new": [], "open": []}, "r.html")
    assert "Do AI answers mention you?" in out


def test_visibility_findings_need_a_check_to_be_marked_fixed():
    store = {"geo.ai_not_cited|q:x": {"rule": "geo.ai_not_cited", "url": "q:x", "source": "visibility", "status": "open", "app": "."}}
    assert fixable_scope(store, ".", True, False, vis=False) == set()              # data deleted: can't claim fixed
    assert fixable_scope(store, ".", True, False, only_paths=["/"]) == set()       # verify doesn't re-search
    assert fixable_scope(store, ".", True, False, vis=True) == set(store)
