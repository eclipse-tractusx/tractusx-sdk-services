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

"""Helper methods for DtrHandler class
"""

from dt_pull_service.models import DtrHandler


def get_dtr_handler(dtr_url: str, authorization: str):
    """
    Creates and returns an instance of the DtrHandler.

    This function initializes an DtrHandler object to interact with the Digital Twin Registry (DTR).

    :param dtr_url: The URL to access the DTR.
    :param authorization: The negotiated key to access the DTR.
    :return: An initialized DtrHandler instance.
    """

    dtr_handler = DtrHandler(
            dtr_url,
            authorization,
            '',
    )

    return dtr_handler
