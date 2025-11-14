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
from unittest.mock import AsyncMock, Mock, patch

from orchestrator.api.special_characteristics import router as notification_router
from orchestrator.errors import HTTPError
from orchestrator.utils.special_characteristics import (
    validate_notification_payload,
    is_notification_valid
)

# Create a FastAPI app instance and include the router for testing
app = FastAPI()
app.include_router(notification_router)


# Correctly handle the custom HTTPError to return a proper JSON response
@app.exception_handler(HTTPError)
async def http_error_handler(request, exc: HTTPError):
    """Error handler for tests"""
    return JSONResponse(status_code=exc.status_code, content=exc.json)

client = TestClient(app)

# Dummy data for testing
DUMMY_COUNTER_PARTY_ADDRESS = "https://connector.example.com/api/v1/dsp"
DUMMY_COUNTER_PARTY_ID = "BPNL000000000001"
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
    assert result["message"] == "Required fields are missing in the notification"
    assert any("Missing" in e for e in result["details"])


def test_validate_notification_payload_invalid_formats():
    """Validation should fail with proper error messages for wrong UUID, BPN, or datetime."""
    result = validate_notification_payload(DUMMY_INVALID_NOTIFICATION_PAYLOAD_WRONG_FORMATS)
    assert result["message"] == "Notification validation failed"
    error_text = " ".join(result["details"])
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


@pytest.fixture
def mock_get_dtr_access():
    """Mock get_dtr_access for DTR lookup."""
    with patch("orchestrator.api.data_transfer.get_dtr_access", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_make_request():
    """Mock make_request for DT Pull Service calls."""
    with patch("orchestrator.api.data_transfer.make_request", new_callable=AsyncMock) as mock:
        yield mock


def test_data_transfer_success(mock_get_dtr_access, mock_make_request):
    """
    Test /data-transfer/ endpoint when everything works correctly.
    """
    mock_get_dtr_access.return_value = (
        "https://dtr.partner.example.com",
        "dummy-token",
        True
    )

    mock_make_request.return_value = {
        "items": [{"idShort": "ExampleTwin"}]
    }

    response = client.post(
        "/data-transfer/",
        json=DUMMY_VALID_NOTIFICATION_PAYLOAD,
        params={
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["receiverBpn"] == DUMMY_VALID_NOTIFICATION_PAYLOAD["header"]["receiverBpn"]


def test_data_transfer_dtr_not_found(mock_get_dtr_access):
    """
    Test /data-transfer/ endpoint when DTR endpoint is missing.
    """
    mock_get_dtr_access.return_value = (None, None, None)

    response = client.post(
        "/data-transfer/",
        json=DUMMY_VALID_NOTIFICATION_PAYLOAD,
        params={
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
        },
    )

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "NOT_FOUND"
    assert "Partner DTR endpoint not found" in data["message"]


def test_data_transfer_invalid_payload():
    """
    Test /data-transfer/ when payload is invalid (missing fields).
    """
    response = client.post(
        "/data-transfer/",
        json=DUMMY_INVALID_NOTIFICATION_PAYLOAD_MISSING_FIELDS,
        params={
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
        },
    )

    assert response.status_code == 400 or response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "nok" in data["status"] or "validation" in data.get("message", "").lower()


def test_data_transfer_too_many_events(mock_get_dtr_access):
    """
    Test /data-transfer/ rejects payloads with too many listOfEvents.
    """
    mock_get_dtr_access.return_value = (
        "https://dtr.partner.example.com",
        "dummy-token",
        True
    )

    payload = DUMMY_VALID_NOTIFICATION_PAYLOAD.copy()
    payload["content"]["listOfEvents"] = [
        {
            "eventType": "CreateSubmodel",
            "catenaXId": f"urn:uuid:{i:032d}",
            "submodelSemanticId": "urn:bamm:io.catenax.serial_part:3.0.0#SerialPart",
        }
        for i in range(5)
    ]

    response = client.post(
        "/data-transfer/",
        json=payload,
        params={
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
        },
    )

    assert response.status_code == 422 or response.status_code == 200
    data = response.json()
    assert "more than" in data["message"] or "maximum" in str(data)