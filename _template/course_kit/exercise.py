"""Helpers for exercise tests (pytest flavour).

ADAPT: this file is the Python/pytest binding of the course conventions. A course
in another language ports these four ideas to its own test runner:

  1. workspace(__file__)  -> the learner's copy of this module, or SKIP if not started
  2. load(ws, "file.py")  -> import a workspace file in isolation (no clash with code/)
  3. answer(ws, n)        -> the learner's NOTES.md section for exercise n
  4. require_answer(...)  -> fail with a helpful message until that section is filled in
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import uuid
from pathlib import Path
from types import ModuleType

import pytest

PLACEHOLDER = "_Your answer here._"


def course_root(start: str | Path) -> Path:
    for p in Path(start).resolve().parents:
        if (p / "course_kit").is_dir():
            return p
    raise RuntimeError(f"no course root above {start}")


def workspace(test_file: str | Path) -> Path:
    """Path to workspace/<unit>/ for the module that owns `test_file`; skips if not started.

    Call at module level:  WS = workspace(__file__)
    """
    unit = Path(test_file).resolve().parent.parent  # modules/NN-slug/exercises/test_x.py
    root = course_root(test_file)
    ws = root / "workspace" / unit.name
    if not ws.is_dir():
        key = unit.name.split("-", 1)[0] if unit.parent.name == "modules" else unit.name.removeprefix("appendix-")
        pytest.skip(f"module not started: run `make start {key}`", allow_module_level=True)
    return ws


def load(ws: Path, filename: str) -> ModuleType:
    """Import `ws/filename` as a fresh, uniquely named module.

    Sibling imports inside it (e.g. `import dev_issuer`) resolve to the workspace
    copies, and sys.modules is restored afterwards, so the reference code/ modules
    loaded by other tests are never shadowed. Every call gives fresh module state.
    """
    path = (ws / filename).resolve()
    if not path.exists():
        pytest.fail(f"{path.relative_to(course_root(path))} not found")
    siblings = {p.stem for p in path.parent.glob("*.py")}
    owned = lambda n: n.split(".")[0] in siblings  # noqa: E731
    saved = {n: m for n, m in sys.modules.items() if owned(n)}
    for n in saved:
        del sys.modules[n]
    sys.path.insert(0, str(path.parent))
    try:
        name = f"_ws_{path.stem}_{uuid.uuid4().hex[:8]}"
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(path.parent))
        for n in [n for n in sys.modules if owned(n)]:
            del sys.modules[n]
        sys.modules.update(saved)


def answer(ws: Path, n: int) -> str:
    """Text of the `## Exercise n` section of NOTES.md, minus comments and the placeholder."""
    notes = ws / "NOTES.md"
    if not notes.exists():
        return ""
    text = notes.read_text(encoding="utf-8")
    m = re.search(rf"^##\s+Exercise\s+{n}\b[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return ""
    body = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S).replace(PLACEHOLDER, "")
    return body.strip()


def require_answer(ws: Path, n: int, *, min_words: int = 25, mentions: tuple[tuple[str, ...], ...] = ()) -> str:
    """Assert NOTES.md has a real answer for exercise n.

    `mentions` is a tuple of alternatives groups: each group needs at least one of its
    terms (case-insensitive). It checks the answer engages with the key idea, not that
    it is right; the reference answer is in the module's solutions/NOTES.md.
    """
    body = answer(ws, n)
    where = f"{ws.name}/NOTES.md, section 'Exercise {n}'"
    words = len(re.findall(r"\w+", body))
    assert words >= min_words, f"Write your answer in {where} (at least {min_words} words; found {words})."
    low = body.lower()
    missing = [" / ".join(g) for g in mentions if not any(t.lower() in low for t in g)]
    assert not missing, f"Your answer in {where} should address: {'; '.join(missing)}"
    return body


def run_pytest(target: Path, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run the learner's own tests (e.g. a test they were asked to write) in a subprocess."""
    root = course_root(target)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", str(root), *args, str(target)],
        cwd=root, capture_output=True, text=True, timeout=timeout,
    )
