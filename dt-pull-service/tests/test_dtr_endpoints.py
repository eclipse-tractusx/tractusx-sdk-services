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

"""Tests for the DT Pull Service's DTR endpoints
"""

from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.parametrize(
    'params,expected',
    [
        ({
            'dataplane_url': 'localhost',
            'limit': 1
         },
         {'test': 'example'})
    ]
)
def test_get_shell_descriptors(test_client, params, expected):
    """Should return the returned value of the shell_descriptor request."""

    handler_mock = MagicMock()
    handler_mock.dtr_find_shell_descriptor.return_value = expected

    with patch('dt_pull_service.api.dtr.get_dtr_handler', return_value=handler_mock):
        response = test_client.get('/dtr/shell-descriptors/',
                                   params=params)

    assert response.status_code == 200
    assert response.json() == expected
