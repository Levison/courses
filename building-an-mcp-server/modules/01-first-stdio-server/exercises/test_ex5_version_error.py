"""Ex 5: unsupported protocol version error code."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_recorded_error_code():
    require_answer(WS, 5, min_words=5, mentions=(("-32022",),))
