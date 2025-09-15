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

"""Tests for models.py
"""

from dt_pull_service.models import EdrHandler
from dt_pull_service.utils import policy_checker, policy_check_item, get_recursively


def test_policy_check():
    """Tests the policy_checker method"""

    policies = [{'policy1': 'value1'}]
    catalog = {
        'dcat:dataset': {
            'odrl:hasPolicy': [{
                'odrl:leftOperand': {'@id': 'policy1'},
                'odrl:rightOperand': 'value1'
            }]
        }
    }

    assert policy_checker(policies, catalog) == (True, 0)


def test_policy_check_item():
    """Tests the policy_check_item method"""

    policies = [{'policy1': 'value1'}]
    item = {
        'odrl:leftOperand': {'@id': 'policy1'},
        'odrl:rightOperand': 'value1'
    }

    assert policy_check_item(policies, item) is True


def test_get_recursively():
    """Tests the get_recursively method"""

    data = {
        'level1': {
            'odrl:leftOperand': {'@id': 'policy1'},
            'nested': {'odrl:leftOperand': {'@id': 'policy2'}}
        }
    }
    result = get_recursively(data, 'odrl:leftOperand')

    assert len(result) == 2
    assert result[0]['odrl:leftOperand']['@id'] == 'policy1'
    assert result[1]['odrl:leftOperand']['@id'] == 'policy2'


def test_query_catalog(mock_edc_client):
    """Tests the .query_catalog method of EdrHandler"""

    handler = EdrHandler('partner1', 'edc-address', [], 'http://test-url', 'api-key', None, '/management')
    handler.edc_client = mock_edc_client
    result = handler.query_catalog('some-property', 'some-value')

    assert result[0] == 'test-offer-id'
    assert result[1] == 'test-asset-id'


def test_initiate_edr_negotiate(mock_edc_client):
    """Tests the initiate_edr_negotiate method of EdrHandler"""

    handler = EdrHandler('partner1', 'edc-address', [], 'http://test-url', 'api-key', None,'/management')
    handler.edc_client = mock_edc_client
    edr_id = handler.initiate_edr_negotiate('offer-id', 'asset-id', {}, {}, {})

    assert edr_id == {'@id': 'test-edr-id'}


def test_check_edr_negotiate_state(mock_edc_client):
    """Tests the check_edr_negotiate_state method of EdrHandler"""

    handler = EdrHandler('partner1', 'edc-address', [], 'http://test-url', 'api-key', None, '/management')
    handler.edc_client = mock_edc_client
    result = handler.check_edr_negotiate_state('test-edr-id')

    assert result == {'state': 'FINALIZED'}


def test_get_ddtr_address(mock_edc_client):
    """Tests the get_ddtr_address method of EdrHandler"""

    handler = EdrHandler('partner1', 'edc-address', [], 'http://test-url', 'api-key', None, '/management')
    handler.edc_client = mock_edc_client
    ddtr_address_json = handler.get_ddtr_address()

    assert ddtr_address_json['endpoint'] == 'test-endpoint'
    assert ddtr_address_json['authorization'] == 'test-auth'
