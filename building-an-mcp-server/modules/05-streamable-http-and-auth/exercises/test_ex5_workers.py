"""Ex 5: multi-worker behavior, modern vs legacy clients."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_observations():
    require_answer(WS, 5, min_words=30, mentions=(("legacy",), ("session", "sticky", "stickiness")))
