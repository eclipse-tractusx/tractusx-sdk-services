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

"""API endpoints for EDR
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter
from fastapi import Request, Depends, HTTPException
from dt_pull_service.auth import verify_auth

from dt_pull_service.edr_helper import get_edr_handler

router = APIRouter()
logger = logging.getLogger(__name__)

import requests


@router.get('/get-catalog/',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def get_catalog(counter_party_address: str,
                      counter_party_id: str,
                      operand_left: Optional[str] = None,
                      operand_right: Optional[str] = None,
                      operator: Optional[str] = 'like',
                      offset: Optional[int] = 0,
                      limit: Optional[int] = 50
                      ):
    """
    Retrieves the catalog JSON for the given query parameters.

     - :param operand_left: The left operand for filtering the catalog.
     - :param operand_right: The right operand for filtering the catalog.
     - :param operator: The operator for filtering the catalog, default is 'like'.
     - :param offset: The first element of the catalog to be returned.
     - :param limit: The amount of elements the catalog should return.
     - :param counter_party_address: The address of the counterparty's EDC.
     - :param counter_party_id: The Business Partner Number of the counterparty.
     - :return: A JSON object containing the catalog information.
    """

    edr_handler = get_edr_handler(counter_party_id, counter_party_address)

    catalog_json = edr_handler.query_catalog_json(
        prop=operand_left,
        value=operand_right,
        operator=operator,
        offset=offset,
        limit=limit
    )

    return catalog_json


@router.post('/init-negotiation/',
             response_model=Dict,
             dependencies=[Depends(verify_auth)])
async def init_negotiation(catalog_json: Dict,
                           counter_party_address: str,
                           counter_party_id: str):
    """
    Initiates negotiation based on the provided catalog JSON.

     - :param catalog_json: The catalog JSON containing asset information.
     - :param counter_party_address: The address of the counterparty's EDC.
     - :param counter_party_id: The Business Partner Number of the counterparty.
     - :return: A JSON object containing the negotiation details.
    """

    edr_handler = get_edr_handler(counter_party_id, counter_party_address)

    [edr_offer_id,
    edr_asset_id,
    edr_permission,
    edr_prohibition,
    edr_obligation] = edr_handler.query_catalog(catalog_json=catalog_json)

    initiate_edr_negotiate_json = edr_handler.initiate_edr_negotiate(edr_offer_id,
                                                                     edr_asset_id,
                                                                     edr_permission,
                                                                     edr_prohibition,
                                                                     edr_obligation)

    return initiate_edr_negotiate_json


@router.get('/negotiation-state/',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def negotiation_state(state_id: str,
                            counter_party_address: str,
                            counter_party_id: str):
    """
    Retrieves the state of the ongoing negotiation.

     - :param state_id: The unique identifier for the negotiation state.
     - :param counter_party_address: The address of the counterparty's EDC.
     - :param counter_party_id: The Business Partner Number of the counterparty.
     - :return: A JSON object containing the current state of the negotiation.
    """

    edr_handler = get_edr_handler(counter_party_id, counter_party_address)
    state_json = edr_handler.check_edr_negotiate_state(state_id)

    return state_json

@router.get('/negotiation-result/',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def negotiation_result(state_id: str,
                            counter_party_address: str,
                            counter_party_id: str):
    """
    Retrieves the state of the ongoing negotiation.

     - :param state_id: The unique identifier for the negotiation state.
     - :param counter_party_address: The address of the counterparty's EDC.
     - :param counter_party_id: The Business Partner Number of the counterparty.
     - :return: A JSON object containing the current state of the negotiation.
    """

    edr_handler = get_edr_handler(counter_party_id, counter_party_address)
    negotiation_result = edr_handler.check_edr_negotiation_result(state_id)

    return negotiation_result

@router.post('/transfer-process/',
             response_model=List[Dict],
             dependencies=[Depends(verify_auth)])
async def transfer_process(data: Dict,
                           counter_party_address: str,
                           counter_party_id: str):
    """
    Initiates and retrieves the transfer process.

     - :param data: The JSON data containing transfer specifications.
     - :param counter_party_address: The address of the counterparty's EDC.
     - :param counter_party_id: The Business Partner Number of the counterparty.
     - :return: A list of JSON objects representing the transfer process details.
    """

    edr_handler = get_edr_handler(counter_party_id, counter_party_address)

    transfer_process_json:requests.Response = edr_handler.edc_client.edrs.get_all(json=data,
                                                                proxies=edr_handler.proxies)

    return transfer_process_json.json()


@router.get('/data-address/',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def edr_data_address(transfer_process_id: str,
                           counter_party_address: str,
                           counter_party_id: str):
    """
    Retrieves the data address for the given transfer process ID.

     - :param transfer_process_id: The unique identifier for the transfer process.
     - :param counter_party_address: The address of the counterparty's EDC.
     - :param counter_party_id: The Business Partner Number of the counterparty.
     - :return: A JSON object containing the EDR data address.
    """

    edr_handler = get_edr_handler(counter_party_id, counter_party_address)
    edr_data_address_json:requests.Response = edr_handler.edc_client.edrs.get_data_address(transfer_process_id,
                                                                         params={"auto_refresh": "true"},
                                                                         proxies=edr_handler.proxies)

    return edr_data_address_json.json()
