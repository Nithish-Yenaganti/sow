import re

import pytest

from compliance import draft, licenses
from compliance.rules import RULES
from conftest import SKILL


@pytest.mark.parametrize("expr,kind", [
    ("MIT", "permissive"), ("Apache-2.0", "permissive"), ("(MIT OR GPL-3.0)", "permissive"),
    ("MIT AND GPL-2.0-only", "strong_copyleft"), ("GPL-3.0-or-later", "strong_copyleft"), ("LGPL-2.1", "weak_copyleft"),
    ("MPL-2.0", "weak_copyleft"), ("AGPL-3.0-only", "network_copyleft"), ("SSPL-1.0", "network_copyleft"),
    ("BUSL-1.1", "restricted"), ("", "unknown"), ("UNLICENSED", "unknown"), ("SEE LICENSE IN LICENSE.md", "unknown"),
])
def test_license_classes(expr, kind):
    assert licenses.classify(expr) == kind


def test_every_rule_source_is_documented():
    ids = set(re.findall(r"^\| ([a-z0-9-]+) \|", (SKILL / "references/sources.md").read_text(), re.M))
    used = {s for r in RULES.values() for s in r.sources}
    assert used - ids == set()


def test_every_fix_anchor_exists():
    for r in RULES.values():
        path, _, anchor = r.fix.partition("#")
        text = (SKILL / path).read_text()
        if anchor:
            assert "{#" + anchor + "}" in text, r.fix


def test_every_template_renders_with_minimal_context():
    ctx = draft.context({"regions": ["eu_uk", "us_ca"], "categories": ["saas", "ai", "marketplace"],
                         "charging": "subscription", "minors": "under13"},
                        [], [{"name": "OpenAI", "kind": "ai"}, {"name": "Meta Pixel", "kind": "ads"}],
                        ["baseline", "payments", "ai", "ugc", "kids"], {})
    for doc in draft.DOCS:
        text, missing = draft.render(doc, ctx)
        assert text.startswith("> **DRAFT: not legal advice.**"), doc
        assert missing, doc                      # an empty profile always leaves facts to fill in, never guesses
