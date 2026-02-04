
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
import re
from datetime import datetime
from typing import Dict, List

from test_orchestrator import config
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.request_handler import make_request
from test_orchestrator.utils import get_dataplane_access

logger = logging.getLogger(__name__)

def normalize_catena_x_id(catena_x_id: str) -> str:
    """
    Normalize Catena-X ID to ensure it has the urn:uuid: prefix.
    
    - :catena_x_id (str): The Catena-X ID which may or may not have the urn:uuid: prefix.
    
    return: Normalized Catena-X ID with urn:uuid: prefix.
    """
    if not catena_x_id:
        return None
    if not catena_x_id.startswith('urn:uuid:'):
        return f'urn:uuid:{catena_x_id}'
    return catena_x_id


def validate_notification_payload(payload: Dict):
    """
    Validate the structure, required fields, and formatting of a Catena-X
    notification payload.

    Steps performed:
    1. Ensure the presence of `header` and `content` sections.
    2. Validate mandatory header fields such as UUIDs, timestamps, and BPNs.
    3. Validate `listOfEvents` structure and required event fields.
    4. Accumulate and report all validation errors.

    - :payload (Dict): Raw notification payload provided by the calling service.

    return: a dict containing `{ "status": "ok" }` if validation succeeds,
            otherwise an HTTPError is raised.
    """

    errors: List[str] = []

    if 'header' not in payload or 'content' not in payload:
        errors.append("Missing required sections: 'header' and/or 'content'.")
        raise HTTPError(
            Error.MISSING_REQUIRED_FIELD,
            message='Required fields are missing in the notification',
            details=errors)

    header = payload.get('header', {})
    content = payload.get('content', {})

    required_header_fields = [
        'messageId', 'context', 'sentDateTime', 'senderBpn',
        'receiverBpn', 'expectedResponseBy', 'relatedMessageId', 'version'
    ]

    for field in required_header_fields:
        if field not in header:
            errors.append(f'Missing header field: {field}')

    uuid_pattern = re.compile(r'^(urn:uuid:)?[0-9a-fA-F-]{36}$')
    bpn_pattern = re.compile(r'^BPN[LSA][A-Z0-9]{10}[A-Z0-9]{2}$')
    context_pattern = re.compile(r'^IndustryCore-DigitalTwinEvent-Create:\d+\.\d+\.\d+$')

    for key in ['messageId', 'relatedMessageId']:
        value = header.get(key)

        if value and not uuid_pattern.match(value):
            errors.append(f'Invalid UUID format in header.{key}: {value}')

    context_value = header.get('context')
    if context_value and not context_pattern.match(context_value):
        errors.append(f'Invalid context format in header: {context_value} (expected format: IndustryCore-DigitalTwinEvent-Create:X.Y.Z)')

    for key in ['sentDateTime', 'expectedResponseBy']:
        value = header.get(key)

        try:
            if value:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            errors.append(f'Invalid datetime format in header.{key}: {value}')

    for key in ['senderBpn', 'receiverBpn']:
        value = header.get(key)

        if value and not bpn_pattern.match(value):
            errors.append(f'Invalid BPN format in header.{key}: {value} (expected e.g. BPNL000000000000)')

    if 'information' not in content or 'listOfEvents' not in content:
        errors.append("Missing required content fields: 'information' and/or 'listOfEvents'.")
    else:
        list_of_events = content.get('listOfEvents', [])

        if not isinstance(list_of_events, list) or not list_of_events:
            errors.append('listOfEvents must be a non-empty array.')
        else:
            for i, event in enumerate(list_of_events):
                for key in ['eventType', 'catenaXId', 'submodelSemanticId']:
                    if key not in event:
                        errors.append(f"Missing field '{key}' in listOfEvents[{i}]")

                normalized_id = normalize_catena_x_id(event.get('catenaXId'))
                event['catenaXId'] = normalized_id
                
                if normalized_id and not uuid_pattern.match(normalized_id):
                    errors.append(f'Invalid UUID format in listOfEvents[{i}].catenaXId: {normalized_id}')

    if errors:
        logger.error(f'Notification validation failed: {errors}')
        raise HTTPError(
            Error.NOTIFICATION_VALIDATION_FAILED,
            message='Notification validation failed',
            details=errors)

    return {'status': 'ok',
            'message': 'No errors found during validating the input json.'}


async def validate_payload(payload: Dict, max_events: int):
    """
    Extract and validate event data from the notification payload and enforce
    maximum allowed event count.

    Steps performed:
    1. Read receiver BPN from the notification header.
    2. Extract listOfEvents from the payload content.
    3. Validate that the number of events does not exceed the configured limit.

    - :payload (Dict): Notification payload with header and content fields.
    - :max_events (int): Maximum number of allowed events.

    return: receiver BPN and the list of events if validation succeeds.
    """

    header = payload['header']
    content = payload['content']
    receiver_bpn = header['receiverBpn']
    events = content.get('listOfEvents', [])

    if len(events) > max_events:
        raise HTTPError(
            Error.NOTIFICATION_VALIDATION_FAILED,
            message=f'Notification contains more than {max_events} events',
            details=[f'listOfEvents has {len(events)} items, maximum allowed is {max_events}']
        )

    return receiver_bpn, events


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

    dtr_url_shell, dtr_token, policy_validation = await get_dataplane_access(
        counter_party_address=counter_party_address,
        counter_party_id=counter_party_id,
        operand_left='http://purl.org/dc/terms/type',
        operand_right='%https://w3id.org/catenax/taxonomy#DigitalTwinRegistry%',
        policy_validation=False,
        timeout=timeout
    )

    if not dtr_url_shell:
        raise HTTPError(
            Error.ASSET_NOT_FOUND,
            message='Partner DTR endpoint not found',
            details='DT Pull Service did not return a DTR endpoint for the partner'
        )

    return dtr_url_shell, dtr_token, policy_validation


async def validate_events_in_dtr(events: list, dtr_url_shell: str, dtr_token: str, timeout: int):
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

    for event in events:
        aas_id = event.get('catenaXId')
        shell_descriptors_spec = None
        try:
            shell_descriptors_spec = await make_request(
                'GET',
                f'{config.DT_PULL_SERVICE_ADDRESS}/dtr/shell-descriptors/',
                params={'dataplane_url': dtr_url_shell, 'aas_id': aas_id, 'limit': 1},
                headers=get_dt_pull_service_headers(headers={'Authorization': dtr_token}),
                timeout=timeout
            )
            shell_descriptors.append(shell_descriptors_spec)
        except HTTPError as exc:
            errors.append(f'Failed to fetch Digital Twin for {aas_id}: {exc.message}')
        except Exception as exc:  # W: Catching too general exception Exception
            errors.append(f'Unexpected error for {aas_id}: {str(exc)}')

        if shell_descriptors_spec and 'errors' in shell_descriptors_spec:
            errors.append(f'The AAS ID {aas_id} could not be found in the DTR')

    if errors:
        raise HTTPError(
            Error.NOTIFICATION_VALIDATION_FAILED,
            message='One or more events failed DTR validation',
            details=errors
        )

    return shell_descriptors


async def process_notification_and_retrieve_dtr(
    payload: Dict,
    counter_party_address: str,
    counter_party_id: str,
    timeout: int,
    max_events: int = 2
):
    """
    Process the notification payload and retrieve corresponding Digital Twin
    shell descriptors from the partner's DTR.

    Steps performed:
    1. Validate the payload and ensure event count does not exceed the allowed limit.
    2. Resolve the partner’s DTR endpoint and obtain an access token.
    3. Retrieve shell descriptors for all Catena-X IDs listed in the notification.
    4. Return all retrieved shell descriptors.

    - :payload (Dict): Notification payload with metadata and event list.
    - :param counter_party_address: Partner connector DSP endpoint.
    - :param counter_party_id: Identifier of the test subject operating the connector.
    - :timeout (int): Timeout for external requests.
    - :max_events (int, optional): Maximum number of allowed events. Defaults to 2.

    return: list of shell descriptor objects retrieved from the partner DTR.
    """

    receiver_bpn, events = await validate_payload(payload, max_events)
    dtr_url_shell, dtr_token, policy_validation = \
        await get_partner_dtr(counter_party_address, counter_party_id, timeout)
    shell_descriptors = await validate_events_in_dtr(events, dtr_url_shell, dtr_token, timeout)

    return shell_descriptors, policy_validation
