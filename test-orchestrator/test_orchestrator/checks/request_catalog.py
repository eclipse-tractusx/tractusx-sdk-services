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

"""Catalog request helper
"""
from typing import Optional

from test_orchestrator import config
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.errors import HTTPError, Error
from test_orchestrator.logging.log_manager import LoggingManager
from test_orchestrator.request_handler import make_request, make_request_verbose

logger = LoggingManager.get_logger(__name__)


async def get_catalog(
        counter_party_address: str,
        counter_party_id: str,
        operand_left: Optional[str] = None,
        operator: Optional[str] = "like",
        operand_right: Optional[str] = None,
        offset: Optional[int] = 0,
        limit: Optional[int] = 10,
        timeout: int = 80,
):
    """
    Retrieve the catalog from the DT Pull Service.

    Parameters mirror those previously used directly in utils.get_dataplane_access.
    """
    response = await make_request_verbose(
        "GET",
        f"{config.DT_PULL_SERVICE_ADDRESS}/edr/get-catalog/",
        params={
            "operand_left": operand_left,
            "operand_right": operand_right,
            "operator": operator,
            "counter_party_address": counter_party_address,
            "counter_party_id": counter_party_id,
            "offset": offset,
            "limit": limit,
        },
        timeout=timeout,
        headers=get_dt_pull_service_headers(),
    )

    catalog_json = response['response_json']

    # Validate if the response code is 200.
    status_code = response.get('response', {}).get('status_code')
    if status_code != 200:
        error_code = catalog_json.get('error', 'BAD_GATEWAY')
        message = catalog_json.get('message', 'Unknown error')
        details = catalog_json.get('details', 'No additional details provided')
        error_code_enum = Error.__members__.get(error_code, Error.BAD_GATEWAY)
        raise HTTPError(error_code_enum,
                        message=message,
                        details=details)

    logger.info("Catalog JSON received: %s", catalog_json)

    # Validate if there is an offer for the desired asset/type available.
    if len(catalog_json["dcat:dataset"]) == 0:
        raise HTTPError(
            Error.CONTRACT_NEGOTIATION_FAILED,
            message='In case this is the Digital Twin Registry Asset please check ' + \
                    'https://eclipse-tractusx.github.io/docs-kits/kits/digital-twin-kit/' + \
                    'software-development-view/#digital-twin-registry-as-edc-data-asset for troubleshooting.',
            details=f'There were no offers of type/id {operand_right} found in the catalog of connector {counter_party_address}. ' + \
                    'Either the properties or access policy of the asset are misconfigured. ' + \
                    'Make sure to allow access to the asset for the Testbed BPNL.')

    return response
