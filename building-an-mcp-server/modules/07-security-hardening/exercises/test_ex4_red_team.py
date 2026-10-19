"""Ex 4: red-team results against two models."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_results():
    require_answer(WS, 4, min_words=60, mentions=(("fence", "fenced", "untrusted"),))
