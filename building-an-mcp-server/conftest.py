"""Shared pytest config for reference tests (modules/*/code) and exercise tests (modules/*/exercises)."""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
