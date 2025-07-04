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

"""Application environment configuration
"""

import os

from dotenv import find_dotenv, load_dotenv

DT_PULL_SERVICE_ADDRESS = os.getenv('DT_PULL_SERVICE_ADDRESS')
SCHEMA_PATH = 'test_orchestrator/schema_files'
DT_PULL_SERVICE_API_KEY = os.getenv('DT_PULL_SERVICE_API_KEY')
DT_PULL_SERVICE_API_KEY_HEADER = os.getenv('DT_PULL_SERVICE_API_KEY_HEADER')
API_KEY_BACKEND = os.getenv('API_KEY_BACKEND')
API_KEY_BACKEND_HEADER = os.getenv('API_KEY_BACKEND_HEADER')