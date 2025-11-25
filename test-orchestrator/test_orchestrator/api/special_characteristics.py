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
Provides FastAPI endpoints for validating Catena-X notification payloads,
Digital Twin availability, and submodel schema compliance.

This module defines API endpoints used to verify notification structures,
validate Digital Twin presence in a partner’s Digital Twin Registry (DTR), and
perform schema validation of referenced submodels. These endpoints support the
test orchestration workflows required to ensure interoperability of event-driven
processes within the Catena-X ecosystem.

The primary goal is to confirm that participants correctly implement
notification formats, DTR integration, DT retrieval, and submodel provisioning
according to Catena-X specifications. This ensures that event exchanges and
Digital Twin interactions function reliably across the network.

Endpoints:
- POST /notification-validation/: Validates the structure and content of a notification payload.
- POST /data-transfer/: Validates the payload and verifies Digital Twin availability in the partner DTR.
- POST /schema-validation/: Validates the payload and checks partner submodels against semantic schemas.
"""

import logging
from typing import Dict
from fastapi import APIRouter, Depends

from test_orchestrator.auth import verify_auth
from test_orchestrator.base_utils import submodel_validation
from test_orchestrator.utils.special_characteristics import (
    process_notification_and_retrieve_dtr,
    validate_notification_payload
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post('/notification-validation/',
             response_model=Dict,
             dependencies=[Depends(verify_auth)])
async def notification_validation(payload: Dict,
                                  timeout: int = 80):
    """
    Endpoint to validate a notification payload.

    Steps performed:
    1. Validate the structure and fields of the incoming notification.
    2. Ensure all required header and content fields are present.
    3. Verify field formats such as UUIDs, BPNs, and timestamps.

    - :payload (Dict): Notification payload containing header and content.
    - :timeout (int, optional): Timeout for validation-related operations. Defaults to 80.

    return: a json object containing `"status": "ok"` if validation succeeds.
    """

    return validate_notification_payload(payload)


@router.post('/data-transfer/',
             response_model=Dict,
             dependencies=[Depends(verify_auth)])
async def data_transfer(payload: Dict,
                        counter_party_address: str,
                        counter_party_id: str,
                        timeout: int = 80,
                        max_events: int = 2):
    """
    Endpoint to validate a notification payload and verify Digital Twin presence
    in the partner's Digital Twin Registry (DTR).

    Steps performed:
    1. Validate the incoming notification payload structure and event fields.
    2. Resolve the partner's DTR endpoint and obtain access credentials.
    3. For each event, retrieve the corresponding Digital Twin shell descriptor
    via the DT Pull Service.
    4. Raise an error if any Digital Twin cannot be retrieved.
    5. Return a confirmation message if all lookups succeed.

    - :payload (Dict): Notification payload containing header, content, and events.
    - :param counter_party_address: Address of the partner's DSP endpoint
                                    (must end with api/v1/dsp for DSP version 2024-01).
    - :param counter_party_id: Identifier of the test subject operating the connector.
    - :timeout (int, optional): Timeout for DTR and DT Pull Service requests. Defaults to 80.
    - :max_events (int, optional): Maximum allowed number of events. Defaults to 2.

    return: a json with a success message if Digital Twin resolution succeeds.
    """

    validate_notification_payload(payload)

    await process_notification_and_retrieve_dtr(payload=payload,
                                                counter_party_address=counter_party_address,
                                                counter_party_id=counter_party_id,
                                                timeout=timeout,
                                                max_events=max_events)

    return {'message': 'DT linkage & data transfer test is completed succesfully.'}


@router.post('/schema-validation/',
             response_model=Dict,
             dependencies=[Depends(verify_auth)])
async def schema_validation(payload: Dict,
                            counter_party_address: str,
                            counter_party_id: str,
                            timeout: int = 80,
                            max_events: int = 2):
    """
    Endpoint to validate a notification payload against partner schemas.

    Steps performed:
    1. Validate the incoming notification payload structure.
    2. Retrieve Digital Twin Registry (DTR) shell descriptors for the provided events
       using the partner's address and ID.
    3. For each shell descriptor, perform submodel schema validation to ensure
       compliance with Catena-X standards.
    4. Return a simple success message if all validations pass.

     - :payload (Dict): Notification payload containing header and content.
     - :param counter_party_address: Address of the dsp endpoint of a connector
                                     (ends on api/v1/dsp for DSP version 2024-01).
     - :param counter_party_id: The identifier of the test subject that operates the connector.
     - :timeout (int, optional): Timeout for external requests. Defaults to 80.

    return: a json with a success message if validation succeeds.
    """

    validate_notification_payload(payload)

    shell_descriptors = await process_notification_and_retrieve_dtr(payload=payload,
                                                                    counter_party_address=counter_party_address,
                                                                    counter_party_id=counter_party_id,
                                                                    timeout=timeout,
                                                                    max_events=max_events)
    semantic_ids = [sub["submodelSemanticId"] for sub in payload['content']['listOfEvents']]
    submodel_validations = []

    for semantic_id, shell_descriptor in zip(semantic_ids, shell_descriptors):
        submodel_validations.append(await submodel_validation(counter_party_id, shell_descriptor, semantic_id))

    return {'message': 'Special Characteristics validation is completed.',
            'submodel_validation_message': submodel_validations}
