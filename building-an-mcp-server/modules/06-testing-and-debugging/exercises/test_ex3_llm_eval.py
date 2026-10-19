"""Ex 3: tool-selection eval set + results."""

import json

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)
TOOLS = {"package_info", "check_vulnerabilities", "audit_requirements"}


def test_eval_set():
    path = WS / "eval_intents.json"
    assert path.exists(), "create eval_intents.json: a list of {intent, expected_tool}"
    cases = json.loads(path.read_text())
    assert len(cases) >= 20, f"need at least 20 intents, found {len(cases)}"
    for c in cases:
        assert c["intent"].strip() and c["expected_tool"] in TOOLS | {"none"}, c
    assert {c["expected_tool"] for c in cases} >= TOOLS, "cover every tool"


def test_results_recorded():
    require_answer(WS, 3, min_words=30, mentions=(("accuracy", "%"), ("description",)))
