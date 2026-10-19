# Module 01: Example module

> Replace this module. It exists to show the layout every module follows.

## Concepts

What the learner needs to know, with links to primary sources. Keep it short and current; date anything volatile.

## Tutorial

A guided walk through the reference code in [`code/`](code/). Commands assume you are in the course directory:

```bash
make start 01                         # copies code/ to workspace/01-example-module/
uv run python -c "import sys; sys.path.insert(0, 'workspace/01-example-module'); import greeter; print(greeter.greet('Ada'))"
```

## Exercises

Work in `workspace/01-example-module/` (run `make start 01` first). Check with `make check 01`.

1. Add a `shout: bool = False` parameter to `greet` that upper-cases the greeting. Edit
   `workspace/01-example-module/greeter.py`.
2. Why does `greet` raise on a blank name instead of returning an empty string? Answer in
   `workspace/01-example-module/NOTES.md` under "Exercise 2".

Reference answers: [`solutions/`](solutions/) (spoilers).

## Links

- Primary sources for this module, each with a date.
