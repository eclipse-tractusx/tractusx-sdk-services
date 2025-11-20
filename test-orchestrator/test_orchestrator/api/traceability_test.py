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
Provide FastAPI endpoints for data asset checks.

"""

from fastapi import APIRouter, Depends

from test_orchestrator import config
from test_orchestrator.auth import verify_auth
from test_orchestrator.checks.create_notification import (
    qualitynotification_receive,
    qualitynotification_update,
)
from test_orchestrator.checks.policy_validation import validate_policy
from test_orchestrator.checks.catalog_version_validation import validate_catalog_version
from test_orchestrator.checks.request_catalog import get_catalog
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.logging.log_manager import LoggingManager
from test_orchestrator.utils import init_negotiation, obtain_negotiation_state, get_data_address

router = APIRouter()
logger = LoggingManager.get_logger(__name__)


@router.post('/check',
             dependencies=[Depends(verify_auth)])
async def traceability_test(
        counter_party_address: str,
        counter_party_id: str,
        job_id: str,
        asset_id: str,
):
    """
    Execute data asset checks for all Quality Notification API data assets.
    Call dt-pull-service to get each data asset and verify it exists.
    JSON response should have exactly one field.

    """
    # Define data assets with their DCT type IDs and asset IDs
    data_assets = [
        {
            'dct_type_id': 'ReceiveQualityInvestigationNotification',
            'asset_id': 'qualityinvestigationnotification-receive',
            'notificationType': 'Traceability-QualityNotification-Investigation:2.0.0'
        },
        {
            'dct_type_id': 'ReceiveQualityAlertNotification',
            'asset_id': 'qualityalertnotification-receipt',
            'notificationType': 'Traceability-QualityNotification-Alert:2.0.0'
        },
        {
            'dct_type_id': 'UpdateQualityInvestigationNotification',
            'asset_id': 'qualityinvestigationnotification-update',
            'notificationType': 'Traceability-QualityNotification-Investigation:2.0.0'
        },
        {
            'dct_type_id': 'UpdateQualityAlertNotification',
            'asset_id': 'qualityalertnotification-update',
            'notificationType': 'Traceability-QualityNotification-Alert:2.0.0'
        }
    ]

    results = []

    for asset in data_assets:
        asset_result = {
            'asset_id': asset['asset_id'],
            'dct_type_id': asset['dct_type_id'],
            'status': 'success',
            'message': None,
            'steps': []
        }

        def add_step(name: str, status: str, message: str | None = None, details: str | None = None):
            step = {'step': name, 'status': status}
            if message is not None:
                step['message'] = message
            if details is not None:
                step['details'] = details
            asset_result['steps'].append(step)

        proceed = True

        # Step 1: Get catalog
        try:
            logger.info(f"Running data asset checks for {asset['asset_id']}")
            catalog_response = await get_catalog(
                counter_party_address=counter_party_address,
                counter_party_id=counter_party_id,
                operand_left="'http://purl.org/dc/terms/type'.'@id'",
                operand_right='https://w3id.org/catenax/taxonomy#' + asset['dct_type_id'],
            )
            # Prefer downstream dt-pull-service request/response if provided; fallback to local TO call metadata
            dtps_body = catalog_response.get('response_json', {}) if isinstance(catalog_response, dict) else {}
            details_req = (dtps_body or {}).get('request') or catalog_response.get('request')
            details_res = (dtps_body or {}).get('response') or catalog_response.get('response')
            add_step('get_catalog', 'success', details={'request': details_req, 'response': details_res})
        except HTTPError as e:
            asset_result['status'] = 'failed'
            add_step('get_catalog', 'failed', str(e), getattr(e, 'details', None))
            proceed = False
        except Exception as e:
            asset_result['status'] = 'failed'
            add_step('get_catalog', 'failed', f'Unexpected error: {e}')
            proceed = False

        if not proceed:
            results.append(asset_result)
            continue

        # Step 2: Validate policy
        try:
            logger.info(f"Validating policy for {asset['asset_id']}")
            policy_validation_outcome = validate_policy(catalog_response['response_json'], asset['dct_type_id'], "traceability:1.0")
            if policy_validation_outcome.get('status') != 'ok':
                raise HTTPError(
                    Error.POLICY_VALIDATION_FAILED,
                    message='The usage policy that is used within the asset is not accurate. ',
                    details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' +
                            'software-development-view/policies for troubleshooting.'
                )
            add_step('validate_policy', 'success')
        except HTTPError as e:
            asset_result['status'] = 'failed'
            add_step('validate_policy', 'failed', str(e), getattr(e, 'details', None))
            results.append(asset_result)
            continue
        except Exception as e:
            asset_result['status'] = 'failed'
            add_step('validate_policy', 'failed', f'Unexpected error: {e}')
            results.append(asset_result)
            continue

        # Step 3: Validate catalog version (https://w3id.org/catenax/ontology/common#version == 2.0)
        try:
            logger.info(f"Validating catalog version for {asset['asset_id']}")
            catalog_json = catalog_response.get('response_json', {}) if isinstance(catalog_response, dict) else {}
            version_check = validate_catalog_version(catalog_json, asset['dct_type_id'], '2.0')
            if version_check.get('status') != 'ok':
                raise HTTPError(
                    Error.UNPROCESSABLE_ENTITY,
                    message=version_check.get('message', 'Invalid API version in catalog dataset.'),
                    details=version_check.get('details')
                )
            add_step('validate_catalog_version', 'success')
        except HTTPError as e:
            asset_result['status'] = 'failed'
            add_step('validate_catalog_version', 'failed', str(e), getattr(e, 'details', None))
            results.append(asset_result)
            continue
        except Exception as e:
            asset_result['status'] = 'failed'
            add_step('validate_catalog_version', 'failed', f'Unexpected error: {e}')
            results.append(asset_result)
            continue

        # Step 4: Initiate negotiation
        try:
            logger.info(f"Initiate negotiation for {asset['asset_id']}")
            negotiation = await init_negotiation(
                counter_party_address=counter_party_address,
                counter_party_id=counter_party_id,
                catalog_json=catalog_response['response_json'],
                operand_right=asset['dct_type_id']
            )
            # Prefer downstream dt-pull-service request/response if provided; fallback to local TO call metadata
            n_body = negotiation.get('response_json', {}) if isinstance(negotiation, dict) else {}
            n_req = (n_body or {}).get('request') or (negotiation.get('request') if isinstance(negotiation, dict) else None)
            n_res = (n_body or {}).get('response') or (negotiation.get('response') if isinstance(negotiation, dict) else None)
            add_step('init_negotiation', 'success', details={'request': n_req, 'response': n_res})
        except HTTPError as e:
            asset_result['status'] = 'failed'
            add_step('init_negotiation', 'failed', str(e), getattr(e, 'details', None))
            results.append(asset_result)
            continue
        except Exception as e:
            asset_result['status'] = 'failed'
            add_step('init_negotiation', 'failed', f'Unexpected error: {e}')
            results.append(asset_result)
            continue

        # Step 5: Obtain negotiation state
        try:
            logger.info(f"Obtain negotiation state for {asset['asset_id']}")
            # Support both wrapper ({request,response,response_json}) and plain JSON
            n_body = negotiation.get('response_json', negotiation) if isinstance(negotiation, dict) else negotiation
            edr_state_id = n_body.get('@id')
            state = await obtain_negotiation_state(
                counter_party_address=counter_party_address,
                counter_party_id=counter_party_id,
                edr_state_id=edr_state_id,
                operand_right=asset['dct_type_id']
            )
            # dt-pull-service negotiation-state injects request/response into its JSON body; prefer those
            s_req = state.get('request') if isinstance(state, dict) else None
            s_res = state.get('response') if isinstance(state, dict) else None
            add_step('obtain_negotiation_state', 'success', details={'request': s_req, 'response': s_res})
        except HTTPError as e:
            asset_result['status'] = 'failed'
            add_step('obtain_negotiation_state', 'failed', str(e), getattr(e, 'details', None))
            results.append(asset_result)
            continue
        except Exception as e:
            asset_result['status'] = 'failed'
            add_step('obtain_negotiation_state', 'failed', f'Unexpected error: {e}')
            results.append(asset_result)
            continue

        # Step 6: Get EDR data address
        try:
            logger.info(f"Get EDR data address for {asset['asset_id']}")
            edr_data_address = await get_data_address(
                counter_party_address=counter_party_address,
                counter_party_id=counter_party_id,
                edr_state_id=edr_state_id
            )
            # Support both wrapper ({request,response,response_json}) and plain JSON
            da_body = edr_data_address.get('response_json', edr_data_address) if isinstance(edr_data_address, dict) else edr_data_address
            endpoint = da_body.get('endpoint') if isinstance(da_body, dict) else None
            authorization = da_body.get('authorization') if isinstance(da_body, dict) else None
            logger.info(
                f"EDR data address for {asset['asset_id']} (type {asset['dct_type_id']}): "
                f"endpoint={endpoint}, authorization={authorization}")
            # Prefer dt-pull-service provided request/response within JSON body; fallback to wrapper metadata
            da_req = (da_body or {}).get('request') if isinstance(da_body, dict) else None
            da_res = (da_body or {}).get('response') if isinstance(da_body, dict) else None
            if not da_req and isinstance(edr_data_address, dict):
                da_req = edr_data_address.get('request')
            if not da_res and isinstance(edr_data_address, dict):
                da_res = edr_data_address.get('response')
            add_step('get_data_address', 'success', details={'request': da_req, 'response': da_res})
        except HTTPError as e:
            asset_result['status'] = 'failed'
            add_step('get_data_address', 'failed', str(e), getattr(e, 'details', None))
            results.append(asset_result)
            continue
        except Exception as e:
            asset_result['status'] = 'failed'
            add_step('get_data_address', 'failed', f'Unexpected error: {e}')
            results.append(asset_result)
            continue

        # Step 7: Invoke notification operation based on the asset type
        dct_type_lower = asset['dct_type_id'].lower()
        step_name = None
        try:
            if 'receive' in dct_type_lower:
                step_name = 'invoke_receive'
                response = await qualitynotification_receive(
                    endpoint=endpoint,
                    authorization=authorization,
                    notification_type=asset['notificationType'],
                    job_id=job_id,
                    sender_bpn=f'{config.SENDER_BPN}',
                    receiver_bpn=counter_party_id,
                    asset_id=asset_id,
                )
                asset_result['message'] = "Receive invoked successfully"
                r_req = response.get('request') if isinstance(response, dict) else None
                r_res = response.get('response') if isinstance(response, dict) else None
                add_step('invoke_receive', 'success', details={'request': r_req, 'response': r_res})
            elif 'update' in dct_type_lower:
                step_name = 'invoke_update'
                response = await qualitynotification_update(
                    endpoint=endpoint,
                    authorization=authorization,
                    notification_type=asset['notificationType'],
                    job_id=job_id,
                    sender_bpn=f'{config.SENDER_BPN}',
                    receiver_bpn=counter_party_id,
                )
                asset_result['message'] = "Update invoked successfully"
                u_req = response.get('request') if isinstance(response, dict) else None
                u_res = response.get('response') if isinstance(response, dict) else None
                add_step('invoke_update', 'success', details={'request': u_req, 'response': u_res})
            else:
                asset_result['message'] = 'No matching operation for asset type'
                add_step('invoke_operation', 'skipped', 'No matching operation for asset type')
        except HTTPError as e:
            asset_result['status'] = 'failed'
            add_step(step_name or 'invoke_operation', 'failed', str(e), getattr(e, 'details', None))
        except Exception as inner_e:
            asset_result['status'] = 'failed'
            add_step(step_name or 'invoke_operation', 'failed', 'Notification call failed', str(inner_e))

        results.append(asset_result)

    # Determine overall status
    failed_checks = [r for r in results if r['status'] == 'failed']
    overall_status = 'success' if not failed_checks else 'partial_success' if len(failed_checks) < len(
        results) else 'failed'

    return {
        'status': overall_status,
        'message': 'CX-0125 Traceability checks completed',
        'results': results
    }
