"""Ex 5: what an MCP gateway can and cannot enforce."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_design():
    require_answer(WS, 5, min_words=60, mentions=(("pin",), ("cannot", "can't", "can not")))
