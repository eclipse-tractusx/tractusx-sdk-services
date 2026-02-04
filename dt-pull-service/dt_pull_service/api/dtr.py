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

from typing import Dict, Optional, List

from fastapi import APIRouter, Header, Depends, HTTPException
from dt_pull_service.auth import verify_auth

from dt_pull_service.dtr_helper import get_dtr_handler

router = APIRouter()


@router.get('/shell-descriptors/',
            response_model= List| Dict,
            dependencies=[Depends(verify_auth)])
async def shell_descriptors(dataplane_url: str,
                            aas_id: Optional[str] = '',
                            limit: Optional[int] = None,
                            authorization: str = Header(None)):
    """
    Retrieves the shell descriptors from the partner's DTR.

     - :param dataplane_url: The URL for getting the DTR handler.
     - :param limit: Optional limit on the number of shell descriptors returned.
     - :param aas_id: The aas_id (asset) to get the shell descriptor for.
     - :return: A JSON object containing the shell descriptor details.
    """

    dtr_handler = get_dtr_handler(dataplane_url, authorization)

    if aas_id:
        return dtr_handler.dtr_find_shell_descriptor(aas_id)

    response = dtr_handler.get_all_shells(limit=limit)

    if response is None or len(response) == 0:
        raise HTTPException(status_code=404, detail="No shell descriptors found.")

    return response


@router.post('/send-feedback/',
             response_model=Dict,
             dependencies=[Depends(verify_auth)])
async def send_feedback(data: Dict,
                        dataplane_url: str,
                        authorization: str = Header(None)):
    """
    Sends feedback to the partner's DTR.

     - :param dataplane_url: The URL for getting the DTR handler.
     - :param data: The status of the certificate validation, that needs to be posted
                    to the /companycertificate/status endpoint.
     - :return: The returning JSON contains information, if the feedback was accepted.
    """

    dtr_handler = get_dtr_handler(dataplane_url, authorization)

    return dtr_handler.send_feedback(data)


@router.post('/lookup/',
             response_model=Dict,
             dependencies=[Depends(verify_auth)])
async def lookup(dataplane_url: str,
                 data: list[dict],
                 authorization: str = Header(None)):
    """
    Performs a lookup request against the partner's Digital Twin Registry (DTR) via the dataplane.

    This endpoint receives a list of asset link dictionaries and forwards them to the DTR handler,
    which executes a POST request to the partner's `lookup/shellsByAssetLink` endpoint. The result
    is returned as a JSON object containing the matching shell descriptors.

    :param dataplane_url: The dataplane URL used to initialize the DTR handler for the partner.
    :param data: A list of dictionaries representing asset link information for the lookup.
    :param authorization: The Authorization header containing the partner DTR access token.
    :return: A JSON object containing the lookup results from the partner's DTR.
    :raises HTTPError: Raised if the lookup fails or the partner DTR returns a non‑200 response.
    """

    dtr_handler = get_dtr_handler(dataplane_url, authorization)

    return dtr_handler.lookup(data)
