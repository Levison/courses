"""Module 1: a minimal-but-real MCP server over stdio.

Run it:      uv run mcp run textkit_server.py      (or: python textkit_server.py)
Inspect it:  uv run mcp dev textkit_server.py
"""

import logging
import random
import re
from collections import Counter
from typing import Annotated

from pydantic import BaseModel, Field

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

# On stdio, stdout IS the protocol. Log to stderr only (the logging default).
log = logging.getLogger("textkit")

mcp = MCPServer(
    "textkit",
    version="0.1.0",
    instructions="Small text utilities. Use word_stats before summarising long text.",
)


class WordStats(BaseModel):
    """Structured output: the SDK derives an outputSchema from this model."""

    words: int
    unique_words: int
    sentences: int
    top_words: list[tuple[str, int]] = Field(description="Most frequent words, (word, count)")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
def word_stats(
    text: Annotated[str, Field(min_length=1, max_length=100_000, description="Text to analyse")],
    top_n: Annotated[int, Field(ge=1, le=50)] = 5,
) -> WordStats:
    """Count words, unique words and sentences, and return the most frequent words."""
    words = re.findall(r"[a-zA-Z']+", text.lower())
    sentences = len([s for s in re.split(r"[.!?]+", text) if s.strip()])
    log.info("word_stats on %d chars", len(text))
    return WordStats(
        words=len(words),
        unique_words=len(set(words)),
        sentences=sentences,
        top_words=Counter(words).most_common(top_n),
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=False))
def roll_dice(
    count: Annotated[int, Field(ge=1, le=100)] = 1,
    sides: Annotated[int, Field(ge=2, le=1000)] = 6,
) -> list[int]:
    """Roll `count` dice with `sides` sides each."""
    return [random.randint(1, sides) for _ in range(count)]


@mcp.tool()
def slugify(title: str) -> str:
    """Turn a title into a URL slug. Fails (visibly to the model) on empty output."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        # ToolError's message reaches the model as an is_error=True result.
        # Any OTHER exception is reported generically and its details stay in your logs.
        raise ToolError(f"Title {title!r} contains no slug-able characters.")
    return slug


if __name__ == "__main__":
    mcp.run()  # stdio by default
