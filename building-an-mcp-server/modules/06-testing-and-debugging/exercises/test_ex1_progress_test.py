"""Ex 1: you wrote a test that audit_requirements reports progress."""

from course_kit.exercise import run_pytest, workspace

WS = workspace(__file__)


def test_progress_test_exists_and_passes():
    files = [p for p in sorted(WS.glob("test_*.py")) if "progress_callback" in p.read_text()]
    assert files, "write a test in your workspace that passes progress_callback= to call_tool('audit_requirements', ...)"
    for f in files:
        proc = run_pytest(f, "-k", "progress")
        assert proc.returncode != 5, f"no test with 'progress' in its name in {f.name}"
        assert proc.returncode == 0, f"{f.name}:\n{proc.stdout[-2000:]}"
