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

"""Tests for notification validation
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
import pytest

from orchestrator.api.special_characteristics import router as notification_router
from orchestrator.errors import HTTPError
from orchestrator.utils.special_characteristics import (
    validate_notification_payload,
    is_notification_valid
)

# --------------------------------------------------------------------
# Setup FastAPI app and client
# --------------------------------------------------------------------

app = FastAPI()
app.include_router(notification_router)


@app.exception_handler(HTTPError)
async def http_error_handler(request, exc: HTTPError):
    """Error handler for tests"""
    return JSONResponse(status_code=exc.status_code, content=exc.json)


client = TestClient(app)

# Dummy payloads for testing
DUMMY_VALID_NOTIFICATION_PAYLOAD = {
    "header": {
        "messageId": "05e5CC3A-BDce-c3EB-0E0b-Ec8BDA34DeBc",
        "context": "IndustryCore-DigitalTwinEvent-Create:3.0.0",
        "sentDateTime": "2007-08-31T16:47+00:00",
        "senderBpn": "BPNLAVrVv2kE9cOD",
        "receiverBpn": "BPNLEzukvJyXgZZd",
        "expectedResponseBy": "2007-08-31T16:47+00:00",
        "relatedMessageId": "B6E1daeB-b15C-e67b-2Fe2-f31f84C53CDF",
        "version": "3.0.0"
    },
    "content": {
        "information": "List of events about the creation, update, or deletion of submodels of digital twins.",
        "listOfEvents": [
            {
                "eventType": "CreateSubmodel",
                "catenaXId": "urn:uuid:d32d3b55-d222-41e9-8d19-554af53124dd",
                "submodelSemanticId": "urn:bamm:io.catenax.serial_part:3.0.0#SerialPart"
            }
        ]
    }
}

DUMMY_INVALID_NOTIFICATION_PAYLOAD_MISSING_FIELDS = {
    "header": {
        "senderBpn": "BPNLAVrVv2kE9cOD",
        "receiverBpn": "BPNLEzukvJyXgZZd",
    },
    "content": {}
}

DUMMY_INVALID_NOTIFICATION_PAYLOAD_WRONG_FORMATS = {
    "header": {
        "messageId": "INVALID-ID",
        "context": "IndustryCore-DigitalTwinEvent-Update:3.0.0",
        "sentDateTime": "not-a-date",
        "senderBpn": "INVALIDBPN123",
        "receiverBpn": "BPNL---WRONG",
        "expectedResponseBy": "2025-11-06T16:00Z",
        "relatedMessageId": "12345",
        "version": "3.0.0"
    },
    "content": {
        "information": "invalid example",
        "listOfEvents": [
            {
                "eventType": "CreateSubmodel",
                "catenaXId": "not-a-uuid",
                "submodelSemanticId": "wrong:prefix:serial_part"
            }
        ]
    }
}

# Unit Tests: utils.special_characteristics
def test_validate_notification_payload_valid():
    """Validation function should return status ok for valid payload."""
    result = validate_notification_payload(DUMMY_VALID_NOTIFICATION_PAYLOAD)
    assert result["status"] == "ok"


def test_validate_notification_payload_missing_fields():
    """Validation should fail when required fields are missing."""
    result = validate_notification_payload(DUMMY_INVALID_NOTIFICATION_PAYLOAD_MISSING_FIELDS)
    assert result["status"] == "nok"
    assert any("Missing" in e for e in result["errors"])


def test_validate_notification_payload_invalid_formats():
    """Validation should fail with proper error messages for wrong UUID, BPN, or datetime."""
    result = validate_notification_payload(DUMMY_INVALID_NOTIFICATION_PAYLOAD_WRONG_FORMATS)
    assert result["status"] == "nok"
    error_text = " ".join(result["errors"])
    assert "Invalid UUID format" in error_text
    assert "Invalid BPN format" in error_text
    assert "Invalid datetime format" in error_text
    assert "Invalid semantic ID" in error_text


def test_is_notification_valid_true():
    """Helper should return True for valid payload."""
    assert is_notification_valid(DUMMY_VALID_NOTIFICATION_PAYLOAD) is True


def test_is_notification_valid_false():
    """Helper should return False for invalid payload."""
    assert is_notification_valid(DUMMY_INVALID_NOTIFICATION_PAYLOAD_WRONG_FORMATS) is False


# Integration Tests: API /notification-validation/
def test_notification_validation_api_success():
    """POST /notification-validation/ should return ok for valid payload."""
    response = client.post("/notification-validation/", json=DUMMY_VALID_NOTIFICATION_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_notification_validation_api_invalid_missing_fields():
    """POST /notification-validation/ should return nok for missing fields."""
    response = client.post("/notification-validation/", json=DUMMY_INVALID_NOTIFICATION_PAYLOAD_MISSING_FIELDS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "nok"
    assert len(data["errors"]) > 0


def test_notification_validation_api_invalid_formats():
    """POST /notification-validation/ should return nok for incorrect formats."""
    response = client.post("/notification-validation/", json=DUMMY_INVALID_NOTIFICATION_PAYLOAD_WRONG_FORMATS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "nok"
    assert any("Invalid" in e for e in data["errors"])
