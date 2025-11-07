
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

import logging
import re
from typing import Dict, List
from datetime import datetime

from test_orchestrator.errors import Error, HTTPError

logger = logging.getLogger(__name__)

def validate_notification_payload(payload: Dict):
    """
    Validate the structure and fields of a notification payload.
    Returns a dict with 'status' and optionally 'errors' or 'message'.
    """
    errors: List[str] = []

    if 'header' not in payload or 'content' not in payload:
        errors.append("Missing required sections: 'header' and/or 'content'.")
        raise HTTPError(
            Error.MISSING_REQUIRED_FIELD,
            message="Required fields are missing in the notification",
            details=errors)

    header = payload.get('header', {})
    content = payload.get('content', {})

    required_header_fields = [
        'messageId', 'context', 'sentDateTime', 'senderBpn',
        'receiverBpn', 'expectedResponseBy', 'relatedMessageId', 'version'
    ]
    for field in required_header_fields:
        if field not in header:
            errors.append(f"Missing header field: {field}")

    uuid_pattern = re.compile(r"^(urn:uuid:)?[0-9a-fA-F-]{36}$")
    bpn_pattern = re.compile(r"^BPN[LSA][A-Z0-9]{10}[A-Z0-9]{2}$")

    for key in ['messageId', 'relatedMessageId']:
        value = header.get(key)
        if value and not uuid_pattern.match(value):
            errors.append(f"Invalid UUID format in header.{key}: {value}")

    for key in ['sentDateTime', 'expectedResponseBy']:
        value = header.get(key)
        try:
            if value:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            errors.append(f"Invalid datetime format in header.{key}: {value}")

    for key in ['senderBpn', 'receiverBpn']:
        value = header.get(key)
        if value and not bpn_pattern.match(value):
            errors.append(f"Invalid BPN format in header.{key}: {value} (expected e.g. BPNL000000000000)")

    if 'information' not in content or 'listOfEvents' not in content:
        errors.append("Missing required content fields: 'information' and/or 'listOfEvents'.")
    else:
        list_of_events = content.get('listOfEvents', [])
        if not isinstance(list_of_events, list) or not list_of_events:
            errors.append("listOfEvents must be a non-empty array.")
        else:
            for i, event in enumerate(list_of_events):
                for key in ['eventType', 'catenaXId', 'submodelSemanticId']:
                    if key not in event:
                        errors.append(f"Missing field '{key}' in listOfEvents[{i}]")

                catena_id = event.get('catenaXId')
                if catena_id and not uuid_pattern.match(catena_id):
                    errors.append(f"Invalid UUID format in listOfEvents[{i}].catenaXId: {catena_id}")

                semantic_id = event.get('submodelSemanticId')
                if semantic_id and not semantic_id.startswith('urn:bamm:io.catenax.'):
                    errors.append(f"Invalid semantic ID in listOfEvents[{i}].submodelSemanticId: {semantic_id}")

    if errors:
        logger.error(f"Notification validation failed: {errors}")
        raise HTTPError(
            Error.NOTIFICATION_VALIDATION_FAILED,
            message='Notification validation failed',
            details=errors)

    return {'status': 'ok'}

def is_notification_valid(payload: Dict) -> bool:
    """
    Runs the notification validation and returns True if valid, False otherwise.

    • :param payload: The notification JSON object to be validated.
    • :return: Boolean indicating if the notification is valid.
    """
    try:
        result = validate_notification_payload(payload)
        return result.get("status") == "ok"
    except HTTPError:
        return False
