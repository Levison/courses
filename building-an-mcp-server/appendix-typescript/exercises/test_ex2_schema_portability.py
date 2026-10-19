"""Ex 2: zod constructs and schema portability."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_answer():
    require_answer(WS, 2, min_words=30, mentions=(("tuple",), ("items",), ("strict",)))
