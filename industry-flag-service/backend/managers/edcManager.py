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

import copy
import logging
logger = logging.getLogger('staging')
from utilities.operators import op
import uuid
import hashlib
from service.edcService import EdcService
from service.discoveryServices import EdcDiscoveryService
from managers.idpManager import IdpManager
from datetime import datetime, timezone
class EdcManager:
    """
    Class responsible for managing the edc location and search
    """ 
    
    ## Declare variables
    known_edcs: dict
    dct_type: str
    expiration_time: int
    edc_discovery: EdcDiscoveryService
    catalog_timeout:int
    
    REFRESH_INTERVAL_KEY:str

    def __init__(self, dct_type:str,  edc_discovery:EdcDiscoveryService, expiration_time=60):
        self.known_edcs = {}
        self.dct_type = dct_type
        self.expiration_time = expiration_time
        self.edc_discovery = edc_discovery
        self.REFRESH_INTERVAL_KEY:str="refresh_interval"
        self.EDC_LIST_KEY:str="edcs"
        
    def add_edcs(self, bpn:str, edcs:list[str]) -> None:
        if bpn not in self.known_edcs:
            self.known_edcs[bpn] = {self.REFRESH_INTERVAL_KEY: op.get_future_timestamp(minutes=self.expiration_time)}

        if(self.REFRESH_INTERVAL_KEY not in self.known_edcs[bpn]):
            self.known_edcs[bpn][self.REFRESH_INTERVAL_KEY] = op.get_future_timestamp(minutes=self.expiration_time)
        
        if(self.EDC_LIST_KEY in self.known_edcs[bpn]) and (len(self.known_edcs[bpn][self.EDC_LIST_KEY]) > 0) and (not op.is_interval_reached(self.known_edcs[bpn][self.REFRESH_INTERVAL_KEY])):
            return
        
        self.known_edcs[bpn][self.EDC_LIST_KEY] = op.get_future_timestamp(minutes=self.expiration_time)
        self.known_edcs[bpn][self.EDC_LIST_KEY] = edcs
        
        logger.info(f"[EDC Manager] [{bpn}] Added [{len(self.known_edcs[bpn][self.EDC_LIST_KEY])}] EDCs to the cache! Next refresh at [{op.timestamp_to_datetime(self.known_edcs[bpn][self.REFRESH_INTERVAL_KEY])}] UTC")
        
    
    def is_edc_known(self, bpn:str, edc:str) -> bool:
        if bpn not in self.known_edcs:
            return False

        edc_id = hashlib.sha3_256(str(edc).encode('utf-8')).hexdigest()
        return edc_id in self.known_edcs[bpn]
    
    def get_edc_by_id(self, bpn:str, edc_id:str) -> str | None:
        if bpn not in self.known_edcs or edc_id not in self.known_edcs[bpn]:
            return None
        
        return self.known_edcs[bpn][edc_id]

    
    def get_known_edcs(self) -> dict:
        return self.known_edcs

    def delete_edc(self, bpn ,edc_id) -> dict:
        del self.known_edcs[bpn][edc_id]
        
    def purge_bpn(self, bpn):
        del self.known_edcs[bpn]
            
    def purge_cache(self):
        self.known_edcs = {}
    
    
    def get_edcs(self, bpn:str) -> list:

        known_edcs:dict = {}
        
        ## If the edcs are known then the cache is loaded
        if(bpn in self.known_edcs):
            known_edcs = copy.deepcopy(self.known_edcs[bpn])
        
        ## In case there is edcs, and the interval has not yet been reached
        if(known_edcs != {}) and (self.REFRESH_INTERVAL_KEY in known_edcs) and (not op.is_interval_reached(end_timestamp=known_edcs[self.REFRESH_INTERVAL_KEY])):
            return [edc_url for edc_id, edc_url in self.known_edcs[bpn].items()] ## Return the urls from the edcs
        
        logger.info(f"[EDC Manager] No cached EDC were found, discoverying EDCs for bpn [{bpn}]...")
        
        edcs:list|None = self.edc_discovery.find_edc_by_bpn(bpn=bpn)
        if(edcs is None or len(edcs) == 0):
            return []
        
        
        self.add_edcs(bpn=bpn, edcs=edcs)
        
        return edcs
        
        
