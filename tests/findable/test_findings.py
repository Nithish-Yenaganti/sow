from findable import findings
from findable.rules import Finding


def F(rule, url="/x"):
    return Finding(rule, url, rule, "now", "target", "medium")


def test_lifecycle():
    store = {}
    d = findings.apply_run(store, [F("a"), F("b")])
    assert sorted(d["new"]) == ["a|/x", "b|/x"]
    d = findings.apply_run(store, [F("a")])
    assert d["fixed"] == ["b|/x"] and store["a|/x"]["status"] == "open"
    d = findings.apply_run(store, [F("a"), F("b")])
    assert d["regressed"] == ["b|/x"]
    assert findings.dismiss(store, "a|/x", "intentional")
    findings.apply_run(store, [F("a"), F("b")])
    assert store["a|/x"]["status"] == "dismissed"          # never re-raised
    assert [r["fingerprint"] for r in findings.active(store)] == ["b|/x"]


def test_scope_prevents_false_fixes():
    store = {}
    findings.apply_run(store, [F("live.thing")])
    d = findings.apply_run(store, [], scope=set())          # e.g. code-only run can't confirm live findings
    assert d["fixed"] == [] and store["live.thing|/x"]["status"] == "new"
