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
Provides FastAPI endpoints for validating notifications.

This module defines an API endpoint built with FastAPI to validate Catena-X notification payloads
against the required format and field rules. The endpoint checks for required fields, validates
UUIDs, timestamps, and semantic identifiers used in the header and content sections of the message.

The primary goal is to ensure that the notification structure and key values conform to the
expected messaging standards.

Endpoints:
- POST /notification-validation/: Validates a given notification payload against its expected format.
"""

import logging
from typing import Dict
from fastapi import APIRouter, Depends

from test_orchestrator.auth import verify_auth
from test_orchestrator.utils.special_characteristics import validate_notification_payload

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
