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

"""Tests for certificate validation
"""

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
import pytest

from orchestrator.api.cert_validation import router as cert_validation_router
from orchestrator.errors import HTTPError, Error

# Create a FastAPI app instance and include the router for testing
app = FastAPI()
app.include_router(cert_validation_router)


# Correctly handle the custom HTTPError to return a proper JSON response
@app.exception_handler(HTTPError)
async def http_error_handler(request, exc: HTTPError):
    """Error handler for the tests
    """
    return JSONResponse(status_code=exc.status_code, content=exc.json)

client = TestClient(app)

# Dummy data for testing
DUMMY_COUNTER_PARTY_ADDRESS = "https://connector.example.com/api/v1/dsp"
DUMMY_COUNTER_PARTY_ID = "BPNL000000000001"
DUMMY_DATAPLANE_URL = "https://dataplane.example.com/data"
DUMMY_DATAPLANE_KEY = "dummy-auth-key"
DUMMY_CERTIFICATE_PAYLOAD = {
    "header": {
        "senderFeedbackUrl": DUMMY_COUNTER_PARTY_ADDRESS,
        "senderBpn": DUMMY_COUNTER_PARTY_ID,
        "receiverBpn": "BPNL000000000002"
    },
    "content": {
        "document": {
            "documentID": "doc123"
        }
    }
}
DUMMY_FEEDBACK_PAYLOAD = {
    "header": {
        "messageId": "msg123"
    },
    "content": {}
}


@pytest.fixture
def mock_get_ccmapi_access():
    """Fixture to mock get_ccmapi_access."""
    with patch('orchestrator.api.cert_validation.get_ccmapi_access', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_send_feedback():
    """Fixture to mock send_feedback."""
    with patch('orchestrator.api.cert_validation.send_feedback', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_validate_ccmapi_offer():
    """Fixture to mock validate_ccmapi_offer_setup."""
    with patch('orchestrator.api.cert_validation.validate_ccmapi_offer_setup', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_run_cert_checks():
    """Fixture to mock run_certificate_checks."""
    with patch('orchestrator.api.cert_validation.run_certificate_checks') as mock:
        yield mock


@pytest.fixture
def mock_read_asset_policy():
    """Fixture to mock read_asset_policy."""
    with patch('orchestrator.api.cert_validation.read_asset_policy', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_validate_policy():
    """Fixture to mock validate_policy."""
    with patch('orchestrator.api.cert_validation.validate_policy') as mock:
        yield mock


@pytest.fixture
def mock_run_feedback_check():
    """Fixture to mock run_feedback_check."""
    with patch('orchestrator.api.cert_validation.run_feedback_check') as mock:
        yield mock


# --- Tests for /feedbackmechanism-validation/ ---

def test_feedback_mechanism_validation_success(mock_get_ccmapi_access, mock_send_feedback):
    """
    Test feedback_mechanism_validation endpoint for a successful 'RECEIVED' message.
    """
    mock_get_ccmapi_access.return_value = (DUMMY_DATAPLANE_URL, DUMMY_DATAPLANE_KEY)
    mock_send_feedback.return_value = {}

    response = client.get(
        "/feedbackmechanism-validation/",
        params={
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "message_type": "RECEIVED"
        }
    )

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'message': 'RECEIVED feedback sent successfully'}
    mock_get_ccmapi_access.assert_awaited_once()
    mock_send_feedback.assert_awaited_once()
    assert 'errors' not in mock_send_feedback.call_args.kwargs or not mock_send_feedback.call_args.kwargs['errors']


def test_feedback_mechanism_validation_rejected_success(mock_get_ccmapi_access, mock_send_feedback):
    """
    Test feedback_mechanism_validation endpoint for a successful 'REJECTED' message.
    """
    mock_get_ccmapi_access.return_value = (DUMMY_DATAPLANE_URL, DUMMY_DATAPLANE_KEY)
    mock_send_feedback.return_value = {}

    response = client.get(
        "/feedbackmechanism-validation/",
        params={
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "message_type": "REJECTED"
        }
    )

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'message': 'REJECTED feedback sent successfully'}
    mock_get_ccmapi_access.assert_awaited_once()
    mock_send_feedback.assert_awaited_once()
    assert mock_send_feedback.call_args.kwargs['errors'] is not None
    assert len(mock_send_feedback.call_args.kwargs['errors']) > 0


def test_feedback_mechanism_validation_failure(mock_get_ccmapi_access):
    """
    Test feedback_mechanism_validation failure when get_ccmapi_access raises an error.
    """
    error = HTTPError(Error.CONNECTOR_UNAVAILABLE, "Connector not found", "Test details")
    mock_get_ccmapi_access.side_effect = error

    response = client.get(
        "/feedbackmechanism-validation/",
        params={
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
        }
    )

    assert response.status_code == error.status_code
    assert response.json() == error.json


# --- Tests for /cert-validation-test/ ---

def test_validate_certificate_success(mock_get_ccmapi_access, mock_send_feedback, mock_validate_ccmapi_offer,
                                      mock_run_cert_checks):
    """
    Test validate_certificate for a fully successful validation path.
    """
    mock_get_ccmapi_access.return_value = (DUMMY_DATAPLANE_URL, DUMMY_DATAPLANE_KEY)
    mock_validate_ccmapi_offer.return_value = {"status": "ok"}

    response = client.post("/cert-validation-test/", json=DUMMY_CERTIFICATE_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'message': 'Validation was successful'}

    mock_get_ccmapi_access.assert_awaited_once()
    mock_validate_ccmapi_offer.assert_awaited_once()
    mock_run_cert_checks.assert_called_once()

    assert mock_send_feedback.await_count == 2
    assert mock_send_feedback.await_args_list[0].args[1] == 'RECEIVED'
    assert mock_send_feedback.await_args_list[1].args[1] == 'ACCEPTED'


def test_validate_certificate_validation_fails(mock_get_ccmapi_access, mock_send_feedback, mock_validate_ccmapi_offer,
                                               mock_run_cert_checks):
    """
    Test validate_certificate when run_certificate_checks raises an HTTPError.
    """
    error = HTTPError(Error.SUBMODEL_VALIDATION_FAILED, "Validation failed", "Test details")
    mock_get_ccmapi_access.return_value = (DUMMY_DATAPLANE_URL, DUMMY_DATAPLANE_KEY)
    mock_run_cert_checks.side_effect = error
    mock_validate_ccmapi_offer.return_value = {"status": "ok"}

    response = client.post("/cert-validation-test/", json=DUMMY_CERTIFICATE_PAYLOAD)

    assert response.status_code == error.status_code
    assert response.json() == error.json

    assert mock_send_feedback.await_count == 2
    assert mock_send_feedback.await_args_list[0].args[1] == 'RECEIVED'
    assert mock_send_feedback.await_args_list[1].args[1] == 'REJECTED'
    assert mock_send_feedback.await_args_list[1].kwargs['errors'] == [error.json]


# --- Tests for /ccmapi-offer-test/ ---

def test_validate_ccmapi_offer_setup_success(mock_read_asset_policy, mock_validate_policy):
    """
    Test validate_ccmapi_offer_setup for a successful validation.
    """
    mock_read_asset_policy.return_value = ("asset-123", [{"policy_key": "policy_value"}])
    mock_validate_policy.return_value = True

    response = client.get("/ccmapi-offer-test/", params={
        "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
        "counter_party_id": DUMMY_COUNTER_PARTY_ID
    })

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'message': 'CCMAPI Offer is set up correctly'}


def test_validate_ccmapi_offer_asset_not_found(mock_read_asset_policy):
    """
    Test validate_ccmapi_offer_setup when the asset is not found.
    """
    mock_read_asset_policy.return_value = (None, None)

    response = client.get("/ccmapi-offer-test/", params={
        "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
        "counter_party_id": DUMMY_COUNTER_PARTY_ID
    })

    expected_error = HTTPError(
        Error.ASSET_NOT_FOUND,
        message="Please check asset/policy/contractdefinition configuration",
        details="The CCMAPI asset could not be found..."  # Simplified for test
    )

    assert response.status_code == expected_error.status_code
    assert response.json()['error'] == "ASSET_NOT_FOUND"
    assert response.json()['message'] is not None


def test_validate_ccmapi_offer_policy_fails(mock_read_asset_policy, mock_validate_policy):
    """
    Test validate_ccmapi_offer_setup when policy validation returns False.
    """
    mock_read_asset_policy.return_value = ("asset-123", [{"policy_key": "policy_value"}])
    mock_validate_policy.return_value = False

    response = client.get("/ccmapi-offer-test/", params={
        "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
        "counter_party_id": DUMMY_COUNTER_PARTY_ID
    })

    assert response.status_code == 200
    assert "warning" in response.json()
    assert response.json()["warning"] == "POLICY_VALIDATION_FAILED"


# --- Tests for /feedbackmessage-validation/ ---

def test_feedback_message_validation_success(mock_run_feedback_check):
    """
    Test feedback_message_validation for a successful validation.
    """
    response = client.post("/feedbackmessage-validation/", json=DUMMY_FEEDBACK_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {'status': 'ok',
                               'message': 'Validation successful: ' + \
                                          'The feedback payload conforms to the required standard.'}
    mock_run_feedback_check.assert_called_once()
    assert mock_run_feedback_check.call_args.kwargs['validation_schema'] == DUMMY_FEEDBACK_PAYLOAD


def test_feedback_message_validation_failure(mock_run_feedback_check):
    """
    Test feedback_message_validation when run_feedback_check raises an error.
    """
    error = HTTPError(Error.SUBMODEL_VALIDATION_FAILED, "Feedback validation failed", "Test details")
    mock_run_feedback_check.side_effect = error

    response = client.post("/feedbackmessage-validation/", json=DUMMY_FEEDBACK_PAYLOAD)

    assert response.status_code == error.status_code
    assert response.json() == error.json
