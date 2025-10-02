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
Tests for graph check module.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import logging
import networkx as nx

from test_orchestrator.checks.traceability.graph_check import run, run_graph_check

# Test data
TEST_SHELL_ID = "shell-123"
TEST_SHELL_ID_2 = "shell-456"
TEST_DATAPLANE_URL = "https://dataplane.example.com"
TEST_COUNTER_PARTY_ADDRESS = "https://connector.example.com/api/v1/dsp"
TEST_COUNTER_PARTY_ID = "BPNL000000000001"

# Sample shell descriptor response
SAMPLE_SHELL_DESCRIPTOR = {
    "submodelDescriptors": [
        {
            "identification": "submodel-abc",
            "semanticId": {
                "value": ["urn:samm:io.catenax.assemblypartrelationship:1.0.0#AssemblyPartRelationship"]
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

# Sample relationship data - valid hierarchy
VALID_RELATIONSHIPS = [
    # Format: (child_id, parent_id)
    {"childCatenaXId": "part-1", "parentCatenaXId": "part-2"},
    {"childCatenaXId": "part-2", "parentCatenaXId": "part-3"},
    {"childCatenaXId": "part-3", "parentCatenaXId": "part-4"},
]

# Sample relationship data - contains a cycle
CYCLIC_RELATIONSHIPS = [
    {"childCatenaXId": "part-1", "parentCatenaXId": "part-2"},
    {"childCatenaXId": "part-2", "parentCatenaXId": "part-3"},
    {"childCatenaXId": "part-3", "parentCatenaXId": "part-1"},  # Creates a cycle
]

# Sample relationship data - contains orphans
ORPHANED_RELATIONSHIPS = [
    {"childCatenaXId": "part-1", "parentCatenaXId": "part-2"},
    {"childCatenaXId": "part-3", "parentCatenaXId": "part-4"},  # Orphaned branch
]

# Sample relationship data - deep hierarchy
DEEP_HIERARCHY_RELATIONSHIPS = [
    {"childCatenaXId": "part-1", "parentCatenaXId": "part-2"},
    {"childCatenaXId": "part-2", "parentCatenaXId": "part-3"},
    {"childCatenaXId": "part-3", "parentCatenaXId": "part-4"},
    {"childCatenaXId": "part-4", "parentCatenaXId": "part-5"},
    {"childCatenaXId": "part-5", "parentCatenaXId": "part-6"},
    {"childCatenaXId": "part-6", "parentCatenaXId": "part-7"},
]


@pytest.fixture
def mock_make_request():
    """Fixture to mock the make_request function."""
    with patch('test_orchestrator.checks.traceability.graph_check.make_request', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_get_dtr_access():
    """Fixture to mock the get_dtr_access function."""
    with patch('test_orchestrator.checks.traceability.graph_check.get_dtr_access', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_networkx():
    """Fixture to mock networkx functions."""
    with patch('test_orchestrator.checks.traceability.graph_check.nx') as mock:
        yield mock


@pytest.mark.asyncio
async def test_run_success(mock_make_request, mock_get_dtr_access, mock_networkx):
    """
    Test successful graph check with valid relationship data (no cycles, orphans, or excessive depth).
    """
    # Configure mocks for successful path
    mock_make_request.side_effect = [
        SAMPLE_SHELL_DESCRIPTOR,  # Shell descriptor response
        VALID_RELATIONSHIPS       # Submodel payload with relationship data
    ]
    
    mock_get_dtr_access.return_value = (
        "https://endpoint.example.com", 
        "Bearer token123",
        {"status": "ok"}
    )
    
    # Configure networkx to detect no cycles
    mock_graph = MagicMock()
    mock_networkx.DiGraph.return_value = mock_graph
    mock_networkx.simple_cycles.return_value = []
    
    # Set up graph to have nodes with appropriate in/out degrees for orphan check
    nodes = ["part-1", "part-2", "part-3", "part-4"]
    mock_graph.nodes.return_value = nodes
    mock_graph.in_degree.side_effect = lambda node: 0 if node == "part-1" else 1
    mock_graph.out_degree.side_effect = lambda node: 1 if node != "part-4" else 0
    mock_graph.successors.side_effect = lambda node: [] if node == "part-4" else [nodes[nodes.index(node) + 1]]
    
    # Input parameters
    input_data = {
        'shell_ids': [TEST_SHELL_ID],
        'dataplane_url': TEST_DATAPLANE_URL,
        'counter_party_id': TEST_COUNTER_PARTY_ID,
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS,
        'max_depth_threshold': 10
    }
    
    # Run the function
    result = await run(input_data)
    
    # Verify result
    assert result["step"] == "graph_check"
    assert result["status"] == "pass"
    assert result["problems"] == []
    assert result["impact_set"] == []
    
    # Verify mock calls
    mock_make_request.assert_called()
    mock_get_dtr_access.assert_called_once()
    mock_networkx.simple_cycles.assert_called_once()


@pytest.mark.asyncio
async def test_run_with_cycles(mock_make_request, mock_get_dtr_access, mock_networkx):
    """
    Test graph check when cyclic relationships are detected.
    """
    # Configure mocks
    mock_make_request.side_effect = [
        SAMPLE_SHELL_DESCRIPTOR,  # Shell descriptor response
        CYCLIC_RELATIONSHIPS      # Submodel payload with cyclic relationship data
    ]
    
    mock_get_dtr_access.return_value = (
        "https://endpoint.example.com", 
        "Bearer token123",
        {"status": "ok"}
    )
    
    # Configure networkx to detect cycles
    mock_graph = MagicMock()
    mock_networkx.DiGraph.return_value = mock_graph
    cycle = [["part-1", "part-2", "part-3"]]
    mock_networkx.simple_cycles.return_value = cycle
    
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
    assert result["step"] == "graph_check"
    assert result["status"] == "fail"
    assert len(result["problems"]) == 1
    assert result["problems"][0]["type"] == "cycle"
    assert TEST_SHELL_ID in result["problems"][0]["shellIds"]
    assert "cycles" in result["problems"][0]["details"]
    assert TEST_SHELL_ID in result["impact_set"]
    
    # Verify mock calls
    mock_networkx.simple_cycles.assert_called_once()


@pytest.mark.asyncio
async def test_run_with_orphans(mock_make_request, mock_get_dtr_access, mock_networkx):
    """
    Test graph check when orphaned nodes are detected.
    """
    # Configure mocks
    mock_make_request.side_effect = [
        SAMPLE_SHELL_DESCRIPTOR,   # Shell descriptor response
        ORPHANED_RELATIONSHIPS     # Submodel payload with orphaned relationship data
    ]
    
    mock_get_dtr_access.return_value = (
        "https://endpoint.example.com", 
        "Bearer token123",
        {"status": "ok"}
    )
    
    # Configure networkx
    mock_graph = MagicMock()
    mock_networkx.DiGraph.return_value = mock_graph
    mock_networkx.simple_cycles.return_value = []  # No cycles
    
    # Set up graph to have nodes with appropriate in/out degrees for orphan check
    nodes = ["part-1", "part-2", "part-3", "part-4"]
    mock_graph.nodes.return_value = nodes
    
    # Configure part-3 as an orphan (has outgoing edge but no incoming edge)
    mock_graph.in_degree.side_effect = lambda node: 0 if node in ["part-1", "part-3"] else 1
    mock_graph.out_degree.side_effect = lambda node: 1 if node not in ["part-2", "part-4"] else 0
    
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
    assert result["step"] == "graph_check"
    assert result["status"] == "fail"
    assert len(result["problems"]) == 1
    assert result["problems"][0]["type"] == "orphan"
    assert TEST_SHELL_ID in result["problems"][0]["shellIds"]
    assert "orphaned_nodes" in result["problems"][0]["details"]
    assert TEST_SHELL_ID in result["impact_set"]


@pytest.mark.asyncio
async def test_run_exceeding_max_depth(mock_make_request, mock_get_dtr_access, mock_networkx):
    """
    Test graph check when maximum depth exceeds threshold.
    """
    # Configure mocks
    mock_make_request.side_effect = [
        SAMPLE_SHELL_DESCRIPTOR,      # Shell descriptor response
        DEEP_HIERARCHY_RELATIONSHIPS  # Submodel payload with deep hierarchy
    ]
    
    mock_get_dtr_access.return_value = (
        "https://endpoint.example.com", 
        "Bearer token123",
        {"status": "ok"}
    )
    
    # Configure networkx
    mock_graph = MagicMock()
    mock_networkx.DiGraph.return_value = mock_graph
    mock_networkx.simple_cycles.return_value = []  # No cycles
    
    # Set up graph for depth calculation
    nodes = [f"part-{i}" for i in range(1, 8)]
    mock_graph.nodes.return_value = nodes
    
    # No orphans
    mock_graph.in_degree.side_effect = lambda node: 0 if node == "part-1" else 1
    mock_graph.out_degree.side_effect = lambda node: 1 if node != "part-7" else 0
    
    # Set up successors for depth calculation
    def mock_successors(node):
        if node == "part-7":
            return []
        idx = nodes.index(node)
        return [nodes[idx + 1]]
    
    mock_graph.successors.side_effect = mock_successors
    
    # Input parameters with low max_depth_threshold
    input_data = {
        'shell_ids': [TEST_SHELL_ID],
        'dataplane_url': TEST_DATAPLANE_URL,
        'counter_party_id': TEST_COUNTER_PARTY_ID,
        'counter_party_address': TEST_COUNTER_PARTY_ADDRESS,
        'max_depth_threshold': 3  # Set low to trigger depth issue
    }
    
    # Run the function
    result = await run(input_data)
    
    # Verify result
    assert result["step"] == "graph_check"
    assert result["status"] == "fail"
    assert any(problem["type"] == "max_depth" for problem in result["problems"])
    for problem in result["problems"]:
        if problem["type"] == "max_depth":
            assert problem["details"]["threshold"] == 3
            assert TEST_SHELL_ID in problem["shellIds"]
    assert TEST_SHELL_ID in result["impact_set"]


@pytest.mark.asyncio
async def test_run_missing_shell_ids():
    """
    Test graph check with missing shell IDs.
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
    assert result["step"] == "graph_check"
    assert result["status"] == "fail"
    assert len(result["problems"]) == 1
    assert result["problems"][0]["type"] == "input_error"
    assert "No shell IDs provided" in result["problems"][0]["details"]
    assert result["impact_set"] == []


@pytest.mark.asyncio
async def test_run_graph_check_wrapper():
    """
    Test the run_graph_check wrapper function calls run with correct parameters.
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
    with patch('test_orchestrator.checks.traceability.graph_check.run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"step": "graph_check", "status": "pass"}
        
        # Call the wrapper function
        result = await run_graph_check(config, logger)
        
        # Verify the run function was called with correct parameters
        mock_run.assert_awaited_once_with(config)
        assert result == {"step": "graph_check", "status": "pass"}