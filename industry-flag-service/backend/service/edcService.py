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
import threading

import requests
from fastapi.responses import Response
from utilities.dspUtils import DspUtils
from utilities.httpUtils import HttpUtils
from utilities.operators import op
from utilities.sovityAuth import SovityAuth

logger = logging.getLogger('staging')
import hashlib


class EdcService:
    """
    Class responsible for managing and executing the data space components (EDC) data exchange.

    Following the standard `CX-0018` and the DSP Protocol defined by the EDWG: 

    * `CX-0018`: https://catenax-ev.github.io/docs/standards/CX-0018-DataspaceConnectivity
    * `Dataspace Protocol (DSP)`: https://docs.internationaldataspaces.org/ids-knowledgebase/dataspace-protocol
    """

    ## Declare variables
    consumer_endpoint: str
    auth_key: str
    api_key: str
    bearer_key: str
    bearer_token: str
    participant_id: str
    edc_apis: dict
    default_policies: list
    edr_managment_url: str
    edr_waiting_timeout: int
    edr_max_retries: int

    ## Here will be stored the contract agreement information
    cached_edrs: dict

    TRANSFER_ID_KEY = "transferProcessId"
    NEGOTATION_ID_KEY = "contractNegotiationId"

    def __init__(self, config: dict):
        """
        Initializes the EDC (Eclipse Datapace Connector) Service with the provided configuration.

        Parameters:
        config (dict): The configuration parameters for the EDC Service.

        Raises:
        Exception: If the EDC endpoint or participant ID is not specified in the configuration.
        """
        ## Mandatory parameters
        if "url" not in config:
            raise Exception(
                "[EDC Service] No EDC endpoint was defined in configuration! Not able to start the EDC Service.")
        if "participantId" not in config:
            raise Exception("[EDC Service] The BPN or participantId is required in the configuration!")

        ## Get all the variables
        oauth_config = config.get('oauth', {})
        self.apiKey = oauth_config.get("apiKey")
        self.consumer_endpoint = config.get('url')
        self.participant_id = config.get("participantId")

        edr_config: dict = config.get('edr', {"max_retries": 6, "waiting_timeout": 10})
        self.edr_max_retries = edr_config.get('max_retries', 6)
        self.edr_waiting_timeout = edr_config.get('waiting_timeout', 10)

        self.cached_edrs = dict()

        # self.auth_key = op.get_attribute(sourceObject=config, attrPath='apiKey.key', defaultValue="X-Api-Key")
        # self.api_key = op.get_attribute(sourceObject=config, attrPath='apiKey.value', defaultValue="password")

        self.default_policies = [{
            "odrl:permission": [],
            "odrl:prohibition": [],
            "odrl:obligation": []
        }]

        self.DCT_TYPE_KEY = config.get("dct_type_key", "'http://purl.org/dc/terms/type'.'@id'")

        ## If no api is defined
        if "apis" not in config:
            logger.error("No EDC apis were specified, taking default values.")
            self.edc_apis = op.get_attribute(
                sourceObject=config,
                attrPath='apis',
                defaultValue=
                {
                    "readiness": "/api/check/readiness",
                    "catalog": "/data/v3/catalog/request",
                    "edr_prefix": "/data/v2/edrs",
                    "view_edr": "/request",
                    "transfer_edr": "/dataaddress?auto_refresh=true",
                    "dsp": "/api/v1/dsp"
                }
            )
            return

        tmp_apis = config.get("apis")

        ## If it was specified get the data, if not get the default values
        self.edc_apis = {
            "readiness": tmp_apis.get("readiness", "/api/check/readiness"),
            "catalog": tmp_apis.get("catalog", "/control/data/v3/catalog/request"),
            "edr_prefix": tmp_apis.get("edr_prefix", "/control/data/v2/edrs"),
            "view_edr": tmp_apis.get("view_edr", "/request"),
            "transfer_edr": tmp_apis.get("transfer_edr", "/dataaddress?auto_refresh=true"),
            "dsp": tmp_apis.get("dsp", "/control/api/v1/dsp")
        }

        self.edr_managment_url = HttpUtils.join_path(url=self.consumer_endpoint, path=self.edc_apis["edr_prefix"])

        if (not self.test_connection_catalog()):
            raise Exception("[EDC Service] It was not possible to connect to the EDC! It is not yet available...")

        logger.info("[EDC Service] The connection to the Eclipse Datapase Connector [%s] was established!",
                    self.consumer_endpoint)

    def test_connection(self) -> bool:
        ## Try to get the connection endpoint
        readiness_api: str = HttpUtils.join_path(url=self.consumer_endpoint, path=self.edc_apis["readiness"])
        response: Response = HttpUtils.do_get(url=readiness_api, headers=self.get_control_plane_headers())
        ## In case the response code is not successful or the response is null
        if response is None or response.status_code != 200:
            logger.critical("It was not possible to connect to the EDC because the response was not successful!")
            return False

        ## Parse the response
        data: dict = response.json()
        ## Check if the system health endpoint is available
        if "isSystemHealthy" not in data:
            logger.critical("[EDC Service] It was not possible to find the health information")
            return False

        ## Will return the health status from the edc 
        return data["isSystemHealthy"]

    def test_connection_catalog(self) -> bool:
        ## Try to get the connection endpoint 
        response: Response = self.get_catalog(counter_party_address=self.consumer_endpoint)

        ## In case the response code is not successfull or the response is null
        if response is None:
            return False

        return True

    def get_control_plane_headers(self):
        ## Build the headers needed for the edc the app to communicate with the edc control plane
        return {
            # self.auth_key: self.api_key,
            "X-Api-Key": f"{self.apiKey}",
            "Content-Type": "application/json"
        }

    def get_data_plane_headers(self, access_token, content_type=None):
        ## Build the headers needed for the edc the app to communicate with the edc data plane
        headers = {
            "Accept": "*/*",
            "Authorization": access_token
        }

        if content_type is not None:
            headers["Content-Type"] = content_type

        return headers

    ## Allows to get the catalog without specifying the request, which can be overridden
    def get_catalog(self, counter_party_address: str, request: dict = None, timeout=10) -> dict | None:
        """
        Retrieves the EDC DCAT catalog.

        Parameters:
        counter_party_address (str): The URL of the EDC provider.
        request (dict, optional): The request payload for the catalog API. If not provided, a default request will be used.

        Returns:
        dict | None: The EDC catalog as a dictionary, or None if the request fails.
        """
        ## Get EDC DCAT catalog
        if (request is None):
            request = self.get_catalog_request(counter_party_id=self.participant_id,
                                               counter_party_address=counter_party_address)

        ## Build catalog api url
        catalog_api: str = HttpUtils.join_path(url=self.consumer_endpoint, path=self.edc_apis["catalog"])
        response: Response = HttpUtils.do_post(url=catalog_api, headers=self.get_control_plane_headers(), json=request,
                                               timeout=timeout)
        ## In case the response code is not successfull or the response is null
        if response is None or response.status_code != 200:
            logger.critical(
                "[EDC Service] It was not possible to get the catalog because the EDC response was not successful!")
            return None
        return response.json()

    ## Simple catalog request with filter
    def get_catalog_request_with_filter(self, counter_party_id: str, counter_party_address: str, key: str, value: str,
                                        operator: str = "=") -> dict:
        """
        Prepares a catalog request with a filter for a specific key-value pair.

        Parameters:
        counter_party_id (str): The identifier of the counterparty (Business Partner Number [BPN]).
        counter_party_address (str): The URL of the EDC provider.
        key (str): The key for the filter condition.
        value (str): The value for the filter condition.
        operator (str): The operator for the filter condition. Default is "=" (equal).

        Returns:
        dict: A catalog request with the filter condition included.
        """
        catalog_request: dict = self.get_catalog_request(counter_party_id=counter_party_id,
                                                         counter_party_address=counter_party_address)
        catalog_request["querySpec"] = {
            "filterExpression": [
                {
                    "operandLeft": key,
                    "operator": operator,
                    "operandRight": value
                }
            ]
        }
        return catalog_request

    def get_edr_negotiation_request(self, counter_party_id: str, counter_party_address: str, target: str,
                                    policy: dict) -> dict:
        """
        Builds the EDR Negotiation Request.

        Parameters:
        counter_party_id (str): The identifier of the counterparty (Business Partner Number [BPN]).
        counter_party_address (str): The URL of the EDC provider.
        target (str): The target asset identifier.
        policy (dict): The policy to be negotiated.

        Returns:
        dict: The EDR negotiation request in the form of a dictionary.
        """
        policy_header: dict = {
            "target": target,
            "assigner": counter_party_id
        }

        # Make union of policy header and the policy
        enriched_policy: dict = policy_header | policy

        return {
            "@context": [
                "https://w3id.org/tractusx/policy/v1.0.0",
                "http://www.w3.org/ns/odrl.jsonld",
                {
                    "@vocab": "https://w3id.org/edc/v0.0.1/ns/"
                }
            ],
            "@type": "ContractRequest",
            "counterPartyAddress": self.build_dsp_endpoint(url=counter_party_address),
            "protocol": "dataspace-protocol-http",
            "policy": enriched_policy,
            "callbackAddresses": []
        }

    ## Simple catalog request without filter
    def get_catalog_request(self, counter_party_id: str, counter_party_address: str) -> dict:
        return {
            "@context": {
                "edc": "https://w3id.org/edc/v0.0.1/ns/",
                "odrl": "http://www.w3.org/ns/odrl/2/",
                "dct": "https://purl.org/dc/terms/"
            },
            "@type": "edc:CatalogRequest",
            "counterPartyId": counter_party_id,  ## bpn of the provider
            "counterPartyAddress": self.build_dsp_endpoint(url=counter_party_address),  ## dsp url from the provider
            "protocol": "dataspace-protocol-http"
        }

    def get_edr_negotiation_filter(self, negotiation_id: str) -> dict:

        return {
            "@context": {
                "@vocab": "https://w3id.org/edc/v0.0.1/ns/"
            },
            "@type": "QuerySpec",
            "filterExpression": [
                {
                    "operandLeft": self.NEGOTATION_ID_KEY,
                    "operator": "=",
                    "operandRight": negotiation_id
                }
            ]
        }

    def get_catalogs_by_dct_type(self, counter_party_id: str, edcs: list, dct_type: str, timeout: int = None):
        return self.get_catalogs_with_filter(counter_party_id=counter_party_id, edcs=edcs, key=self.DCT_TYPE_KEY,
                                             value=dct_type, operator="=", timeout=timeout)

    def get_catalogs_with_filter(self, counter_party_id: str, edcs: list, key: str, value: str, operator: str = "=",
                                 timeout: int = None):

        ## Where the catalogs get stored
        catalogs: dict = {}
        threads: list[threading.Thread] = []

        for edc_url in edcs:
            thread = threading.Thread(target=self.get_catalog_with_filter_parallel, kwargs=
            {
                'counter_party_id': counter_party_id,
                'counter_party_address': edc_url,
                'key': key,
                'operator': operator,
                'value': value,
                'timeout': timeout,
                'catalogs': catalogs
            }
                                      )
            thread.start()  ## Start thread
            threads.append(thread)

        ## Allow the threads to process
        for thread in threads:
            thread.join()  ## Waiting until they process

        return catalogs

    def get_catalog_by_dct_type(self, counter_party_id: str, counter_party_address: str, dct_type: str, timeout=None):
        return self.get_catalog_with_filter(counter_party_id=counter_party_id,
                                            counter_party_address=counter_party_address, key=self.DCT_TYPE_KEY,
                                            value=dct_type, operator="=", timeout=timeout)

    def get_catalog_with_filter_parallel(self, counter_party_id: str, counter_party_address: str, key: str, value: str,
                                         operator: str = "=", catalogs: dict = None, timeout: int = None) -> None:
        catalogs[counter_party_address] = self.get_catalog_with_filter(counter_party_id=counter_party_id,
                                                                       counter_party_address=counter_party_address,
                                                                       key=key, value=value, operator=operator,
                                                                       timeout=timeout)

    ## Get catalog request with filter
    def get_catalog_with_filter(self, counter_party_id: str, counter_party_address: str, key: str, value: str,
                                operator: str = "=", timeout: int = None) -> dict:
        """
        Retrieves a catalog from the EDC provider based on a specified filter.

        Parameters:
        counter_party_id (str): The identifier of the counterparty (Business Partner Number [BPN]).
        counter_party_address (str): The URL of the EDC provider.
        key (str): The key to filter the catalog entries by.
        value (str): The value to filter the catalog entries by.
        operator (str, optional): The comparison operator to use for filtering. Defaults to "=".

        Returns:
        dict: The catalog entries that match the specified filter.
        """
        return self.get_catalog(counter_party_address=counter_party_address,
                                request=self.get_catalog_request_with_filter(counter_party_id=counter_party_id,
                                                                             counter_party_address=counter_party_address,
                                                                             key=key, value=value, operator=operator),
                                timeout=timeout)

    ## Build the dsp endpoint api
    def build_dsp_endpoint(self, url: str) -> dict:
        """
        Builds the DSP (Data Space Protocol) endpoint URL by appending the DSP endpoint path to the given URL.

        Parameters:
        url (str): The original URL of the EDC provider.

        Returns:
        dict: The DSP endpoint URL.

        Raises:
        Exception: If the given URL does not end with the DSP endpoint path.
        """
        ## If the url has already the dsp endpoint
        if url.endswith(self.edc_apis["dsp"]):
            return url  ## Return the url

        ## Add dsp endpoint
        return HttpUtils.join_path(url=url, path=self.edc_apis["dsp"])

    def get_token(self, transfer_id: str) -> str:
        """
        Retrieves the authorization token from the EDR (Endpoint Data Reference) for a given transfer ID.

        Parameters:
        transfer_id (str): The unique identifier for the transfer process.

        Returns:
        str: The authorization token for the specified transfer ID.

        Raises:
        Exception: If the EDR entry is not found or the authorization token is not available.
        """
        ## Get authorization key from the edr
        edr: dict = self.get_edr(transfer_id=transfer_id)
        if (edr is None):
            raise Exception("[EDC Service] It was not possible to retrieve the edr token!")
        return edr["authorization"]

    def get_endpoint_with_token(self, transfer_id: str) -> tuple[str, str]:
        """
        @returns: tuple[dataplane_endpoint:str, authorization:str]
        """
        ## Get authorization key from the edr
        edr: dict = self.get_edr(transfer_id=transfer_id)
        if (edr is None):
            raise Exception("[EDC Service] It was not possible to retrieve the edr token and the dataplane endpoint!")

        return edr["endpoint"], edr["authorization"]

    def start_edr_negotiation(self, counter_party_id: str, counter_party_address: str, target: str,
                              policy: dict) -> str | None:
        """
        Starts the edr negotiation and gives the negotation id

        @param counter_party_id: The identifier of the counterparty (Business Partner Number [BPN]).
        @param counter_party_address: The URL of the EDC provider.
        @param target: The target asset for the negotiation.
        @param policy: The policy to be used for the negotiation.
        @returns: negotiation_id:str or if Fail -> None
        """

        ## Prepare the request
        request: dict = self.get_edr_negotiation_request(counter_party_id=counter_party_id,
                                                         counter_party_address=counter_party_address, target=target,
                                                         policy=policy)

        ## Build catalog api url
        response: Response = HttpUtils.do_post(url=self.edr_managment_url, headers=self.get_control_plane_headers(),
                                               json=request)
        ## In case the response code is not successfull or the response is null
        if (response is None or response.status_code != 200):
            logger.critical("[EDC Service] It was not possible to start the edr negotiation!")
            return None

        content: dict = response.json()
        ## Check if the id was returned in the response
        if ("@id" not in content):
            logger.critical("[EDC Service] No negotiation id was found in the response!")
            return None

        return content.get("@id", None)

    def get_edr_entry(self, negotiation_id: str) -> dict | None:
        """
        Gets the edr negotiation details for a given negotiation id

        @param negotiation_id: The unique identifier for the negotiation process.
        
        @returns: EndpointDataReferenceEntry:dict or if Fail -> None

        EndpointDataReferenceEntry Example: 
        ```
            {
                "@id": "04e9ec58-a053-4e40-85d8-35efb4a3a343",
                "@type": "EndpointDataReferenceEntry",
                "providerId": "BPNL000000000T4X",
                "assetId": "urn:uuid:0c3d2db0-e5c6-27f9-5875-15a9a00e7a27",
                "agreementId": "a6816e69-a6ea-491c-b842-3532aafb75dd",
                "transferProcessId": "04e9ec58-a053-4e40-85d8-35efb4a3a343",
                "createdAt": 1729683943014,
                "contractNegotiationId": "d9a0d5a4-1f4d-49a7-9270-2ea5163a2a10",
                "@context": {
                    "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
                    "edc": "https://w3id.org/edc/v0.0.1/ns/",
                    "tx": "https://w3id.org/tractusx/v0.0.1/ns/",
                    "tx-auth": "https://w3id.org/tractusx/auth/",
                    "cx-policy": "https://w3id.org/catenax/policy/",
                    "odrl": "http://www.w3.org/ns/odrl/2/"
                }
            }
        ```
        """

        request: dict = self.get_edr_negotiation_filter(negotiation_id=negotiation_id)
        url: str = self.edr_managment_url + self.edc_apis["view_edr"]
        ## Build catalog api url
        response: requests.Response = HttpUtils.do_post(url=url, headers=self.get_control_plane_headers(), json=request)
        ## In case the response code is not successfull or the response is null
        if (response is None or response.status_code != 200):
            logger.critical(f"[EDC Service] EDR Entry not found for the negotiation_id=[{negotiation_id}]!")
            return None

        ## The response is a list
        data = response.json()

        if (len(data) == 0):
            return None

        return data.pop()  ## Return last entry of the list (should be just one entry because of the filter)

    def get_edr(self, transfer_id: str) -> dict | None:
        """
        Gets and EDR Token.

        This function sends a GET request to the EDC to retrieve the EDR (Endpoint Data Reference) 
        token for the given transfer ID. The EDR token is used to access the data behind the EDC.

        Parameters:
        transfer_id (str): The unique identifier for the transfer process.

        Returns:
        dict | None: The response content from the GET request, or None if the request fails.

        Raises:
        Exception: If the EDC response is not successful (status code is not 200).
        """
        ## Build edr transfer url
        tmp_url: str = self.edr_managment_url + f"/{transfer_id}"
        transfer_url: str = tmp_url + self.edc_apis["transfer_edr"]

        response: Response = HttpUtils.do_get(url=transfer_url, headers=self.get_control_plane_headers())
        if (response is None or response.status_code != 200):
            logger.critical(
                "[EDC Service] It was not possible to get the edr because the EDC response was not successful!")
            return None
        return response.json()

    def get_transfer_id(self, counter_party_id: str, counter_party_address: str, dct_type: str,
                        policies: list = None) -> str:

        """
        Checks if the transfer is already available at the location or not...

        Parameters:
        counter_party_id (str): The identifier of the counterparty (Business Partner Number [BPN]).
        counter_party_address (str): The URL of the EDC provider.
        policies (list, optional): The policies to be used for the transfer. Defaults to None.
        dct_type (str, optional): The DCT type to be used for the transfer

        Returns:
        str: The transfer ID.

        Raises:
        Exception: If the EDR entry is not found or the transfer ID is not available.
        """

        ## Hash the policies to get checksum. 
        curent_policies_checksum = hashlib.sha3_256(str(policies).encode('utf-8')).hexdigest()

        ## If the countrer party id is already available and also the dct type is in the counter_party_id and the transfer key is also present
        counterparty_data: dict = self.cached_edrs.get(counter_party_id, {})
        edc_data: dict = counterparty_data.get(counter_party_address, {})
        dct_data: dict = edc_data.get(dct_type, {})

        ## Get policies checksum
        cached_entry: dict = dct_data.get(curent_policies_checksum, {})

        ## Get the edr
        transfer_id: str | None = cached_entry.get(self.TRANSFER_ID_KEY, None)

        ## If is there return the cached one, if the selection is the same the transfer id can be reused!
        if (transfer_id is not None):
            logger.info(
                "[EDC Service] [%s]: EDR transfer_id=[%s] found in the cache for counter_party_id=[%s], dct_type=[%s] and selected policies",
                counter_party_address, transfer_id, counter_party_id, dct_type)
            return transfer_id

        logger.info(
            "[EDC Service] The EDR was not found in the cache for counter_party_address=[%s], counter_party_id=[%s], dct_type=[%s] and selected policies, starting new contract negotiation!",
            counter_party_address, counter_party_id, dct_type)

        ## If not the contract negotiation MUST be done!
        edr_entry: dict = self.negotiate_and_transfer(counter_party_id=counter_party_id,
                                                      counter_party_address=counter_party_address, policies=policies,
                                                      dct_type=dct_type)

        ## Check if the edr entry is not none
        if (edr_entry is None):
            raise Exception("[EDC Service] Failed to get edr entry! Response was none!")

        ## Check if the transfer id is available
        transfer_process_id: str = edr_entry.get(self.TRANSFER_ID_KEY, None)
        if transfer_process_id is None or transfer_process_id == "":
            raise Exception(
                "[EDC Service] The transfer id key was not found or is empty! Not able to do the contract negotiation!")

        logger.info(f"[EDC Service] The EDR Entry was found! Transfer Process ID: [{transfer_process_id}]")

        ## Check if the contract negotiation was alredy specified
        if counter_party_id not in self.cached_edrs:
            self.cached_edrs[counter_party_id] = {}

        ## Using pointers update the memory cache
        cached_edcs = self.cached_edrs[counter_party_id]

        ## Check if the dct type is already available
        if counter_party_address not in cached_edcs:
            cached_edcs[counter_party_address] = {}

        cached_dct_types = cached_edcs[counter_party_address]

        ## Check if the dct type is already available in the EDC
        if dct_type not in cached_dct_types:
            cached_dct_types[dct_type] = {}

        cached_details = cached_dct_types[dct_type]

        ## Store the edr entry!
        if curent_policies_checksum not in cached_details:
            cached_details[curent_policies_checksum] = {}

        ## Prepare edr to be stored in cache
        saved_edr = copy.deepcopy(edr_entry)
        del saved_edr["@type"], saved_edr["providerId"], saved_edr["@context"]

        ## Store edr in cache
        cached_details[curent_policies_checksum] = saved_edr

        if "edrs" not in self.cached_edrs:
            self.cached_edrs["edrs"] = 0

        self.cached_edrs["edrs"] += 1

        logger.info(
            f"[EDC Service] A new EDR entry was saved in the memory cache! [{self.cached_edrs['edrs']}] EDRs Available")

        return transfer_process_id  ## Return transfer_process_id!

    def assets_exists(self, counter_party_id: str, counter_party_address: str, dct_type: str, timeout=10) -> bool:

        try:
            catalog = self.get_catalog_with_filter(counter_party_id=counter_party_id,
                                                   counter_party_address=counter_party_address, key=self.DCT_TYPE_KEY,
                                                   value=dct_type, timeout=timeout)
        except Exception as e:
            logger.error(
                f"[EDC Service] Failed to get catalog for counter_party_id=[{counter_party_id}], counter_party_address=[{counter_party_address}], dct_type=[{dct_type}]")
            return False

        if catalog is None:
            return False

        return not DspUtils.is_catalog_empty(catalog=catalog)

    def do_get(self, counter_party_id: str, counter_party_address: str, dct_type: str, path: str = "/",
               policies: list = None, verify: bool = False, headers: dict = {}, timeout: int = None,
               params: dict = None, allow_redirects: bool = False) -> Response:
        """
        Executes a HTTP GET request to a asset behind an EDC!
        Abstracts everything for you doing the dsp exchange.

        Parameters:
        counter_party_id (str): The identifier of the counterparty (Business Partner Number [BPN]).
        counter_party_address (str): The URL of the EDC provider.
        path (str, optional): The path to be appended to the dataplane URL. Defaults to "/".
        policies (list, optional): The policies to be used for the transfer. Defaults to None.
        dct_type (str, optional): The DCT type to be used for the transfer. Defaults to "IndustryFlagService".

        Returns:
        Response: The HTTP response from the GET request. If the request fails, an Exception is raised.
        """
        ## If policies are empty use default policies

        dataplane_url, access_token = self.do_dsp(counter_party_id=counter_party_id,
                                                  counter_party_address=counter_party_address, policies=policies,
                                                  dct_type=dct_type)

        if dataplane_url is None or access_token is None:
            raise Exception("[EDC Service] No dataplane URL or access_token was able to be retrieved!")

        ## Build edr transfer url
        url: str = dataplane_url + path

        dataplane_headers: dict = self.get_data_plane_headers(access_token=access_token)

        ## Do get request to get a response!
        return HttpUtils.do_get(url=url, headers=(headers | dataplane_headers), verify=verify, timeout=timeout,
                                params=params, allow_redirects=allow_redirects)

    def do_post(self, counter_party_id: str, counter_party_address: str, body, dct_type: str, path: str = "/",
                content_type: str = "application/json", policies: list = None, verify: bool = False,
                headers: dict = None,
                timeout: int = None, params: dict = None, allow_redirects: bool = False) -> Response:
        """
        Performs a HTTP POST request to a specific asset behind an EDC.

        This function abstracts the entire process of exchanging data with the EDC. It first negotiates the EDR (Endpoint Data Reference)
        using the provided counterparty ID, EDC provider URL, policies, and DCT type. Then, it constructs the dataplane URL and access token
        using the negotiated EDR. Finally, it sends a POST request to the dataplane URL with the provided body, headers, and content type.

        Parameters:
        counter_party_id (str): The identifier of the counterparty (Business Partner Number [BPN]).
        counter_party_address (str): The URL of the EDC provider.
        body (dict): The data to be sent in the POST request.
        path (str, optional): The path to be appended to the dataplane URL. Defaults to "/".
        content_type (str, optional): The content type of the POST request. Defaults to "application/json".
        policies (list, optional): The policies to be used for the transfer. Defaults to None.
        dct_type (str, optional): The DCT type to be used for the transfer. Defaults to "IndustryFlagService".

        Returns:
        Response: The HTTP response from the POST request. If the request fails, an Exception is raised.
        """
        ## If policies are empty use default policies

        dataplane_url, access_token = self.do_dsp(counter_party_id=counter_party_id,
                                                  counter_party_address=counter_party_address, policies=policies,
                                                  dct_type=dct_type)

        if dataplane_url is None or access_token is None:
            raise Exception("[EDC Service] No dataplane URL or access_token was able to be retrieved!")

        ## Build edr transfer url
        url: str = dataplane_url + path

        dataplane_headers: dict = self.get_data_plane_headers(access_token=access_token, content_type=content_type)

        ## Do get request to get a response!
        return HttpUtils.do_post(url=url, json=body, headers=(headers | dataplane_headers), verify=verify,
                                 timeout=timeout, allow_redirects=allow_redirects)

    def do_dsp(self, counter_party_id: str, counter_party_address: str, dct_type: str, policies: list = None) -> tuple[
        str, str]:
        """
        Does all the dsp necessary operations until getting the edr.
        Giving you all the necessary data to request data to the edc dataplane.

        @param counter_party_id: The identifier of the counterparty (Business Partner Number [BPN]).
        @param counter_party_address: The URL of the EDC provider.
        @param policies: The policies to be used for the transfer. Defaults to None.
        @param dct_type: The DCT type to be used for the transfer. Defaults to "IndustryFlagService".
        @returns: tuple[dataplane_endpoint:str, edr_access_token:str] or if fail Exception
        """

        ## If policies are empty use default policies
        if policies is None:
            policies = self.default_policies

        ## Get the transfer id 
        transfer_id = self.get_transfer_id(counter_party_id=counter_party_id,
                                           counter_party_address=counter_party_address, policies=policies,
                                           dct_type=dct_type)
        ## Get the endpoint and the token
        return self.get_endpoint_with_token(transfer_id=transfer_id)

    def negotiate_and_transfer(self, counter_party_id: str, counter_party_address: str, dct_type: str,
                               policies: list = None) -> dict:
        """
        This method checks if there is a transfer process ID available, or if it needs to be negotiated.

        @param counter_party_id: The identifier of the counterparty (Business Partner Number [BPN]).
        @param counter_party_address: The URL of the EDC provider.
        @param policies: The policies to be used for the transfer. Defaults to None.
        @param dct_type: The DCT type to be used for the transfer. Defaults to "IndustryFlagService".
        @returns: edr_entry:dict, if fails Exception
        """
        ##### 1. Get Catalog
        catalog_response = self.get_catalog_with_filter(counter_party_id=counter_party_id,
                                                        counter_party_address=counter_party_address,
                                                        key=self.DCT_TYPE_KEY, value=dct_type)
        if (catalog_response is None):
            raise Exception(
                f"[EDC Service] [{counter_party_address}] It was not possible to retrieve the catalog from the edc provider! Catalog response is empty!")

        ## Select Policy and Assetid
        asset_id: str | None = None
        policy: dict | None = None

        try:
            valid_assets_policies = DspUtils.filter_assets_and_policies(catalog=catalog_response,
                                                                        allowed_policies=policies)
        except Exception as e:
            raise Exception(
                f"[EDC Service] [{counter_party_address}] It was not possible to find a valid policy in the catalog! Reason: [{str(e)}]")

        if (len(valid_assets_policies) == 0):
            raise Exception(
                f"[EDC Service] [{counter_party_address}] It was not possible to find a valid policy in the catalog! Asset ID and the Policy are empty!")

        negotiation_id: str | None = None

        for valid_asset_policy in valid_assets_policies:
            ## Unwrap asset id and policy tuple
            asset_id = valid_asset_policy[0]
            policy = valid_asset_policy[1]

            logger.info(
                f"[EDC Service] [{counter_party_address}] The following target asset [{asset_id}] and policy [{str(policy['@id'])}] was selected, trying negotiation!")

            ##### 2. EDR Negotiation Start

            negotiation_id = self.start_edr_negotiation(counter_party_id=counter_party_id,
                                                        counter_party_address=counter_party_address, target=asset_id,
                                                        policy=policy)
            if (negotiation_id is not None):
                logger.info(
                    f"[EDC Service] [{counter_party_address}] The EDR Negotiation has started! Negotiation ID: [{negotiation_id}]")
                break

            logger.error(
                f"[{counter_party_address}]: Failed to intialize the edr negotiation for [{asset_id}] and policy [{str(policy['@id'])}]! No id was returned! Trying again with next asset and policy!")

        if (negotiation_id is None):
            raise Exception(
                f"[EDC Service] [{counter_party_address}] It was not possible to start the EDR Negotiation! The negotiation id is empty!")

        ##### 3. Get EDC Entry (details)

        retries: int = 0
        edr_entry: dict | None = None
        while edr_entry is None and retries < self.edr_max_retries:
            edr_entry = self.get_edr_entry(negotiation_id=negotiation_id)
            if edr_entry is not None:  ## If edr is found skip retry
                logging.info(
                    f"[EDC Service] [{counter_party_address}] The EDR Negotiation [{negotiation_id}] entry was found!")
                break
            ## Wait until the timeout has reached to retry again
            logging.info(
                f"[EDC Service] Attempt [{retries + 1}]/[{self.edr_max_retries}]: [{counter_party_address}] The EDR Negotiation [{negotiation_id}] entry was not found! Waiting {self.edr_waiting_timeout} seconds and retrying...")
            op.wait(seconds=self.edr_waiting_timeout)
            retries += 1

        if edr_entry is None:
            raise Exception(
                f"[EDC Service] [{counter_party_address}] The EDR Negotiation [{negotiation_id}] has failed! The EDR entry was not found!")

        return edr_entry
