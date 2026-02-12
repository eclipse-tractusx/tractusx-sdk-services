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

"""Pytest configuration with common fixtures
"""

import json
from unittest.mock import MagicMock

import pytest
from dt_pull_service.app import create_app
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse


@pytest.fixture(scope='session')
def test_app():
    """A testing application"""

    return create_app()


@pytest.fixture
def test_client(test_app):
    """A testing web client"""

    return TestClient(test_app)


@pytest.fixture
def mock_edc_client():
    """Returns a mocked edc client"""

    payload = {
        "dcat:dataset": {
            "@id": "test-asset-id",
            "odrl:hasPolicy": {
                "@id": "test-offer-id",
                "odrl:permission": {},
                "odrl:prohibition": {},
                "odrl:obligation": {}
            }
        }
    }

    mock_client = MagicMock()
    mock_client.catalogs.get_catalog.return_value = JSONResponse(content=payload, status_code=200)

    mock_client.edrs.create.return_value = {"@id": "test-edr-id"}
    mock_client.contract_negotiations.get_state_by_id.return_value.body = json.dumps({"state": "FINALIZED"}).encode()
    mock_client.edrs.get_all.return_value = \
        JSONResponse(content=[{"transferProcessId": "test-transfer-id"}],status_code=200)

    mock_response = MagicMock()
    mock_response.body = json.dumps({
        "endpoint": "test-endpoint",
        "authorization": "test-auth"
    }).encode()
    mock_client.edrs.get_data_address.return_value = mock_response

    return mock_client
