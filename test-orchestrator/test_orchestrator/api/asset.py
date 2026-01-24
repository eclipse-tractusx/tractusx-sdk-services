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
Provides FastAPI endpoints for Digital Twin availability, and submodel schema compliance.

The primary goal is to confirm that participants correctly implement
DTR integration, DT retrieval, and submodel provisioning
according to Catena-X specifications. This ensures that event exchanges and
Digital Twin interactions function reliably across the network.

Endpoints:
- POST /schema-validation/: Validates the payload and checks partner submodels against semantic schemas.
"""

import logging
from typing import Dict
from fastapi import APIRouter, Depends

from test_orchestrator.auth import verify_auth
from test_orchestrator.utils import submodel_validation
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.utils.special_characteristics import (
    process_notification_and_retrieve_dtr
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post('/schema-validation/',
             response_model=Dict,
             dependencies=[Depends(verify_auth)])
async def schema_validation(payload: Dict,
                            counter_party_address: str,
                            counter_party_id: str,
                            timeout: int = 80,
                            max_events: int = 2):
    """
    Endpoint to validate an asset schema.

    Steps performed:
    1. Retrieve Digital Twin Registry (DTR) shell descriptors for the provided events
       using the partner's address and ID.
    2. For each shell descriptor, perform submodel schema validation to ensure
       compliance with Catena-X standards.
    3. Return a simple success message if all validations pass.

     - :payload (Dict): Notification payload containing header and content.
     - :param counter_party_address: Address of the dsp endpoint of a connector
                                     (ends on api/v1/dsp for DSP version 2024-01).
     - :param counter_party_id: The identifier of the test subject that operates the connector.
     - :timeout (int, optional): Timeout for external requests. Defaults to 80.

    return: a json with a success message if validation succeeds.
    """

    shell_descriptors, policy_validation = \
            await process_notification_and_retrieve_dtr(payload=payload,
                                                        counter_party_address=counter_party_address,
                                                        counter_party_id=counter_party_id,
                                                        timeout=timeout,
                                                        max_events=max_events)
    semantic_ids = [sub["submodelSemanticId"] for sub in payload['content']['listOfEvents']]
    submodel_validations = []

    for semantic_id, shell_descriptor in zip(semantic_ids, shell_descriptors):
        try:
            result = await submodel_validation(counter_party_id, shell_descriptor, semantic_id)
            submodel_validations.append(result)
        except HTTPError as e:
            if e.error_code == Error.SUBMODEL_DESCRIPTOR_NOT_FOUND:
                raise HTTPError(
                    Error.SUBMODEL_DESCRIPTOR_NOT_FOUND,
                    message=f"The submodel descriptor for semanticID {semantic_id} could not be found in the DTR.",
                    details="Make sure the submodel is registered accordingly and visible for the testbed BPNL."
                )

            raise

    return {'message': 'Asset validation is completed.',
            'submodel_validation_message': submodel_validations,
            'policy_validation_message': policy_validation}
