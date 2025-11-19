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
from typing import Any, Dict, Optional, List
import json
import json
from typing import Dict, Optional

import httpx

from test_orchestrator import config
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.checks.policy_validation import validate_policy
from test_orchestrator.checks.request_catalog import get_catalog
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.logging.log_manager import LoggingManager
from test_orchestrator.request_handler import make_request
from test_orchestrator.validator import json_validator, schema_finder

logger = LoggingManager.get_logger(__name__)


# pylint: disable=R1702, R0912
async def fetch_transfer_process(retries=5, delay=2, timeout: int = 80, **request_params):
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
                                      json=request_params['data'],
                                      headers=get_dt_pull_service_headers(),
                                      timeout=timeout)

        logger.info(f'Transfer process response: {response}')

        if response and isinstance(response, list) and len(response) > 0:
            return response

        if attempt < retries - 1:
            await asyncio.sleep(delay * (2 ** attempt))

    raise HTTPError(Error.DATA_TRANSFER_FAILED,
                    message='The submodel for the semanticID provided not be transferred. ' + \
                            'Make sure the href in the submodel descriptor point to the correct endpoint.',
                    details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                            'software-development-view/digital-twins#submodel-descriptors ' + \
                            'for troubleshooting.')


async def init_negotiation(counter_party_address: str,
                           counter_party_id: str,
                           catalog_json: dict,
                           operand_right: Optional[str] = None,
                           timeout: int = 80):
    """
    Initiate a contract negotiation using the DT Pull Service.

    Wrapped from get_dtr_access to provide a reusable step and clearer separation of concerns.
    Mirrors existing error handling by mapping any HTTPError from the request to CONTRACT_NEGOTIATION_FAILED.
    """
    try:
        return await make_request('POST',
                                  f'{config.DT_PULL_SERVICE_ADDRESS}/edr/init-negotiation/',
                                  params={'counter_party_address': counter_party_address,
                                          'counter_party_id': counter_party_id},
                                  json=catalog_json,
                                  headers=get_dt_pull_service_headers(),
                                  timeout=timeout)
    except HTTPError:
        raise HTTPError(
            Error.CONTRACT_NEGOTIATION_FAILED,
            message=f'The asset of type/id {operand_right} could not be negotiated. ' + \
                    'Check if the usage policy is according to the standard. Also check your connector logs.',
            details='Please check ' + \
                    'https://eclipse-tractusx.github.io/docs-kits/kits/digital-twin-kit/software-development-view/ ' + \
                    'for troubleshooting.')


async def get_dtr_access(counter_party_address: str,
                         counter_party_id: str,
                         operand_left: Optional[str] = None,
                         operator: Optional[str] = 'like',
                         operand_right: Optional[str] = None,
                         offset: Optional[int] = 0,
                         limit: Optional[int] = 10,
                         policy_validation: Optional[bool] = None,
                         timeout: int = 80):
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

    catalog_response = await get_catalog(
        counter_party_address=counter_party_address,
        counter_party_id=counter_party_id,
        operand_left=operand_left,
        operator=operator,
        operand_right=operand_right,
        offset=offset,
        limit=limit,
        timeout=timeout,
    )

    catalog_json = catalog_response["response_json"]
    logger.debug(f'Catalog JSON: {catalog_json}')

    # Validate result of the policy from the catalog if required
    policy_validation_outcome = validate_policy(catalog_json, "DigitalTwinRegistry", "DataExchangeGovernance:1.0")

    if policy_validation:
        if policy_validation_outcome['status'] != 'ok':
            raise HTTPError(
                Error.POLICY_VALIDATION_FAILED,
                message='The usage policy that is used within the asset is not accurate. ',
                details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/'
                        'digital-twin-kit/software-development-view/#usage-policies for troubleshooting.')

    negotiation = await init_negotiation(
        counter_party_address=counter_party_address,
        counter_party_id=counter_party_id,
        catalog_json=catalog_json,
        operand_right=operand_right,
        timeout=timeout
    )

    edr_state_id = negotiation.get('@id')

    await obtain_negotiation_state(
        counter_party_address=counter_party_address,
        counter_party_id=counter_party_id,
        edr_state_id=edr_state_id,
        operand_right=operand_right,
        timeout=timeout
    )

    edr_data_address = await get_data_address(
        counter_party_address=counter_party_address,
        counter_party_id=counter_party_id,
        edr_state_id=edr_state_id,
        timeout=timeout
    )

    return edr_data_address.get('endpoint'), edr_data_address.get('authorization'), policy_validation_outcome


async def obtain_negotiation_state(counter_party_address: str,
                                   counter_party_id: str,
                                   edr_state_id: str,
                                   operand_right: Optional[str] = None,
                                   timeout: int = 80):
    """
    Obtain the negotiation state after initiating a negotiation.

    Returns the negotiation state response when finalized; raises HTTPError for failures or non-finalized states.
    """
    try:
        response = await make_request(
                        'GET',
                        f'{config.DT_PULL_SERVICE_ADDRESS}/edr/negotiation-state/',
                        params={'counter_party_address': counter_party_address,
                                'counter_party_id': counter_party_id,
                                'state_id': edr_state_id},
                        headers=get_dt_pull_service_headers(),
                        timeout=timeout
        )
    except:
        raise HTTPError(
            Error.CONTRACT_NEGOTIATION_FAILED,
            message='Unknown Error - Check your connector logs for details.',
            details=f'Contract negotiation for asset of type/id {operand_right} failed.')

    # In case negotiation was not successful
    if response["state"] == "TERMINATED":
        error_message = await make_request('GET',
                                           f'{config.DT_PULL_SERVICE_ADDRESS}/edr/negotiation-result/',
                                           params={'counter_party_address': counter_party_address,
                                                   'counter_party_id': counter_party_id,
                                                   'state_id': edr_state_id},
                                           headers=get_dt_pull_service_headers(),
                                           timeout=timeout)
        raise HTTPError(
            Error.CONTRACT_NEGOTIATION_FAILED,
            message=f'Error Message: {json.dumps(error_message["errorDetail"])}',
            details=f'Contract negotiation for asset of type/id {operand_right} failed.')

    if response["state"] != "FINALIZED":
        raise HTTPError(
            Error.CONTRACT_NEGOTIATION_FAILED,
            message=f'Contract negotiation stuck in state {response["state"]}',
            details=f'Contract negotiation for asset of type/id {operand_right} could not be completed.')
    
    return response
  
async def get_data_address(counter_party_address: str,
                           counter_party_id: str,
                           edr_state_id: str,
                           timeout: int = 80):
    """
    Execute the transfer process query and fetch the EDR data address.

    This function wraps the two final steps of get_dtr_access:
    - fetch_transfer_process: query for transfer process by contractNegotiationId
    - GET /edr/data-address/: obtain endpoint and authorization by transfer_process_id

    Returns the full EDR data address payload as returned by the DT Pull Service.
    """
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
        data=data,
        timeout=timeout
    )
    transfer_process_id = transfer_process[0]['transferProcessId']

    edr_data_address = await make_request('GET',
                                          f'{config.DT_PULL_SERVICE_ADDRESS}/edr/data-address/',
                                          params={'counter_party_address': counter_party_address,
                                                  'counter_party_id': counter_party_id,
                                                  'transfer_process_id': transfer_process_id},
                                          headers=get_dt_pull_service_headers(),
                                          timeout=timeout)

    return (edr_data_address.get('endpoint'),
            edr_data_address.get('authorization'),
            policy_validation_outcome,
            warnings)


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
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                    'software-development-view/digital-twins#edc-policies for troubleshooting.')

    # Splitting subprotocolBody to obtain the correct parameters
    subprot_split = subprot_bod.split('=')

    if len(subprot_split) < 3:
        raise HTTPError(
            Error.SUBMODEL_DESCRIPTOR_MALFORMED,
            message=f'The submodel descriptor for semanticID {semantic_id} is malformed.',
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                    'software-development-view/digital-twins#edc-policies for troubleshooting.')

    subm_operandleft = 'https://w3id.org/edc/v0.0.1/ns/id'
    subm_operandright = subprot_split[1].split(';')[0]
    subm_counterparty = subprot_split[2]

    return (
        {'href': href,
         'subm_counterparty': subm_counterparty,
         'subm_operandleft': subm_operandleft,
         'subm_operandright': subm_operandright
         })


def validate_policy(
    catalog_json: Dict[str, Any],
    data_exchange_policy: Optional[Dict[str, Any]] = None,
    dtr_policy: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """Validates the usage policy in a catalog entry.
    """

    # Default policies if not passed in param
    data_exchange_policy = data_exchange_policy or {
        'odrl:leftOperand': {'@id': 'cx-policy:FrameworkAgreement'},
        'odrl:operator': {'@id': 'odrl:eq'},
        'odrl:rightOperand': 'DataExchangeGovernance:1.0'
    }

    dtr_policy = dtr_policy or {
        'odrl:leftOperand': {'@id': 'cx-policy:UsagePurpose'},
        'odrl:operator': {'@id': 'odrl:eq'},
        'odrl:rightOperand': 'cx.core.digitalTwinRegistry:1'
    }

    policy_warning =  {
        "status": "Warning",
        "message": (
            "The usage policy that is used within the asset is not accurate. "
        ),
        "details": (
            "Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/"
            "software-development-view/policies for troubleshooting."
        )
    }

    datasets = catalog_json.get("dcat:dataset", [])

    if not isinstance(datasets, list):
        return policy_warning

    for element in datasets:
        dct_type = element.get("dct:type", {})

        if dct_type.get("@id") != "https://w3id.org/catenax/taxonomy#DigitalTwinRegistry":
            continue

        has_policy = _find_case_insensitive(element, "odrl:hasPolicy")

        if not isinstance(has_policy, dict):
            continue

        permission = _find_case_insensitive(has_policy, "odrl:permission")

        if not isinstance(permission, dict):
            continue

        constraint = _find_case_insensitive(permission, "odrl:constraint")

        if constraint is None:
            continue

        # odrl:constraint is a list
        if isinstance(constraint, list):
            and_constraints: Optional[List[Any]] = constraint
        # odrl:constraint is an object with and list
        elif isinstance(constraint, dict):
            and_constraints = _find_case_insensitive(constraint, "odrl:and")
        else:
            continue

        if not isinstance(and_constraints, list):
            continue

        if data_exchange_policy in and_constraints and dtr_policy in and_constraints:
            return {
                "status": "ok",
                "message": "The usage policy that is used within the asset was successfully validated.",
                "details": "No further policy checks necessary"
            }

    return policy_warning


def _find_case_insensitive(container: Dict[str, Any], key: str) -> Any:
    """Returns value from container where the key matches case-insensitively.
    """

    target = key.lower()

    for k, v in container.items():
        if k.lower() == target:
            return v

    return None


async def submodel_validation(
    counter_party_id,
    shell_descriptors_spec: Dict,
    semantic_id: str
    ):
    """
    This method validates if a submodel descriptor and its corresponding submodel data
    retrieved from the digital twin registry (DTR) are according to specification.

    For this test case to execute successfully, there should be at least one submodel descriptor
    registered in the DTR for the given semantic ID.

    The test is successful if the test-agent was able to perform the following steps:

    1.  Verify that the shell descriptor specification contains at least one submodel descriptor.
    2.  Validate the shell descriptor structure against the expected schema.
    3.  Locate the correct submodel descriptor entry matching the semantic ID.
    4.  Retrieve submodel information and negotiate access to the partner's DTR.
    5.  Fetch the submodel data via the provided href link.
    6.  Validate the submodel data against the schema retrieved from the semantic ID.

     - :param counter_party_id: The identifier of the test subject that operates the connector.
                                Until at least Catena-X Release 25.09 this is the BPNL of the test subject.
     - :param shell_descriptors_spec: Dictionary containing shell descriptors returned by the DTR.
     - :optional param semantic_id: Semantic ID of the submodel to validate. If not provided,
                                    the first semantic ID in the descriptor list is used.
     - :return: A dictionary containing the result of the submodel validation.
                Example: {"status": "ok"} or {"status": "nok", "validation_errors": [...]}
    """

    #Checking if shell_descriptors is not empty
    if 'submodelDescriptors' not in shell_descriptors_spec:
        raise HTTPError(
            Error.NO_SHELLS_FOUND,
            message="The DTR did not return at least one digital twin.",
            details="Please check https://eclipse-tractusx.github.io/docs-kits/kits/digital-twin-kit/" +\
                " software-development-view/#registering-a-new-twin for troubleshooting")

    if len(shell_descriptors_spec['submodelDescriptors']) == 0:
        raise HTTPError(
            Error.NO_SHELLS_FOUND,
            message="The DTR did not return at least one digital twin.",
            details="Please check https://eclipse-tractusx.github.io/docs-kits/kits/digital-twin-kit/" +\
                " software-development-view/#registering-a-new-twin for troubleshooting")

    # Validating the smaller shell_descriptors output against a specific schema
    # to ensure the data we are using is accurate

    try:
        shelldesc_schema = schema_finder('shell_descriptors_spec')
        shelldesc_validation_error = json_validator(shelldesc_schema, shell_descriptors_spec)
    except Exception:
        raise HTTPError(
                    Error.UNKNOWN_ERROR,
                    message="An unknown error processing the shell descriptor occured.",
                    details="Please contact the testbed administrator.")

    if shelldesc_validation_error.get('status') == 'nok':
        raise HTTPError(Error.UNPROCESSABLE_ENTITY,
                message='Validation error',
                details={'validation_errors': shelldesc_validation_error})

    if shelldesc_validation_error.get('status') == 'ok':
        # Look inside the shell_descriptors output and find the correct href link
        submodels_list = shell_descriptors_spec['submodelDescriptors']

        correct_element = [
            item for item in submodels_list
            if item['semanticId']['keys'][0]['value'] == semantic_id
        ]

        if not correct_element:
            raise HTTPError(
                Error.SUBMODEL_DESCRIPTOR_NOT_FOUND,
                message=f'The submodel descriptor for semanticID {semantic_id} could not be found in the DTR. ' +\
                        'Make sure the submodel is registered accordingly and visible for the testbed BPNL',
                details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                        'software-development-view/digital-twins#edc-policies for troubleshooting.')

        submodel_info = fetch_submodel_info(correct_element, semantic_id)

        # Gain access to the submodel link
        (dtr_url_subm, dtr_key_subm, policy_validation_outcome_not_used) = await get_dtr_access(
            counter_party_address=submodel_info['subm_counterparty'],
            counter_party_id=counter_party_id,
            operand_left=submodel_info['subm_operandleft'],
            operand_right=submodel_info['subm_operandright'],
            policy_validation=False
            )

        # Run the submodels request pointed at the href link. To comply with industry core standards, the testbed appends $value.
        response = httpx.get(submodel_info['href']+'/$value', headers={'Authorization': dtr_key_subm})

        if response.status_code != 200:
            raise HTTPError(Error.UNPROCESSABLE_ENTITY,
                            message='Make sure your dataplane can resolve the request and that the href above ' +\
                                    'is according to the industry core specification, ending in /submodel.',
                            details=f'Failed to obtain the required submodel data for({submodel_info['href']}).')

        try:
            submodels = response.json()
        except Exception:
            raise HTTPError(
                Error.UNPROCESSABLE_ENTITY,
                message='The submodel response is not a valid json',
                details=f'Response: {response}')

        # Find the right schema and validate the submodels against it
        try:
            subm_schema_dict = submodel_schema_finder(semantic_id)
            subm_schema = subm_schema_dict['schema']
        except Exception:
            raise HTTPError(
                Error.SUBMODEL_VALIDATION_FAILED,
                message=f'The validation of the requested submodel for semanticID {semantic_id} failed: ' + \
                        'Could not find the submodel schema based on the semantic_id provided.',
                details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                        'software-development-view/aspect-models for troubleshooting and samples.')

        return json_validator(subm_schema, submodels)
