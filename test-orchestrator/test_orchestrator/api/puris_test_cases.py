import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends
from test_orchestrator.auth import verify_auth
import httpx

from test_orchestrator import config
from test_orchestrator.puris_specified_validations import role_validator
from test_orchestrator.puris_specified_validations.policy_validation import validate_puris_policy
from test_orchestrator.puris_specified_validations.role_validator import validate_role, check_submodel_direction_value
from test_orchestrator.request_handler import make_request
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.utils import get_dtr_access, fetch_submodel_info, submodel_schema_finder
from test_orchestrator.validator import json_validator, schema_finder

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get('/shell-descriptors-test/',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def shell_descriptors_test(
        counter_party_address: str,
        counter_party_id: str,
        partner_role: str,
        aas_id: str,
        operand_left: Optional[str] = 'http://purl.org/dc/terms/type',
        operator: Optional[str] = 'like',
        operand_right: Optional[str] ='%https://w3id.org/catenax/taxonomy#DigitalTwinRegistry%',
        policy_validation: Optional[bool] = None,
        timeout: int = 80):

    (dtr_url, dtr_key, policy_validation_outcome) = await get_dtr_access(
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
        params={'dataplane_url': dtr_url, 'aas_id': aas_id, 'limit': 1},
        headers=get_dt_pull_service_headers(headers={'Authorization': dtr_key}),
        timeout=timeout)


    schema = schema_finder('shell_descriptors_spec', 'puris')
    validation_error = json_validator(schema, shell_descriptors)
    role_validation = validate_role(shell_descriptors, partner_role)

    return {'status': 'ok',
            'message': 'Shell descriptors validation completed successfully',
            'validation_message': validation_error,
            'partner_role_validation_message: ': role_validation,
            'policy_validation_message': policy_validation_outcome}


@router.get('/submodel-test/',
            dependencies=[Depends(verify_auth)])
async def submodel_test(counter_party_address: str,
                        counter_party_id: str,
                        semantic_id: str,
                        aas_id: str,
                        partner_role: Optional[str] = None,
                        submodel_asset_id: Optional[str] = None,
                        operand_left: Optional[str] = 'http://purl.org/dc/terms/type',
                        operator: Optional[str] = 'like',
                        operand_right: Optional[str] = '%https://w3id.org/catenax/taxonomy#DigitalTwinRegistry%',
                        policy_validation: Optional[bool] = None,
                        timeout: int = 80
                        ):

    (dtr_url_shell, dtr_key_shell, policy_validation_outcome) = await get_dtr_access(
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
            message='The asset that is specified in the subprotocol body can’t be accessed.' + \
                    'Make sure the connector hosting it is available and the asset is visible ' + \
                    'to the testbed connector',
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/puris-kit/' + \
                    '/software-development-view/#policies for troubleshooting.')

    if 'errors' in shell_descriptors_spec:
        raise HTTPError(
            Error.AAS_ID_NOT_FOUND,
            message=f'The AAS ID {aas_id} could not be found in the DTR. ' + \
                    'Make sure you passed the right AAS ID',
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/puris-kit/' + \
                    'software-development-view/#policies for troubleshooting.')

    #Checking if shell_descriptors is not empty
    if 'submodelDescriptors' not in shell_descriptors_spec:
        raise HTTPError(
            Error.NO_SHELLS_FOUND,
            message="The DTR did not return at least one digital twin.",
            details="Please check https://eclipse-tractusx.github.io/docs-kits/kits/digital-twin-kit/" + \
                    " software-development-view/#registering-a-new-twin for troubleshooting")

    if len(shell_descriptors_spec['submodelDescriptors']) == 0:
        raise HTTPError(
            Error.NO_SHELLS_FOUND,
            message="The DTR did not return at least one digital twin.",
            details="Please check https://eclipse-tractusx.github.io/docs-kits/kits/digital-twin-kit/" + \
                    " software-development-view/#registering-a-new-twin for troubleshooting")

    # Validating the smaller shell_descriptors output against a specific schema
    # to ensure the data we are using is accurate
    try:
        shelldesc_schema = schema_finder('shell_descriptors_spec', 'puris')
        shelldesc_validation_error = json_validator(shelldesc_schema, shell_descriptors_spec)
    except Exception:
        raise HTTPError(
            Error.ASSET_NOT_FOUND,
            message='The DTR asset could not be found in the specified connector. ' + \
                    'It might be missing or misconfigured.',
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/digital-twin-kit/' + \
                    'software-development-view/#digital-twin-registry-as-edc-data-asset for troubleshooting. ' + \
                    f'Furthermore, validate if the Access Policy allows access for the Testbed-BPNL {counter_party_id}')

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
                details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/puris-kit/' + \
                        'software-development-view/#policies for troubleshooting.')

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
                            message=f'Make sure your dataplane can resolve the request and that the href above ' + \
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
                details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/puris-kit/' + \
                        'software-development-view/aspect-models for troubleshooting and samples.')

        subm_validation_error = json_validator(subm_schema, submodels)

        puris_policy_validation_outcome = 'The validation of the submodel policy was not performed. Enter the corresponding asset id.'
        if submodel_asset_id is not None:
            puris_policy_validation_outcome = await validate_puris_policy(submodel_asset_id, counter_party_address, counter_party_id)

        submodel_value_check = 'For the given submodel is no verification of the values needed.'
        split_string = semantic_id.split(':')
        aspect_model = split_string[2]
        if aspect_model == 'io.catenax.item_stock' or aspect_model == 'io.catenax.days_of_supply':
            submodel_value_check = check_submodel_direction_value(partner_role, aspect_model, submodels)


        return {'status': 'ok',
                'message': 'Submodel validation completed successfully',
                'subm_validation_message': subm_validation_error,
                'subm_value_validation_message': submodel_value_check,
                'puris_subm_policy_message': puris_policy_validation_outcome,
                'policy_validation_message': policy_validation_outcome}