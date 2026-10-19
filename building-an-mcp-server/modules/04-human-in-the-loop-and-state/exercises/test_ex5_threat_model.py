"""Ex 5: threat model for injected approvals."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_threat_model():
    require_answer(WS, 5, min_words=40, mentions=(("human", "user"), ("auto",)))
