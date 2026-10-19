"""Reference code for the example module. Learners never edit this file;
`make start 01` copies it to workspace/01-example-module/greeter.py."""


def greet(name: str) -> str:
    """Return a greeting for `name`."""
    if not name.strip():
        raise ValueError("name must not be blank")
    return f"Hello, {name.strip()}!"
