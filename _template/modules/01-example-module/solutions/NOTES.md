# Notes: Module 01: Example module (reference answers)

## Exercise 1: Add a `shout: bool = False` parameter to `greet` that upper-cases the greeting.

Add the keyword with a default so existing callers are unaffected, and apply `.upper()` last so the
blank-name check still runs first. See `files/greeter.py`.

## Exercise 2: Why does `greet` raise on a blank name instead of returning an empty string?

Raising a ValueError makes the bad input impossible to miss: the caller gets an exception at the point
of the mistake instead of silently propagating an empty greeting that fails somewhere far away.
