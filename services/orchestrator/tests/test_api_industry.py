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

"""Tests for the industry endpoints
"""

import json
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
import pytest


@pytest.mark.asyncio
@patch('orchestrator.api.industry_test_cases.make_request', new_callable=AsyncMock)
@patch('orchestrator.api.industry_test_cases.get_dtr_access', new_callable=AsyncMock)
async def test_shell_descriptors_request(mock_get_dtr_access, mock_make_request, test_app, constants):
    """Tests if the shell descriptors endpoint returns OK for a valid json
    """

    mock_get_dtr_access.return_value = ('localhost', 'Example_key', {})
    test_file_path = './tests/test_files/test_shell_descriptors_1_full_correct.json'

    with open(test_file_path, 'r', encoding='utf-8') as file:
        json_to_validate = json.load(file)

    mock_make_request.return_value = json_to_validate

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url=pytest.BASE_URL
    ) as ac:
        response = await ac.get(
            '/test-cases/industry-core/v1/shell-descriptors-test/',
            params={
                'counter_party_address': pytest.COUNTER_PARTY_ADDRESS,
                'counter_party_id': pytest.BPN
            }
    )

    assert response.status_code == 200
    assert response.json() == {
       'message': 'Shell descriptors validation completed successfully',
       'status': 'ok',
       'validation_message': {
           'message': 'Congratulations, your JSON file passed the validation test',
           'status': 'ok',
       },
       "policy_validation_message": {}
    }
