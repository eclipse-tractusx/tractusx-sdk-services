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
"""Tests for Product Carbon Footprint validation functions
"""
import pytest
from unittest.mock import AsyncMock, patch
from test_orchestrator.utils.product_carbon_footprint import (
    validate_inputs,
    fetch_pcf_offer_via_dtr,
    send_pcf_responses,
    send_pcf_put_request,
    pcf_check,
    validate_pcf_update,
    delete_cache_entry
)
from test_orchestrator.errors import HTTPError, Error
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from test_orchestrator.api.product_carbon_footprint import router as pcf_router


# --- Tests for validate_inputs ---

def test_validate_inputs_missing_bpn():
    """Should raise error when edc_bpn is missing."""
    with pytest.raises(HTTPError) as exc:
        validate_inputs("", "PART123")
    assert exc.value.error_code == Error.MISSING_REQUIRED_FIELD
    assert "Missing required header: Edc-Bpn" in exc.value.message


def test_validate_inputs_invalid_bpn_format():
    """Should raise error when BPN format is invalid."""
    with pytest.raises(HTTPError) as exc:
        validate_inputs("INVALID_BPN", "PART123")
    assert exc.value.error_code == Error.REGEX_VALIDATION_FAILED
    assert "Invalid BPN" in exc.value.message


def test_validate_inputs_invalid_part_id_chars():
    """Should raise error when manufacturer_part_id contains invalid characters."""
    with pytest.raises(HTTPError) as exc:
        validate_inputs("BPNL000000000000", "PART@123#")
    assert exc.value.error_code == Error.REGEX_VALIDATION_FAILED
    assert "Invalid manufacturerPartId" in exc.value.message


def test_validate_inputs_success():
    """Should pass validation with correct inputs."""
    # Should not raise any exception
    validate_inputs("BPNL000000000000", "PART-123_ABC")
    validate_inputs("BPNS123456789012", "PART123")
    validate_inputs("BPNA987654321098", None)  # part_id can be None


# --- Tests for fetch_pcf_offer_via_dtr ---

@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.make_request')
async def test_fetch_pcf_offer_no_shells_found(mock_make_request):
    """Should raise error when no shells found in DTR."""
    mock_make_request.return_value = []
    
    with pytest.raises(HTTPError) as exc:
        await fetch_pcf_offer_via_dtr(
            manufacturerPartId="PART123",
            dataplane_url="https://dataplane.example.com",
            dtr_key="api-key",
            timeout=10
        )
    assert exc.value.error_code == Error.NO_SHELLS_FOUND
    assert "No shells found in DTR" in exc.value.message


@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.make_request')
async def test_fetch_pcf_offer_multiple_shells(mock_make_request):
    """Should raise error when multiple shells found."""
    mock_make_request.return_value = ["shell1", "shell2", "shell3"]
    
    with pytest.raises(HTTPError) as exc:
        await fetch_pcf_offer_via_dtr(
            manufacturerPartId="PART123",
            dataplane_url="https://dataplane.example.com",
            dtr_key="api-key"
        )
    assert exc.value.error_code == Error.TOO_MANY_ASSETS_FOUND
    assert "Multiple shells found" in exc.value.message


@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.get_dt_pull_service_headers')
@patch('test_orchestrator.utils.product_carbon_footprint.make_request')
async def test_fetch_pcf_offer_no_pcf_submodel(mock_make_request, mock_headers):
    """Should raise error when shell exists but no PCF submodel found."""
    # First call returns shell ID
    # Second call returns shell descriptor without PCF submodel
    mock_make_request.side_effect = [
        ["urn:uuid:shell-123"],
        {
            "submodelDescriptors": [
                {
                    "semanticId": {
                        "keys": [{"value": "urn:samm:io.catenax.other:1.0.0#Other"}]
                    }
                }
            ]
        }
    ]
    mock_headers.return_value = {"Authorization": "Bearer token"}
    
    with pytest.raises(HTTPError) as exc:
        await fetch_pcf_offer_via_dtr(
            manufacturerPartId="PART123",
            dataplane_url="https://dataplane.example.com",
            dtr_key="api-key"
        )
    assert exc.value.error_code == Error.NO_SHELLS_FOUND
    assert "No PCF submodel found" in exc.value.message


@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.get_dt_pull_service_headers')
@patch('test_orchestrator.utils.product_carbon_footprint.make_request')
async def test_fetch_pcf_offer_success(mock_make_request, mock_headers):
    """Should successfully fetch PCF offer from DTR."""
    pcf_submodel = {
        "semanticId": {
            "keys": [{"value": "urn:samm:io.catenax.pcf:8.0.0#ProductCarbonFootprint"}]
        },
        "endpoints": [{"interface": "SUBMODEL-3.0"}]
    }
    
    mock_make_request.side_effect = [
        ["urn:uuid:shell-123"],
        {
            "id": "urn:uuid:shell-123",
            "submodelDescriptors": [pcf_submodel]
        }
    ]
    mock_headers.return_value = {"Authorization": "Bearer token"}
    
    result = await fetch_pcf_offer_via_dtr(
        manufacturerPartId="PART123",
        dataplane_url="https://dataplane.example.com",
        dtr_key="api-key"
    )
    
    assert result["pcf_submodel"] == pcf_submodel
    assert result["dataplane_url"] == "https://dataplane.example.com"
    assert result["dtr_key"] == "api-key"
    assert result["dct:type"]["@id"] == "cx-taxo:PcfExchange"
    assert "shell" in result


# --- Tests for send_pcf_responses ---

@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.make_request')
async def test_send_pcf_responses_success(mock_make_request):
    """Should successfully send PCF responses with and without requestId."""
    mock_make_request.side_effect = [
        {"data": "with_requestId"},
        {"data": "without_requestId"}
    ]
    
    result = await send_pcf_responses(
        dataplane_url="https://dataplane.example.com",
        dtr_key="api-key",
        product_id="PART123",
        request_id="req-456",
        bpn="BPNL000000000000",
        timeout=80
    )
    
    assert result["with_requestId"] == {"data": "with_requestId"}
    assert result["without_requestId"] == {"data": "without_requestId"}
    assert mock_make_request.call_count == 2


@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.make_request')
async def test_send_pcf_responses_failure(mock_make_request):
    """Should raise error when PCF response cannot be sent."""
    mock_make_request.side_effect = HTTPError(
        Error.CONNECTOR_UNAVAILABLE,
        "Connection failed",
        "Network error"
    )
    
    with pytest.raises(HTTPError) as exc:
        await send_pcf_responses(
            dataplane_url="https://dataplane.example.com",
            dtr_key="api-key",
            product_id="PART123",
            request_id="req-456",
            bpn="BPNL000000000000"
        )
    assert exc.value.error_code == Error.UNPROCESSABLE_ENTITY
    assert "Were not able to send PCF response" in exc.value.message


# --- Tests for send_pcf_put_request ---

@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.make_request')
async def test_send_pcf_put_request_success(mock_make_request):
    """Should successfully send PCF PUT request."""
    mock_make_request.return_value = {"status": "accepted"}
    
    payload = {"id": "pcf-123", "pcfData": {}}
    result = await send_pcf_put_request(
        counter_party_address="https://supplier.example.com",
        product_id="PART123",
        request_id="req-456",
        bpn="BPNL000000000000",
        payload=payload,
        timeout=80
    )
    
    assert result == {"status": "accepted"}
    mock_make_request.assert_awaited_once()
    call_args = mock_make_request.call_args
    assert call_args.kwargs["method"] == "PUT"
    assert call_args.kwargs["json"] == payload


# --- Tests for pcf_check ---

@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.send_pcf_responses')
@patch('test_orchestrator.utils.product_carbon_footprint.fetch_pcf_offer_via_dtr')
@patch('test_orchestrator.utils.product_carbon_footprint.get_dataplane_access')
async def test_pcf_check_without_request_id(mock_get_dtr, mock_fetch_offer, mock_send_responses):
    """Should execute PCF check workflow without request_id - cache and verify retrieval."""
    mock_get_dtr.return_value = ("https://dataplane.example.com", "api-key", None)
    mock_fetch_offer.return_value = {
        "shell": {},
        "pcf_submodel": {"id": "pcf-submodel"},
        "dataplane_url": "https://dataplane.example.com",
        "dtr_key": "api-key"
    }
    mock_send_responses.return_value = {"with_requestId": {}, "without_requestId": {}}
    
    mock_cache = AsyncMock()
    
    result = await pcf_check(
        manufacturer_part_id="PART123",
        counter_party_id="BPNL111111111111",
        counter_party_address="https://supplier.example.com",
        pcf_version="8.0.0",
        edc_bpn_l="BPNL000000000000",
        timeout=80,
        request_id=None,
        cache=mock_cache
    )
    
    assert result["status"] == "ok"
    assert result["manufacturerPartId"] == "PART123"
    assert "requestId" in result
    assert "offer" in result
    mock_cache.set.assert_awaited_once()
    mock_send_responses.assert_awaited_once()


@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.make_request')
@patch('test_orchestrator.utils.product_carbon_footprint.pcf_dummy_dataloader')
@patch('test_orchestrator.utils.product_carbon_footprint.fetch_pcf_offer_via_dtr')
@patch('test_orchestrator.utils.product_carbon_footprint.get_dataplane_access')
async def test_pcf_check_with_request_id(mock_get_dtr, mock_fetch_offer, mock_dummy_loader, mock_make_request):
    """Should execute PCF check workflow with request_id - send dummy PCF data."""
    mock_get_dtr.return_value = ("https://dataplane.example.com", "api-key", None)
    mock_fetch_offer.return_value = {
        "shell": {},
        "pcf_submodel": {"id": "pcf-submodel"},
        "dataplane_url": "https://dataplane.example.com",
        "dtr_key": "api-key"
    }
    mock_dummy_loader.return_value = {
        "id": "dummy-id",
        "pcfData": {}
    }
    mock_make_request.return_value = {"status": "ok"}
    
    result = await pcf_check(
        manufacturer_part_id="PART123",
        counter_party_id="BPNL111111111111",
        counter_party_address="https://supplier.example.com",
        pcf_version="8.0.0",
        edc_bpn_l="BPNL000000000000",
        timeout=80,
        request_id="req-existing-123",
        cache=None
    )
    
    assert result["status"] == "ok"
    assert result["requestId"] == "req-existing-123"
    mock_dummy_loader.assert_awaited_once()
    mock_make_request.assert_awaited_once()


@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.get_dataplane_access')
async def test_pcf_check_dtr_access_failed(mock_get_dtr):
    """Should raise error when DTR access negotiation fails."""
    mock_get_dtr.return_value = (None, None, None)
    
    with pytest.raises(HTTPError) as exc:
        await pcf_check(
            manufacturer_part_id="PART123",
            counter_party_id="BPNL111111111111",
            counter_party_address="https://supplier.example.com",
            pcf_version="8.0.0",
            edc_bpn_l="BPNL000000000000",
            timeout=80,
            cache=None
        )
    assert exc.value.error_code == Error.CATALOG_FETCH_FAILED
    assert "DTR access negotiation failed" in exc.value.message


@pytest.mark.asyncio
async def test_pcf_check_invalid_bpn():
    """Should raise error for invalid BPN format."""
    with pytest.raises(HTTPError) as exc:
        await pcf_check(
            manufacturer_part_id="PART123",
            counter_party_id="BPNL111111111111",
            counter_party_address="https://supplier.example.com",
            pcf_version="8.0.0",
            edc_bpn_l="INVALID",
            timeout=80,
            cache=None
        )
    assert exc.value.error_code == Error.REGEX_VALIDATION_FAILED


# --- Tests for validate_pcf_update ---

@pytest.mark.asyncio
async def test_validate_pcf_update_invalid_bpn():
    """Should raise error when BPN format is invalid."""
    mock_cache = AsyncMock()
    
    with pytest.raises(HTTPError) as exc:
        await validate_pcf_update(
            manufacturer_part_id="PART123",
            requestId="req-456",
            edc_bpn="INVALID_BPN",
            cache=mock_cache
        )
    assert exc.value.error_code == Error.REGEX_VALIDATION_FAILED
    assert "Invalid BPN format" in exc.value.message


@pytest.mark.asyncio
async def test_validate_pcf_update_invalid_part_id():
    """Should raise error when manufacturer_part_id contains invalid characters."""
    mock_cache = AsyncMock()
    
    with pytest.raises(HTTPError) as exc:
        await validate_pcf_update(
            manufacturer_part_id="PART@#$",
            requestId="req-456",
            edc_bpn="BPNL000000000000",
            cache=mock_cache
        )
    assert exc.value.error_code == Error.REGEX_VALIDATION_FAILED
    assert "invalid characters" in exc.value.message


@pytest.mark.asyncio
async def test_validate_pcf_update_request_not_found():
    """Should raise error when requestId not found in cache."""
    mock_cache = AsyncMock()
    mock_cache.get.return_value = None
    
    with pytest.raises(HTTPError) as exc:
        await validate_pcf_update(
            manufacturer_part_id="PART123",
            requestId="req-456",
            edc_bpn="BPNL000000000000",
            cache=mock_cache
        )
    assert exc.value.error_code == Error.NOT_FOUND
    assert "No cached request found" in exc.value.message


@pytest.mark.asyncio
async def test_validate_pcf_update_part_id_mismatch():
    """Should raise error when manufacturerPartId doesn't match cached data."""
    mock_cache = AsyncMock()
    mock_cache.get.return_value = {"manufacturerPartId": "PART999"}
    
    with pytest.raises(HTTPError) as exc:
        await validate_pcf_update(
            manufacturer_part_id="PART123",
            requestId="req-456",
            edc_bpn="BPNL000000000000",
            cache=mock_cache
        )
    assert exc.value.error_code == Error.UNPROCESSABLE_ENTITY
    assert "ManufacturerPartId mismatch" in exc.value.message


@pytest.mark.asyncio
@patch('test_orchestrator.utils.product_carbon_footprint.delete_cache_entry')
async def test_validate_pcf_update_success(mock_delete_cache):
    """Should successfully validate PCF update."""
    mock_cache = AsyncMock()
    mock_cache.get.return_value = {
        "manufacturerPartId": "PART123",
        "offer": {}
    }
    
    result = await validate_pcf_update(
        manufacturer_part_id="PART123",
        requestId="req-456",
        edc_bpn="BPNL000000000000",
        cache=mock_cache
    )
    
    assert result["status"] == "ok"
    assert result["requestId"] == "req-456"
    assert result["manufacturerPartId"] == "PART123"
    mock_delete_cache.assert_awaited_once_with("req-456", mock_cache)


# --- Tests for delete_cache_entry ---

@pytest.mark.asyncio
async def test_delete_cache_entry_success():
    """Should successfully delete cache entry."""
    mock_cache = AsyncMock()
    
    await delete_cache_entry("req-456", mock_cache)
    
    mock_cache.delete.assert_awaited_once_with("req-456")


@pytest.mark.asyncio
async def test_delete_cache_entry_failure_no_exception():
    """Should log warning but not raise exception when deletion fails."""
    mock_cache = AsyncMock()
    mock_cache.delete.side_effect = Exception("Cache error")
    
    # Should not raise exception
    await delete_cache_entry("req-456", mock_cache)
    
    mock_cache.delete.assert_awaited_once()


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

# Dummy data for testing
DUMMY_MANUFACTURER_PART_ID = "PART-12345-ABC"
DUMMY_COUNTER_PARTY_ID = "BPNL111111111111"
DUMMY_COUNTER_PARTY_ADDRESS = "https://supplier.example.com/api/v1/dsp"
DUMMY_EDC_BPN_L = "BPNL000000000000"
DUMMY_REQUEST_ID = "550e8400-e29b-41d4-a716-446655440000"
DUMMY_PCF_VERSION = "8.0.0"

DUMMY_PCF_OFFER = {
    "shell": {
        "id": "urn:uuid:shell-123",
        "submodelDescriptors": []
    },
    "pcf_submodel": {
        "semanticId": {
            "keys": [{"value": "urn:samm:io.catenax.pcf:8.0.0#ProductCarbonFootprint"}]
        }
    },
    "dataplane_url": "https://dataplane.example.com",
    "dtr_key": "api-key-123"
}


# --- Fixtures ---

@pytest.fixture
def app():
    """Create FastAPI app with PCF router and overridden dependencies."""
    from test_orchestrator.auth import verify_auth
    from test_orchestrator.cache import get_cache_provider
    
    app = FastAPI()
    
    # Override auth and cache dependencies
    async def mock_verify_auth():
        return True
    
    async def mock_cache():
        cache = AsyncMock()
        cache.get.return_value = None
        cache.set.return_value = None
        cache.delete.return_value = None
        return cache
    
    app.dependency_overrides[verify_auth] = mock_verify_auth
    app.dependency_overrides[get_cache_provider] = mock_cache
    
    # Include router AFTER overriding dependencies
    app.include_router(pcf_router)
    
    # Add HTTPError handler
    @app.exception_handler(HTTPError)
    async def http_error_handler(request, exc: HTTPError):
        return JSONResponse(status_code=exc.status_code, content=exc.json)
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_pcf_check():
    """Mock pcf_check used by API router."""
    with patch(
        "test_orchestrator.api.product_carbon_footprint.pcf_check",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate_pcf_update():
    """Mock validate_pcf_update used by API router."""
    with patch(
        "test_orchestrator.api.product_carbon_footprint.validate_pcf_update",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


# --- Tests for GET /productIds/{manufacturer_part_id} ---

def test_get_product_pcf_success(client, mock_pcf_check):
    """
    Test successful PCF offer retrieval without request_id.
    """
    mock_pcf_check.return_value = {
        "status": "ok",
        "manufacturerPartId": DUMMY_MANUFACTURER_PART_ID,
        "requestId": DUMMY_REQUEST_ID,
        "offer": DUMMY_PCF_OFFER
    }
    
    response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "pcf_version": DUMMY_PCF_VERSION
        },
        headers={"Edc-Bpn-L": DUMMY_EDC_BPN_L}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["manufacturerPartId"] == DUMMY_MANUFACTURER_PART_ID
    assert "requestId" in response.json()
    assert "offer" in response.json()
    
    mock_pcf_check.assert_awaited_once()
    call_kwargs = mock_pcf_check.call_args.kwargs
    assert call_kwargs["manufacturer_part_id"] == DUMMY_MANUFACTURER_PART_ID
    assert call_kwargs["counter_party_id"] == DUMMY_COUNTER_PARTY_ID
    assert call_kwargs["pcf_version"] == DUMMY_PCF_VERSION
    assert call_kwargs["edc_bpn_l"] == DUMMY_EDC_BPN_L
    assert call_kwargs["request_id"] is None


def test_get_product_pcf_with_request_id(client, mock_pcf_check):
    """
    Test PCF retrieval with existing request_id.
    """
    mock_pcf_check.return_value = {
        "status": "ok",
        "manufacturerPartId": DUMMY_MANUFACTURER_PART_ID,
        "requestId": DUMMY_REQUEST_ID,
        "offer": DUMMY_PCF_OFFER
    }
    
    response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "pcf_version": DUMMY_PCF_VERSION,
            "request_id": DUMMY_REQUEST_ID
        },
        headers={"Edc-Bpn-L": DUMMY_EDC_BPN_L}
    )
    
    assert response.status_code == 200
    assert response.json()["requestId"] == DUMMY_REQUEST_ID
    
    call_kwargs = mock_pcf_check.call_args.kwargs
    assert call_kwargs["request_id"] == DUMMY_REQUEST_ID


def test_get_product_pcf_version_7(client, mock_pcf_check):
    """
    Test PCF retrieval with version 7.0.0.
    """
    mock_pcf_check.return_value = {
        "status": "ok",
        "manufacturerPartId": DUMMY_MANUFACTURER_PART_ID,
        "requestId": DUMMY_REQUEST_ID,
        "offer": DUMMY_PCF_OFFER
    }
    
    response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "pcf_version": "7.0.0"
        },
        headers={"Edc-Bpn-L": DUMMY_EDC_BPN_L}
    )
    
    assert response.status_code == 200
    call_kwargs = mock_pcf_check.call_args.kwargs
    assert call_kwargs["pcf_version"] == "7.0.0"


def test_get_product_pcf_custom_timeout(client, mock_pcf_check):
    """
    Test PCF retrieval with custom timeout.
    """
    mock_pcf_check.return_value = {
        "status": "ok",
        "manufacturerPartId": DUMMY_MANUFACTURER_PART_ID,
        "requestId": DUMMY_REQUEST_ID,
        "offer": DUMMY_PCF_OFFER
    }
    
    response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS,
            "timeout": 120
        },
        headers={"Edc-Bpn-L": DUMMY_EDC_BPN_L}
    )
    
    assert response.status_code == 200
    call_kwargs = mock_pcf_check.call_args.kwargs
    assert call_kwargs["timeout"] == 120


def test_get_product_pcf_missing_header(client, mock_pcf_check):
    """
    Test PCF retrieval without required Edc-Bpn-L header.
    """
    response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS
        }
    )
    
    assert response.status_code == 422  # Validation error from FastAPI


def test_get_product_pcf_missing_query_params(client, mock_pcf_check):
    """
    Test PCF retrieval without required query parameters.
    """
    response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        headers={"Edc-Bpn-L": DUMMY_EDC_BPN_L}
    )
    
    assert response.status_code == 422  # Validation error


def test_get_product_pcf_invalid_bpn(client, mock_pcf_check):
    """
    Test PCF retrieval with invalid BPN format.
    """
    error = HTTPError(
        Error.REGEX_VALIDATION_FAILED,
        "Invalid BPN: INVALID",
        "Invalid format"
    )
    mock_pcf_check.side_effect = error
    
    response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS
        },
        headers={"Edc-Bpn-L": "INVALID"}
    )
    
    assert response.status_code == error.status_code
    assert response.json() == error.json


def test_get_product_pcf_dtr_access_failed(client, mock_pcf_check):
    """
    Test PCF retrieval when DTR access negotiation fails.
    """
    error = HTTPError(
        Error.CATALOG_FETCH_FAILED,
        "DTR access negotiation failed",
        "No dataplane URL or DTR key received"
    )
    mock_pcf_check.side_effect = error
    
    response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS
        },
        headers={"Edc-Bpn-L": DUMMY_EDC_BPN_L}
    )
    
    assert response.status_code == error.status_code
    assert response.json() == error.json


def test_get_product_pcf_no_shells_found(client, mock_pcf_check):
    """
    Test PCF retrieval when no shells found in DTR.
    """
    error = HTTPError(
        Error.NO_SHELLS_FOUND,
        "No shells found in DTR",
        f"No shell for manufacturerPartId: {DUMMY_MANUFACTURER_PART_ID}"
    )
    mock_pcf_check.side_effect = error
    
    response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS
        },
        headers={"Edc-Bpn-L": DUMMY_EDC_BPN_L}
    )
    
    assert response.status_code == error.status_code
    assert response.json()["error"] == "NO_SHELLS_FOUND"


def test_get_product_pcf_no_pcf_submodel(client, mock_pcf_check):
    """
    Test PCF retrieval when shell exists but no PCF submodel found.
    """
    error = HTTPError(
        Error.NO_SHELLS_FOUND,
        "No PCF submodel found",
        "Shell exists but no PCF submodel descriptor"
    )
    mock_pcf_check.side_effect = error
    
    response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS
        },
        headers={"Edc-Bpn-L": DUMMY_EDC_BPN_L}
    )
    
    assert response.status_code == error.status_code
    assert "No PCF submodel found" in response.json()["message"]


# --- Tests for PUT /productIds/{manufacturer_part_id} ---

def test_update_product_pcf_success(client, mock_validate_pcf_update):
    """
    Test successful PCF update validation.
    """
    mock_validate_pcf_update.return_value = {
        "status": "ok",
        "message": "PCF data validated successfully",
        "requestId": DUMMY_REQUEST_ID,
        "manufacturerPartId": DUMMY_MANUFACTURER_PART_ID
    }
    
    response = client.put(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={"requestId": DUMMY_REQUEST_ID},
        headers={"Edc-Bpn": DUMMY_COUNTER_PARTY_ID}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["requestId"] == DUMMY_REQUEST_ID
    assert response.json()["manufacturerPartId"] == DUMMY_MANUFACTURER_PART_ID
    
    mock_validate_pcf_update.assert_awaited_once()
    call_kwargs = mock_validate_pcf_update.call_args.kwargs
    assert call_kwargs["manufacturer_part_id"] == DUMMY_MANUFACTURER_PART_ID
    assert call_kwargs["requestId"] == DUMMY_REQUEST_ID
    assert call_kwargs["edc_bpn"] == DUMMY_COUNTER_PARTY_ID


def test_update_product_pcf_missing_request_id(client, mock_validate_pcf_update):
    """
    Test PCF update without required requestId parameter.
    """
    response = client.put(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        headers={"Edc-Bpn": DUMMY_COUNTER_PARTY_ID}
    )
    
    assert response.status_code == 422  # Validation error


def test_update_product_pcf_missing_header(client, mock_validate_pcf_update):
    """
    Test PCF update without required Edc-Bpn header.
    """
    response = client.put(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={"requestId": DUMMY_REQUEST_ID}
    )
    
    assert response.status_code == 422  # Validation error


def test_update_product_pcf_invalid_bpn(client, mock_validate_pcf_update):
    """
    Test PCF update with invalid BPN format.
    """
    error = HTTPError(
        Error.REGEX_VALIDATION_FAILED,
        "Invalid BPN format: INVALID",
        "Expected format like BPNL000000000000"
    )
    mock_validate_pcf_update.side_effect = error
    
    response = client.put(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={"requestId": DUMMY_REQUEST_ID},
        headers={"Edc-Bpn": "INVALID"}
    )
    
    assert response.status_code == error.status_code
    assert response.json() == error.json


def test_update_product_pcf_request_not_found(client, mock_validate_pcf_update):
    """
    Test PCF update when requestId not found in cache.
    """
    error = HTTPError(
        Error.NOT_FOUND,
        f"No cached request found for requestId: {DUMMY_REQUEST_ID}",
        "The requestId may have expired or is invalid"
    )
    mock_validate_pcf_update.side_effect = error
    
    response = client.put(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={"requestId": DUMMY_REQUEST_ID},
        headers={"Edc-Bpn": DUMMY_COUNTER_PARTY_ID}
    )
    
    assert response.status_code == error.status_code
    assert response.json()["error"] == "NOT_FOUND"
    assert "No cached request found" in response.json()["message"]


def test_update_product_pcf_part_id_mismatch(client, mock_validate_pcf_update):
    """
    Test PCF update when manufacturerPartId doesn't match cached data.
    """
    error = HTTPError(
        Error.UNPROCESSABLE_ENTITY,
        "ManufacturerPartId mismatch",
        f"Expected PART-999, got {DUMMY_MANUFACTURER_PART_ID}"
    )
    mock_validate_pcf_update.side_effect = error
    
    response = client.put(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={"requestId": DUMMY_REQUEST_ID},
        headers={"Edc-Bpn": DUMMY_COUNTER_PARTY_ID}
    )
    
    assert response.status_code == error.status_code
    assert response.json()["error"] == "UNPROCESSABLE_ENTITY"
    assert "ManufacturerPartId mismatch" in response.json()["message"]


def test_update_product_pcf_invalid_part_id_chars(client, mock_validate_pcf_update):
    """
    Test PCF update with invalid characters in manufacturerPartId.
    """
    error = HTTPError(
        Error.REGEX_VALIDATION_FAILED,
        "manufacturerPartId contains invalid characters",
        "manufacturerPartId contains invalid characters"
    )
    mock_validate_pcf_update.side_effect = error
    
    invalid_part_id = "PART@#$%"
    response = client.put(
        f"/productIds/{invalid_part_id}",
        params={"requestId": DUMMY_REQUEST_ID},
        headers={"Edc-Bpn": DUMMY_COUNTER_PARTY_ID}
    )
    
    assert response.status_code == error.status_code
    assert "invalid characters" in response.json()["message"]


# --- Integration-style tests ---

def test_get_then_put_workflow(client, mock_pcf_check, mock_validate_pcf_update):
    """
    Test complete workflow: GET to retrieve offer, then PUT to validate update.
    """
    # Step 1: GET request
    mock_pcf_check.return_value = {
        "status": "ok",
        "manufacturerPartId": DUMMY_MANUFACTURER_PART_ID,
        "requestId": DUMMY_REQUEST_ID,
        "offer": DUMMY_PCF_OFFER
    }
    
    get_response = client.get(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={
            "counter_party_id": DUMMY_COUNTER_PARTY_ID,
            "counter_party_address": DUMMY_COUNTER_PARTY_ADDRESS
        },
        headers={"Edc-Bpn-L": DUMMY_EDC_BPN_L}
    )
    
    assert get_response.status_code == 200
    request_id = get_response.json()["requestId"]
    
    # Step 2: PUT request with received requestId
    mock_validate_pcf_update.return_value = {
        "status": "ok",
        "message": "PCF data validated successfully",
        "requestId": request_id,
        "manufacturerPartId": DUMMY_MANUFACTURER_PART_ID
    }
    
    put_response = client.put(
        f"/productIds/{DUMMY_MANUFACTURER_PART_ID}",
        params={"requestId": request_id},
        headers={"Edc-Bpn": DUMMY_COUNTER_PARTY_ID}
    )
    
    assert put_response.status_code == 200
    assert put_response.json()["status"] == "ok"
    assert put_response.json()["requestId"] == request_id
