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

import json
from pathlib import Path

import pytest

from test_orchestrator.base_utils import validate_policy


def build_catalog(usage_purpose: str = None, include_data_exchange: bool = True, asset_type: str = 'https://w3id.org/catenax/taxonomy#DigitalTwinRegistry', and_structure='list'):
    data_exchange_policy = {
        'odrl:leftOperand': {'@id': 'cx-policy:FrameworkAgreement'},
        'odrl:operator': {'@id': 'odrl:eq'},
        'odrl:rightOperand': 'DataExchangeGovernance:1.0'
    }

    constraints = []
    if include_data_exchange:
        constraints.append(data_exchange_policy)

    if usage_purpose is not None:
        constraints.append({
            'odrl:leftOperand': {'@id': 'cx-policy:UsagePurpose'},
            'odrl:operator': {'@id': 'odrl:eq'},
            'odrl:rightOperand': usage_purpose
        })

    # Shape the 'and' structure as required for specific malformed scenarios
    if and_structure == 'list':
        and_value = constraints
    elif and_structure == 'dict':
        and_value = {str(i): v for i, v in enumerate(constraints)}  # malformed: dict instead of list
    elif and_structure == 'missing':
        and_value = None  # will be excluded later
    else:
        and_value = constraints

    constraint_block = {'odrl:constraint': {'and': and_value}} if and_structure != 'missing' else {}

    policy = {
        'odrl:hasPolicy': {
            'odrl:permission': constraint_block
        }
    }

    element = {
        'dct:type': {'@id': asset_type},
        **policy
    }

    return {'dcat:dataset': [element]}


@pytest.mark.parametrize('allowed_purpose', [
    'cx.core.digitalTwinRegistry:1',
    'cx.pcf.base:1',
    'cx.core.industrycore:1'
])
def test_validate_policy_ok_when_allowed_usage_and_framework_present(allowed_purpose):
    catalog = build_catalog(usage_purpose=allowed_purpose, include_data_exchange=True)
    result = validate_policy(catalog, "DigitalTwinRegistry", "DataExchangeGovernance:1.0")
    assert result['status'] == 'ok'
    assert 'successfully' in result['message']


def test_validate_policy_warning_when_missing_framework_agreement():
    # Usage purpose allowed but missing DataExchangeGovernance -> should warn
    catalog = build_catalog(usage_purpose='cx.core.digitalTwinRegistry:1', include_data_exchange=False)
    result = validate_policy(catalog, "DigitalTwinRegistry", "DataExchangeGovernance:1.0")
    assert result['status'] == 'Warning'


def test_validate_policy_warning_when_usage_purpose_not_allowed():
    catalog = build_catalog(usage_purpose='not.allowed:1', include_data_exchange=True)
    result = validate_policy(catalog, "DigitalTwinRegistry", "DataExchangeGovernance:1.0")
    assert result['status'] == 'Warning'


def test_validate_policy_warning_when_not_dtr_asset_type():
    catalog = build_catalog(
        usage_purpose='cx.core.digitalTwinRegistry:1',
        include_data_exchange=True,
        asset_type='https://w3id.org/catenax/taxonomy#SomeOtherType'
    )
    result = validate_policy(catalog, "DigitalTwinRegistry", "DataExchangeGovernance:1.0")
    assert result['status'] == 'Warning'


@pytest.mark.parametrize('and_structure', ['dict', 'missing'])
def test_validate_policy_warning_on_malformed_and_structure(and_structure):
    catalog = build_catalog(
        usage_purpose='cx.core.digitalTwinRegistry:1',
        include_data_exchange=True,
        and_structure=and_structure
    )
    result = validate_policy(catalog, "DigitalTwinRegistry", "DataExchangeGovernance:1.0")
    assert result['status'] == 'Warning'



def test_validate_policy_from_file_success():
    # Load catalog JSON from test file and validate
    test_file = Path(__file__).parent / 'test_files' / 'catalog-response-422.json'
    with test_file.open('r', encoding='utf-8') as f:
        catalog = json.load(f)

    result = validate_policy(catalog, "UpdateQualityAlertNotification", "traceability:1.0")

    assert result['status'] == 'ok'
    assert 'successfully' in result['message']
