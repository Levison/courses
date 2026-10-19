"""Ex 1: audit_requirements reports progress the client can observe."""

import sys
from pathlib import Path

import httpx
import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "course_kit").is_dir())
sys.path.insert(0, str(ROOT / "modules" / "03-wrapping-a-real-api" / "code"))
from depintel_server import create_server  # noqa: E402

from mcp import Client  # noqa: E402


@pytest.mark.anyio
async def test_audit_reports_progress():
    events: list[tuple[float, float | None, str | None]] = []

    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        events.append((progress, total, message))

    clean_osv = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    async with Client(create_server(clean_osv)) as c:
        r = await c.call_tool("audit_requirements", {"requirements": "a==1\nb==2\nc==3\n"}, progress_callback=on_progress)
    assert not r.is_error
    assert len(events) == 3, events  # one per line
    assert sorted(e[0] for e in events) == [1, 2, 3] and all(e[1] == 3 for e in events)
