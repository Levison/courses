"""Ex 4: token exchange sketch."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_sketch():
    require_answer(WS, 4, min_words=50, mentions=(("8693", "token exchange"), ("audience", "aud"), ("passthrough", "confused deputy", "forward")))
