"""Pytest configuration with common fixtures
"""

import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest
from starlette.responses import JSONResponse

from dt_pull_service.app import create_app


@pytest.fixture(scope='session')
def test_app():
    """A testing application"""

    return create_app()


@pytest.fixture
def test_client(test_app):
    """A testing web client"""

    return TestClient(test_app)


@pytest.fixture
def mock_edc_client():
    """Returns a mocked edc client"""

    payload = {
        "dcat:dataset": {
            "@id": "test-asset-id",
            "odrl:hasPolicy": {
                "@id": "test-offer-id",
                "odrl:permission": {},
                "odrl:prohibition": {},
                "odrl:obligation": {}
            }
        }
    }

    mock_client = MagicMock()
    mock_client.catalogs.get_catalog.return_value = JSONResponse(content=payload, status_code=200)

    mock_client.edrs.create.return_value = {"@id": "test-edr-id"}
    mock_client.contract_negotiations.get_state_by_id.return_value.body = json.dumps({"state": "FINALIZED"}).encode()
    mock_client.edrs.get_all.return_value = \
        JSONResponse(content=[{"transferProcessId": "test-transfer-id"}],status_code=200)

    mock_response = MagicMock()
    mock_response.body = json.dumps({
        "endpoint": "test-endpoint",
        "authorization": "test-auth"
    }).encode()
    mock_client.edrs.get_data_address.return_value = mock_response

    return mock_client
