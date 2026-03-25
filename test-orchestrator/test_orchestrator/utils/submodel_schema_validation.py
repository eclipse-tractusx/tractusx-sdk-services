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
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
# *************************************************************

import logging
from typing import List

from test_orchestrator import config
from test_orchestrator.request_handler import make_request
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.utils import get_dtr_access

logger = logging.getLogger(__name__)


async def get_partner_dtr(counter_party_address: str, counter_party_id: str, timeout: int):
    """
    Resolve the partner's Digital Twin Registry (DTR) shell-descriptor endpoint
    and obtain an access token through the DT Pull Service.

    Steps performed:
    1. Request DTR access information from the DT Pull Service.
    2. Validate that the returned DTR endpoint is usable.
    3. Return both the shell-descriptor URL and the access token.

    - :param counter_party_address: DSP endpoint URL of the partner connector
                                    (must end with api/v1/dsp).
    - :param counter_party_id: Identifier of the partner system.
    - :timeout (int): Timeout for DT Pull Service requests.

    return: a tuple containing (dtr_url_shell, dtr_token).
    """

    dtr_url_shell, dtr_token, policy_validation = await get_dtr_access(
        counter_party_address=counter_party_address,
        counter_party_id=counter_party_id,
        operand_left='http://purl.org/dc/terms/type',
        operand_right='%https://w3id.org/catenax/taxonomy#DigitalTwinRegistry%',
        policy_validation=False,
        timeout=timeout
    )

    if not dtr_url_shell:
        raise HTTPError(
            Error.NOT_FOUND,
            message='Partner DTR endpoint not found',
            details='DT Pull Service did not return a DTR endpoint for the partner'
        )

    return dtr_url_shell, dtr_token, policy_validation


async def validate_events_in_dtr(asset_id: str, dtr_url_shell: str, dtr_token: str, timeout: int):
    """
    Validate that each event's Catena-X ID corresponds to an existing Digital Twin
    in the partner's Digital Twin Registry.

    Steps performed:
    1. For each event, extract the Catena-X ID.
    2. Query the DT Pull Service for a matching shell descriptor.
    3. Collect retrieval errors for any IDs that cannot be resolved.
    4. Return the list of shell-descriptor specifications if all queries succeed.

    - :events (List): List of event objects from the notification payload.
    - :dtr_url_shell (str): Shell descriptor endpoint of the partner’s DTR.
    - :dtr_token (str): Authorization token for accessing the partner's DTR.
    - :timeout (int): Timeout for Digital Twin lookup requests.

    return: list of shell descriptors for the provided events.
    """

    errors = []
    shell_descriptors = []

    try:
        shell_descriptors_spec = await make_request(
            'GET',
            f'{config.DT_PULL_SERVICE_ADDRESS}/dtr/shell-descriptors/',
            params={'dataplane_url': dtr_url_shell, 'aas_id': asset_id, 'limit': 1},
            headers=get_dt_pull_service_headers(headers={'Authorization': dtr_token}),
            timeout=timeout
        )
        shell_descriptors.append(shell_descriptors_spec)
    except HTTPError as exc:
        errors.append(f'Failed to fetch Digital Twin for {asset_id}: {exc.message}')
    except Exception as exc:  # W: Catching too general exception Exception
        errors.append(f'Unexpected error for {asset_id}: {str(exc)}')

    if 'errors' in shell_descriptors_spec:
        errors.append(f'The AAS ID {asset_id} could not be found in the DTR')

    if errors:
        raise HTTPError(
            Error.NOTIFICATION_VALIDATION_FAILED,
            message='One or more events failed DTR validation',
            details=errors
        )

    return shell_descriptors


async def process_and_retrieve_dtr(
    asset_id: str,
    # submodel_semantic_id: str,
    counter_party_address: str,
    counter_party_id: str,
    timeout: int,
):
    """
    Retrieve Digital Twin shell descriptors from the partner's DTR for the
    provided events.

    Steps performed:
    1. Ensure event count does not exceed the allowed limit.
    2. Resolve the partner's DTR endpoint and obtain an access token.
    3. Retrieve shell descriptors for all Catena-X IDs in the events.
    4. Return all retrieved shell descriptors.

    - :param events: List of events containing catenaXId.
    - :param counter_party_address: Partner connector DSP endpoint.
    - :param counter_party_id: Identifier of the test subject operating the connector.
    - :param timeout: Timeout for external requests.
    - :param max_events: Maximum number of allowed events. Defaults to 2.

    return: tuple of (shell_descriptors, policy_validation).
    """
    dtr_url_shell, dtr_token, policy_validation = \
        await get_partner_dtr(counter_party_address, counter_party_id, timeout)
    shell_descriptors = await validate_events_in_dtr(asset_id, dtr_url_shell, dtr_token, timeout)

    return shell_descriptors, policy_validation