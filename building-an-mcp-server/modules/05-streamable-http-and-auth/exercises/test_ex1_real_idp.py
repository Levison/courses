"""Ex 1: point the verifier at a real IdP (recorded in NOTES.md)."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_recorded_real_idp_run():
    require_answer(WS, 1, min_words=30, mentions=(("authorization_servers",), ("https://",), ("jwks", "pyjwkclient")))
