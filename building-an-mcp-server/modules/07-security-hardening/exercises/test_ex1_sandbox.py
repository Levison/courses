"""Ex 1: a sandboxed launch recipe for the hardened server."""

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_recipe():
    script = WS / "sandbox.sh"
    assert script.exists(), "write sandbox.sh with your docker run recipe"
    text = script.read_text()
    for flag in ("--network none", "--read-only", ":ro"):
        assert flag in text, f"sandbox.sh should use {flag}"


def test_what_stops_working():
    require_answer(WS, 1, min_words=20, mentions=(("fetch_doc_page",), ("network",)))
