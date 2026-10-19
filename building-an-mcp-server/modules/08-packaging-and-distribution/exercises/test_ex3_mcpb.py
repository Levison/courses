"""Ex 3: an MCPB bundle manifest."""

import json

from course_kit.exercise import require_answer, workspace

WS = workspace(__file__)


def test_manifest():
    manifests = [p for p in WS.rglob("manifest.json") if "node_modules" not in p.parts]
    assert manifests, "create an MCPB manifest.json (npx @anthropic-ai/mcpb init) in your workspace"
    m = json.loads(manifests[0].read_text())
    assert m.get("manifest_version") and m.get("server", {}).get("mcp_config", {}).get("command"), m
    assert m["name"] and m["version"] and m["description"]


def test_user_config_and_secrets():
    require_answer(WS, 3, min_words=25, mentions=(("user_config",), ("sensitive", "secret")))
