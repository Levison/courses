"""Solution to exercise 1 (`make solve 01 FORCE=1` copies it into your workspace)."""


def greet(name: str, shout: bool = False) -> str:
    """Return a greeting for `name`, upper-cased when `shout` is true."""
    if not name.strip():
        raise ValueError("name must not be blank")
    text = f"Hello, {name.strip()}!"
    return text.upper() if shout else text
