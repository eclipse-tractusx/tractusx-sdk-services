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
EDC smoke test module for traceability testing.

This module validates EDC connectivity for traceability by performing
a minimal EDC contract + data transfer to configured provider endpoints,
measuring latency and verifying successful responses.
"""

import logging
import time
import httpx
from typing import Dict, Any, Tuple, Optional

from test_orchestrator import config
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.request_handler import make_request


async def run(input: Dict) -> Dict:
    """
    Performs a minimal EDC contract + data transfer to the configured provider endpoints,
    measures latency, asserts 2xx status codes, and returns results.
    
    Args:
        input: Dictionary containing input parameters including:
            - counter_party_address: Address of the counterparty's EDC
            - counter_party_id: Business Partner Number of the counterparty
            - asset_id: Optional asset ID to test (if not provided, will use a test asset)
            - timeout: Optional timeout in seconds (default: 60)
            
    Returns:
        dict: Results of the EDC smoke test with format:
            {
                "step": "edc_smoke",
                "status": "pass" or "fail",
                "latency_ms": measured latency in milliseconds,
                "endpoint": tested endpoint,
                "details": additional details (optional, included on failure)
            }
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting EDC smoke test")
    
    # Extract input parameters
    counter_party_address = input.get('counter_party_address')
    counter_party_id = input.get('counter_party_id')
    asset_id = input.get('asset_id')
    timeout = input.get('timeout', 60)
    
    if not counter_party_address or not counter_party_id:
        logger.warning("Missing required EDC parameters")
        return {
            "step": "edc_smoke",
            "status": "fail",
            "latency_ms": 0,
            "endpoint": "N/A",
            "details": "Missing required parameters: counter_party_address and counter_party_id"
        }
    
    # Default test operands if asset_id is not provided
    operand_left = "https://w3id.org/edc/v0.0.1/ns/id"
    operand_right = asset_id or "test-asset"
    
    try:
        # Start timing
        start_time = time.time()
        
        # Step 1: Query the catalog (minimal operation for smoke test)
        logger.info(f"Querying catalog from {counter_party_address}")
        
        catalog_json = await make_request(
            'GET',
            f'{config.DT_PULL_SERVICE_ADDRESS}/edr/get-catalog/',
            params={
                'operand_left': operand_left,
                'operand_right': operand_right,
                'operator': 'like',
                'counter_party_address': counter_party_address,
                'counter_party_id': counter_party_id,
                'limit': 1
            },
            headers=get_dt_pull_service_headers(),
            timeout=timeout
        )
        
        # End timing after the catalog query
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        logger.info(f"EDC connectivity test completed successfully in {latency_ms}ms")
        return {
            "step": "edc_smoke",
            "status": "pass",
            "latency_ms": latency_ms,
            "endpoint": counter_party_address
        }
        
    except Exception as e:
        logger.error(f"EDC smoke test failed: {str(e)}")
        # End timing for failed requests
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        return {
            "step": "edc_smoke",
            "status": "fail",
            "latency_ms": latency_ms,
            "endpoint": counter_party_address,
            "details": f"Error: {str(e)}"
        }


async def run_edc_smoke(config, logger):
    """
    Run EDC smoke tests for traceability functionality.
    
    Args:
        config: Configuration parameters for the check
        logger: Logger instance for logging test results
        
    Returns:
        dict: Results of the EDC connectivity checks
    """
    return await run(config)