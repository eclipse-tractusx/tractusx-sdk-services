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
Graph check module for traceability testing.

This module validates graph consistency for traceability data by building
a directed graph from AssemblyPartRelationship data and performing various
consistency checks.
"""

import logging
import networkx as nx
from typing import Dict, List, Any, Set, Tuple, Optional

from test_orchestrator import config
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.request_handler import make_request
from test_orchestrator.utils import get_dtr_access
from test_orchestrator.schemas import load_assembly_part_relationship_schema


async def run(input: Dict) -> Dict:
    """
    Builds a directed graph from AssemblyPartRelationship (child→parent) using networkx,
    checks for cycles, orphans, and maximum depth, and returns results.
    
    Args:
        input: Dictionary containing input parameters including:
            - shell_ids: List of shell IDs to process
            - dataplane_url: URL for the data plane
            - counter_party_id: Business Partner Number of the counterparty
            - counter_party_address: Address of the counterparty's EDC
            - max_depth_threshold: Optional maximum depth threshold (default: 10)
            
    Returns:
        dict: Results of the graph validation with format:
            {
                "step": "graph_check",
                "status": "pass" or "fail",
                "impact_set": [shellIds with issues],
                "problems": [
                    {
                        "type": "cycle" or "orphan" or "max_depth",
                        "shellIds": [affected shell IDs],
                        "details": {problem-specific details}
                    }
                ]
            }
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting graph consistency check")
    
    # Extract input parameters
    shell_ids = input.get('shell_ids', [])
    dataplane_url = input.get('dataplane_url')
    counter_party_id = input.get('counter_party_id')
    counter_party_address = input.get('counter_party_address')
    max_depth_threshold = input.get('max_depth_threshold', 10)
    
    if not shell_ids:
        logger.warning("No shell IDs provided for graph validation")
        return {
            "step": "graph_check",
            "status": "fail",
            "impact_set": [],
            "problems": [{
                "type": "input_error",
                "shellIds": [],
                "details": "No shell IDs provided for validation"
            }]
        }
    
    # Build directed graph
    graph = nx.DiGraph()
    relationship_data = []
    affected_shell_ids = set()
    
    # Collect all relationship data
    for shell_id in shell_ids:
        logger.info(f"Processing shell ID for relationships: {shell_id}")
        try:
            # Get shell descriptor
            shell_descriptors = await make_request(
                'GET',
                f'{config.DT_PULL_SERVICE_ADDRESS}/dtr/shell-descriptors/',
                params={'dataplane_url': dataplane_url, 'aas_id': shell_id},
                headers=get_dt_pull_service_headers(),
                timeout=60
            )
            
            # Process each submodel in the shell
            if isinstance(shell_descriptors, dict):
                submodel_descriptors = shell_descriptors.get('submodelDescriptors', [])
            elif isinstance(shell_descriptors, list) and len(shell_descriptors) > 0:
                submodel_descriptors = shell_descriptors[0].get('submodelDescriptors', [])
            else:
                submodel_descriptors = []
            
            # Find AssemblyPartRelationship submodel
            for submodel in submodel_descriptors:
                semantic_id = submodel.get('semanticId', {}).get('value', [''])[0] \
                    if isinstance(submodel.get('semanticId', {}).get('value', []), list) else ''
                
                # Check if this is an AssemblyPartRelationship submodel
                if 'assemblypartrelationship' in semantic_id.lower():
                    logger.info(f"Found AssemblyPartRelationship submodel for {shell_id}")
                    
                    # Extract endpoint information and get the data
                    endpoints = submodel.get('endpoints', [])
                    if not endpoints:
                        continue
                    
                    endpoint_info = endpoints[0].get('protocolInformation', {})
                    href = endpoint_info.get('href', '')
                    
                    if not href:
                        continue
                    
                    # Get data from the submodel
                    try:
                        # Extract parameters from the subprotocolBody if available
                        subprotocol_body = endpoint_info.get('subprotocolBody', '')
                        endpoint = None
                        authorization = None
                        
                        if subprotocol_body:
                            parts = subprotocol_body.split(';')
                            for part in parts:
                                if '=' in part:
                                    key, value = part.split('=', 1)
                                    if key == 'asset':
                                        asset_id = value
                                        logger.info(f"Extracted asset ID: {asset_id}")
                                        
                                        # Get data access
                                        endpoint, authorization, _ = await get_dtr_access(
                                            counter_party_address=counter_party_address,
                                            counter_party_id=counter_party_id,
                                            operand_left="https://w3id.org/edc/v0.0.1/ns/id",
                                            operand_right=asset_id,
                                            timeout=60
                                        )
                                        break
                        
                        # Fetch the relationship data
                        if endpoint:
                            headers = {"Authorization": authorization} if authorization else {}
                            relations = await make_request(
                                'GET', 
                                endpoint,
                                headers=headers, 
                                timeout=60
                            )
                            
                            if relations:
                                # If it's a single relation or a list of relations, handle accordingly
                                if isinstance(relations, dict):
                                    relationship_data.append((shell_id, relations))
                                elif isinstance(relations, list):
                                    for relation in relations:
                                        relationship_data.append((shell_id, relation))
                        
                    except Exception as e:
                        logger.error(f"Error fetching relationship data: {str(e)}")
                        affected_shell_ids.add(shell_id)
            
        except Exception as e:
            logger.error(f"Error processing shell ID {shell_id}: {str(e)}")
            affected_shell_ids.add(shell_id)
    
    # Build the graph from relationship data
    for shell_id, relation in relationship_data:
        child_id = relation.get('childCatenaXId')
        parent_id = relation.get('parentCatenaXId')
        
        if child_id and parent_id:
            graph.add_edge(child_id, parent_id)
            logger.info(f"Added edge from {child_id} to {parent_id}")
    
    # Validate graph
    problems = []
    
    # Check for cycles
    try:
        cycles = list(nx.simple_cycles(graph))
        if cycles:
            logger.warning(f"Found {len(cycles)} cycles in the graph")
            affected_shell_ids.update(shell_ids)  # All shell IDs are potentially affected by cycles
            problems.append({
                "type": "cycle",
                "shellIds": list(shell_ids),
                "details": {
                    "cycles": [{"nodes": cycle} for cycle in cycles]
                }
            })
    except Exception as e:
        logger.error(f"Error checking for cycles: {str(e)}")
        problems.append({
            "type": "error",
            "shellIds": list(shell_ids),
            "details": f"Error checking for cycles: {str(e)}"
        })
    
    # Check for orphans (nodes with no incoming edges - except root nodes)
    orphans = []
    for node in graph.nodes():
        # An orphan is a node that has no incoming edges but has outgoing edges
        # (It's not a root node or an isolated node)
        if graph.out_degree(node) > 0 and graph.in_degree(node) == 0:
            orphans.append(node)
    
    if orphans:
        logger.warning(f"Found {len(orphans)} orphaned nodes")
        # Find which shell IDs contain these orphans
        affected_shell_ids_for_orphans = set()
        for shell_id, relation in relationship_data:
            if relation.get('childCatenaXId') in orphans or relation.get('parentCatenaXId') in orphans:
                affected_shell_ids_for_orphans.add(shell_id)
        
        affected_shell_ids.update(affected_shell_ids_for_orphans)
        problems.append({
            "type": "orphan",
            "shellIds": list(affected_shell_ids_for_orphans),
            "details": {
                "orphaned_nodes": orphans
            }
        })
    
    # Calculate maximum depth of the graph
    max_depth = 0
    try:
        # Find all root nodes (nodes with no incoming edges)
        root_nodes = [node for node in graph.nodes() if graph.in_degree(node) == 0]
        
        # For each root node, find the longest path
        for root in root_nodes:
            # Use BFS to find the longest path from this root
            visited = {root: 0}
            queue = [root]
            
            while queue:
                node = queue.pop(0)
                current_depth = visited[node]
                
                for successor in graph.successors(node):
                    if successor not in visited or visited[successor] < current_depth + 1:
                        visited[successor] = current_depth + 1
                        queue.append(successor)
                        max_depth = max(max_depth, current_depth + 1)
        
        logger.info(f"Maximum graph depth: {max_depth}")
        
        # Check if max depth exceeds threshold
        if max_depth > max_depth_threshold:
            logger.warning(f"Maximum depth {max_depth} exceeds threshold {max_depth_threshold}")
            affected_shell_ids.update(shell_ids)  # All shell IDs are potentially affected by max depth
            problems.append({
                "type": "max_depth",
                "shellIds": list(shell_ids),
                "details": {
                    "current_depth": max_depth,
                    "threshold": max_depth_threshold
                }
            })
    except Exception as e:
        logger.error(f"Error calculating max depth: {str(e)}")
        problems.append({
            "type": "error",
            "shellIds": list(shell_ids),
            "details": f"Error calculating maximum depth: {str(e)}"
        })
    
    # Determine overall status
    status = "pass" if not problems else "fail"
    logger.info(f"Graph validation complete. Status: {status}")
    
    return {
        "step": "graph_check",
        "status": status,
        "impact_set": list(affected_shell_ids),
        "problems": problems
    }


async def run_graph_check(config, logger):
    """
    Run graph consistency checks for traceability data.
    
    Args:
        config: Configuration parameters for the check
        logger: Logger instance for logging validation results
        
    Returns:
        dict: Results of the graph validation
    """
    return await run(config)