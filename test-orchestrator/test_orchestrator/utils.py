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

"""Utility methods
"""

import asyncio
from typing import Optional

import httpx

from test_orchestrator import config
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.request_handler import make_request

# pylint: disable=R1702, R0912
async def fetch_transfer_process(retries=5, delay=2, **request_params):
    """
    Retry mechanism for fetching the transfer process with exponential backoff.

    This function attempts to fetch the transfer process by sending POST requests
    to the DT Pull Service's transfer process endpoint. If no valid transfer process
    is retrieved after the specified number of retries, an HTTPError is raised.

    :param retries: Maximum number of retry attempts. Default is 5.
    :param delay: Initial delay (in seconds) between retries. Default is 2 seconds.
    :param request_params: Parameters to send in the POST request, including counterparty details and data.
    :raises HTTPError: If the transfer process cannot be retrieved after all retry attempts.
    :return: A list containing the transfer process details.
    """

    for attempt in range(retries):
        response = await make_request('POST',
                                      f'{config.DT_PULL_SERVICE_ADDRESS}/edr/transfer-process/',
                                      params={'counter_party_address': request_params['counter_party_address'],
                                              'counter_party_id': request_params['counter_party_id']},
                                      json=request_params['data'])

        if response and isinstance(response, list) and len(response) > 0:
            return response

        if attempt < retries - 1:
            await asyncio.sleep(delay * (2 ** attempt))

    raise HTTPError(Error.DATA_TRANSFER_FAILED,
                message='The submodel for the semanticID provided not be transferred. ' +\
                        'Make sure the href in the submodel descriptor point to the correct endpoint.',
                details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' +\
                        'software-development-view/digital-twins-development-view#submodel-descriptors ' +\
                        'for troubleshooting.')


async def get_dtr_access(counter_party_address: str,
                         counter_party_id: str,
                         operand_left: Optional[str] = None,
                         operator: Optional[str] = 'like',
                         operand_right: Optional[str] = None,
                         offset: Optional[int] = 0,
                         limit: Optional[int] = 10,
                         policy_validation: Optional[bool] = None):
    """
    Retrieves the Digital Twin Registry (DTR) access details.

    This function performs a sequence of API calls to:
    1. Query the catalog from the DT Pull Service.
    2. Initiate a negotiation for the retrieved catalog data.
    3. Check the negotiation state.
    4. Execute a transfer process to retrieve DTR access details.
    5. Fetch the endpoint and authorization information for DTR access.

    :param operand_left: The left operand for filtering the catalog query.
    :param operand_right: The right operand for filtering the catalog query.
    :param counter_party_address: The address of the counterparty's EDC.
    :param counter_party_id: The Business Partner Number for the transaction.
    :param offset: (Optional) The offset for pagination. Default is 0.
    :param limit: (Optional) The maximum number of results to retrieve. Default is 50.
    :return: A tuple containing the endpoint URL and authorization credentials for DTR access.
    """

    catalog_json = await make_request('GET',
                                      f'{config.DT_PULL_SERVICE_ADDRESS}/edr/get-catalog/',
                                      params={'operand_left': operand_left,
                                              'operand_right': operand_right,
                                              'operator': operator,
                                              'counter_party_address': counter_party_address,
                                              'counter_party_id': counter_party_id,
                                              'offset': offset,
                                              'limit': limit})

    # Validate result of the policy from the catalog if required
    policy_validation_outcome = validate_policy(catalog_json)

    if policy_validation:
        if policy_validation_outcome['status'] != 'ok':
            raise HTTPError(
                Error.POLICY_VALIDATION_FAILED,
                message='The usage policy that is used within the asset is not accurate. ',
                details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/' +\
                    'industry-core-kit/software-development-view/policies-development-view ' +\
                        'for troubleshooting.')

    try:
        init_negotiation = await make_request('POST',
                                              f'{config.DT_PULL_SERVICE_ADDRESS}/edr/init-negotiation/',
                                              params={'counter_party_address': counter_party_address,
                                                      'counter_party_id': counter_party_id},
                                              json=catalog_json)
    except HTTPError:
        raise HTTPError(
            Error.CONTRACT_NEGOTIATION_FAILED,
            message='The DTR asset could not be negotiated. ' + \
                    'Check if the usage policy is according to the standard. Also check your connector logs.',
            details='Please check ' + \
                    'https://eclipse-tractusx.github.io/docs-kits/kits/digital-twin-kit/software-development-view/ ' + \
                    'for troubleshooting.')

    edr_state_id = init_negotiation.get('@id')

    await make_request('GET',
                       f'{config.DT_PULL_SERVICE_ADDRESS}/edr/negotiation-state/',
                       params={'counter_party_address': counter_party_address,
                               'counter_party_id': counter_party_id,
                               'state_id': edr_state_id})

    data = {
        '@context': {'@vocab': 'https://w3id.org/edc/v0.0.1/ns/'},
        '@type': 'QuerySpec',
        'filterExpression': [{
            'operandLeft': 'contractNegotiationId',
            'operator': '=',
            'operandRight': edr_state_id
        }]
    }

    transfer_process = await fetch_transfer_process(
        counter_party_address=counter_party_address,
        counter_party_id=counter_party_id,
        data=data
    )
    transfer_process_id = transfer_process[0]['transferProcessId']

    edr_data_address = await make_request('GET',
                                          f'{config.DT_PULL_SERVICE_ADDRESS}/edr/data-address/',
                                          params={'counter_party_address': counter_party_address,
                                                  'counter_party_id': counter_party_id,
                                                  'transfer_process_id': transfer_process_id})

    return edr_data_address.get('endpoint'), edr_data_address.get('authorization'), policy_validation_outcome


def submodel_schema_finder(
        semantic_id,
        link_core: Optional[str] = 'https://raw.githubusercontent.com/eclipse-tractusx/sldt-semantic-models/main/'):
    """
    Function to facilitate the validation of the submodel output by retrieving the correct schema
    based on the semantic_id provided by the user
    """

    split_string = semantic_id.split(':')

    if len(split_string) < 4:
        raise HTTPError(
            Error.UNPROCESSABLE_ENTITY,
            message='The semanticID provided does not follow the correct structure',
            details={'subprotocolBody': semantic_id}
            )

    loc_elements = split_string[3].split('#')
    schema_link = link_core + split_string[2] + '/' + loc_elements[0] + '/gen/' + loc_elements[1] + '-schema.json'

    # Now we can use the link to pull in the correct schema.
    response = httpx.get(schema_link)

    if response.status_code != 200:
        raise HTTPError(
            Error.UNPROCESSABLE_ENTITY,
            message='Failed to obtain the required schema',
            details={'schema link': schema_link}
        )

    try:
        schema = response.json()
    except Exception:
        raise HTTPError(
            Error.UNPROCESSABLE_ENTITY,
            message='The schema obtained is not a valid json',
            details={'schema link': schema_link}
            )

    return {'status': 'ok',
            'message': 'Submodel validation schema retrieved successfully',
            'schema': schema}


def fetch_submodel_info(correct_element, semantic_id):
    """
    This function parses a previously identified part of the shell_descriptors output +\
    to identify the parameters needed to obtain a json containing submodel descriptors.
    """
    try:
        href = correct_element[0]['endpoints'][0]['protocolInformation']['href']
        subprot_bod = correct_element[0]['endpoints'][0]['protocolInformation']['subprotocolBody']
    except (KeyError, IndexError):
        raise HTTPError(
            Error.SUBMODEL_DESCRIPTOR_MALFORMED,
            message=f'The submodel descriptor for semanticID {semantic_id} is malformed.',
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/' +\
                    'industry-core-kit/software-development-view/digital-twins-development-view' +\
                    '#conventions-for-creating-digital-twins for troubleshooting.')

    # Splitting subprotocolBody to obtain the correct parameters
    subprot_split = subprot_bod.split('=')

    if len(subprot_split) < 3:
        raise HTTPError(
            Error.SUBMODEL_DESCRIPTOR_MALFORMED,
            message=f'The submodel descriptor for semanticID {semantic_id} is malformed.',
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/' +\
                    'industry-core-kit/software-development-view/digital-twins-development-view' +\
                    '#conventions-for-creating-digital-twins for troubleshooting.')

    subm_operandleft = 'https://w3id.org/edc/v0.0.1/ns/id'
    subm_operandright = subprot_split[1].split(';')[0]
    subm_counterparty = subprot_split[2]

    return (
        {'href': href,
         'subm_counterparty': subm_counterparty,
         'subm_operandleft': subm_operandleft,
         'subm_operandright': subm_operandright
         })

def validate_policy(catalog_json):
    """Validates the usage policy"""

    data_exchange_policy = {
        'odrl:leftOperand': {'@id': 'cx-policy:FrameworkAgreement'},
        'odrl:operator': {'@id': 'odrl:eq'},
        'odrl:rightOperand': 'DataExchangeGovernance:1.0'}

    dtr_policy = {
        'odrl:leftOperand': {'@id': 'cx-policy:UsagePurpose'},
        'odrl:operator': {'@id': 'odrl:eq'},
        'odrl:rightOperand': 'cx.core.digitalTwinRegistry:1'}

    policy_validation_outcome = False

    if 'dcat:dataset' in catalog_json:
        if isinstance(catalog_json['dcat:dataset'], list):
            for element in catalog_json['dcat:dataset']:
                if 'dct:type' in element:
                    if isinstance(element['dct:type'], dict):
                        id_in_dct_type = element['dct:type'].get('@id')

                        if id_in_dct_type:
                            if element['dct:type']['@id'] == 'https://w3id.org/catenax/taxonomy#DigitalTwinRegistry':
                                if 'odrl:hasPolicy' in element:
                                    if 'odrl:permission' in element['odrl:hasPolicy']:
                                        if 'odrl:constraint' in element['odrl:hasPolicy']['odrl:permission']:
                                            spec_part = element['odrl:hasPolicy']['odrl:permission']['odrl:constraint']

                                            if isinstance(spec_part, dict):
                                                if 'and' in spec_part:
                                                    if isinstance(spec_part['and'], list):
                                                        if data_exchange_policy in spec_part['and'] and \
                                                          dtr_policy in spec_part['and']:
                                                            policy_validation_outcome = True

    if policy_validation_outcome:
        return {'status': 'ok',
                'message': 'The usage policy that is used within the asset was successfully validated. ',
                'details': 'No further policy checks necessary'}

    return {'status': 'Warning',
            'message': 'The usage policy that is used within the asset is not accurate. ',
            'details': 'Please check https://eclipse-tractusx.github.io/docs-kits/kits/' +\
                'industry-core-kit/software-development-view/policies-development-view ' +\
                    'for troubleshooting.'}
