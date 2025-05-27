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

"""Helper methods for EdrHandler class
"""

from dt_pull_service import config
from dt_pull_service.models import EdrHandler


def get_edr_handler(bpn: str, counter_party_address: str):
    """
    Creates and returns an instance of the EdrHandler.

    This function initializes an EdrHandler object to interact with the Endpoint Data Reference (EDR).
    The handler is configured with essential details such as the Business Partner Number (BPN),
    counterparty address, and API credentials.

    :param bpn: The Business Partner Number of the counterparty.
    :param counter_party_address: The address of the counterparty's EDC (Eclipse Dataspace Connector).
    :return: An initialized EdrHandler instance.
    """

    edr_handler = EdrHandler(
            bpn,
            counter_party_address,
            config.BASE_URL,
            config.API_KEY
    )

    return edr_handler
