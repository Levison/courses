"""Reference tests: run by `make test`. They prove the course content works."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from greeter import greet  # noqa: E402


def test_greet():
    assert greet(" Ada ") == "Hello, Ada!"


def test_blank_name_rejected():
    with pytest.raises(ValueError):
        greet("  ")
