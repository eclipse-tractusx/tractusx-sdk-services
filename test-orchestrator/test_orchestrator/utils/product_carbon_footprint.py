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
from test_orchestrator.validator import json_validator
from test_orchestrator.cache import CacheProvider
from test_orchestrator.base_utils import submodel_schema_finder

logger = logging.getLogger(__name__)

def validate_inputs(edc_bpn: str, manufacturer_part_id: str):
    if not edc_bpn:
        raise HTTPError(Error.MISSING_REQUIRED_FIELD, message="Missing required header: Edc-BPN", details="Missing header")
    
    bpn_pattern = re.compile(r'^BPN[LSA][A-Z0-9]{10}[A-Z0-9]{2}$')
    if not bpn_pattern.match(edc_bpn):
        raise HTTPError(Error.REGEX_VALIDATION_FAILED, message=f'Invalid BPN: {edc_bpn}', details='Invalid format')

    part_id_pattern = re.compile(r"^[A-Za-z0-9\-_]+$")
    if manufacturer_part_id and not part_id_pattern.match(manufacturer_part_id):
        raise HTTPError(Error.REGEX_VALIDATION_FAILED, message="Invalid manufacturerPartId", details="Invalid chars")

async def fetch_pcf_offer_from_catalog(manufacturerPartId: str, timeout: int = 10):
    params = {
        "aas_id": manufacturerPartId,
        "limit": 2,  # detect multiple offers
        "type": "cx-taxo:PcfExchange"
    }

    try:
        response = await make_request(
            "GET",
            f"{config.DT_PULL_SERVICE_ADDRESS}/dtr/shell-descriptors/",
            params=params,
            headers=get_dt_pull_service_headers(),
            timeout=timeout
        )
    except Exception as exc:
        raise HTTPError(
            Error.CATALOG_FETCH_FAILED,
            message=f"Catalog fetch failed: {str(exc)}",
            details=exc)

    offers = response.get("dcat:dataset", [])
    if not offers:
        raise HTTPError(
            Error.NO_SHELLS_FOUND,
            message="PCF offer not found",
            details="PCF offer not found")

    if len(offers) > 1:
        raise HTTPError(
            Error.TOO_MANY_ASSETS_FOUND,
            message="Multiple PCF offers found for this manufacturerPartId",
            details="Multiple PCF offers found for this manufacturerPartId")

    return offers[0]


async def send_pcf_responses(counter_party_address: str, product_id: str, request_id: str, bpn: str, timeout: int = 80):
    responses = {}

    url = f"{counter_party_address}/productIds/{product_id}"

    responses['with_requestId'] = await make_request(
        method="GET",
        url=url,
        timeout=timeout,
        params={"requestId": request_id},
        headers={"Edc-BPN": bpn}
    )

    responses['without_requestId'] = await make_request(
        method="GET",
        url=url,
        timeout=timeout,
        headers={"Edc-BPN": bpn}
    )

    return responses

async def send_pcf_put_request(counter_party_address: str, product_id: str, request_id: str, bpn: str, payload: Dict, timeout: int = 80):
    url = f"{counter_party_address}/productIds/{product_id}"
    
    response = await make_request(
        method="PUT",
        url=url,
        timeout=timeout,
        params={"requestId": request_id},
        headers={"Edc-BPN": bpn},
        json=payload
    )
    return response

async def pcf_check(manufacturer_part_id: str, counter_party_address: str, pcf_version: str, edc_bpn_l: str, timeout: str, request_id: Optional[str] = None, cache: Optional[CacheProvider] = None, payload: Optional[Dict] = None):
    validate_inputs(edc_bpn_l, manufacturer_part_id)

    requestId = request_id if request_id else str(uuid.uuid4())

    offer = None

    if not request_id:
        offer = await fetch_pcf_offer_from_catalog(manufacturer_part_id)

        await cache.set(requestId, {"manufacturerPartId": manufacturer_part_id, "offer": offer}, expire=3600)

        try:
            semantic_id = f"urn:bamm:io.catenax.pcf:{pcf_version}#Pcf"
            subm_schema_dict = submodel_schema_finder(semantic_id)
            validation_result = json_validator(subm_schema_dict['schema'], offer)
        except Exception:
            raise HTTPError(
                Error.UNKNOWN_ERROR,
                message="An unknown error processing the shell descriptor occurred.",
                details="Please contact the testbed administrator."
            )

        if validation_result.get('status') == 'nok':
            raise HTTPError(
                Error.UNPROCESSABLE_ENTITY,
                message='Validation error',
                details={'validation_errors': validation_result}
            )
        
    if request_id:
        url = f"{counter_party_address}/productIds/{manufacturer_part_id}"
        dummy_payload = {
            "id": "urn:uuid:dummy-pcf", 
            "productIds": [manufacturer_part_id], 
            "comment": "Testbed dummy payload"
        }
        await make_request(
            method="PUT",
            url=url,
            timeout=timeout,
            params={"requestId": requestId},
            headers={"Edc-BPN": edc_bpn_l},
            json=dummy_payload
        )
    else:
        await send_pcf_responses(
            counter_party_address=counter_party_address,
            product_id=manufacturer_part_id,
            request_id=requestId,
            timeout=timeout,
            bpn=edc_bpn_l
        )

    return {
        "status": "ok",
        "manufacturerPartId": manufacturer_part_id,
        "requestId": requestId,
        "offer": offer
    }

async def validate_pcf_update(manufacturer_part_id: str, requestId: str, edc_bpn: str, cache: CacheProvider):
    bpn_pattern = re.compile(r'^BPN[LSA][A-Z0-9]{10}[A-Z0-9]{2}$')
    if not bpn_pattern.match(edc_bpn):
        raise HTTPError(
            Error.REGEX_VALIDATION_FAILED,
            message=f'Invalid BPN format: {edc_bpn}',
            details='Expected format like BPNL000000000000'
        )
    
    manufacturerPartId_pattern= re.compile(r"^[A-Za-z0-9\-_]+$")
    if manufacturer_part_id and not manufacturerPartId_pattern.match(manufacturer_part_id):
        raise HTTPError(
            Error.REGEX_VALIDATION_FAILED,
            message="manufacturerPartId contains invalid characters",
            details="manufacturerPartId contains invalid characters")
    
    cached_data = await cache.get(requestId)
    if not cached_data:
        raise HTTPError(
            Error.NOT_FOUND,
            message=f"No cached request found for requestId: {requestId}",
            details="The requestId may have expired or is invalid"
        )
    
    if cached_data.get("manufacturerPartId") != manufacturer_part_id:
        raise HTTPError(
            Error.UNPROCESSABLE_ENTITY,
            message="ManufacturerPartId mismatch",
            details=f"Expected {cached_data.get('manufacturerPartId')}, got {manufacturer_part_id}"
        )
    
    await delete_cache_entry(requestId, cache)

    return {
        "status": "ok",
        "message": "PCF data validated successfully",
        "requestId": requestId,
        "manufacturerPartId": manufacturer_part_id
    }

async def delete_cache_entry(requestId: str, cache: CacheProvider):
    try:
        await cache.delete(requestId)
    except Exception as e:
        logger.warning(f"Failed to delete cache for requestId {requestId}: {str(e)}")
