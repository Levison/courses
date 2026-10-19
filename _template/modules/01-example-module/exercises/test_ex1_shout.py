"""Exercise 1: add a `shout` flag. Tests the learner's workspace copy, never code/."""

from course_kit.exercise import load, workspace

WS = workspace(__file__)  # skips this file until `make start 01`


def test_shout_flag():
    greeter = load(WS, "greeter.py")
    assert greeter.greet("Ada", shout=True) == "HELLO, ADA!"


def test_default_unchanged():
    greeter = load(WS, "greeter.py")
    assert greeter.greet("Ada") == "Hello, Ada!"
