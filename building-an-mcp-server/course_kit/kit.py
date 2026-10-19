#!/usr/bin/env python3
"""Course kit: learner workspace, exercise checks and progress tracking.

Course-agnostic and stdlib-only, so it works for courses in any language as long
as the exercise runner can write JUnit XML (pytest, jest-junit, go-junit-report,
cargo-nextest, ...). Driven by the course Makefile; run `python course_kit/kit.py -h`.

Conventions (see COURSE_AUTHORING.md at the repo root):
  modules/NN-slug/README.md        lesson + "## Exercises" numbered list
  modules/NN-slug/code/            reference code (read-only for learners)
  modules/NN-slug/exercises/       one test file per exercise: test_ex<N>_*.<ext>
  modules/NN-slug/solutions/       NOTES.md (answers per exercise) + files/ (overlay)
  appendix-*/                      same layout; addressed by its suffix (e.g. "typescript")
  workspace/<unit>/                the learner's copy (gitignored on main)
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the course directory
WORKSPACE = ROOT / "workspace"
PROGRESS = ROOT / "PROGRESS.md"
NOTES_TEMPLATE = Path(__file__).with_name("NOTES.template.md")
PLACEHOLDER = "_Your answer here._"

# Never copied into a workspace (build output, deps, secrets, caches).
COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".pytest_cache", "node_modules", "dist", "build", "*.egg-info",
    ".venv", "*.pem", ".env", "target", ".hypothesis",
)

# ADAPT: the command that runs exercise tests and writes JUnit XML. {junit} is the
# report path and {paths} the exercise directories. Override with COURSE_EXERCISE_CMD.
DEFAULT_RUNNER = "{python} -m pytest -q -p no:cacheprovider -o junit_family=xunit1 --junitxml={junit} {paths}"


@dataclass
class Exercise:
    n: int
    title: str
    text: str
    tests: list[Path] = field(default_factory=list)
    status: str = "todo"  # done | todo | not-started | ungraded


@dataclass
class Unit:
    path: Path
    key: str  # "01" for modules/01-foo, "typescript" for appendix-typescript
    title: str
    exercises: list[Exercise]

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def workspace(self) -> Path:
        return WORKSPACE / self.name

    @property
    def started(self) -> bool:
        return self.workspace.is_dir()


# --------------------------------------------------------------------- discovery
def parse_readme(readme: Path) -> tuple[str, list[Exercise]]:
    text = readme.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else readme.parent.name
    sec = re.search(r"^##\s+Exercises\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    exercises: list[Exercise] = []
    if sec:
        # Numbered items; continuation lines are indented.
        for item in re.finditer(r"^(\d+)\.\s+(.*?)(?=^\d+\.\s|\Z)", sec.group(1), re.M | re.S):
            body = " ".join(line.strip() for line in item.group(2).strip().splitlines())
            exercises.append(Exercise(int(item.group(1)), short_title(body), body))
    return title, exercises


def short_title(body: str, limit: int = 100) -> str:
    first = re.split(r"(?<!e\.g\.)(?<!i\.e\.)(?<=[.?!])\s", body, maxsplit=1)[0]
    first = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", first)  # drop link targets
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


def discover() -> list[Unit]:
    units: list[Unit] = []
    dirs = sorted(p for p in (ROOT / "modules").glob("*") if p.is_dir() and re.match(r"\d+-", p.name))
    dirs += sorted(p for p in ROOT.glob("appendix-*") if p.is_dir())
    for d in dirs:
        if not (d / "README.md").exists():
            continue
        title, exercises = parse_readme(d / "README.md")
        key = d.name.split("-", 1)[0] if d.parent.name == "modules" else d.name.removeprefix("appendix-")
        for ex in exercises:
            ex.tests = sorted((d / "exercises").glob(f"test_ex{ex.n}_*")) + sorted(
                (d / "exercises").glob(f"test_ex{ex.n}.*")
            )
        units.append(Unit(d, key, title, exercises))
    return units


def find_unit(key: str) -> Unit:
    key = key.strip()
    units = discover()
    for u in units:
        if key in (u.key, u.name, u.name.split("-", 1)[-1]) or (key.isdigit() and u.key.isdigit() and int(key) == int(u.key)):
            return u
    sys.exit(f"No module {key!r}. Available: {', '.join(u.key for u in units)}")


# --------------------------------------------------------------------- commands
def cmd_list(_args) -> int:
    for u in discover():
        state = "started" if u.started else "-"
        print(f"{u.key:>12}  {u.name:45} {len(u.exercises):2} exercises  {state}")
    return 0


def notes_for(u: Unit) -> str:
    sections = "\n".join(
        f"## Exercise {ex.n}: {ex.title}\n\n<!-- {ex.text.replace('--', '-')} -->\n\n{PLACEHOLDER}\n"
        for ex in u.exercises
    )
    tpl = NOTES_TEMPLATE.read_text(encoding="utf-8")
    return (
        tpl.replace("{{title}}", u.title)
        .replace("{{unit}}", u.name)
        .replace("{{key}}", u.key)
        .replace("{{date}}", dt.date.today().isoformat())
        .replace("{{exercises}}", sections)
    )


def cmd_start(args) -> int:
    u = find_unit(args.unit)
    if u.started and not args.force:
        print(f"workspace/{u.name}/ already exists; your work is untouched. (FORCE=1 to recopy code/ over it.)")
        return 0
    src = u.path / "code"
    if src.is_dir():
        shutil.copytree(src, u.workspace, ignore=COPY_IGNORE, dirs_exist_ok=True)
    else:
        u.workspace.mkdir(parents=True, exist_ok=True)
    notes = u.workspace / "NOTES.md"
    if not notes.exists():
        notes.write_text(notes_for(u), encoding="utf-8")
    rel = u.workspace.relative_to(ROOT)
    print(f"Started {u.title}\n  your copy:  {rel}/\n  notes:      {rel}/NOTES.md")
    print(f"  exercises:  {u.path.relative_to(ROOT)}/README.md#exercises")
    print(f"  check:      make check {u.key}      progress: make progress")
    return 0


def run_exercises(units: list[Unit], show_output: bool) -> dict[tuple[str, int], list[str]]:
    """Run exercise tests; return {(unit name, exercise n): [outcome, ...]}."""
    paths = [str(u.path / "exercises") for u in units if (u.path / "exercises").is_dir()]
    if not paths:
        return {}
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "junit.xml"
        tpl = os.environ.get("COURSE_EXERCISE_CMD", DEFAULT_RUNNER)
        cmd = tpl.format(python=shlex.quote(sys.executable), junit=shlex.quote(str(junit)),
                         paths=" ".join(shlex.quote(p) for p in paths))
        proc = subprocess.run(cmd, shell=True, cwd=ROOT, text=True, capture_output=not show_output)
        if not junit.exists():
            if not show_output:
                sys.stderr.write(proc.stdout + proc.stderr)
            sys.exit(f"exercise runner wrote no JUnit report (exit {proc.returncode}): {cmd}")
        outcomes: dict[tuple[str, int], list[str]] = {}
        names = {u.name for u in units}
        for case in ET.parse(junit).getroot().iter("testcase"):
            where = (case.get("file") or "") + " " + (case.get("classname") or "").replace(".", "/")
            unit = next((n for n in names if n in where), None)
            m = re.search(r"test_ex(\d+)", where)
            if not unit or not m:
                continue
            if case.find("skipped") is not None:
                outcome = "skipped"
            elif case.find("failure") is not None or case.find("error") is not None:
                outcome = "failed"
            else:
                outcome = "passed"
            outcomes.setdefault((unit, int(m.group(1))), []).append(outcome)
        return outcomes


def grade(units: list[Unit], outcomes: dict) -> None:
    for u in units:
        for ex in u.exercises:
            got = outcomes.get((u.name, ex.n), [])
            if not ex.tests:
                ex.status = "ungraded"
            elif not u.started or (got and all(o == "skipped" for o in got)):
                ex.status = "not-started"
            elif "failed" not in got and "passed" in got:
                ex.status = "done"  # optional checks may skip (e.g. a missing tool) as long as nothing fails
            else:
                ex.status = "todo"


def render_progress(units: list[Unit]) -> str:
    graded = [ex for u in units for ex in u.exercises if ex.status != "ungraded"]
    done = sum(ex.status == "done" for ex in graded)
    started = sum(u.started for u in units)
    course = re.search(r"^#\s+(.+)$", (ROOT / "README.md").read_text(encoding="utf-8"), re.M)
    now = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    out = [
        f"# Progress: {course.group(1) if course else ROOT.name}",
        "",
        f"_Generated by `make progress` at {now}. Don't edit by hand; it is overwritten._",
        "",
        f"**{done}/{len(graded)} exercises done** · {started}/{len(units)} modules started",
        "",
    ]
    for u in units:
        ud = sum(ex.status == "done" for ex in u.exercises)
        ug = sum(ex.status != "ungraded" for ex in u.exercises)
        state = f"{ud}/{ug} done" if u.started else f"not started: `make start {u.key}`"
        if u.started and ug and ud == ug:
            state += " ✅"
        title = re.sub(r"^(Module|Appendix)\s+\w+\s*[:.]\s*", "", u.title)
        out += [f"## {u.key} · {title} — {state}", ""]
        for ex in u.exercises:
            box = "x" if ex.status == "done" else " "
            tag = {"ungraded": " _(self-check, no test)_", "todo": "", "not-started": "", "done": ""}[ex.status]
            out.append(f"- [{box}] Ex {ex.n}: {ex.title}{tag}")
        out.append("")
    return "\n".join(out)


def cmd_progress(args) -> int:
    units = discover()
    grade(units, run_exercises(units, show_output=False))
    PROGRESS.write_text(render_progress(units), encoding="utf-8")
    graded = [ex for u in units for ex in u.exercises if ex.status != "ungraded"]
    print(f"wrote {PROGRESS.relative_to(ROOT)}: {sum(e.status == 'done' for e in graded)}/{len(graded)} exercises done")
    return 0


def cmd_check(args) -> int:
    u = find_unit(args.unit)
    if not u.started:
        print(f"{u.title}: not started. Run `make start {u.key}` first.")
        return 1
    outcomes = run_exercises([u], show_output=True)
    grade([u], outcomes)
    print(f"\n{u.title}")
    for ex in u.exercises:
        mark = {"done": "✔", "todo": "✘", "not-started": "·", "ungraded": "?"}[ex.status]
        print(f"  {mark} Ex {ex.n}: {ex.title}")
    return 0 if all(ex.status in ("done", "ungraded") for ex in u.exercises) else 1


def cmd_solve(args) -> int:
    u = find_unit(args.unit)
    sol = u.path / "solutions"
    if not args.force:
        print(f"Spoiler guard: this overwrites files in workspace/{u.name}/ with the reference answers.\n"
              f"Commit your work first, then run: make solve {u.key} FORCE=1\n"
              f"(Or just read {sol.relative_to(ROOT)}/ instead.)")
        return 1
    if not u.started:
        cmd_start(argparse.Namespace(unit=u.key, force=False))
    if (sol / "files").is_dir():
        shutil.copytree(sol / "files", u.workspace, ignore=COPY_IGNORE, dirs_exist_ok=True)
    if (sol / "NOTES.md").exists():
        notes = u.workspace / "NOTES.md"
        if notes.exists():
            shutil.copy2(notes, u.workspace / "NOTES.before-solve.md")
        shutil.copy2(sol / "NOTES.md", notes)
    print(f"Applied {sol.relative_to(ROOT)}/ to workspace/{u.name}/")
    return 0


LEARNER_BEGIN = "# >>> learner-ignore"
LEARNER_END = "# <<< learner-ignore"


def cmd_learner_branch(args) -> int:
    name = args.unit or os.environ.get("USER", "me")
    branch = name if name.startswith("learner/") else f"learner/{name}"
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, check=True)  # noqa: E731
    gi = ROOT / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines(keepends=True)
    if LEARNER_BEGIN not in "".join(lines):
        sys.exit(f"{gi} has no '{LEARNER_BEGIN}' block")
    current = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if current != branch:
        git("switch", "-c", branch)
    keep, inside = [], False
    for line in lines:
        if line.startswith(LEARNER_BEGIN):
            inside = True
            keep.append(line)
            continue
        if line.startswith(LEARNER_END):
            inside = False
        if not inside:
            keep.append(line)
    gi.write_text("".join(keep), encoding="utf-8")
    git("add", str(gi))
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
        git("commit", "-q", "-m", f"{ROOT.name}: track workspace/ and PROGRESS.md on {branch}")
    print(f"On {branch}: workspace/ and PROGRESS.md are now tracked here (still ignored on main).")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, needs_unit in [
        ("list", cmd_list, False), ("start", cmd_start, True), ("check", cmd_check, True),
        ("progress", cmd_progress, False), ("solve", cmd_solve, True), ("learner-branch", cmd_learner_branch, False),
    ]:
        sp = sub.add_parser(name)
        sp.add_argument("unit", nargs=None if needs_unit else "?", help="module number/slug (learner-branch: your name)")
        sp.add_argument("--force", action="store_true", default=os.environ.get("FORCE") == "1")
        sp.set_defaults(fn=fn)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
