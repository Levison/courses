# COURSE TITLE

> **As of YYYY-MM-DD.** Targets: SPEC/LIBRARY X.Y (latest), TOOL A.B. This course is meant to go stale;
> re-check [the changelog](https://example.com/changelog) before reusing it.

One paragraph: who it is for, what they build, what it skips.

## What changed recently

Only if the field moved: a short old-vs-new table so learners can read older material critically.

## Prerequisites

- Toolchain and versions (verified on: ...).
- Assumed knowledge.

```bash
uv sync          # ADAPT: install the toolchain
make test        # reference code tests: must pass on a fresh clone
```

## How to take this course

The course content (`modules/`) is read-only. Your work goes in `workspace/`, which is ignored on `main`.

```bash
make learner-branch NAME=yourname   # once: creates learner/yourname, where workspace/ is tracked
make start 01                       # copies modules/01-*/code/ to workspace/01-*/ + NOTES.md
# ...edit files in workspace/01-*/, answer discussion questions in its NOTES.md...
make check 01                       # exercise tests for module 01 against your copy
make progress                       # writes PROGRESS.md (checklist of every exercise)
git add -A && git commit -m "module 01 progress"
```

Course updates land on `main`; pull them into your branch with `git merge main`. They never conflict with
your work because `main` never touches `workspace/` or `PROGRESS.md`.
Stuck? `solutions/` in each module has reference answers; `make solve NN FORCE=1` applies them.

## Module map

| # | Module | You build | Key ideas |
|---|---|---|---|
| 01 | [Example module](modules/01-example-module/) | `greeter` | Replace me |

## Learning outcomes

By the end you can:

1. ...

## Curated resources

Only verified URLs, each with a date and a note on whether it is still current.

| Resource | Date | Notes |
|---|---|---|
| [Official docs](https://example.com) | YYYY-MM | Primary source |

## Verification

What was run on the "as of" date (test counts, tools, versions) and what was not verified.
