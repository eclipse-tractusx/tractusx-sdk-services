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

from datetime import datetime
import logging
import re
from typing import Dict, List

from test_orchestrator import config
from test_orchestrator.request_handler import make_request
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.base_utils import get_dtr_access

from test_orchestrator.cache import get_cache_provider, CacheProvider
from test_orchestrator.utils import mo

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


async def pcf_check(manufacturerPartId: str, requestId: str, edc_bpn_l: str, cache: CacheProvider):
    if not edc_bpn_l:
        raise HTTPError(
            Error.MISSING_REQUIRED_FIELD,
            message="Missing required header: Edc-BPN-L",
            detail="Missing required header: Edc-BPN-L")
    
    validate_alphanumeric(manufacturerPartId, "manufacturerPartId")
    validate_alphanumeric(requestId, "requestId")

    cached_entry = await cache.get(requestId)
    if cached_entry:
        return {
            "status": "ok",
            "manufacturerPartId": cached_entry.manufacturerPartId,
            "requestId": requestId,
            "offer": cached_entry.offer
        }
    
    offer = await fetch_pcf_offer_from_catalog(manufacturerPartId)

    await cache.set(requestId, {"manufacturerPartId": manufacturerPartId, "offer": offer}, expire=3600)

    return {
        "status": "ok",
        "manufacturerPartId": manufacturerPartId,
        "requestId": requestId,
        "offer": offer
    }