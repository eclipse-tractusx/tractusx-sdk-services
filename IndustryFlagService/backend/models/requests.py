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

from pydantic import BaseModel,  Field

class EdcRequest(BaseModel):
    ## Defined the url from the edc to be called
    url:str
    ## Empty policies by default
    policies:list = Field(default=[{"odrl:permission":[],"odrl:prohibition":[],"odrl:obligation":[]}] )
    ## DCT Type of the application/asset is required
    dct_type:str
    ## Business Partner Number 
    bpn:str
    ## Headers that shall be sent in the request
    headers:dict = Field(default={})
    ## Path that the query shall execute
    path:str
    
class EdcPostRequest(EdcRequest):
    ## Defines the body that will be sent to the edc
    body:dict|str|int|list|None
    ## The content type of the request body 
    content_type:str = Field(default="application/json")
    
    
    
    
    
