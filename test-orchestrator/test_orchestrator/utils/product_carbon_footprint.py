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
import uuid

from typing import Dict, Optional

from test_orchestrator import config

from test_orchestrator.request_handler import make_request
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.cache import CacheProvider
from test_orchestrator.base_utils import pcf_dummy_dataloader, get_dataplane_access

logger = logging.getLogger(__name__)


def validate_inputs(edc_bpn: str, manufacturer_part_id: str):
    """Validate BPN and manufacturer part ID format.

    Args:
        edc_bpn: Business Partner Number in BPN format
        manufacturer_part_id: Manufacturer part identifier containing only alphanumeric, dash, and underscore

    Raises:
        HTTPError: If edc_bpn is missing, has invalid format, or manufacturer_part_id contains invalid characters
    """
    if not edc_bpn:
        raise HTTPError(
            Error.MISSING_REQUIRED_FIELD,
            message="Missing required header: Edc-Bpn",
            details="Missing header",
        )

    bpn_pattern = re.compile(r"^BPN[LSA][A-Z0-9]{10}[A-Z0-9]{2}$")

    if not bpn_pattern.match(edc_bpn):
        raise HTTPError(
            Error.REGEX_VALIDATION_FAILED,
            message=f"Invalid BPN: {edc_bpn}",
            details="Invalid format",
        )

    part_id_pattern = re.compile(r"^[A-Za-z0-9\-_]+$")

    if manufacturer_part_id and not part_id_pattern.match(manufacturer_part_id):
        raise HTTPError(
            Error.REGEX_VALIDATION_FAILED,
            message="Invalid manufacturerPartId",
            details="Invalid chars",
        )


async def fetch_pcf_offer_via_dtr(
    manufacturerPartId: str, dataplane_url: str, dtr_key: str, timeout: int = 10
):
    """Fetch PCF submodel offer from Digital Twin Registry.

    Performs a lookup for the manufacturerPartId in DTR, retrieves the shell descriptor,
    and extracts the PCF submodel information.

    Args:
        manufacturerPartId: The manufacturer part identifier to look up
        dataplane_url: DTR dataplane endpoint URL
        dtr_key: Authorization key for DTR access
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Dict containing shell descriptor, pcf_submodel, dataplane_url, dtr_key, and dct:type

    Raises:
        HTTPError: If no shells found, multiple shells found, or no PCF submodel exists in shell
    """

    asset_link_body = [{"name": "manufacturerPartId", "value": manufacturerPartId}]

    try:
        lookup_response = await make_request(
            "POST",
            f"{config.DT_PULL_SERVICE_ADDRESS}/dtr/lookup/",
            params={"dataplane_url": dataplane_url},
            json=asset_link_body,
            headers=get_dt_pull_service_headers(headers={"Authorization": dtr_key}),
            timeout=timeout,
        )

        shell_ids = (
            lookup_response
            if isinstance(lookup_response, list)
            else lookup_response.get("result", [])
        )

        if not shell_ids:
            raise HTTPError(
                Error.NO_SHELLS_FOUND,
                message="No shells found in DTR",
                details=f"No shell for manufacturerPartId: {manufacturerPartId}",
            )

        if len(shell_ids) > 1:
            raise HTTPError(
                Error.TOO_MANY_ASSETS_FOUND,
                message="Multiple shells found",
                details=f"Found {len(shell_ids)} shells for manufacturerPartId",
            )

        shell_id = (
            shell_ids[0] if isinstance(shell_ids[0], str) else shell_ids[0].get("id")
        )

        logger.info(f"Fetching shell descriptor: {shell_id}")

        shell_response = await make_request(
            "GET",
            f"{config.DT_PULL_SERVICE_ADDRESS}/dtr/shell-descriptors/",
            params={"dataplane_url": dataplane_url, "aas_id": shell_id, "limit": 1},
            headers=get_dt_pull_service_headers(headers={"Authorization": dtr_key}),
            timeout=timeout,
        )

        pcf_submodel = None

        for submodel_desc in shell_response.get("submodelDescriptors", []):
            semantic_id = submodel_desc.get("semanticId", {})
            keys = semantic_id.get("keys", [])

            for key in keys:
                value = key.get("value", "")
                if "pcf" in value.lower() or "ProductCarbonFootprint" in value:
                    pcf_submodel = submodel_desc
                    break

            if pcf_submodel:
                break

        if not pcf_submodel:
            raise HTTPError(
                Error.NO_SHELLS_FOUND,
                message="No PCF submodel found",
                details="Shell exists but no PCF submodel descriptor",
            )

        return {
            "shell": shell_response,
            "pcf_submodel": pcf_submodel,
            "dataplane_url": dataplane_url,
            "dtr_key": dtr_key,
            "dct:type": {"@id": "cx-taxo:PcfExchange"},
        }

    except HTTPError:
        raise
    except Exception as exc:
        raise HTTPError(
            Error.CATALOG_FETCH_FAILED,
            message=f"DTR access or lookup failed: {str(exc)}",
            details=str(exc),
        )


async def send_pcf_responses(
    dataplane_url: str,
    dtr_key: str,
    product_id: str,
    request_id: str,
    bpn: str,
    timeout: int = 80,
):
    """Send PCF response requests with and without requestId parameter.

    Makes two GET requests to verify PCF data retrieval with optional requestId.

    Args:
        dataplane_url: Counterparty dataplane endpoint URL
        dtr_key: Authorization bearer token
        product_id: Product identifier (manufacturer part ID)
        request_id: Request identifier for tracking
        bpn: Business Partner Number for Edc-Bpn header
        timeout: Request timeout in seconds (default: 80)

    Returns:
        Dict with 'with_requestId' and 'without_requestId' response keys

    Raises:
        HTTPError: If PCF response cannot be sent
    """
    responses = {}

    url = f"{dataplane_url}/productIds/{product_id}"

    try:
        responses["with_requestId"] = await make_request(
            method="GET",
            url=url,
            timeout=20,
            params={"requestId": request_id},
            headers={"Edc-Bpn": bpn, "Authorization": dtr_key},
        )

        responses["without_requestId"] = await make_request(
            method="GET",
            url=url,
            timeout=20,
            headers={"Edc-Bpn": bpn, "Authorization": dtr_key},
        )
    except HTTPError as e:
        logger.error("Were not able to send PCF response.")

        raise HTTPError(
            Error.UNPROCESSABLE_ENTITY,
            message="Were not able to send PCF response.",
            details=str(e),
        )

    return responses


async def send_pcf_put_request(
    counter_party_address: str,
    product_id: str,
    request_id: str,
    bpn: str,
    payload: Dict,
    timeout: int = 80,
):
    """Send PCF data via PUT request to counterparty.

    Args:
        counter_party_address: Counterparty endpoint address
        product_id: Product identifier (manufacturer part ID)
        request_id: Request identifier for tracking
        bpn: Business Partner Number for Edc-Bpn header
        payload: PCF data payload to send
        timeout: Request timeout in seconds (default: 80)

    Returns:
        Response from the PUT request
    """
    url = f"{counter_party_address}/productIds/{product_id}"

    response = await make_request(
        method="PUT",
        url=url,
        timeout=timeout,
        params={"requestId": request_id},
        headers={"Edc-Bpn": bpn},
        json=payload,
    )

    return response


async def pcf_check(
    manufacturer_part_id: str,
    counter_party_id: str,
    counter_party_address: str,
    pcf_version: str,
    edc_bpn_l: str,
    timeout: int,
    request_id: Optional[str] = None,
    cache: Optional[CacheProvider] = None,
    payload: Optional[Dict] = None,
):
    """Execute PCF exchange validation by retrieving offer and sending PCF data.

    This function orchestrates the complete PCF check workflow:
    - Validates inputs (BPN and manufacturer part ID)
    - Negotiates DTR access via EDC
    - Fetches PCF offer from Digital Twin Registry
    - If request_id is None: caches offer and sends GET requests to verify retrieval
    - If request_id exists: sends dummy PCF data via PUT request

    Args:
        manufacturer_part_id: Manufacturer part identifier
        counter_party_id: Business Partner Number of the counterparty
        counter_party_address: DSP endpoint address of counterparty's connector
        pcf_version: PCF schema version (e.g., '7.0.0' or '8.0.0')
        edc_bpn_l: Business Partner Number from request header
        timeout: Request timeout in seconds
        request_id: Optional request identifier for tracking existing requests
        cache: Cache provider instance for storing request data
        payload: Optional PCF payload

    Returns:
        Dict containing status, manufacturerPartId, requestId, and offer details

    Raises:
        HTTPError: If validation fails, DTR access fails, or PCF submodel is not found
    """
    validate_inputs(edc_bpn_l, manufacturer_part_id)

    requestId = request_id if request_id else str(uuid.uuid4())
    offer = None

    if not request_id:
        dataplane_url, pcf_key, _ = await get_dataplane_access(
            counter_party_address,
            counter_party_id,
            operand_left="http://purl.org/dc/terms/type",
            operand_right="%https://w3id.org/catenax/taxonomy#PcfExchange%",
            limit=1,
            timeout=timeout,
        )

        await send_pcf_responses(
            dataplane_url=dataplane_url,
            dtr_key=pcf_key,
            product_id=manufacturer_part_id,
            request_id=requestId,
            timeout=timeout,
            bpn=edc_bpn_l,
        )
    else:
        dataplane_url, dtr_key, _ = await get_dataplane_access(
            counter_party_address,
            counter_party_id,
            operand_left="http://purl.org/dc/terms/type",
            operand_right="%https://w3id.org/catenax/taxonomy#PcfExchange%",
            limit=1,
            timeout=timeout,
        )

        if not dataplane_url or not dtr_key:
            raise HTTPError(
                Error.CATALOG_FETCH_FAILED,
                message="DTR access negotiation failed",
                details="No dataplane URL or DTR key received",
            )

        offer = await fetch_pcf_offer_via_dtr(
            manufacturerPartId=manufacturer_part_id,
            dataplane_url=dataplane_url,
            dtr_key=dtr_key,
            timeout=timeout,
        )
        await cache.set(
            requestId,
            {
                "manufacturerPartId": manufacturer_part_id,
                "offer": offer,
                "counter_party_address": counter_party_address,
            },
            expire=3600,
        )

        try:
            if not offer.get("pcf_submodel"):
                raise HTTPError(
                    Error.UNPROCESSABLE_ENTITY,
                    message="No PCF submodel found",
                    details="PCF submodel not found in shell",
                )
        except Exception as e:
            raise HTTPError(
                Error.UNKNOWN_ERROR, message="Offer validation failed", details=str(e)
            )

        semanticid = f"urn:bamm:io.catenax.pcf:{pcf_version}#Pcf"
        dummy_pcf = await pcf_dummy_dataloader(semanticid)
        dummy_pcf["productIds"] = [
            f"urn:mycompany.com:product-id:{manufacturer_part_id}"
        ]
        dummy_pcf["id"] = str(uuid.uuid4())

        url = f"{counter_party_address}/productIds/{manufacturer_part_id}"

        await make_request(
            method="PUT",
            url=url,
            timeout=timeout,
            params={"requestId": requestId},
            headers={"Edc-Bpn": config.CONNECTOR_BPNL,
                     "Authorization": dtr_key},
            json=dummy_pcf,
        )

    return {
        "status": "ok",
        "manufacturerPartId": manufacturer_part_id,
        "requestId": requestId,
        "offer": offer,
    }


async def validate_pcf_update(
    manufacturer_part_id: str, requestId: str, edc_bpn: str, cache: CacheProvider
):
    """Validate incoming PCF update request against cached data.

    Validates that the PCF PUT request contains correct BPN format,
    manufacturer part ID format, and matches cached request data.
    After successful validation, deletes the cache entry.

    Args:
        manufacturer_part_id: Manufacturer part identifier from request path
        requestId: Request identifier from query parameter
        edc_bpn: Business Partner Number from request header
        cache: Cache provider instance for retrieving cached data

    Returns:
        Dict containing status, message, requestId, and manufacturerPartId

    Raises:
        HTTPError: If BPN format is invalid, manufacturer part ID contains invalid characters,
                  requestId not found in cache, or manufacturerPartId mismatch
    """
    bpn_pattern = re.compile(r"^BPN[LSA][A-Z0-9]{10}[A-Z0-9]{2}$")

    if not bpn_pattern.match(edc_bpn):
        raise HTTPError(
            Error.REGEX_VALIDATION_FAILED,
            message=f"Invalid BPN format: {edc_bpn}",
            details="Expected format like BPNL000000000000",
        )

    manufacturerPartId_pattern = re.compile(r"^[A-Za-z0-9\-_]+$")

    if manufacturer_part_id and not manufacturerPartId_pattern.match(
        manufacturer_part_id
    ):
        raise HTTPError(
            Error.REGEX_VALIDATION_FAILED,
            message="manufacturerPartId contains invalid characters",
            details="manufacturerPartId contains invalid characters",
        )

    cached_data = await cache.get(requestId)

    if not cached_data:
        raise HTTPError(
            Error.NOT_FOUND,
            message=f"No cached request found for requestId: {requestId}",
            details="The requestId may have expired or is invalid",
        )

    if cached_data.get("manufacturerPartId") != manufacturer_part_id:
        raise HTTPError(
            Error.UNPROCESSABLE_ENTITY,
            message="ManufacturerPartId mismatch",
            details=f"Expected {cached_data.get('manufacturerPartId')}, got {manufacturer_part_id}",
        )

    await delete_cache_entry(requestId, cache)

    return {
        "status": "ok",
        "message": "PCF data validated successfully",
        "requestId": requestId,
        "manufacturerPartId": manufacturer_part_id,
    }


async def delete_cache_entry(requestId: str, cache: CacheProvider):
    """Delete cache entry for the given request ID.

    Attempts to delete cache entry and logs warning if deletion fails.
    Does not raise exception on failure.

    Args:
        requestId: Request identifier to delete from cache
        cache: Cache provider instance
    """
    try:
        await cache.delete(requestId)
    except Exception as e:
        logger.warning(f"Failed to delete cache for requestId {requestId}: {str(e)}")
