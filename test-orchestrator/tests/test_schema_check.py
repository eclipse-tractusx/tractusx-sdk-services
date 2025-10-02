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

"""
Tests for schema check module.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import logging
import jsonschema

from test_orchestrator.checks.traceability.schema_check import run, run_schema_check

# Test data
TEST_SHELL_ID = "shell-123"
TEST_SUBMODEL_ID = "submodel-456"
TEST_SEMANTIC_ID = "urn:samm:io.catenax.part_instance:1.0.0#PartInstance"
TEST_DATAPLANE_URL = "https://dataplane.example.com"
TEST_COUNTER_PARTY_ADDRESS = "https://connector.example.com/api/v1/dsp"
TEST_COUNTER_PARTY_ID = "BPNL000000000001"

# Sample shell descriptor response
SAMPLE_SHELL_DESCRIPTOR = {
    "submodelDescriptors": [
        {
            "identification": TEST_SUBMODEL_ID,
            "semanticId": {
                "value": [TEST_SEMANTIC_ID]
            },
            "endpoints": [
                {
                    "protocolInformation": {
                        "href": "https://api.example.com/submodel",
                        "subprotocolBody": "asset=asset-123;connector=example-connector"
                    }
                }
            ]
        }
    ]
}

# Sample schema
SAMPLE_SCHEMA = {
    "type": "object",
    "required": ["id", "name"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"}
    }
}

# Sample valid payload
VALID_PAYLOAD = {
    "id": "part-123",
    "name": "Test Part"
}

# Sample invalid payload (missing required field)
INVALID_PAYLOAD = {
    "id": "part-123",
    "description": "This is missing the required name field"
}


@pytest.fixture
def mock_make_request():
    """Fixture to mock the make_request function."""
    with patch('test_orchestrator.checks.traceability.schema_check.make_request', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_submodel_schema_finder():
    """Fixture to mock the submodel_schema_finder function."""
    with patch('test_orchestrator.checks.traceability.schema_check.submodel_schema_finder') as mock:
        yield mock


@pytest.fixture
def mock_fetch_submodel_info():
    """Fixture to mock the fetch_submodel_info function."""
    with patch('test_orchestrator.checks.traceability.schema_check.fetch_submodel_info') as mock:
        yield mock


@pytest.fixture
def mock_get_dtr_access():
    """Fixture to mock the get_dtr_access function."""
    with patch('test_orchestrator.checks.traceability.schema_check.get_dtr_access', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_validator():
    """Fixture to mock jsonschema.Draft7Validator."""
    with patch('test_orchestrator.checks.traceability.schema_check.jsonschema.Draft7Validator') as mock:
        # Create a mock validator instance
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.mark.asyncio
async def test_run_success(mock_make_request, mock_submodel_schema_finder, 
                          mock_fetch_submodel_info, mock_get_dtr_access, mock_validator):
    """
    Test successful schema validation with valid payload.
    """
    # Configure mocks for successful path
    mock_make_request.side_effect = [
        SAMPLE_SHELL_DESCRIPTOR,  # Shell descriptor response
        VALID_PAYLOAD             # Submodel payload
    ]
    
    mock_submodel_schema_finder.return_value = {
        "status": "ok",
        "schema": SAMPLE_SCHEMA
    }
    
    mock_fetch_submodel_info.return_value = {
        "href": "https://api.example.com/submodel",
        "subm_counterparty": TEST_COUNTER_PARTY_ID,
        "subm_operandleft": "https://w3id.org/edc/v0.0.1/ns/id",
        "subm_operandright": "asset-123"
    }
    
    mock_get_dtr_access.return_value = (
        "https://endpoint.example.com", 
        "Bearer token123",
        {"status": "ok"}
    )
    
    # Configure validator to return no errors (valid)
    mock_validator.iter_errors.return_value = []
    
    # Input parameters
    input_data = {
        'shell_ids': [TEST_SHELL_ID],
        'dataplane_url': TEST_DATAPLANE_URL,
        'counter_party_id': TEST_COUNTER_PARTY_ID,
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS
    }
    
    # Run the function
    result = await run(input_data)
    
    # Verify result
    assert result["step"] == "schema_check"
    assert result["status"] == "pass"
    assert len(result["details"]) == 1
    assert result["details"][0]["shellId"] == TEST_SHELL_ID
    assert result["details"][0]["submodel"] == TEST_SUBMODEL_ID
    assert result["details"][0]["message"] == "Schema validation successful"
    
    # Verify mock calls
    mock_make_request.assert_called()
    mock_submodel_schema_finder.assert_called_once_with(TEST_SEMANTIC_ID)
    mock_fetch_submodel_info.assert_called_once()
    mock_get_dtr_access.assert_called_once()
    mock_validator.iter_errors.assert_called_once_with(VALID_PAYLOAD)


@pytest.mark.asyncio
async def test_run_validation_failure(mock_make_request, mock_submodel_schema_finder, 
                                     mock_fetch_submodel_info, mock_get_dtr_access, mock_validator):
    """
    Test schema validation with invalid payload that fails validation.
    """
    # Configure mocks
    mock_make_request.side_effect = [
        SAMPLE_SHELL_DESCRIPTOR,  # Shell descriptor response
        INVALID_PAYLOAD           # Submodel payload
    ]
    
    mock_submodel_schema_finder.return_value = {
        "status": "ok",
        "schema": SAMPLE_SCHEMA
    }
    
    mock_fetch_submodel_info.return_value = {
        "href": "https://api.example.com/submodel",
        "subm_counterparty": TEST_COUNTER_PARTY_ID,
        "subm_operandleft": "https://w3id.org/edc/v0.0.1/ns/id",
        "subm_operandright": "asset-123"
    }
    
    mock_get_dtr_access.return_value = (
        "https://endpoint.example.com", 
        "Bearer token123",
        {"status": "ok"}
    )
    
    # Configure validator to return validation errors
    error = jsonschema.exceptions.ValidationError("'name' is a required property", 
                                                path=[], instance=INVALID_PAYLOAD)
    mock_validator.iter_errors.return_value = [error]
    
    # Input parameters
    input_data = {
        'shell_ids': [TEST_SHELL_ID],
        'dataplane_url': TEST_DATAPLANE_URL,
        'counter_party_id': TEST_COUNTER_PARTY_ID,
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS
    }
    
    # Run the function
    result = await run(input_data)
    
    # Verify result
    assert result["step"] == "schema_check"
    assert result["status"] == "fail"
    assert len(result["details"]) == 1
    assert result["details"][0]["shellId"] == TEST_SHELL_ID
    assert result["details"][0]["submodel"] == TEST_SUBMODEL_ID
    assert "required property" in result["details"][0]["message"]
    
    # Verify mock calls
    mock_validator.iter_errors.assert_called_once_with(INVALID_PAYLOAD)


@pytest.mark.asyncio
async def test_run_missing_shell_ids():
    """
    Test schema validation with missing shell IDs.
    """
    # Input with missing shell_ids
    input_data = {
        'dataplane_url': TEST_DATAPLANE_URL,
        'counter_party_id': TEST_COUNTER_PARTY_ID,
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS
    }
    
    # Run the function
    result = await run(input_data)
    
    # Verify result
    assert result["step"] == "schema_check"
    assert result["status"] == "fail"
    assert len(result["details"]) == 1
    assert result["details"][0]["errorPath"] == "input"
    assert "No shell IDs provided" in result["details"][0]["message"]


@pytest.mark.asyncio
async def test_run_schema_finder_error(mock_make_request, mock_submodel_schema_finder):
    """
    Test schema validation when schema finder fails.
    """
    # Configure mocks
    mock_make_request.return_value = SAMPLE_SHELL_DESCRIPTOR
    
    mock_submodel_schema_finder.return_value = {
        "status": "error",
        "message": "Schema not found"
    }
    
    # Input parameters
    input_data = {
        'shell_ids': [TEST_SHELL_ID],
        'dataplane_url': TEST_DATAPLANE_URL,
        'counter_party_id': TEST_COUNTER_PARTY_ID,
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS
    }
    
    # Run the function
    result = await run(input_data)
    
    # Verify result
    assert result["step"] == "schema_check"
    assert result["status"] == "fail"
    assert len(result["details"]) == 1
    assert result["details"][0]["shellId"] == TEST_SHELL_ID
    assert result["details"][0]["errorPath"] == "schema"
    assert "Failed to retrieve schema" in result["details"][0]["message"]


@pytest.mark.asyncio
async def test_run_dtr_access_error(mock_make_request, mock_submodel_schema_finder, 
                                   mock_fetch_submodel_info, mock_get_dtr_access):
    """
    Test schema validation when DTR access fails.
    """
    # Configure mocks
    mock_make_request.return_value = SAMPLE_SHELL_DESCRIPTOR
    
    mock_submodel_schema_finder.return_value = {
        "status": "ok",
        "schema": SAMPLE_SCHEMA
    }
    
    mock_fetch_submodel_info.return_value = {
        "href": "https://api.example.com/submodel",
        "subm_counterparty": TEST_COUNTER_PARTY_ID,
        "subm_operandleft": "https://w3id.org/edc/v0.0.1/ns/id",
        "subm_operandright": "asset-123"
    }
    
    # DTR access returns no endpoint
    mock_get_dtr_access.return_value = (None, None, {"status": "error"})
    
    # Input parameters
    input_data = {
        'shell_ids': [TEST_SHELL_ID],
        'dataplane_url': TEST_DATAPLANE_URL,
        'counter_party_id': TEST_COUNTER_PARTY_ID,
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS
    }
    
    # Run the function
    result = await run(input_data)
    
    # Verify result
    assert result["step"] == "schema_check"
    assert result["status"] == "fail"
    assert len(result["details"]) == 1
    assert result["details"][0]["shellId"] == TEST_SHELL_ID
    assert result["details"][0]["errorPath"] == "access"
    assert "Failed to get data access endpoint" in result["details"][0]["message"]


@pytest.mark.asyncio
async def test_run_schema_check_wrapper():
    """
    Test the run_schema_check wrapper function calls run with correct parameters.
    """
    # Create mock config and logger
    config = {
        'shell_ids': [TEST_SHELL_ID],
        'dataplane_url': TEST_DATAPLANE_URL,
        'counter_party_id': TEST_COUNTER_PARTY_ID,
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS
    }
    logger = logging.getLogger(__name__)
    
    # Mock the run function
    with patch('test_orchestrator.checks.traceability.schema_check.run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"step": "schema_check", "status": "pass"}
        
        # Call the wrapper function
        result = await run_schema_check(config, logger)
        
        # Verify the run function was called with correct parameters
        mock_run.assert_awaited_once_with(config)
        assert result == {"step": "schema_check", "status": "pass"}