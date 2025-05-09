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

"""Tests for the DT Pull Service's EDR endpoints
"""

from unittest.mock import patch, MagicMock

import pytest

@pytest.mark.parametrize(
    'params,expected',
    [
        ({
            'counter_party_address': 'addr',
            'counter_party_id': 'counter_party_id',
            'operand_left': 'prop',
            'operand_right': 'val',
            'operator': 'like',
            'offset': 10,
            'limit': 20,
         },
         {'test': 'catalog'})
    ]
)
def test_get_catalog(test_client, params, expected):
    """Should return filtered catalog based on query params."""

    handler_mock = MagicMock()
    handler_mock.query_catalog_json.return_value = expected

    with patch('dt_pull_service.api.edr.get_edr_handler', return_value=handler_mock):
        response = test_client.get('/edr/get-catalog/', params=params)

    assert response.status_code == 200
    assert response.json() == expected


def test_init_negotiation(test_client):
    """Should initiate negotiation with catalog data."""

    handler_mock = MagicMock()
    handler_mock.query_catalog.return_value = ['offer', 'asset', ['perm'], ['proh'], ['obl']]
    handler_mock.initiate_edr_negotiate.return_value = {'test': 'initiate_negotiate'}

    with patch('dt_pull_service.api.edr.get_edr_handler', return_value=handler_mock):
        response = test_client.post('/edr/init-negotiation/?counter_party_address=addr' + \
                                    '&counter_party_id=counter_party_id', json={})

    assert response.status_code == 200
    assert response.json() == {'test': 'initiate_negotiate'}


def test_negotiation_state(test_client):
    """Should return current state of negotiation."""

    handler_mock = MagicMock()
    handler_mock.check_edr_negotiate_state.return_value = {'test': 'negotiation_state'}

    with patch('dt_pull_service.api.edr.get_edr_handler', return_value=handler_mock):
        response = test_client.get('/edr/negotiation-state/', params={
            'state_id': 'abc123',
            'counter_party_address': 'addr',
            'counter_party_id': 'counter_party_id'
        })

    assert response.status_code == 200
    assert response.json() == {'test': 'negotiation_state'}


def test_transfer_process(test_client):
    """Should return transfer process data after initiation."""

    handler_mock = MagicMock()
    handler_mock.edc_client.edrs.get_all.return_value = [{'test': 'transfer'}]
    handler_mock.proxies = {}

    with patch('dt_pull_service.api.edr.get_edr_handler', return_value=handler_mock):
        response = test_client.post('/edr/transfer-process/?counter_party_address=addr' + \
                                    '&counter_party_id=counter_party_id', json={'key': 'val'})

    assert response.status_code == 200
    assert response.json() == [{'test': 'transfer'}]


def test_data_address(test_client):
    """Should return data address for a given transfer process."""

    handler_mock = MagicMock()
    handler_mock.edc_client.edrs.get_data_address.return_value = {'test': 'data_address'}
    handler_mock.proxies = {}

    with patch('dt_pull_service.api.edr.get_edr_handler', return_value=handler_mock):
        response = test_client.get('/edr/data-address/', params={
            'transfer_process_id': 'xyz789',
            'counter_party_address': 'addr',
            'counter_party_id': 'counter_party_id'
        })

    assert response.status_code == 200
    assert response.json() == {'test': 'data_address'}
