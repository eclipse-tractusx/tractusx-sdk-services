# *************************************************************
# Eclipse Tractus-X - Test Orchestrator Service
#
# Copyright (c) 2025 BMW AG
# Copyright (c) 2025 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
# *************************************************************

"""Tests for the traceability API endpoints."""

from unittest.mock import AsyncMock, patch
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from test_orchestrator.api.traceability import router as traceability_router
from test_orchestrator.errors import HTTPError, Error

# Create a FastAPI app instance and include the router for testing
app = FastAPI()
app.include_router(traceability_router)

# Correctly handle the custom HTTPError to return a proper JSON response
@app.exception_handler(HTTPError)
async def http_error_handler(request, exc: HTTPError):
    """Error handler for the tests."""
    return JSONResponse(status_code=exc.status_code, content=exc.json)

client = TestClient(app)

# Test data
VALID_REQUEST = {
    "providerBPN": "BPNL000000000001",
    "consumerBPN": "BPNL000000000002",
    "partIds": ["part123", "part456"],
    "depth": 3,
    "strictSemver": True
}

# Mock response data
SCHEMA_CHECK_RESPONSE = {
    "step": "schema_check",
    "status": "pass",
    "details": [
        {
            "shellId": "part123",
            "submodel": "test-submodel",
            "errorPath": "",
            "message": "Schema validation successful"
        }
    ]
}

GRAPH_CHECK_RESPONSE = {
    "step": "graph_check",
    "status": "pass",
    "impact_set": [],
    "problems": []
}

EDC_SMOKE_RESPONSE = {
    "step": "edc_smoke",
    "status": "pass",
    "latency_ms": 123,
    "endpoint": "https://example.com"
}

RECALL_SCENARIO_RESPONSE = {
    "step": "recall_scenario",
    "status": "pass",
    "affected": [
        {"type": "assembly", "id": "assembly123"}
    ]
}

@pytest.fixture
def mock_schema_check():
    """Fixture to mock the schema_check function."""
    with patch("test_orchestrator.api.traceability.run_schema_check", new_callable=AsyncMock) as mock:
        mock.return_value = SCHEMA_CHECK_RESPONSE
        yield mock

@pytest.fixture
def mock_graph_check():
    """Fixture to mock the graph_check function."""
    with patch("test_orchestrator.api.traceability.run_graph_check", new_callable=AsyncMock) as mock:
        mock.return_value = GRAPH_CHECK_RESPONSE
        yield mock

@pytest.fixture
def mock_edc_smoke():
    """Fixture to mock the edc_smoke function."""
    with patch("test_orchestrator.api.traceability.run_edc_smoke", new_callable=AsyncMock) as mock:
        mock.return_value = EDC_SMOKE_RESPONSE
        yield mock

@pytest.fixture
def mock_recall_scenario():
    """Fixture to mock the recall_scenario function."""
    with patch("test_orchestrator.api.traceability.run_recall_scenario", new_callable=AsyncMock) as mock:
        mock.return_value = RECALL_SCENARIO_RESPONSE
        yield mock

@pytest.mark.asyncio
async def test_run_traceability_suite_success(
    mock_schema_check, mock_graph_check, mock_edc_smoke, mock_recall_scenario
):
    """Test successful execution of the traceability suite."""
    # Mock auth dependency
    with patch("test_orchestrator.api.traceability.verify_auth", return_value=None):
        response = client.post("/suites/traceability/run", json=VALID_REQUEST)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify the response structure
    assert data["suite"] == "traceability"
    assert "timestamp" in data
    assert data["status"] == "pass"
    assert "steps" in data
    
    # Verify all steps were executed and have the expected status
    steps = data["steps"]
    assert steps["schema_check"]["status"] == "pass"
    assert steps["graph_check"]["status"] == "pass"
    assert steps["edc_smoke"]["status"] == "pass"
    assert steps["recall_scenario"]["status"] == "pass"
    
    # Verify the mocks were called with expected arguments
    mock_schema_check.assert_called_once()
    mock_graph_check.assert_called_once()
    mock_edc_smoke.assert_called_once()
    mock_recall_scenario.assert_called_once()

@pytest.mark.asyncio
async def test_run_traceability_suite_partial_failure(
    mock_schema_check, mock_graph_check, mock_edc_smoke, mock_recall_scenario
):
    """Test execution of the traceability suite with a failing step."""
    # Make one of the steps fail
    mock_graph_check.return_value = {
        "step": "graph_check",
        "status": "fail",
        "impact_set": ["part123"],
        "problems": [{"type": "cycle", "shellIds": ["part123"]}]
    }
    
    # Mock auth dependency
    with patch("test_orchestrator.api.traceability.verify_auth", return_value=None):
        response = client.post("/suites/traceability/run", json=VALID_REQUEST)
    
    assert response.status_code == 200
    data = response.json()
    
    # Overall status should be fail if any step fails
    assert data["status"] == "fail"
    
    # Verify individual step statuses
    steps = data["steps"]
    assert steps["schema_check"]["status"] == "pass"
    assert steps["graph_check"]["status"] == "fail"
    assert steps["edc_smoke"]["status"] == "pass"
    assert steps["recall_scenario"]["status"] == "pass"

@pytest.mark.asyncio
async def test_run_traceability_suite_missing_required_fields():
    """Test execution of the traceability suite with missing required fields."""
    # Create invalid request missing required fields
    invalid_request = {
        "providerBPN": "BPNL000000000001",
        # Missing consumerBPN and partIds
        "depth": 3
    }
    
    # Mock auth dependency
    with patch("test_orchestrator.api.traceability.verify_auth", return_value=None):
        response = client.post("/suites/traceability/run", json=invalid_request)
    
    assert response.status_code == 422  # Unprocessable Entity
    data = response.json()
    assert "detail" in data  # FastAPI validation error detail