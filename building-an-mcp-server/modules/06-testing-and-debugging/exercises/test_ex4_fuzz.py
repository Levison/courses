"""Ex 4: Hypothesis fuzzing of package_info."""

from course_kit.exercise import run_pytest, workspace

WS = workspace(__file__)


def test_fuzz_test_exists_and_passes():
    files = [p for p in sorted(WS.glob("test_*.py"))
             if "hypothesis" in (t := p.read_text()) and "package_info" in t]
    assert files, "write a Hypothesis test (from hypothesis import given ...) for package_info in your workspace"
    for f in files:
        proc = run_pytest(f, "-k", "fuzz")
        assert proc.returncode != 5, f"no test with 'fuzz' in its name in {f.name}"
        assert proc.returncode == 0, f"{f.name}:\n{proc.stdout[-2000:]}"
