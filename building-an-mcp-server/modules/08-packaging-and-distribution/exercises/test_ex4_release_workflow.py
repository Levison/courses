"""Ex 4: tag-triggered release with PyPI trusted publishing and registry publish via OIDC."""

from course_kit.exercise import workspace

WS = workspace(__file__)


def test_workflow():
    wfs = [p for p in WS.rglob("*.yml") if "release" in p.name]
    assert wfs, "write a release workflow (e.g. release.yml) in your workspace"
    text = wfs[0].read_text()
    for needle, why in [
        ("tags", "trigger on tags"),
        ("id-token: write", "OIDC token permission for trusted publishing"),
        ("pypa/gh-action-pypi-publish", "PyPI trusted publishing action"),
        ("mcp-publisher", "publish server.json to the MCP Registry"),
        ("github-oidc", "mcp-publisher login github-oidc"),
    ]:
        assert needle in text, f"{wfs[0].name}: missing {needle!r} ({why})"
