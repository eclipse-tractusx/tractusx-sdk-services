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

"""
Endpoints to run tests on the data returned by the DT Pull Service.

This module includes:
1. `shell-descriptors-test` endpoint to validate the shell descriptors JSON output.
2. `submodel-test` endpoint for validating the creation of a submodel.
"""


import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends
import httpx

from test_orchestrator import config
from test_orchestrator.auth import verify_auth
from test_orchestrator.request_handler import make_request
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.base_utils import get_dtr_access, fetch_submodel_info, submodel_schema_finder, submodel_validation
from test_orchestrator.validator import json_validator, schema_finder

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('/shell-descriptors-test/',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def shell_descriptors_test(
    counter_party_address: str,
    counter_party_id: str,
    operand_left: Optional[str] = 'http://purl.org/dc/terms/type',
    operator: Optional[str] = 'like',
    operand_right: Optional[str] ='%https://w3id.org/catenax/taxonomy#DigitalTwinRegistry%',
    policy_validation: Optional[bool] = None,
    timeout: int = 80):

    """
    This test case validates if a sample of digital twins registered in the digital twin registry (DTR)
    is according to specification.
    For this test case to execute successfully, there should be at least one digital twin registered in the DTR.
    The test is successful if the test-agent was able to perform the following steps:

    1.	Query for the digital twin registry (DTR) asset in the specified connector (counter_party_address).
    2.	Check for the correctness of all properties of the DTR asset.
    3.	Negotiate access to the DTR asset.
    4.	Access the DTR through the data plane of the connector.
    5.	Validate if the digital twins that are returned are according to specification.

     - :param counter_party_address: Address of the dsp endpoint of a connector
                                     (ends on api/v1/dsp for DSP version 2024-01).
     - :param counter_party_id: The identifier of the test subject that operates the connector.
                                Unitil at least Catena-X Release 25.09 that is the BPNL of the test subject.
     - :optional param operand_left: Specifies the left operand of the filter to search for the DTR asset.
                                     Correctly set per default.
     - :optional param operator: Specifies the operator between the left and right operands of the filter.
     - :optional param operand_right: Specifies the right operand of the filter to search for the DTR asset.
                                      Correctly set per default.
     - :return: A dictionary containing validation errors, if any.
    """

    (dtr_url, dtr_key, policy_validation_outcome, warnings) = await get_dtr_access(
        counter_party_address,
        counter_party_id,
        operand_left=operand_left,
        operator=operator,
        operand_right=operand_right,
        policy_validation=policy_validation,
        timeout=timeout
        )

    shell_descriptors = await make_request(
        'GET',
        f'{config.DT_PULL_SERVICE_ADDRESS}/dtr/shell-descriptors/',
        params={'dataplane_url': dtr_url, 'limit': 1},
        headers=get_dt_pull_service_headers(headers={'Authorization': dtr_key}),
        timeout=timeout)

    #Checking if shell_descriptors is not empty
    if 'result' not in shell_descriptors:
        raise HTTPError(
            Error.NO_SHELLS_FOUND,
            message=f"Response from the DTR was: {shell_descriptors} instead.",
            details="The DTR did not return any digital twins.")

    if len(shell_descriptors['result']) == 0:
        raise HTTPError(
            Error.NO_SHELLS_FOUND,
            message="The DTR did not return at least one digital twin.",
            details="Please check https://eclipse-tractusx.github.io/docs-kits/kits/digital-twin-kit/" +\
                " software-development-view/#registering-a-new-twin for troubleshooting")

    try:
        shelldesc_schema = schema_finder('shell_descriptors')
        shelldesc_validation_error = json_validator(shelldesc_schema, shell_descriptors)

    except Exception:
        raise HTTPError(
                    Error.UNKNOWN_ERROR,
                    message="An unknown error processing the shell descriptor occured.",
                    details="Please contact the testbed administrator.")

    return_message = {'message': 'Shell descriptors validation completed.',
                      'shell_validation_message': shelldesc_validation_error,
                      'policy_validation_message': policy_validation_outcome}

    if warnings:
        return_message['warnings'] = warnings

    return return_message


@router.get('/submodel-test/',
            dependencies=[Depends(verify_auth)])
async def submodel_test(counter_party_address: str,
                        counter_party_id: str,
                        semantic_id: str,
                        aas_id: str,
                        operand_left: Optional[str] = 'http://purl.org/dc/terms/type',
                        operator: Optional[str] = 'like',
                        operand_right: Optional[str] = '%https://w3id.org/catenax/taxonomy#DigitalTwinRegistry%',
                        policy_validation: Optional[bool] = None,
                        timeout: int = 80
                        ):
    """
    This test case fetches and validates data for a specific submodel of a digital twin identified by the aas_id
    (“id” of the digital twin) and the semantic_id.
    The test case returns successful if the test-agent was able eto perform the following steps:

    1.	Query for the digital twin registry (DTR) asset in the specified connector (counter_party_address).
    2.	Check for the correctness of all properties of the DTR asset.
    3.	Negotiate access to the DTR asset.
    4.	Access a specific digital twin through the data plane of the connector.
    5.	Filter out the relevant submodel descriptor based on the semantic_id
    6.	Negotiate access to the asset that’s specified in the submodel descriptor.
    7.	Retrieve the data based on the “href” of the submodel descriptor.
    8.	Validate the data against the aspect model from the Catena-X semantic hub based on the semantic_id.

     - :param counter_party_address: Address of the dsp endpoint of a connector
                                     (ends on api/v1/dsp for DSP version 2024-01).
     - :param counter_party_id: The identifier of the test subject that operates the connector.
                                Unitil at least Catena-X Release 25.09 that is the BPNL of the test subject.
     - :param semantic_id: The identifier of the Catena-X aspect model associated with the submodel descriptor.
                           The list of supported aspect models can be found in the Industry Core Standards
                           CX-0126 und CX-0127: https://catenax-ev.github.io/docs/standards. Must be of format
                           urn:samm:io.catenax.single_level_bom_as_planned:3.0.0#SingleLevelBomAsPlanned
     - :param aas_id: The identifier of a digital twin in the DTR. Called “id” in the shell descriptor. Must be unique.

     - :optional param operand_left: Specifies the left operand of the filter to search for the DTR asset.
                                     Correctly set per default.
     - :optional param operator: Specifies the operator between the left and right operands of the filter.
     - :optional param operand_right: Specifies the right operand of the filter to search for the DTR asset.
                                      Correctly set per default.
     - :return: A dictionary containing validation errors, if any.
    """

    # Gain access to the shell descriptors specific output
    (dtr_url_shell, dtr_key_shell, policy_validation_outcome, _) = await get_dtr_access(
        counter_party_address,
        counter_party_id,
        operand_left=operand_left,
        operand_right=operand_right,
        operator=operator,
        policy_validation=policy_validation,
        timeout=timeout)

    # Here we get the main catalog only for the global asset specifice by catenaXid
    try:
        shell_descriptors_spec = await make_request(
            'GET',
            f'{config.DT_PULL_SERVICE_ADDRESS}/dtr/shell-descriptors/',
            params={'dataplane_url': dtr_url_shell, 'aas_id': aas_id, 'limit': 1},
            headers=get_dt_pull_service_headers(headers={'Authorization': dtr_key_shell}),
            timeout=timeout)

    except HTTPError:
        raise HTTPError(
            Error.ASSET_ACCESS_FAILED,
            message='The asset that is specified in the subprotocol body can’t be accessed.' +\
                    'Make sure the connector hosting it is available and the asset is visible ' +\
                    'to the testbed connector',
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                    'software-development-view/digital-twins#edc-policies for troubleshooting.')

    if 'errors' in shell_descriptors_spec:
        raise HTTPError(
            Error.AAS_ID_NOT_FOUND,
            message=f'The AAS ID {aas_id} could not be found in the DTR. ' +\
                    'Make sure you passed the right AAS ID',
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                    'software-development-view/digital-twins#edc-policies for troubleshooting.')


    subm_validation_error = await submodel_validation(counter_party_id,
                                                      shell_descriptors_spec,
                                                      semantic_id)

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
                message=f'The submodel descriptor for semanticID {semantic_id} could not be found in the DTR. ' + \
                        'Make sure the submodel is registered accordingly and visible for the testbed BPNL',
                details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                        'software-development-view/digital-twins#edc-policies for troubleshooting.')

        submodel_info = fetch_submodel_info(correct_element, semantic_id)

        # Gain access to the submodel link
        (dtr_url_subm, dtr_key_subm, policy_validation_outcome_not_used, _) = await get_dtr_access(
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
                            message='Make sure your dataplane can resolve the request and that the href above ' + \
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

        subm_validation_error = json_validator(subm_schema, submodels)

        return {'message': 'Submodel validation completed.',
                'submodel_validation_message': subm_validation_error,
                'policy_validation_message': policy_validation_outcome}
