"""Exercise 2 is a discussion question: the checkable artifact is the learner's
answer in workspace/01-example-module/NOTES.md under '## Exercise 2'."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_answer_written():
    require_answer(WS, 2, min_words=20, mentions=(("ValueError", "exception", "raise"),))
