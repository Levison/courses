"""Ex 5: tool vs resource for search (design answer)."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_design_answer():
    require_answer(WS, 5, min_words=40, mentions=(("tool",), ("resource",)))
