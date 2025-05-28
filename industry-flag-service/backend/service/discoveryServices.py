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
from io import BytesIO
import logging
logger = logging.getLogger('staging')

class DiscoveryFinderService:

    @staticmethod
    def find_discovery_urls(url:str,  oauth:IdpManager, keys:list=["bpn"]) -> str | None:
        """
          Allows you to find a discovery service urls by key
        """

        ## Check if IAM is connected
        if(not oauth.connected):
            raise ConnectionError("[EDC Discovery Service] The authentication service is not connected! Please execute the oauth.connect() method")
        
        ## Setup headers and body
        headers:dict = oauth.add_auth_header(headers={'Content-Type' : 'application/json'})
        body:dict = {
            "types": keys
        }

        response:Response = HttpUtils.do_post(url=url, headers=headers, json=body)
        ## In case the response code is not successfull or the response is null
        if(response is None or response.status_code != 200):
            raise Exception("[EDC Discovery Service] It was not possible to get the discovery service because the response was not successful!")
        
        data = response.json()

        if(not("endpoints" in data) or len(data["endpoints"]) == 0):
            raise Exception("[EDC Discovery Service] No endpoints were found in the discovery service for this keys!")

        # Map to every key the endpoint address
        return dict(map(lambda x: (x['type'], x['endpointAddress']), data['endpoints']))
  
      
class EdcDiscoveryService:
    
    edc_discovery_url:str
    oauth:IdpManager
    
    def __init__(self, oauth:IdpManager, config:dict):  
        self.update_edc_discovery_url(oauth=oauth, config=config)
        self.oauth = oauth

    
    def update_edc_discovery_url(self, oauth:IdpManager, config:dict):
        key = op.get_attribute(config, 'keys.edc_discovery', None)
        if(key is None):
            raise Exception("[EDC Discovery Service] No edc discovery key was specified in the configuration!")

        discoveryUrl = op.get_attribute(config, 'url', None)
        if(discoveryUrl is None):
          raise Exception("[EDC Discovery Service]No discovery url was specified in the configuration!")


        endpoints = DiscoveryFinderService.find_discovery_urls(url=discoveryUrl, oauth=oauth, keys=[key])
        if(key not in endpoints):
          raise Exception("[EDC Discovery Service] EDC Discovery endpoint not found!")
        
        self.edc_discovery_url = endpoints[key]
        
        return self.edc_discovery_url
    
    def find_edc_by_bpn(self,bpn:str) -> list | None:
        
        body:list = [
            bpn
        ]
        
        headers:dict = self.oauth.add_auth_header(headers={'Content-Type' : 'application/json'})
        
        response = HttpUtils.do_post(url=self.edc_discovery_url, headers=headers, json=body)
        if(response is None or response.status_code != 200):
            logger.critical("[EDC Discovery Service]It was not possible to get the edc urls because the edc discovery service response was not successful!")
            return None
        
        json_response:dict = response.json()

        # Iterate over the json_response to find the connectorEndpoint for the specified BPN
        for item in json_response:
            if item.get("bpn") == bpn:
                return item.get("connectorEndpoint", [])
        
        # If the BPN is not found, return None or an empty list
        logger.warning(f"[EDC Discovery Service] No connector endpoints found for BPN: [{str(bpn)}]")
        return None
        
        
        
        
        
        
