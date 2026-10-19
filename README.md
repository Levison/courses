# Courses

Hands-on courses for my continued learning. They're deliberately current rather than evergreen: each one is pinned to the state of the art on its "as of" date, pairs the best existing material with original tutorials, and ships runnable, tested code.

| Course | As of | Summary |
| --- | --- | --- |
| [Building an MCP server](building-an-mcp-server/) | 2026-10-19 (MCP spec 2026-07-28) | From a first stdio server to remote HTTP with OAuth, testing, security hardening, and distribution. Python first, with a TypeScript appendix. 8 modules + appendix, 42 checked exercises. |

## Layout

Every course is a self-contained directory with the same shape (template: [`_template/`](_template/)):

```
<course>/
  README.md                as-of date, prerequisites, outcomes, module map, curated resources
  Makefile                 make start NN / check NN / progress / test / solve NN / list / learner-branch
  course_kit/              stdlib-only workspace + progress tool, test helpers, NOTES template
  modules/NN-slug/
    README.md              lesson: concepts, tutorial, numbered "## Exercises", links
    code/                  reference code + its tests (read-only for learners)
    exercises/             one check per exercise: test_exN_*.py
    solutions/             NOTES.md (answer per exercise) + files/ (solved workspace)
  workspace/               the learner's copies (ignored on main)
  PROGRESS.md              generated checklist (ignored on main)
```

Course content is never edited while taking a course. `make start NN` copies a module's reference code into
`<course>/workspace/NN-slug/` with a `NOTES.md` for discussion answers, and the exercise checks test that copy.

## Taking a course: the learner-branch workflow

`main` holds course content only. Learner work lives on a personal branch, so `main` stays clean and course updates
merge in without conflicts.

```bash
cd building-an-mcp-server
uv sync && make test                 # course content is green
make learner-branch NAME=chris       # once: creates learner/chris and un-ignores workspace/ + PROGRESS.md there
make start 01                        # your copy: workspace/01-first-stdio-server/
make check 01                        # exercise checks against your copy
make progress                        # PROGRESS.md: every module and exercise as a checklist
git add -A && git commit -m "mcp: module 01"
git push -u origin learner/chris     # optional backup. This repo is public, so a pushed learner branch is public too.

git switch main && git pull          # later, when a course is updated...
git switch learner/chris && git merge main
```

How it stays conflict-free: each course's `.gitignore` ends with a marked `learner-ignore` block that ignores `/workspace/`
and `/PROGRESS.md`. `make learner-branch` deletes the lines inside that block in one commit on your branch. `main` never
edits inside the block and never contains `workspace/` or `PROGRESS.md`, so merges from `main` cannot touch your files. If
you start a module on `main` by accident, nothing is lost: the files are ignored there, and `make learner-branch` picks
them up.

## Writing a course

See [COURSE_AUTHORING.md](COURSE_AUTHORING.md): conventions, how exercise checks work, and how to start a new course from `_template/`.
