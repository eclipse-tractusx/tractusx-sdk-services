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


def find_env_file() -> str:
    """Find an env file

    First, the environment variable ENVFILE_PATH is considered. If it is set,
    its value will be used as a filename. 
    If it is not set, python-dotenv's find_dotenv will be used instead.
    """

    if 'ENVFILE_PATH' in os.environ:
        return os.environ('ENVFILE_PATH')

    return find_dotenv()


load_dotenv(find_env_file())

DT_PULL_SERVICE_ADDRESS = os.getenv('DT_PULL_SERVICE_ADDRESS')
SCHEMA_PATH = 'test_orchestrator/schema_files'
