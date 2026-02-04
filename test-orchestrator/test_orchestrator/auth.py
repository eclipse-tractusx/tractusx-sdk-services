# *************************************************************
# Eclipse Tractus-X - Digital Twin Pull Service
#
# Copyright (c) 2025 Catena-X Automotive Network e.V.
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

from fastapi import HTTPException, Request
from tractusx_sdk.dataspace.managers import AuthManager

from test_orchestrator import config

auth_manager = AuthManager(
    configured_api_key=config.API_KEY_BACKEND,
    api_key_header=config.API_KEY_BACKEND_HEADER,
    auth_enabled=True
)

def verify_auth(
    request: Request
):
    if(config.API_KEY_BACKEND is None or
       config.API_KEY_BACKEND_HEADER is None):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not auth_manager.is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
def get_dt_pull_service_headers(headers: dict = {}) -> dict:
    headers[config.DT_PULL_SERVICE_API_KEY_HEADER] = config.DT_PULL_SERVICE_API_KEY
    headers["Content-Type"] = "application/json"
    return headers