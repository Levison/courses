"""Ex 4: fuzz package_info. Names that fail the PEP 508 pattern must never reach the network."""

import re
import sys
from pathlib import Path

import anyio
import httpx
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "course_kit").is_dir())
sys.path.insert(0, str(ROOT / "modules" / "03-wrapping-a-real-api" / "code"))
from depintel_server import PKG_NAME, create_server  # noqa: E402

from mcp import Client  # noqa: E402

# Bias towards nasty inputs: path and query characters, unicode, whitespace, near-valid names.
names = st.one_of(
    st.text(max_size=120),
    st.text(alphabet="abc./?#%&=@:\\ \t\n-_", max_size=40),
    st.from_regex(r"[a-z]{1,10}[/?#%][a-z./]{0,10}", fullmatch=True),
)


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(name=names)
def test_fuzz_package_info_never_requests_invalid_names(name):
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(404)

    async def run():
        async with Client(create_server(httpx.MockTransport(handler))) as c:
            return await c.call_tool("package_info", {"name": name})

    result = anyio.run(run)
    if not re.fullmatch(PKG_NAME, name):
        assert result.is_error
        assert requests == [], f"invalid name {name!r} reached upstream: {requests}"
    else:
        assert all(u.startswith("https://pypi.org/pypi/") for u in requests)
