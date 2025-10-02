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
API endpoints for traceability test suites.

This module provides endpoints for executing traceability test suites
that validate Catena-X traceability functionality.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from test_orchestrator.auth import verify_auth
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.checks.traceability import (
    run_schema_check,
    run_graph_check,
    run_edc_smoke,
    run_recall_scenario
)

router = APIRouter()
logger = logging.getLogger(__name__)


class TraceabilityRunRequest(BaseModel):
    """Request model for traceability test suite execution."""
    providerBPN: str = Field(
        ..., description="Business Partner Number of the provider"
    )
    consumerBPN: str = Field(
        ..., description="Business Partner Number of the consumer"
    )
    partIds: List[str] = Field(
        ..., description="List of part IDs to test"
    )
    depth: int = Field(
        default=5, description="Maximum depth for graph traversal"
    )
    strictSemver: bool = Field(
        default=True, description="Whether to enforce strict semantic versioning"
    )


class StepResult(BaseModel):
    """Result model for individual test step."""
    status: str = Field(
        ..., description="Result status (pass or fail)"
    )
    details: Any = Field(
        None, description="Additional details about the test result"
    )


class TraceabilityRunResponse(BaseModel):
    """Response model for traceability test suite execution."""
    suite: str = Field(
        "traceability", description="Name of the test suite"
    )
    timestamp: str = Field(
        ..., description="ISO-8601 timestamp of the test execution"
    )
    status: str = Field(
        ..., description="Overall test suite status (pass or fail)"
    )
    steps: Dict[str, StepResult] = Field(
        ..., description="Results for each test step"
    )


@router.post('/suites/traceability/run',
             response_model=TraceabilityRunResponse,
             dependencies=[Depends(verify_auth)])
async def run_traceability_suite(request: TraceabilityRunRequest):
    """
    Execute the traceability test suite.
    
    This endpoint runs the complete traceability test suite, executing all
    four test steps in sequence: schema_check, graph_check, edc_smoke, and
    recall_scenario. The test steps validate different aspects of traceability
    functionality according to Catena-X standards.
    
    Args:
        request: The request parameters for the traceability test suite
        
    Returns:
        A JSON object containing the test results for each step and overall status
    """
    logger.info(f"Starting traceability test suite with parameters: {request.dict()}")
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    steps_results = {}
    overall_status = "pass"
    
    # Prepare common configuration for all test steps
    base_config = {
        "counter_party_address": f"https://edc.{request.providerBPN}.catena-x.net/api/v1/dsp",
        "counter_party_id": request.providerBPN,
        "shell_ids": request.partIds,
        "dataplane_url": f"https://edc.{request.providerBPN}.catena-x.net/api/v1/dsp",
        "max_depth_threshold": request.depth
    }
    
    # Step 1: Schema Check
    try:
        logger.info("Running schema_check step")
        schema_result = await run_schema_check(base_config, logger)
        steps_results["schema_check"] = StepResult(
            status=schema_result.get("status", "fail"),
            details=schema_result.get("details", [])
        )
        if schema_result.get("status") == "fail":
            overall_status = "fail"
    except Exception as e:
        logger.error(f"Error in schema_check step: {str(e)}")
        steps_results["schema_check"] = StepResult(
            status="fail",
            details={"error": str(e)}
        )
        overall_status = "fail"
    
    # Step 2: Graph Check
    try:
        logger.info("Running graph_check step")
        graph_result = await run_graph_check(base_config, logger)
        steps_results["graph_check"] = StepResult(
            status=graph_result.get("status", "fail"),
            details={
                "problems": graph_result.get("problems", []),
                "impact_set": graph_result.get("impact_set", [])
            }
        )
        if graph_result.get("status") == "fail":
            overall_status = "fail"
    except Exception as e:
        logger.error(f"Error in graph_check step: {str(e)}")
        steps_results["graph_check"] = StepResult(
            status="fail",
            details={"error": str(e)}
        )
        overall_status = "fail"
    
    # Step 3: EDC Smoke Test
    try:
        logger.info("Running edc_smoke step")
        edc_config = {
            "counter_party_address": base_config["counter_party_address"],
            "counter_party_id": base_config["counter_party_id"]
        }
        edc_result = await run_edc_smoke(edc_config, logger)
        steps_results["edc_smoke"] = StepResult(
            status=edc_result.get("status", "fail"),
            details={
                "latency_ms": edc_result.get("latency_ms", 0),
                "endpoint": edc_result.get("endpoint", ""),
                "details": edc_result.get("details", "")
            }
        )
        if edc_result.get("status") == "fail":
            overall_status = "fail"
    except Exception as e:
        logger.error(f"Error in edc_smoke step: {str(e)}")
        steps_results["edc_smoke"] = StepResult(
            status="fail",
            details={"error": str(e)}
        )
        overall_status = "fail"
    
    # Step 4: Recall Scenario
    try:
        logger.info("Running recall_scenario step")
        recall_config = {
            **base_config,
            "faulty_part_id": request.partIds[0] if request.partIds else None
        }
        recall_result = await run_recall_scenario(recall_config, logger)
        steps_results["recall_scenario"] = StepResult(
            status=recall_result.get("status", "fail"),
            details=recall_result.get("affected", [])
        )
        if recall_result.get("status") == "fail":
            overall_status = "fail"
    except Exception as e:
        logger.error(f"Error in recall_scenario step: {str(e)}")
        steps_results["recall_scenario"] = StepResult(
            status="fail",
            details={"error": str(e)}
        )
        overall_status = "fail"
    
    # Prepare and return the final response
    response = TraceabilityRunResponse(
        timestamp=timestamp,
        status=overall_status,
        steps=steps_results
    )
    
    logger.info(f"Completed traceability test suite with status: {overall_status}")
    return response