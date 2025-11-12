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
FastAPI router providing endpoints for notification validation and data transfer orchestration.

Endpoints
----------
1. **POST /notification-validation/**
   Validates the structure and content of a Catena-X notification payload.
   Returns `{ "status": "ok" }` on success or raises `HTTPError` if invalid.

2. **POST /data-transfer/**
   Validates the payload, resolves the partner EDC endpoint, queries the partner DTR
   to check for the presence of the Digital Twin (DT) matching the notification’s Catena-X ID.
   Returns DTR data if found or raises `HTTPError` otherwise.

Both endpoints are protected by authentication (`verify_auth`).
"""

import logging
from typing import Dict
from fastapi import APIRouter, Depends

from test_orchestrator.auth import verify_auth
from test_orchestrator.utils.special_characteristics import validate_notification_payload, process_notification_and_retrieve_dtr

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post('/notification-validation/',
             response_model=Dict,
             dependencies=[Depends(verify_auth)])
async def notification_validation(payload: Dict,
                                  timeout: int = 80):
    """
    Endpoint to validate a notification payload.
    """
    return validate_notification_payload(payload)

@router.post("/data-transfer/",
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def data_transfer(payload: Dict,
                        counter_party_address: str,
                        counter_party_id: str,
                        timeout: int = 80,
                        max_events: int = 2):
    """
    Orchestrates data transfer validation and Digital Twin verification.
    """
    return await process_notification_and_retrieve_dtr(payload=payload,
                                                       counter_party_address=counter_party_address,
                                                       counter_party_id=counter_party_id,
                                                       timeout=timeout,
                                                       max_events=max_events)