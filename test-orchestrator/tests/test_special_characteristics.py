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
"""Tests for Special Characteristics notification validation and Digital Twin validation
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from test_orchestrator.api.special_characteristics import router as notification_router
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.utils.special_characteristics import (
    get_partner_dtr,
    process_notification_and_retrieve_dtr,
    validate_events_in_dtr,
    validate_notification_payload,
    validate_payload,
)

# =============================================================================
# TEST DATA
# =============================================================================

DUMMY_COUNTER_PARTY_ADDRESS = "https://connector.example.com/api/v1/dsp"
DUMMY_COUNTER_PARTY_ID = "BPNL000000000001"

VALID_NOTIFICATION = {
    "header": {
        "messageId": "urn:uuid:05e5cc3a-bdce-c3eb-0e0b-ec8bda34debc",
        "context": "IndustryCore-DigitalTwinEvent-Create:3.0.0",
        "sentDateTime": "2007-08-31T16:47+00:00",
        "senderBpn": "BPNL111111111111",
        "receiverBpn": "BPNL222222222222",
        "expectedResponseBy": "2007-08-31T16:47+00:00",
        "relatedMessageId": "urn:uuid:b6e1daeb-b15c-e67b-2fe2-f31f84c53cdf",
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

INVALID_MISSING_FIELDS = {
    "header": {
        "senderBpn": "BPNL111111111111",
        "receiverBpn": "BPNL222222222222"
    },
    "content": {}
}

INVALID_FORMATS = {
    "header": {
        "messageId": "INVALID-ID",
        "context": "IndustryCore-DigitalTwinEvent-Update:3.0.0",
        "sentDateTime": "not-a-date",
        "senderBpn": "INVALIDBPN",
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

DUMMY_SHELL_DESCRIPTOR = {
    "id": "urn:uuid:d32d3b55-d222-41e9-8d19-554af53124dd",
    "idShort": "ExampleTwin",
    "submodelDescriptors": [
        {
            "id": "submodel-123",
            "semanticId": {
                "keys": [{"value": "urn:bamm:io.catenax.serial_part:3.0.0#SerialPart"}]
            }
        }
    ]
}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def app():
    """Create FastAPI app with notification router and overridden dependencies."""
    from test_orchestrator.auth import verify_auth

    app = FastAPI()

    # Override auth dependency
    async def mock_verify_auth():
        return True

    app.dependency_overrides[verify_auth] = mock_verify_auth
    app.include_router(notification_router)

    # Add HTTPError handler
    @app.exception_handler(HTTPError)
    async def http_error_handler(request, exc: HTTPError):
        return JSONResponse(status_code=exc.status_code, content=exc.json)

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# =============================================================================
# UNIT TESTS: validate_notification_payload
# =============================================================================

def test_validate_notification_payload_valid():
    """Should pass validation for valid notification."""
    result = validate_notification_payload(VALID_NOTIFICATION)
    assert result["status"] == "ok"
    assert "No errors found" in result["message"]


def test_validate_notification_payload_missing_sections():
    """Should raise error when header or content is missing."""
    with pytest.raises(HTTPError) as exc:
        validate_notification_payload({"header": {}})
    assert exc.value.error_code == Error.MISSING_REQUIRED_FIELD

    assert "Required fields are missing" in exc.value.message


def test_validate_notification_payload_missing_header_fields():
    """Should raise error when required header fields are missing."""
    with pytest.raises(HTTPError) as exc:
        validate_notification_payload(INVALID_MISSING_FIELDS)

    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED
    assert any("Missing header field" in e for e in exc.value.details)


def test_validate_notification_payload_invalid_uuid():
    """Should raise error for invalid UUID format."""
    with pytest.raises(HTTPError) as exc:
        validate_notification_payload(INVALID_FORMATS)
    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED
    assert any("Invalid UUID format" in e for e in exc.value.details)


def test_validate_notification_payload_invalid_bpn():
    """Should raise error for invalid BPN format."""
    with pytest.raises(HTTPError) as exc:
        validate_notification_payload(INVALID_FORMATS)
    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED
    assert any("Invalid BPN format" in e for e in exc.value.details)


def test_validate_notification_payload_invalid_datetime():
    """Should raise error for invalid datetime format."""
    with pytest.raises(HTTPError) as exc:
        validate_notification_payload(INVALID_FORMATS)
    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED
    assert any("Invalid datetime format" in e for e in exc.value.details)


def test_validate_notification_payload_missing_content_fields():
    """Should raise error when information or listOfEvents is missing."""
    payload = VALID_NOTIFICATION.copy()
    payload["content"] = {}

    with pytest.raises(HTTPError) as exc:
        validate_notification_payload(payload)
    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED
    assert any("Missing required content fields" in e for e in exc.value.details)


def test_validate_notification_payload_empty_list_of_events():
    """Should raise error when listOfEvents is empty."""
    payload = VALID_NOTIFICATION.copy()
    payload["content"]["listOfEvents"] = []

    with pytest.raises(HTTPError) as exc:
        validate_notification_payload(payload)
    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED
    assert any("non-empty array" in e for e in exc.value.details)


def test_validate_notification_payload_missing_event_fields():
    """Should raise error when event fields are missing."""
    payload = VALID_NOTIFICATION.copy()
    payload["content"]["listOfEvents"] = [{"eventType": "CreateSubmodel"}]

    with pytest.raises(HTTPError) as exc:
        validate_notification_payload(payload)
    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED
    assert any("Missing field" in e for e in exc.value.details)


# =============================================================================
# UNIT TESTS: validate_payload
# =============================================================================

@pytest.mark.asyncio
async def test_validate_payload_success():
    """Should extract receiver BPN and events successfully."""
    receiver_bpn, events = await validate_payload(VALID_NOTIFICATION, max_events=2)

    assert receiver_bpn == "BPNL222222222222"
    assert len(events) == 1

    assert isinstance(events, list)


@pytest.mark.asyncio
async def test_validate_payload_too_many_events():
    """Should raise error when event count exceeds maximum."""
    payload = VALID_NOTIFICATION.copy()
    payload["content"]["listOfEvents"] = [
        {
            "eventType": "CreateSubmodel",
            "catenaXId": f"urn:uuid:d32d3b55-d222-41e9-8d19-{i:012d}",
            "submodelSemanticId": "urn:bamm:io.catenax.serial_part:3.0.0#SerialPart"
        }
        for i in range(5)
    ]

    with pytest.raises(HTTPError) as exc:
        await validate_payload(payload, max_events=2)
    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED
    assert "more than 2 events" in exc.value.message


# =============================================================================
# UNIT TESTS: get_partner_dtr
# =============================================================================

@pytest.mark.asyncio
@patch('test_orchestrator.utils.special_characteristics.get_dataplane_access')
async def test_get_partner_dtr_success(mock_get_dataplane_access):
    """Should successfully retrieve partner DTR endpoint."""
    mock_get_dataplane_access.return_value = (
        "https://dtr.partner.example.com/shell-descriptors",
        "Bearer token-123",
        "Policy validation passed"
    )

    dtr_url, dtr_token, policy = await get_partner_dtr(
        DUMMY_COUNTER_PARTY_ADDRESS,
        DUMMY_COUNTER_PARTY_ID,
        timeout=80
    )

    assert dtr_url == "https://dtr.partner.example.com/shell-descriptors"
    assert dtr_token == "Bearer token-123"
    assert policy == "Policy validation passed"

    mock_get_dataplane_access.assert_awaited_once()


@pytest.mark.asyncio
@patch('test_orchestrator.utils.special_characteristics.get_dataplane_access')
async def test_get_partner_dtr_not_found(mock_get_dataplane_access):
    """Should raise error when DTR endpoint is not found."""
    mock_get_dataplane_access.return_value = (None, None, None)

    with pytest.raises(HTTPError) as exc:
        await get_partner_dtr(
            DUMMY_COUNTER_PARTY_ADDRESS,
            DUMMY_COUNTER_PARTY_ID,
            timeout=80
        )
    assert exc.value.error_code == Error.ASSET_NOT_FOUND
    assert "Partner DTR endpoint not found" in exc.value.message


# =============================================================================
# UNIT TESTS: validate_events_in_dtr
# =============================================================================

@pytest.mark.asyncio
@patch('test_orchestrator.utils.special_characteristics.make_request')
async def test_validate_events_in_dtr_success(mock_make_request):
    """Should successfully validate all events in DTR."""
    mock_make_request.return_value = DUMMY_SHELL_DESCRIPTOR

    events = VALID_NOTIFICATION["content"]["listOfEvents"]
    shell_descriptors = await validate_events_in_dtr(
        events,
        "https://dtr.partner.example.com/shell-descriptors",
        "Bearer token-123",
        timeout=80
    )

    assert len(shell_descriptors) == len(events)
    assert shell_descriptors[0] == DUMMY_SHELL_DESCRIPTOR
    assert mock_make_request.await_count == len(events)


@pytest.mark.asyncio
@patch('test_orchestrator.utils.special_characteristics.make_request')
async def test_validate_events_in_dtr_not_found(mock_make_request):
    """Should raise error when Digital Twin not found in DTR."""
    mock_make_request.return_value = {"errors": ["Not found"]}

    events = VALID_NOTIFICATION["content"]["listOfEvents"]

    with pytest.raises(HTTPError) as exc:
        await validate_events_in_dtr(
            events,
            "https://dtr.partner.example.com/shell-descriptors",
            "Bearer token-123",
            timeout=80
        )
    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED
    assert "could not be found in the DTR" in str(exc.value.details)


@pytest.mark.asyncio
@patch('test_orchestrator.utils.special_characteristics.make_request')
async def test_validate_events_in_dtr_request_failure(mock_make_request):
    """Should raise error when DTR request fails."""
    mock_make_request.side_effect = HTTPError(
        Error.CONNECTOR_UNAVAILABLE,
        "DTR request failed",
        "Connection timeout"
    )

    events = [VALID_NOTIFICATION["content"]["listOfEvents"][0]]

    with pytest.raises(HTTPError) as exc:
        await validate_events_in_dtr(
            events,
            "https://dtr.partner.example.com/shell-descriptors",
            "Bearer token-123",
            timeout=80
        )
    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED
    assert "Failed to fetch Digital Twin" in str(exc.value.details)


# =============================================================================
# UNIT TESTS: process_notification_and_retrieve_dtr
# =============================================================================

@pytest.mark.asyncio
@patch('test_orchestrator.utils.special_characteristics.validate_events_in_dtr')
@patch('test_orchestrator.utils.special_characteristics.get_partner_dtr')
@patch('test_orchestrator.utils.special_characteristics.validate_payload')
async def test_process_notification_success(mock_validate_payload, mock_get_dtr, mock_validate_events):
    """Should successfully process notification and retrieve DTR data."""
    mock_validate_payload.return_value = (
        "BPNL222222222222",
        VALID_NOTIFICATION["content"]["listOfEvents"]
    )
    mock_get_dtr.return_value = (
        "https://dtr.partner.example.com/shell-descriptors",
        "Bearer token-123",
        "Policy OK"
    )
    mock_validate_events.return_value = [DUMMY_SHELL_DESCRIPTOR]

    shell_descriptors, policy = await process_notification_and_retrieve_dtr(
        VALID_NOTIFICATION,
        DUMMY_COUNTER_PARTY_ADDRESS,
        DUMMY_COUNTER_PARTY_ID,
        timeout=80,
        max_events=2
    )

    assert len(shell_descriptors) == 1
    assert shell_descriptors[0] == DUMMY_SHELL_DESCRIPTOR
    assert policy == "Policy OK"


@pytest.mark.asyncio
async def test_process_notification_too_many_events():
    """Should raise error when notification has too many events."""
    payload = VALID_NOTIFICATION.copy()
    payload["content"]["listOfEvents"] = [
        {
            "eventType": "CreateSubmodel",
            "catenaXId": f"urn:uuid:d32d3b55-d222-41e9-8d19-{i:012d}",
            "submodelSemanticId": "urn:bamm:io.catenax.serial_part:3.0.0#SerialPart"
        }
        for i in range(5)
    ]

    with pytest.raises(HTTPError) as exc:
        await process_notification_and_retrieve_dtr(
            payload,
            DUMMY_COUNTER_PARTY_ADDRESS,
            DUMMY_COUNTER_PARTY_ID,
            timeout=80,
            max_events=2
        )
    assert exc.value.error_code == Error.NOTIFICATION_VALIDATION_FAILED


# =============================================================================
# API TESTS: /notification-validation/
# =============================================================================

def test_api_notification_validation_success(client):
    """Should return success for valid notification."""
    response = client.post(
        "/notification-validation/",
        json=VALID_NOTIFICATION
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_notification_validation_missing_fields(client):
    """Should return error for missing fields."""
    response = client.post(
        "/notification-validation/",
        json=INVALID_MISSING_FIELDS
    )


    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "NOTIFICATION_VALIDATION_FAILED"


def test_api_notification_validation_invalid_formats(client):
    """Should return error for invalid formats."""
    response = client.post(
        "/notification-validation/",
        json=INVALID_FORMATS
    )

    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "NOTIFICATION_VALIDATION_FAILED"


@pytest.fixture
def mock_process_notification():
    """Mock process_notification_and_retrieve_dtr."""
    with patch(
        "test_orchestrator.api.special_characteristics.process_notification_and_retrieve_dtr",
        new_callable=AsyncMock
    ) as mock:
        yield mock


# =============================================================================
# API TESTS: /schema-validation/
# =============================================================================

@pytest.fixture
def mock_submodel_validation():
    """Mock submodel_validation."""
    with patch(
        "test_orchestrator.api.special_characteristics.submodel_validation",
        new_callable=AsyncMock
    ) as mock:
        yield mock


def test_api_schema_validation_success(client, mock_process_notification, mock_submodel_validation):
    """Should return success when schema validation passes."""
    mock_process_notification.return_value = (
        [DUMMY_SHELL_DESCRIPTOR],
        "Policy validation passed"
    )
    mock_submodel_validation.return_value = "Submodel validation successful"

    response = client.post(
        "/schema-validation/",
        json=VALID_NOTIFICATION,
        params={
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "counter_party_id": DUMMY_COUNTER_PARTY_ID
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "Special Characteristics validation is completed" in data["message"]
    assert data["policy_validation_message"] == "Policy validation passed"
    assert len(data["submodel_validation_message"]) == 1


def test_api_schema_validation_invalid_payload(client):
    """Should return error for invalid payload."""
    response = client.post(
        "/schema-validation/",
        json=INVALID_MISSING_FIELDS,
        params={
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "counter_party_id": DUMMY_COUNTER_PARTY_ID
        }
    )

    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "NOTIFICATION_VALIDATION_FAILED"