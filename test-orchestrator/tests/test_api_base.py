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

"""Tests for the base endpoints
"""

from unittest.mock import AsyncMock, Mock, patch

from httpx import ASGITransport, AsyncClient, Response, Request
import pytest

# pylint: disable=R0801


@pytest.fixture
def mock_make_request():
    """Mocks the make request inside he base_test_cases
    """
    with patch('orchestrator.api.base_test_cases.make_request', new_callable=AsyncMock) as mock:
        yield mock


@pytest.mark.asyncio
async def test_ping_request(test_app, mock_make_request, constants):
    """Tests the ping test endpoint, if DT Pull service returns with no error
    """
    mock_make_request.return_value = {'example': True}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url=pytest.BASE_URL
    ) as ac:
        response = await ac.get(
            '/test-cases/base/v1/ping-test/',
            params={
                'counter_party_address': pytest.COUNTER_PARTY_ADDRESS,
                'counter_party_id': pytest.BPN
            }
    )

    assert response.status_code == 200
    assert response.json() == {
        'status': 'ok',
        'message': 'No errors found during the ping request'
    }


@pytest.mark.asyncio
async def test_make_request_http_error(test_app, constants):
    """Tests what happens if DT Pull Service returns 500
    """

    fake_response = Response(
        status_code=500,
        request=Request(method='GET', url='http://example.com'),
        json={
            'error': 'BAD_GATEWAY',
            'message': 'Something went wrong',
            'details': 'More info'
        }
    )

    fake_response.json = Mock(return_value={
        'error': 'BAD_GATEWAY',
        'message': 'Something went wrong',
        'details': 'More info'
    })

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url=pytest.BASE_URL
    ) as ac:
        response = await ac.get(
            '/test-cases/base/v1/ping-test/',
            params={
                'counter_party_address': pytest.COUNTER_PARTY_ADDRESS,
                'counter_party_id': pytest.BPN
            }
    )

    assert response.status_code == 502
    assert response.json() == {
        'details': 'Please check '
        'https://eclipse-tractusx.github.io/docs-kits/kits/connector-kit/operation-view/ '
        'for troubleshooting.',
        'error': 'CONNECTION_FAILED',
        'message': 'Connection to the connector was not successful',
    }
