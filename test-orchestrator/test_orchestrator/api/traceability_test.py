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
import logging

from fastapi import APIRouter, Depends

from test_orchestrator.auth import verify_auth
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.logging.log_manager import LoggingManager
from test_orchestrator.checks.request_catalog import get_catalog
from test_orchestrator.checks.policy_validation import validate_policy
from test_orchestrator.utils import init_negotiation, obtain_negotiation_state, get_data_address

router = APIRouter()
logger = LoggingManager.get_logger(__name__)


@router.post('/check',
             dependencies=[Depends(verify_auth)])
async def traceability_test(
        counter_party_address: str,
        counter_party_id: str
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
            'asset_id': 'qualityinvestigationnotification-receive'
        },
        {
            'dct_type_id': 'ReceiveQualityAlertNotification',
            'asset_id': 'qualityalertnotification-receipt'
        },
        {
            'dct_type_id': 'UpdateQualityInvestigationNotification',
            'asset_id': 'qualityinvestigationnotification-update'
        },
        {
            'dct_type_id': 'UpdateQualityAlertNotification',
            'asset_id': 'qualityalertnotification-update'
        }
    ]

    results = []

    for asset in data_assets:
        asset_result = {
            'asset_id': asset['asset_id'],
            'dct_type_id': asset['dct_type_id'],
            'status': 'success',
            'message': None
        }

        try:
            logger.info(f"Running data asset checks for {asset['asset_id']}")
            catalog_json = await get_catalog(
                counter_party_address=counter_party_address,
                counter_party_id=counter_party_id,
                operand_left="'http://purl.org/dc/terms/type'.'@id'",
                operand_right='https://w3id.org/catenax/taxonomy#' + asset['dct_type_id'],
            )
            policy_validation_outcome = validate_policy(catalog_json, asset['dct_type_id'], "traceability:1.0")
            if policy_validation_outcome.get('status') != 'ok':
                raise HTTPError(
                    Error.POLICY_VALIDATION_FAILED,
                    message='The usage policy that is used within the asset is not accurate. ',
                    details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                            'software-development-view/policies for troubleshooting.'
                )

            # After successful policy validation, initiate negotiation and obtain EDR data address
            negotiation = await init_negotiation(
                counter_party_address=counter_party_address,
                counter_party_id=counter_party_id,
                catalog_json=catalog_json,
                operand_right=asset['dct_type_id']
            )

            edr_state_id = negotiation.get('@id')

            await obtain_negotiation_state(
                counter_party_address=counter_party_address,
                counter_party_id=counter_party_id,
                edr_state_id=edr_state_id,
                operand_right=asset['dct_type_id']
            )

            edr_data_address = await get_data_address(
                counter_party_address=counter_party_address,
                counter_party_id=counter_party_id,
                edr_state_id=edr_state_id
            )

            endpoint = edr_data_address.get('endpoint')
            authorization = edr_data_address.get('authorization')
            logger.info(
                f"EDR data address for {asset['asset_id']} (type {asset['dct_type_id']}): "
                f"endpoint={endpoint}, authorization={authorization}")

            # TODO Call the endpoint and create the asset at the traceability app

            asset_result['message'] = 'Data asset check passed'

        except HTTPError as e:
            # If this is the first asset and the connector is unavailable, raise the error
            if asset == data_assets[0] and e.error_code == Error.CONNECTOR_UNAVAILABLE:
                raise HTTPError(
                    Error.CONNECTOR_UNAVAILABLE,
                    message="Connection to your connector was not successful.",
                    details="The testbed can't access the specified connector. Make sure the counter_party_address points " + \
                            "to the DSP endpoint of your connector and the counter_party_id is correct. Please check " + \
                            "https://eclipse-tractusx.github.io/docs-kits/kits/connector-kit/operation-view/ " + \
                            "for troubleshooting.")
            # For other errors, mark as failed but continue
            asset_result['status'] = 'failed'
            asset_result['message'] = f'Data asset check failed: {str(e)}'
            logger.error(f"Failed to check asset {asset['asset_id']}: {str(e)}")

        except Exception as e:
            asset_result['status'] = 'failed'
            asset_result['message'] = f'Unexpected error: {str(e)}'
            logger.error(f"Unexpected error checking asset {asset['asset_id']}: {str(e)}")

        results.append(asset_result)

    # Determine overall status
    failed_checks = [r for r in results if r['status'] == 'failed']
    overall_status = 'success' if not failed_checks else 'partial_success' if len(failed_checks) < len(
        results) else 'failed'

    return {
        'status': overall_status,
        'message': 'All data asset checks completed',
        'results': results
    }
