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
from typing import Dict, Literal
from fastapi import APIRouter, Depends, Query, Header, Path

from test_orchestrator.auth import verify_auth
from test_orchestrator.cache import get_cache_provider, CacheProvider
from test_orchestrator.utils.product_carbon_footprint import (
    pcf_check
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/productIds/{manufacturerPartId}",
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def get_product_pcf(manufacturerPartId: str = Path(..., description="Manufacturer Part ID"),
                          requestId: str = Query(..., description="Unique request identifier"),
                          counter_party_address: str = Query(..., description="The DSP endpoint address of the supplier's connector"),
                          pcf_version: Literal["7.0.0", "8.0.0"]  = Query(..., description="Schema version - 7.0.0 or 8.0.0 supported"),
                          edc_bpn_l: str = Header(..., alias="Edc-Bpn-L"),
                          timeout: int = 80,
                          cache: CacheProvider = Depends(get_cache_provider)):
    return pcf_check(manufacturerPartId=manufacturerPartId,
                     requestId=requestId,
                     counter_party_address=counter_party_address,
                     pcf_version=pcf_version,
                     edc_bpn_l=edc_bpn_l,
                     timeout=timeout,
                     cache=cache)