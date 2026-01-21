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

import logging
from typing import Dict, Literal, Optional
from fastapi import APIRouter, Depends, Query, Header, Path

from test_orchestrator.auth import verify_auth
from test_orchestrator.cache import get_cache_provider, CacheProvider
from test_orchestrator.utils.product_carbon_footprint import (
    pcf_check,
    validate_pcf_update
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('/productIds/{manufacturer_part_id}',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def get_product_pcf(manufacturer_part_id: str = Path(..., description='Manufacturer Part ID'),
                          counter_party_id: str = Query(..., description="Counter party ID"),
                          counter_party_address: str =
                            Query(..., description="The DSP endpoint address of the supplier's connector"),
                          pcf_version: Literal['7.0.0', '8.0.0', '9.0.0']  =
                            Query('8.0.0', description='Schema version - 7.0.0 or 8.0.0 supported'),
                          edc_bpn_l: str = Header(..., alias='Edc-Bpn-L'),
                          request_id: Optional[str] = Query(None, description='Optional Request ID'),
                          timeout: int = 80,
                          cache: CacheProvider = Depends(get_cache_provider)):
    """Retrieve Product Carbon Footprint offer from supplier's Digital Twin Registry.
    
    This endpoint initiates the PCF exchange by negotiating access to the supplier's DTR,
    fetching the PCF submodel offer, and verifying data retrieval capabilities.
    
    Args:
        manufacturer_part_id: Manufacturer part identifier
        counter_party_id: Supplier's Business Partner Number
        counter_party_address: Supplier's EDC DSP endpoint
        pcf_version: PCF schema version (7.0.0 or 8.0.0)
        edc_bpn_l: Requester's Business Partner Number (from header)
        request_id: Optional request ID for tracking
        timeout: Request timeout in seconds
        cache: Cache provider dependency
    
    Returns:
        Dict with status, manufacturerPartId, requestId, and offer information
    """
    return await pcf_check(manufacturer_part_id=manufacturer_part_id,
                           counter_party_id=counter_party_id,
                           counter_party_address=counter_party_address,
                           pcf_version=pcf_version,
                           edc_bpn_l=edc_bpn_l,
                           request_id=request_id,
                           timeout=timeout,
                           cache=cache)


@router.put('/productIds/{manufacturer_part_id}',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def update_product_pcf(manufacturer_part_id: str = Path(..., description='Manufacturer Part ID'),
                             request_id: str = Query(..., description='Request ID from previous GET call'),
                             edc_bpn: str = Header(..., alias='Edc-Bpn'),
                             cache: CacheProvider = Depends(get_cache_provider)):
    """Validate incoming PCF data update from supplier.
    
    This endpoint receives PCF data from the supplier and validates it against
    the previously cached request information from the GET call.
    
    Args:
        manufacturer_part_id: Manufacturer part identifier
        requestId: Request ID from the initial GET request
        edc_bpn: Supplier's Business Partner Number (from header)
        cache: Cache provider dependency
    
    Returns:
        Dict with validation status, message, requestId, and manufacturerPartId
    """
    return await validate_pcf_update(manufacturer_part_id=manufacturer_part_id,
                                     request_id=request_id,
                                     edc_bpn=edc_bpn,
                                     cache=cache)
