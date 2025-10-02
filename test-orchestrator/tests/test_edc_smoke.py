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
Tests for EDC smoke test module.
"""

import pytest
from unittest.mock import AsyncMock, patch
import logging

from test_orchestrator.checks.traceability.edc_smoke import run, run_edc_smoke
from test_orchestrator.errors import HTTPError, Error

# Test data
TEST_COUNTER_PARTY_ADDRESS = "https://edc.example.com/api/v1/dsp"
TEST_COUNTER_PARTY_ID = "BPNL000000000001"
TEST_ASSET_ID = "test-asset-123"
TEST_TIMEOUT = 30

# Sample catalog response
SAMPLE_CATALOG = {
    "dcat:dataset": [
        {
            "@id": "test-asset-123",
            "dct:type": {
                "@id": "https://w3id.org/catenax/taxonomy#TestAsset"
            }
        }
    ]
}


@pytest.fixture
def mock_make_request():
    """Fixture to mock the make_request function."""
    with patch('test_orchestrator.checks.traceability.edc_smoke.make_request', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_time():
    """Fixture to mock time.time() for consistent latency measurements."""
    with patch('test_orchestrator.checks.traceability.edc_smoke.time.time') as mock:
        # Set up mock to return increasing values
        mock.side_effect = [100.0, 100.5]  # 500ms difference
        yield mock


@pytest.mark.asyncio
async def test_run_success(mock_make_request, mock_time):
    """
    Test successful EDC smoke test with all required parameters.
    """
    # Set up mock to return sample catalog
    mock_make_request.return_value = SAMPLE_CATALOG
    
    # Input parameters
    input_data = {
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS,
        'counter_party_id': TEST_COUNTER_PARTY_ID,
        'asset_id': TEST_ASSET_ID,
        'timeout': TEST_TIMEOUT
    }
    
    # Run the function
    result = await run(input_data)
    
    # Verify result
    assert result["step"] == "edc_smoke"
    assert result["status"] == "pass"
    assert result["latency_ms"] == 500  # From mock_time (100.5 - 100.0) * 1000
    assert result["endpoint"] == TEST_COUNTER_PARTY_ADDRESS
    
    # Verify mock calls
    mock_make_request.assert_called_once()
    assert mock_make_request.call_args.args[0] == 'GET'
    assert TEST_COUNTER_PARTY_ADDRESS in mock_make_request.call_args.kwargs['params']['counter_party_address']
    assert TEST_COUNTER_PARTY_ID in mock_make_request.call_args.kwargs['params']['counter_party_id']
    assert TEST_TIMEOUT == mock_make_request.call_args.kwargs['timeout']


@pytest.mark.asyncio
async def test_run_missing_parameters():
    """
    Test EDC smoke test with missing required parameters.
    """
    # Input with missing parameters
    input_data = {
        'asset_id': TEST_ASSET_ID
    }
    
    # Run the function
    result = await run(input_data)
    
    # Verify result
    assert result["step"] == "edc_smoke"
    assert result["status"] == "fail"
    assert result["latency_ms"] == 0
    assert result["endpoint"] == "N/A"
    assert "Missing required parameters" in result["details"]


@pytest.mark.asyncio
async def test_run_api_error(mock_make_request, mock_time):
    """
    Test EDC smoke test when API request fails.
    """
    # Set up mock to raise an exception
    error_message = "Connection error"
    mock_make_request.side_effect = Exception(error_message)
    
    # Input parameters
    input_data = {
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS,
        'counter_party_id': TEST_COUNTER_PARTY_ID,
        'asset_id': TEST_ASSET_ID
    }
    
    # Run the function
    result = await run(input_data)
    
    # Verify result
    assert result["step"] == "edc_smoke"
    assert result["status"] == "fail"
    assert result["latency_ms"] == 500  # From mock_time
    assert result["endpoint"] == TEST_COUNTER_PARTY_ADDRESS
    assert error_message in result["details"]


@pytest.mark.asyncio
async def test_run_edc_smoke_wrapper():
    """
    Test the run_edc_smoke wrapper function calls run with correct parameters.
    """
    # Create mock config and logger
    config = {
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS,
        'counter_party_id': TEST_COUNTER_PARTY_ID
    }
    logger = logging.getLogger(__name__)
    
    # Mock the run function
    with patch('test_orchestrator.checks.traceability.edc_smoke.run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"step": "edc_smoke", "status": "pass"}
        
        # Call the wrapper function
        result = await run_edc_smoke(config, logger)
        
        # Verify the run function was called with correct parameters
        mock_run.assert_awaited_once_with(config)
        assert result == {"step": "edc_smoke", "status": "pass"}