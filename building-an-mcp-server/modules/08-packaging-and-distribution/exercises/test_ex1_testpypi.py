"""Ex 1: published to TestPyPI (recorded in NOTES.md)."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_recorded():
    require_answer(WS, 1, min_words=15, mentions=(("test.pypi.org",), ("uvx",)))
