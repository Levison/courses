"""Ex 5: read the server spans for one tools/call."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_spans_recorded():
    require_answer(WS, 5, min_words=20, mentions=(("span",), ("tools/call",)))
