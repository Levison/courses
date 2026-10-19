"""Ex 2: files://{+path} template and path traversal."""

import pytest

from course_kit.exercise import load, require_answer, workspace
from mcp import Client, MCPError

WS = workspace(__file__)
ATTACKS = ["files://../runbook_server.py", "files://..%2F..%2Fetc%2Fpasswd", "files:///etc/passwd",
           "files://sub/../../runbook_server.py"]


@pytest.mark.anyio
async def test_serves_files_and_blocks_traversal():
    assert (WS / "files" / "hello.md").exists(), "create files/hello.md in your workspace"
    async with Client(load(WS, "runbook_server.py").mcp) as c:
        templates = {t.uri_template for t in (await c.list_resource_templates()).resource_templates}
        assert "files://{+path}" in templates
        ok = await c.read_resource("files://hello.md")
        assert ok.contents[0].text == (WS / "files" / "hello.md").read_text()
        for uri in ATTACKS:
            try:
                res = await c.read_resource(uri)
            except MCPError:
                continue
            text = " ".join(getattr(x, "text", "") for x in res.contents)
            assert "RUNBOOKS" not in text and "root:" not in text, f"{uri} escaped the files/ directory"


def test_who_stops_it():
    require_answer(WS, 2, min_words=20, mentions=(("sdk", "resourcesecurity", "framework", "server"),))
