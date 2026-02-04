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

"""Pytest configuration with common fixtures
"""

import pytest
from httpx import ASGITransport, AsyncClient
from test_orchestrator.app import create_app


@pytest.fixture(scope='session')
def test_app():
    """A testing application"""

    return create_app()


@pytest.fixture
async def async_client(test_app):
    """A testing web client"""

    async with AsyncClient(transport=ASGITransport(app=test_app),
                           base_url='http://test') as client:
        yield client


@pytest.fixture
def constants():
    """Useful constants"""
    pytest.BASE_URL = 'http://test'
    pytest.BPN = 'BPN123'
    pytest.COUNTER_PARTY_ADDRESS = 'http://example.com'
