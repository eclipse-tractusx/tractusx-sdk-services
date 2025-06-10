# *************************************************************
# Eclipse Tractus-X - Digital Twin Pull Service
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

"""API endpoints for DTR
"""

from typing import Dict, Optional

from fastapi import APIRouter, Header, Request, Depends, HTTPException
from dt_pull_service.auth import verify_auth

from dt_pull_service.dtr_helper import get_dtr_handler

router = APIRouter()


@router.get('/shell-descriptors/',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def shell_descriptors(dataplane_url: str,
                            aas_id: Optional[str] = '',
                            authorization: str = Header(None)):
    """
    Retrieves the shell descriptors from the partner's DTR.

     - :param dataplane_url: The URL for getting the DTR handler.
     - :param agreement_id: The aggrement_id (asset) to get the shell descriptor for.
     - :return: A JSON object containing the shell descriptor details.
    """

    dtr_handler = get_dtr_handler(dataplane_url, authorization)

    if aas_id:
        return dtr_handler.dtr_find_shell_descriptor(aas_id)
    
    response = dtr_handler.get_all_shells()
    if response is None:
        raise HTTPException(status_code=404, detail="No shell descriptors found.")
    return response