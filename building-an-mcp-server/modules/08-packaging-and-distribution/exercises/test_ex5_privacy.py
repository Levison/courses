"""Ex 5: privacy and data-flow disclosure in the package README."""

import re

from course_kit.exercise import workspace

WS = workspace(__file__)


def test_privacy_section():
    readme = (WS / "depintel-mcp" / "README.md").read_text()
    m = re.search(r"^#{2,3} [^\n]*(privacy|data)[^\n]*$(.*?)(?=^#{1,3} |\Z)", readme, re.I | re.M | re.S)
    assert m, "add a '## Privacy' (or '## Data ...') section"
    section = m.group(2).lower()
    assert "pypi.org" in section and "osv.dev" in section, "say which services receive what"
    assert len(section.split()) >= 40, "be specific: what is sent, to whom, what is not sent, retention"
