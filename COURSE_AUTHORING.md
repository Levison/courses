# Course authoring guide

How courses in this repo are structured, and how to start a new one. `building-an-mcp-server/` is the worked example;
`_template/` is the skeleton to copy.

## Principles

- **Current, not evergreen.** Every course states an "as of" date and the exact versions it targets, and says what changed
  recently. Re-verify before reusing it; don't silently update dates.
- **Read-only content, separate learner work.** Learners never edit `modules/`. `make start NN` copies reference code into
  `workspace/NN-slug/`, and every exercise is checked against that copy.
- **Everything runs.** Reference code has tests (`make test`). Every exercise has a check and a reference solution, and the
  checks are verified to skip, then fail, then pass (see "Verifying a course").
- **Cite sources.** Curated resources carry a URL, a date and a note on whether they are still current. Only include URLs you opened.

## Directory contract

```
<course>/
  README.md               # as-of, prerequisites, outcomes, module map, curated resources, verification
  Makefile                # copied from _template; edit only the ADAPT variables
  course_kit/             # copied verbatim from _template/course_kit (do not fork per course)
  pyproject.toml          # toolchain (Python flavour shown); pytest pythonpath must include "."
  conftest.py
  .gitignore              # keep the learner-ignore block last and untouched
  modules/NN-slug/        # NN = two digits, defines order and the `make start NN` key
    README.md             # "# Module NN: Title", then sections; must contain "## Exercises"
    code/                 # reference code + tests; what `make start` copies
    exercises/test_exN_<slug>.py   # one file per exercise number N (several test functions are fine)
    solutions/NOTES.md    # "## Exercise N: ..." sections with reference answers
    solutions/files/      # solved workspace overlay (only the files that change)
    solutions/README.md   # one-paragraph spoiler warning
  appendix-<name>/        # optional; same layout, addressed as `make start <name>`
```

What the kit relies on:
- **Exercise list**: the numbered list under `## Exercises` in the module README. Item N's first sentence becomes its title
  in NOTES.md and PROGRESS.md, so make that sentence stand alone.
- **Check files**: `exercises/test_ex<N>_*.<ext>`. An exercise is **done** when its checks have no failures and at least one
  pass (skips are allowed for optional tools, e.g. a CLI that may not be installed), **not started** when everything skips
  (no workspace), and **to do** otherwise. An exercise with no check file is listed as a self-check.
- **Workspace**: `workspace/<unit dir name>/`, created from `code/` minus caches, `node_modules`, `dist`, `.venv` and `*.pem`.

## Writing exercise checks

Use the helpers in `course_kit/exercise.py` (pytest flavour):

```python
from course_kit.exercise import load, require_answer, run_pytest, workspace

WS = workspace(__file__)              # skips the whole file until `make start NN`

def test_feature():
    server = load(WS, "server.py")    # imports the learner's copy in isolation; fresh module state per call
    ...

def test_discussion():
    require_answer(WS, 3, min_words=30, mentions=(("idempotent", "retry"), ("token",)))
```

Rules of thumb:
- **Test behaviour through the public surface** (call the tool, read the resource, hit the HTTP endpoint), not
  implementation details. Pin names and shapes in the exercise text when the check needs them ("a `tenant` argument with
  `x-mcp-header: Tenant`").
- **A fresh `make start` copy must fail every check.** Otherwise the exercise is marked done before the learner does
  anything. Behavioural checks that the reference code already passes need a second, failing part (usually a NOTES answer).
- **"Write a test" exercises**: check that the learner's test file mentions the thing and passes, using `run_pytest(path)`.
  Ask for a recognisable test name (e.g. `-k fuzz`).
- **Discussion and open-ended exercises**: the artifact is the matching `## Exercise N` section of the learner's
  `NOTES.md`. `require_answer` checks length and that each `mentions` group is touched. It checks engagement, not
  correctness, so keep the groups to the one or two concepts any good answer must name, and put the real answer in
  `solutions/NOTES.md`.
- **Exercises needing things a check can't see** (real IdPs, hosts, accounts, API keys, Docker): ask for a checkable
  artifact (a script, a config file, a manifest) plus recorded observations in NOTES.md, and say in the course README
  that these are self-attested.
- **No network in checks** unless opt-in. Use mock transports, local subprocesses on free ports, and temp dirs.
- Don't import reference modules by bare name in checks; `load()` exists because `code/` and `workspace/` contain
  files with the same names.

## Solutions

- `solutions/NOTES.md` uses the same `## Exercise N: <title>` headings as the generated NOTES.md and must pass the
  discussion checks itself.
- `solutions/files/` mirrors the workspace layout, so `make solve NN FORCE=1` can overlay it. It is cumulative (all exercises
  applied). If an exercise changes a reference test's expectations (for example, a new tool changes the catalog), ship the
  updated test file too, so the learner's copy stays green.
- Say honestly what the author could not run (for example "not verified: no Docker on the build machine") instead of
  inventing results.

## Starting a new course from the template

```bash
cp -r _template my-new-course && cd my-new-course
# 1. README.md: title, as-of date, versions, prerequisites, outcomes, module map, curated resources
# 2. pyproject.toml / Makefile: fill in the ADAPT lines (deps, TEST_PATHS; COURSE_EXERCISE_CMD for non-pytest runners)
# 3. Replace modules/01-example-module/ with real modules (copy its shape)
uv sync && make test                  # reference code green
make progress                         # all exercises "not started"
```

Then add a row to the root [README.md](README.md) table.

**Other languages.** `course_kit/kit.py` is stdlib-only Python and language-agnostic: it discovers modules, copies
workspaces, and grades from a **JUnit XML** report. Point `COURSE_EXERCISE_CMD` at any runner that writes JUnit to
`{junit}` for the exercise directories in `{paths}` (jest with `jest-junit`, `go test` with `go-junit-report`,
`cargo nextest --profile ci`). Check files still follow `test_ex<N>_*` naming so results map to exercises. Port the four
helpers in `exercise.py` (workspace/skip, isolated load, NOTES answer, run learner tests) to that language's test framework.

## Verifying a course (do this before every "as of" bump)

In a throwaway clone, never on your real learner branch:

```bash
git clone . /tmp/course-check && cd /tmp/course-check/<course>
uv sync
make test                                          # reference tests pass
make progress                                      # every exercise "not started"; checks skip without a workspace
for m in $(make -s list | awk '{print $1}'); do
  make start $m >/dev/null
  make check $m && echo "BUG: $m passes before any work"
  make solve $m FORCE=1 >/dev/null && make check $m || echo "BUG: $m solutions fail"
done
make progress && cat PROGRESS.md                   # everything checked
```

## Updating `course_kit`

`course_kit/` is vendored into each course so a course can be copied out on its own. Change it in `_template/course_kit/`,
then copy it into every course and rerun their checks. `diff -r _template/course_kit <course>/course_kit` should show nothing.

## Git conventions

- `main` contains course content only: never `workspace/`, `PROGRESS.md` or secrets (`*.pem`, `.env` are ignored).
- Learners work on `learner/<name>` branches (`make learner-branch NAME=<name>`).
- Course `.gitignore`: add new rules **above** the learner-ignore comment block and never edit inside the markers. That keeps
  the learner branch's one-line deletions conflict-free.
