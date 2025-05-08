"""Pytest configuration with common fixtures
"""

import pytest
from httpx import ASGITransport, AsyncClient

from orchestrator.app import create_app


@pytest.fixture(scope='session')
def test_app():
    """A testing application"""

    return create_app()


@pytest.fixture
async def async_client(test_app):
    """A testing web client"""

    async with AsyncClient(transport=ASGITransport(app=test_app),
                           base_url='http://test') as client:
        yield client


@pytest.fixture
def constants():
    """Useful constants"""
    pytest.BASE_URL = 'http://test'
    pytest.BPN = 'BPN123'
    pytest.COUNTER_PARTY_ADDRESS = 'http://example.com'
