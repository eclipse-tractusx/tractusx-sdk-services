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
Provides FastAPI endpoints for verifying Digital Twin availability and
submodel schema compliance.

This module defines API endpoints used to validate Digital Twin presence in a
partner's Digital Twin Registry (DTR), and perform schema validation of
referenced submodels. These endpoints support the test orchestration workflows
required to ensure interoperability within the Catena-X ecosystem.

The primary goal is to confirm that participants correctly implement DTR
integration, DT retrieval, and submodel provisioning according to Catena-X
specifications.

Endpoints:
- POST /data-transfer/: Verifies Digital Twin availability in the partner DTR.
- POST /schema-validation/: Checks partner submodels against semantic schemas.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends

from test_orchestrator.auth import verify_auth
from test_orchestrator.base_utils import submodel_validation
from test_orchestrator.utils.submodel_schema_validation import (
    process_and_retrieve_dtr,
)
from test_orchestrator.errors import HTTPError

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post('/check',
             response_model=Dict,
             dependencies=[Depends(verify_auth)])
async def submodel_schema_validation(
    counter_party_address: str,
    counter_party_id: str,
    asset_id: str,
    submodel_semantic_id: str,
    timeout: int = 80,
):
    """
    Endpoint to validate partner submodels against semantic schemas.

    Provides step-based feedback for each validation stage.
    """
    result: dict[str, Any] = {
        "status": "success",
        "message": "Submodel validation completed",
        "steps": []
    }

    def add_step(name: str, status: str, message: str | None = None, details: dict | None = None):
        step: dict[str, Any] = {"step": name, "status": status}
        if message is not None:
            step["message"] = message
        if details is not None:
            step["details"] = details
        result["steps"].append(step)
        if status == "failed":
            result["status"] = "failed"

    # Step 1: Retrieve DTR shell descriptors
    try:
        add_step("retrieve_shell_descriptors", "info", "Fetching shell descriptors from partner DTR")
        shell_descriptor, policy_validation = await process_and_retrieve_dtr(
            asset_id=asset_id,
            counter_party_address=counter_party_address,
            counter_party_id=counter_party_id,
            timeout=timeout
        )
        add_step("retrieve_shell_descriptors", "success", "Shell descriptors retrieved successfully",
                 details={"policy_validation": policy_validation})
    except HTTPError as e:
        add_step("retrieve_shell_descriptors", "failed", str(e), getattr(e, "details", None))
        return result
    except Exception as e:
        add_step("retrieve_shell_descriptors", "failed", f"Unexpected error: {e}")
        return result

    # Step 2: Validate submodel descriptor
    try:
        add_step("validate_submodel_descriptor", "info", f"Validating submodel {submodel_semantic_id}")
        validation_result = await submodel_validation(
            counter_party_id=counter_party_id,
            shell_descriptors_spec=shell_descriptor,
            semantic_id=submodel_semantic_id
        )
        add_step("validate_submodel_descriptor", "success",
                 "Submodel validated successfully",
                 details={"validation_result": validation_result})
    except HTTPError as e:
        add_step("validate_submodel_descriptor", "failed", str(e), getattr(e, "details", None))
        return result
    except Exception as e:
        add_step("validate_submodel_descriptor", "failed", f"Unexpected error: {e}")
        return result

    result["message"] = "Submodel validation completed successfully"
    return result