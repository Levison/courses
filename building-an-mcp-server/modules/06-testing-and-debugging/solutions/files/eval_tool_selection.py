"""Ex 3: measure tool-selection accuracy for the depintel catalog.

    python eval_tool_selection.py                 # offline baseline: keyword overlap "model"
    python eval_tool_selection.py --descriptions descriptions_v2.json   # try rewritten descriptions
    python eval_tool_selection.py --llm           # ADAPT: plug in your provider in choose_llm()

The point is the loop, not the model: fixed intents -> the live catalog (names +
descriptions, exactly what the model sees) -> a chooser -> accuracy and a
confusion list. Rewrite a description, rerun, compare.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import anyio

from mcp import Client

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "course_kit").is_dir())
sys.path.insert(0, str(ROOT / "modules" / "03-wrapping-a-real-api" / "code"))
from depintel_server import create_server  # noqa: E402

CASES = json.loads(Path(__file__).with_name("eval_intents.json").read_text())


def words(s: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", s.lower()))


def choose_keyword(intent: str, tools) -> str:
    """Baseline: pick the tool whose description shares the most words with the intent."""
    scores = {t.name: len(words(intent) & words(f"{t.name.replace('_', ' ')} {t.description}")) for t in tools}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else "none"


def choose_llm(intent: str, tools) -> str:  # pragma: no cover - needs an API key
    raise SystemExit("ADAPT: call your model with the tool list and return the chosen tool name or 'none'.")


async def main() -> None:
    async with Client(create_server()) as c:
        tools = (await c.list_tools()).tools
    if "--descriptions" in sys.argv:  # override descriptions without touching the server
        alt = json.loads(Path(sys.argv[sys.argv.index("--descriptions") + 1]).read_text())
        tools = [t.model_copy(update={"description": alt.get(t.name, t.description)}) for t in tools]
    choose = choose_llm if "--llm" in sys.argv else choose_keyword
    misses = [(case, got) for case in CASES if (got := choose(case["intent"], tools)) != case["expected_tool"]]
    acc = 1 - len(misses) / len(CASES)
    print(f"accuracy {acc:.0%} ({len(CASES) - len(misses)}/{len(CASES)})")
    for case, got in misses:
        print(f"  expected {case['expected_tool']:22} got {got:22} | {case['intent'][:60]!r}")


if __name__ == "__main__":
    anyio.run(main)
