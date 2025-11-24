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

"""Policy validation utilities"""

from test_orchestrator.logging.log_manager import LoggingManager

logger = LoggingManager.get_logger(__name__)


def validate_policy(catalog_json, dct_type, framework_agreement):
    """Validates the usage policy in a catalog response.

    Returns a dict with keys: status, message, details
    """
    logger.info('validating policy')
    data_exchange_policy = {
        'odrl:leftOperand': {'@id': 'cx-policy:FrameworkAgreement'},
        'odrl:operator': {'@id': 'odrl:eq'},
        'odrl:rightOperand': framework_agreement}

    allowed_purposes = [
        'cx.core.legalRequirementForThirdparty:1',
        'cx.core.industrycore:1',
        'cx.core.qualityNotifications:1',
        'cx.core.digitalTwinRegistry:1',
        'cx.pcf.base:1',
        'cx.quality.base:1',
        'cx.dcm.base:1',
        'cx.puris.base:1',
        'cx.circular.dpp:1',
        'cx.circular.smc:1',
        'cx.circular.marketplace:1',
        'cx.circular.materialaccounting:1',
        'cx.bpdm.gate.upload:1',
        'cx.bpdm.gate.download:1',
        'cx.bpdm.pool:1',
        'cx.bpdm.vas.countryrisk:1',
        'cx.bpdm.vas.dataquality.upload:1',
        'cx.bpdm.vas.dataquality.download:1',
        'cx.bpdm.vas.bdv.upload:1',
        'cx.bpdm.vas.bdv.download:1',
        'cx.bpdm.vas.fpd.upload:1',
        'cx.bpdm.vas.fpd.download:1',
        'cx.bpdm.vas.swd.upload:1',
        'cx.bpdm.vas.swd.download:1',
        'cx.bpdm.vas.nps.upload:1',
        'cx.bpdm.vas.nps.download:1',
        'cx.ccm.base:1',
        'cx.bpdm.poolAll:1',
        'cx.logistics.base:1'
    ]

    policy_validation_outcome = False

    if 'dcat:dataset' in catalog_json:
        datasets = catalog_json['dcat:dataset']
        if not isinstance(datasets, list):
            datasets = [datasets]

        for element in datasets:
            if 'dct:type' in element:
                if isinstance(element['dct:type'], dict):
                    id_in_dct_type = element['dct:type'].get('@id')

                    if id_in_dct_type:
                        if element['dct:type']['@id'] == f"https://w3id.org/catenax/taxonomy#{dct_type}":
                            if 'odrl:hasPolicy' in element:
                                if 'odrl:permission' in element['odrl:hasPolicy']:
                                    if 'odrl:constraint' in element['odrl:hasPolicy']['odrl:permission']:
                                        spec_part = element['odrl:hasPolicy']['odrl:permission']['odrl:constraint']

                                        if isinstance(spec_part, dict):
                                            if 'odrl:and' in spec_part:
                                                if isinstance(spec_part['odrl:and'], list):
                                                    has_data_exchange = data_exchange_policy in spec_part['odrl:and']
                                                    has_allowed_purpose = any({
                                                        'odrl:leftOperand': {'@id': 'cx-policy:UsagePurpose'},
                                                        'odrl:operator': {'@id': 'odrl:eq'},
                                                        'odrl:rightOperand': purpose
                                                    } in spec_part['odrl:and'] for purpose in allowed_purposes)
                                                    if has_data_exchange and has_allowed_purpose:
                                                        policy_validation_outcome = True

    logger.info(f'Policy validation outcome: {policy_validation_outcome}')

    if policy_validation_outcome:
        return {'status': 'ok',
                'message': 'The usage policy that is used within the asset was successfully validated. ',
                'details': 'No further policy checks necessary'}

    return {'status': 'Warning',
            'message': 'The usage policy that is used within the asset is not accurate. ',
            'details': 'Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/'
                       'software-development-view/policies for troubleshooting.'}
