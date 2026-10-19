"""Ex 4: sketch a URL-mode elicitation flow."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_sketch():
    require_answer(WS, 4, min_words=50, mentions=(("url",), ("retry", "retries", "poll")))
