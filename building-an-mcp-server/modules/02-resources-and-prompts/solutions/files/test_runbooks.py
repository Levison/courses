import sys
from pathlib import Path

import anyio
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from runbook_server import mcp  # noqa: E402

from mcp import Client, MCPError  # noqa: E402
from mcp.types import PromptReference, ResourceTemplateReference  # noqa: E402


@pytest.fixture
async def client():
    async with Client(mcp, raise_exceptions=True) as c:
        yield c


@pytest.mark.anyio
async def test_static_and_template_resources(client):
    listed = await client.list_resources()
    assert [str(r.uri) for r in listed.resources] == ["runbook://index"]
    assert listed.ttl_ms == 30_000 and listed.cache_scope == "private"

    templates = await client.list_resource_templates()
    assert {t.uri_template for t in templates.resource_templates} == {
        "runbook://{slug}",
        "runbook://{slug}/checklist{?format}",
        "runbook://{slug}/history",
        "files://{+path}",
    }

    body = await client.read_resource("runbook://db-failover")
    assert "Promote replica" in body.contents[0].text

    cl = await client.read_resource("runbook://cert-expiry/checklist?format=json")
    assert '"Force renewal"' in cl.contents[0].text


@pytest.mark.anyio
async def test_missing_resource_is_invalid_params(client):
    with pytest.raises(MCPError) as exc:
        await client.read_resource("runbook://nope")
    assert exc.value.error.code == -32602


@pytest.mark.anyio
async def test_prompt_embeds_resource(client):
    p = await client.get_prompt("postmortem", {"slug": "queue-backlog", "impact": "30 min delay"})
    assert p.messages[0].content.type == "resource"
    assert "blameless postmortem" in p.messages[1].content.text


@pytest.mark.anyio
async def test_completions(client):
    r = await client.complete(PromptReference(type="ref/prompt", name="postmortem"), {"name": "slug", "value": "c"})
    assert r.completion.values == ["cert-expiry"]
    r = await client.complete(
        ResourceTemplateReference(type="ref/resource", uri="runbook://{slug}"), {"name": "slug", "value": "q"}
    )
    assert r.completion.values == ["queue-backlog"]


@pytest.mark.anyio
async def test_resource_update_notification(client):
    async with client.listen(resource_subscriptions=["runbook://db-failover"]) as sub:
        await client.call_tool("add_note", {"slug": "db-failover", "note": "replica lag was 12s"})
        with anyio.fail_after(5):
            event = await sub.__anext__()
        assert "db-failover" in str(event)
    body = await client.read_resource("runbook://db-failover")
    assert "replica lag was 12s" in body.contents[0].text


@pytest.mark.anyio
async def test_create_runbook_lists_changed(client):
    async with client.listen(resources_list_changed=True) as sub:
        await client.call_tool("create_runbook", {"slug": "disk-full", "title": "Disk full", "body": "1. Find big files"})
        with anyio.fail_after(5):
            await sub.__anext__()
    index = await client.read_resource("runbook://index")
    assert "disk-full" in index.contents[0].text
