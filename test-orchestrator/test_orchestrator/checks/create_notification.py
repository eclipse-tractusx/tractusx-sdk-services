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

"""Helpers to create or update Quality Notifications via HTTP.

This module exposes two async functions which perform POST requests to the
provided endpoint using the shared request handler.

Both functions accept the same parameters and will place them into the JSON
payload that is sent to the server. The Authorization header is forwarded as-is
under the key "Authorization".
"""

from typing import Any, Dict

from test_orchestrator.logging.log_manager import LoggingManager
from test_orchestrator.request_handler import make_request_status_only

__all__ = [
    "qualitynotification_receive",
    "qualitynotification_update",
]
logger = LoggingManager.get_logger(__name__)


async def qualitynotification_receive(
        endpoint: str,
        authorization: str,
        notification_type: str,
        job_id: str,
        sender_bpn: str,
        receiver_bpn: str,
) -> dict:
    """Send a Quality Notification receive request.

    Parameters
    - endpoint: Target URL to POST the request to.
    - authorization: Value for the Authorization header (e.g., a bearer token).
    - notificationType: Notification type value to include in the payload.
    - jobId: Job identifier to include in the payload.
    - senderBpn: Sender BPN to include in the payload.
    - receiverBpn: Receiver BPN to include in the payload.

    Returns the parsed JSON response from the server.
    """
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json",
    }

    # Build payload to mirror scripts/notifications.http POST /qualitynotifications/receive
    # Map jobId -> header.notificationId; map notificationType -> header.classification.
    payload = {
        "header": {
            "notificationId": job_id,
            "senderBPN": sender_bpn,
            "senderAddress": "home",
            "recipientBPN": receiver_bpn,
            "classification": notification_type,
            "severity": "CRITICAL",
            "status": "SENT",
        },
        "content": {
            "information": "Automated test notification",
            "listOfAffectedItems": ["urn:uuid:6b2296cc-26c0-4f38-8a22-092338c36e22"],
        },
    }

    logger.info(f"Sending receive notification to {endpoint} with payload: {payload}")

    return await make_request_status_only("POST", endpoint, headers=headers, json=payload)


async def qualitynotification_update(
        endpoint: str,
        authorization: str,
        notification_type: str,
        job_id: str,
        sender_bpn: str,
        receiver_bpn: str,
) -> Dict[str, Any]:
    """Send a Quality Notification update request.

    Parameters are identical to qualitynotification_receive. The function will
    POST the given data to the provided endpoint.

    Returns the parsed JSON response from the server.
    """
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json",
    }

    payload = {
        "header": {
            "notificationId": job_id,
            "senderBPN": sender_bpn,
            "senderAddress": "home",
            "recipientBPN": receiver_bpn,
            "classification": notification_type,
            "severity": "CRITICAL",
            "status": "SENT",
        },
        "content": {
            "information": "Automated test notification",
            "listOfAffectedItems": ["urn:uuid:6b2296cc-26c0-4f38-8a22-092338c36e22"],
        },
    }

    logger.info(f"Sending update notification to {endpoint} with payload: {payload}")

    return await make_request_status_only("POST", endpoint, headers=headers, json=payload)
