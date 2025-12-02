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

from test_orchestrator import config
from test_orchestrator.request_handler import make_request
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.errors import Error, HTTPError

from test_orchestrator.cache import CacheProvider

logger = logging.getLogger(__name__)


def validate_alphanumeric(value: str, name: str):
    if not re.match(r"^[A-Za-z0-9\-_]+$", value):
        raise HTTPError(
            Error.REGEX_VALIDATION_FAILED,
            message=f"{name} contains invalid characters",
            detail=f"{name} contains invalid characters")


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
            detail=exc)

    offers = response.get("dcat:dataset", [])
    if not offers:
        raise HTTPError(
            Error.NO_SHELLS_FOUND,
            message="PCF offer not found",
            detail="PCF offer not found")

    if len(offers) > 1:
        raise HTTPError(
            Error.TOO_MANY_ASSETS_FOUND,
            message="Multiple PCF offers found for this manufacturerPartId",
            detail="Multiple PCF offers found for this manufacturerPartId")

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


async def pcf_check(manufacturerPartId: str, requestId: str, counter_party_address: str, pcf_version: str, timeout: str, edc_bpn_l: str, cache: CacheProvider):
    if not edc_bpn_l:
        raise HTTPError(
            Error.MISSING_REQUIRED_FIELD,
            message="Missing required header: Edc-BPN-L",
            detail="Missing required header: Edc-BPN-L")
    
    bpn_pattern = re.compile(r'^BPN[LSA][A-Z0-9]{10}[A-Z0-9]{2}$')
    if edc_bpn_l and not bpn_pattern.match(edc_bpn_l):
        raise HTTPError(
            Error.REGEX_VALIDATION_FAILED,
            message=f'Invalid BPN format in header.: {edc_bpn_l} (expected e.g. BPNL000000000000)',
            detail=f'Invalid BPN format in header.: {edc_bpn_l} (expected e.g. BPNL000000000000)')
    
    validate_alphanumeric(manufacturerPartId, "manufacturerPartId")
    validate_alphanumeric(requestId, "requestId")

    cached_entry = await cache.get(requestId)
    if cached_entry:
        await send_pcf_responses(
            counter_party_address=counter_party_address,
            product_id=manufacturerPartId,
            request_id=requestId,
            timeout=timeout,
            bpn=edc_bpn_l
        )

        return {
            "status": "ok",
            "manufacturerPartId": cached_entry.manufacturerPartId,
            "requestId": requestId,
            "offer": cached_entry.offer
        }
    else:
        offer = await fetch_pcf_offer_from_catalog(manufacturerPartId)

        await cache.set(requestId, {"manufacturerPartId": manufacturerPartId, "offer": offer}, expire=3600)

        await send_pcf_responses(
            counter_party_address=counter_party_address,
            product_id=manufacturerPartId,
            request_id=requestId,
            timeout=timeout,
            bpn=edc_bpn_l
        )

        return {
            "status": "ok",
            "manufacturerPartId": manufacturerPartId,
            "requestId": requestId,
            "offer": offer
        }