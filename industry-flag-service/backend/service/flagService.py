#################################################################################
# Tractus-X - Industry Flag Service
#
# Copyright (c) 2025 CGI Deutschland B.V. & Co. KG
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
# distributed under the License is distributed on an "AS IS" BASIS
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the
# License for the specific language govern in permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
#################################################################################

import requests
from fastapi.responses import JSONResponse, Response
from fastapi import FastAPI, Request

from utilities.httpUtils import HttpUtils
from utilities.operators import op
from managers.idpManager import IdpManager
from service.edcService import EdcService
from service.discoveryServices import EdcDiscoveryService
from managers.edcManager import EdcManager
from managers.flagManager import FlagManager
from io import BytesIO
from utilities.dspUtils import DspUtils
import logging
logger = logging.getLogger('staging')


class FlagService:
    """
    The flag service is responsible for retrieving data from behind the EDC
    """

    edc_service: EdcService
    edc_manager: EdcManager
    idp_manager: IdpManager
    flag_manager: FlagManager
    catalog_timeout: int
    dct_type: str
    GET_FLAGS_PATH: str

    def __init__(self,  edc_service: EdcService, edc_manager: EdcManager, idp_manager: IdpManager, flag_manager: FlagManager, config: dict, catalog_timeout: int = 10):
        # Pointers to the respective services
        self.edc_service = edc_service
        self.edc_manager = edc_manager
        self.idp_manager = idp_manager
        self.flag_manager = flag_manager
        self.dct_type = config.get('dct_type', "IndustryFlagService")
        self.policies = op.json_string_to_object(config.get('policies', {
            "odrl:permission": {
                "odrl:action": {
                    "@id": "odrl:use"
                },
                "odrl:constraint": {
                    "odrl:and": [
                        {
                            "odrl:leftOperand": {
                                "@id": "cx-policy:UsagePurpose"
                            },
                            "odrl:operator": {
                                "@id": "odrl:eq"
                            },
                            "odrl:rightOperand": "catenax.industryflagservice"
                        }
                    ]
                }
            },
            "odrl:prohibition": [],
            "odrl:obligation": []
        }))
        self.catalog_timeout = catalog_timeout
        self.GET_FLAGS_PATH = "/flags"

    def search_apps(self, bpn: str, edcs: list) -> list | None:
        catalogs = self.edc_service.get_catalogs_by_dct_type(
            counter_party_id=bpn, edcs=edcs, dct_type=self.dct_type, timeout=self.catalog_timeout)
        found_apps: list = []

        for edc_url, catalog in catalogs.items():
            # If the catalog is empty the app does not exist
            if (DspUtils.is_catalog_empty(catalog=catalog)):
                continue
            found_apps.append(edc_url)

        if (len(found_apps) == 0):
            return None

        self.flag_manager.add_apps(bpn=bpn, edc_urls=found_apps)
        return found_apps

    def find_apps(self, bpn: str) -> list | None:
        # List of known edcs for bpn
        edcs: list = self.edc_manager.get_edcs(bpn=bpn)

        if (len(edcs) == 0):
            raise Exception(f"There was no EDCs found for bpn [{bpn}]")

        # Find edcs that contain the apps
        apps: list = self.flag_manager.get_apps(bpn=bpn)

        if (len(apps) == 0):
            # If not found in cache it is required to search for them in the edcs
            apps = self.search_apps(bpn=bpn, edcs=edcs)

        return apps

    def get_app_flags(self, bpn: str, edc_url: str, raw_response=True):
        response: requests.Response = self.edc_service.do_get(
            counter_party_id=bpn, counter_party_address=edc_url, dct_type=self.dct_type, path=self.GET_FLAGS_PATH, policies=self.policies)
        if (response is None or response.status_code != 200):
            logger.error(
                f"[Flag Service] It was not possible to get the Industry Flags from BPN [{bpn}] from the following EDC [{edc_url}]!")
            return None

        if (raw_response):
            return response

        return response.json()

    def get_app_flag_proof(self, bpn: str, edc_url: str, id: str, raw_response=True):
        response: requests.Response = self.edc_service.do_get(
            counter_party_id=bpn, counter_party_address=edc_url, dct_type=self.dct_type, path=f"{self.GET_FLAGS_PATH}/{id}", policies=self.policies)
        if (response is None or response.status_code != 200):
            logger.error(
                f"[Flag Service] It was not possible to get the Industry Flags from BPN [{bpn}] from the following EDC [{edc_url}]!")
            return None

        if (raw_response):
            return response

        return response.content

    def get_flags(self, bpn: str, raw_response=True) -> dict | list | requests.Response | None:

        # List of edcs that are known and that have apps
        apps: list = self.find_apps(bpn=bpn)

        if (apps is None):
            raise Exception(
                f"There was no Industry Flag Services found for bpn [{bpn}] and the configured policies!")

        # The first one we find is going to be the one that will be used to retrieve the flags
        for edc_url in apps:
            flags_response = self.get_app_flags(
                bpn=bpn, edc_url=edc_url, raw_response=raw_response)
            if (flags_response is None):
                continue
            return flags_response

        raise Exception(
            f"It was not possible to get any Industry Flag from any of the Industry Flag Services [{bpn}] applications!")

    def get_flag_proof(self, bpn: str, id: str, raw_response=True) -> dict | list | requests.Response | None:

        # List of edcs that are known and that have apps
        apps: list = self.find_apps(bpn=bpn)

        if (apps is None):
            raise Exception(
                f"There was no Industry Flag Services found for bpn [{bpn}] and the configured policies!")

        # The first one we find is going to be the one that will be used to retrieve the flags
        for edc_url in apps:
            proof = self.get_app_flag_proof(
                bpn=bpn, edc_url=edc_url, id=id, raw_response=raw_response)
            if (proof is None):
                continue
            return proof

        raise Exception(
            f"It was not possible to get any Industry Flag Proof for the id search in any of the Industry Flag Services [{bpn}] applications!")
