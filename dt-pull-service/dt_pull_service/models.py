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

"""Models used by the application for communication with the EDC
"""

import base64
import logging
import time
from typing import Dict, Optional

import requests
from tractusx_sdk.dataspace.models.connector.model_factory import ModelFactory
from tractusx_sdk.dataspace.services import BaseEdcService

from dt_pull_service.errors import Error, HTTPError
from dt_pull_service.utils import policy_checker

logger = logging.getLogger(__name__)


class EdrRequestError(Exception):
    """
    Represents an error during an EDR request.

    This exception is raised when the EDR negotiation or transfer process encounters issues.
    """


class EdrHandler:
    """
    Manages communication with the EDC (Eclipse Dataspace Connector).

    Attributes:
        partner_id (str): The identifier of the partner organization.
        partner_edc (str): The EDC endpoint of the partner.
        policies (list): Policies to be checked for compliance.
        base_url (str): The base URL for the EDC client.
        api_key (str): API key for authentication with the EDC.
        proxies (dict): Proxy settings for HTTP requests.
    """

    def __init__(self, partner_id, partner_edc, base_url, api_key, api_context, policies='', proxy=''):
        """Initialize the EdrHanler class"""

        headers = {'x-api-key': api_key, "Content-Type": "application/json"}
        
        self.edc_client = BaseEdcService('v0_9_0', base_url, api_context, headers)
        self.partner_edc = partner_edc
        self.partner_id = partner_id
        self.policies = policies
        self.proxies = {'http': proxy, 'https': proxy} if proxy else {}

    def asset_policy_check(self, catalog):
        """
        Checks asset policies to ensure they comply with predefined conditions.

        :param catalog: The catalog dictionary containing asset information.
        :return: A tuple with a boolean indicating policy match and its index.
        """

        logger.info(f'Asset Policy check for {self.policies}')
        found, index = policy_checker(self.policies, catalog)

        if not found:
            logger.warning('Asset Policy check failed!')

        return found, index

    def query_catalog_json(self,
                           prop: str,
                           value: str,
                           operator: str,
                           offset: Optional[int] = 0,
                           limit: Optional[int] = 50):
        """
        Queries the catalog and retrieves the JSON representation of the result.

        :param prop: The property used for querying the catalog.
        :param value: The value associated with the property to filter the catalog.
        :param operator: The value associated with the operator to filter the catalog.
        :param offset: The first element of the catalog to be returned.
        :param limit: The amount of elements the catalog should return.
        :raises HTTPError: Raised if the request encounters errors such as authentication issues,
                           server unavailability, or unknown errors.
        :return: A JSON object containing the catalog data.
        """

        logger.info(f'EDR query catalog {prop} {value}')

        query_spec = {
            "@type": "QuerySpecDto",
            "https://w3id.org/edc/v0.0.1/ns/offset": offset,
            "https://w3id.org/edc/v0.0.1/ns/limit": limit,
            "https://w3id.org/edc/v0.0.1/ns/filterExpression": [
            ]
        }

        if prop and value:
            query_spec['https://w3id.org/edc/v0.0.1/ns/filterExpression'] = \
                [
                    {"@type": "CriterionDto",
                     "operandLeft": prop,
                     "operator": operator,
                     "operandRight": value}
                ]

        connector_version = 'v0_9_0'
        catalog_request = ModelFactory.get_catalog_model(connector_version=connector_version,
                                                         counter_party_address=self.partner_edc,
                                                         counter_party_id=self.partner_id,
                                                         queryspec=query_spec)

        try:
            result:requests.Response = self.edc_client.catalogs.get_catalog(catalog_request, proxies=self.proxies)
        except (requests.exceptions.SSLError, requests.exceptions.JSONDecodeError) as e:
            logger.error(f'EDR query catalog returned with an error: {e}')

            raise HTTPError(Error.FORBIDDEN,
                            message='EDC connection failed!',
                            details='Check your credentials like your API key ' +\
                                    'and also check your VPN if you use one') from e

        if result.status_code == 200:
            body = result.json()
            # Attach the actual downstream HTTP request/response metadata from dt-pull-service
            try:
                sent_req = getattr(result, 'request', None)
                request_info = {
                    'method': getattr(sent_req, 'method', None),
                    'url': str(getattr(sent_req, 'url', '')) if sent_req else '',
                    'headers': dict(getattr(sent_req, 'headers', {})) if sent_req else {},
                    'content': None
                }
                if sent_req is not None and getattr(sent_req, 'body', None) is not None:
                    # requests.Request stores payload in .body
                    try:
                        request_info['content'] = sent_req.body.decode('utf-8') if isinstance(sent_req.body, (bytes, bytearray)) else str(sent_req.body)
                    except Exception:
                        request_info['content'] = None
            except Exception:
                request_info = None
            response_info = {
                'status_code': result.status_code,
                'headers': dict(result.headers),
                'text': result.text,
            }
            # Prefer non-intrusive keys; but expose plainly for convenience
            if isinstance(body, dict):
                body.setdefault('request', request_info)
                body.setdefault('response', response_info)
            return body

        if result.status_code == 403:
            raise HTTPError(Error.FORBIDDEN,
                            message='EDC connection failed due to authentication error',
                            details='Check your credentials like your API key and also check your VPN if you use one')
        if result.status_code in [500, 502]:
            raise HTTPError(Error.BAD_GATEWAY,
                            message='Connection to the server was not successful',
                            details='Check the path to the server (counter_party_address), ' +
                                    'bpn and if the server is available')

        logger.error(f'EDR query catalog returned {result.status_code}')

        raise HTTPError(Error.UNKNOWN_ERROR,
                        message='Something terrible happened',
                        details='Please contact support')

    def query_catalog(self,
                      prop: Optional[str] = '',
                      value: Optional[str] = '',
                      operator: Optional[str] = 'like',
                      policy_check: Optional[bool] = False,
                      catalog_json: Optional[Dict] = None,
                      offset: Optional[int] = 0,
                      limit: Optional[int] = 50):
        """
        Retrieves parts of the catalog request, used by other requests

        :param prop: (Optional) The value associated with the operandLeft.
        :param value: (Optional) The value associated with the operandRight.
        :param policy_check: (Optional) Whether to check for compliance with asset policies.
        :param catalog_json: (Optional) Preloaded catalog JSON data.
        :param offset: The first element of the catalog to be returned.
        :param limit: The amount of elements the catalog should return.
        :raises ValueError: Raised if neither "catalog_json" nor "prop" with "value" is provided.
        :return: A tuple containing catalog information such as offer ID, asset ID, and policy details.
        """

        if catalog_json:
            catalog = catalog_json
        elif prop and value:
            try:
                catalog = self.query_catalog_json(prop, value, operator, offset=offset, limit=limit)
            except HTTPError as exc:
                raise HTTPError(exc.error_code, message=exc.message, details=exc.details) from exc
        else:
            raise ValueError('"catalog_json" or "prop" with "value" needs to be set')

        policy_index = 0

        if policy_check:
            found, policy_index = self.asset_policy_check(catalog)

            if not found:
                return None, None, None, None, None

        catalog_dcat_dataset = catalog['dcat:dataset']

        if len(catalog_dcat_dataset) > 0:
            if isinstance(catalog_dcat_dataset, list):
                catalog_dcat_dataset = catalog_dcat_dataset[0]

            has_policy = catalog_dcat_dataset['odrl:hasPolicy']
            policy = has_policy[policy_index] if isinstance(has_policy, list) else has_policy
            edr_asset_id = catalog_dcat_dataset['@id']
            edr_offer_id = policy['@id']
            edr_permission = policy['odrl:permission']
            edr_prohibition = policy['odrl:prohibition']
            edr_obligation = policy['odrl:obligation']

            return edr_offer_id, edr_asset_id, edr_permission, edr_prohibition, edr_obligation

        return None, None, None, None, None


    def initiate_edr_negotiate(self,
                               edr_offer_id,
                               edr_asset_id,
                               edr_permission,
                               edr_prohibition,
                               edr_obligation):
        """
        Initiates an EDR negotiation and retrieves the JSON response.

        This method uses the given offer, asset ID, and policy details to start an EDR negotiation.

        :param edr_offer_id: The ID of the EDR offer.
        :param edr_asset_id: The ID of the asset being negotiated.
        :param edr_permission: The permissions associated with the EDR offer.
        :param edr_prohibition: The prohibitions associated with the EDR offer.
        :param edr_obligation: The obligations associated with the EDR offer.
        :return: A JSON object containing the response of the EDR negotiation.
        """

        offer = {
            "odrl:permission": edr_permission,
            "odrl:prohibition": edr_prohibition,
            "odrl:obligation": edr_obligation
        }

        context = ["https://w3id.org/tractusx/policy/v1.0.0",
                   "http://www.w3.org/ns/odrl.jsonld",
                   {"@vocab": "https://w3id.org/edc/v0.0.1/ns/",
                    "odrl": "http://www.w3.org/ns/odrl/2/",
                    "edc": "https://w3id.org/edc/v0.0.1/ns/",
                    "cx-policy": "https://w3id.org/catenax/policy/"
                    }]

        connector_version = 'v0_9_0'

        edr = ModelFactory.get_contract_negotiation_model(context=context,
                                                          connector_version=connector_version,
                                                          counter_party_address=self.partner_edc,
                                                          offer_id=edr_offer_id,
                                                          asset_id=edr_asset_id,
                                                          provider_id=self.partner_id,
                                                          offer_policy=offer)

        edr_response:requests.Response = self.edc_client.edrs.create(edr, proxies=self.proxies)

        # Augment response JSON with actual downstream HTTP metadata
        try:
            body = edr_response.json()
        except Exception:
            body = {}
        try:
            sent_req = getattr(edr_response, 'request', None)
            request_info = {
                'method': getattr(sent_req, 'method', None),
                'url': str(getattr(sent_req, 'url', '')) if sent_req else '',
                'headers': dict(getattr(sent_req, 'headers', {})) if sent_req else {},
                'content': None
            }
            if sent_req is not None and getattr(sent_req, 'body', None) is not None:
                try:
                    request_info['content'] = sent_req.body.decode('utf-8') if isinstance(sent_req.body, (bytes, bytearray)) else str(sent_req.body)
                except Exception:
                    request_info['content'] = None
        except Exception:
            request_info = None
        response_info = {
            'status_code': edr_response.status_code,
            'headers': dict(getattr(edr_response, 'headers', {})) if hasattr(edr_response, 'headers') else {},
            'text': getattr(edr_response, 'text', None),
        }
        if isinstance(body, dict):
            body.setdefault('request', request_info)
            body.setdefault('response', response_info)
        return body


    def check_edr_negotiate_state(self, edr_id_response: str):
        """
        Retries and checks the EDR negotiation state until finalized.

        :param edr_id_response: The ID response obtained from the EDR negotiation initiation.
        :raises EdrRequestError: Raised if the EDR contract negotiation fails.
        :return: A JSON object containing the finalized negotiation state, augmented with request/response metadata.
        """

        logger.info('Checking EDR negotiation state')
        retries = 0
        last_body = None

        while retries < 10:
            resp: requests.Response = self.edc_client.contract_negotiations.get_state_by_id(
                edr_id_response,
                proxies=self.proxies
            )
            try:
                body = resp.json()
            except Exception:
                body = {}

            # Attach actual downstream HTTP request/response metadata
            try:
                sent_req = getattr(resp, 'request', None)
                request_info = {
                    'method': getattr(sent_req, 'method', None),
                    'url': str(getattr(sent_req, 'url', '')) if sent_req else '',
                    'headers': dict(getattr(sent_req, 'headers', {})) if sent_req else {},
                    'content': None
                }
                if sent_req is not None and getattr(sent_req, 'body', None) is not None:
                    try:
                        request_info['content'] = sent_req.body.decode('utf-8') if isinstance(sent_req.body, (bytes, bytearray)) else str(sent_req.body)
                    except Exception:
                        request_info['content'] = None
            except Exception:
                request_info = None
            response_info = {
                'status_code': resp.status_code,
                'headers': dict(getattr(resp, 'headers', {})) if hasattr(resp, 'headers') else {},
                'text': getattr(resp, 'text', None),
            }
            if isinstance(body, dict):
                body.setdefault('request', request_info)
                body.setdefault('response', response_info)

            last_body = body
            state = body.get('state') if isinstance(body, dict) else None

            if state == 'FINALIZED':
                return body

            retries += 1
            time.sleep(2)

        logger.warning(f'EDR negotiation state {state}')

        return last_body if last_body is not None else {}

    def check_edr_negotiation_result(self, edr_id_response: str):
            """
            Retries and checks the EDR negotiation state until finalized.

            :param edr_id_response: The ID response obtained from the EDR negotiation initiation.
            :raises EdrRequestError: Raised if the EDR contract negotiation fails.
            :return: A JSON object containing the finalized negotiation state.
            """

            logger.info('Checking EDR negotiation result')

            negotiation_result_json:requests.Response = self.edc_client.contract_negotiations.get_by_id(
                                    edr_id_response,
                                    proxies=self.proxies)
            negotiation_result_json = negotiation_result_json.json()

            return negotiation_result_json


    def negotiate_ddtr_transfer_process_id(self):
        """
        Returns the DDTR transfer process id

        This method queries the catalog for Digital Twin Registry information,
        negotiates the EDR process, and retrieves the resulting transfer process ID.

        :return: The transfer process ID if successful, or None if the negotiation fails.
        """

        logger.info('Check EDR agreement id')
        edr_offer_id, edr_asset_id, edr_permission, edr_prohibition, edr_obligation = self.query_catalog(
            prop='http://purl.org/dc/terms/type', value='%https://w3id.org/catenax/taxonomy#DigitalTwinRegistry%')

        if not edr_offer_id:
            return None

        edr_id_response = self.initiate_edr_negotiate(edr_offer_id, edr_asset_id, edr_permission,
                                                      edr_prohibition,
                                                      edr_obligation)['@id']

        self.check_edr_negotiate_state(edr_id_response)

        data = {
            "@context": {
                "@vocab": "https://w3id.org/edc/v0.0.1/ns/"
            },
            "@type": "QuerySpec",
            "filterExpression": [
                {
                    "operandLeft": "contractNegotiationId",
                    "operator": "=",
                    "operandRight": edr_id_response
                }
            ]
        }
        time.sleep(4)
        transfer_process:requests.Response = self.edc_client.edrs.get_all(json=data, proxies=self.proxies)

        transfer_process= transfer_process.json()
        transfer_process_id = transfer_process[0]['transferProcessId']

        return transfer_process_id


    def get_ddtr_address(self):
        """
        Retrieves the Digital Twin Registry (DDTR) address.

        This method uses the DDTR transfer process ID to fetch the data address
        for communication with the EDC.

        :raises EdrRequestError: Raised if the DDTR address cannot be retrieved.
        :return: A JSON object containing the DDTR address.
        """

        logger.info(f'EDR read partner address {self.partner_id}')
        transfer_process_id = self.negotiate_ddtr_transfer_process_id()

        if transfer_process_id:
            result:requests.Response = self.edc_client.edrs.get_data_address(transfer_process_id,
                                                           params={'auto_refresh': 'true'},
                                                           proxies=self.proxies)
            data_address = result.json()

            return data_address

        raise EdrRequestError('DTR Address could not be retrieved')


    def find_sub_model_edr_agreement_id(self, sub_model_asset_id: str):
        """
        Finds the EDR agreement ID for a specific submodel asset.

        This method queries the catalog to locate the EDR agreement ID associated
        with the given submodel asset ID.

        :param sub_model_asset_id: The asset ID of the submodel to search for.
        :return: The EDR agreement ID if found, otherwise None.
        """

        logger.info(
            f'EDR find transfer process id partner_id {self.partner_id} sub_model_asset_id {sub_model_asset_id}')
        edr_offer_id, _, _, _, _ = self.query_catalog(
            prop='https://w3id.org/edc/v0.0.1/ns/id', value=sub_model_asset_id, policy_check=True)

        if edr_offer_id:
            return edr_offer_id

        logger.warning(f'Sub model not found {sub_model_asset_id}')

        return None


class DtrHandler:
    """
    Manages communication with the partner's Digital Twin Registry (DTR).

    This class provides methods to interact with the partner DTR, such as retrieving
    shell descriptors for specific assets.

    Attributes:
        partner_dtr_addr (str): The partner DTR's base address.
        partner_dtr_secret (str): The authorization secret for accessing the DTR.
        proxies (dict): Proxy settings for HTTP requests.
    """

    def __init__(self, partner_dtr_address, partner_dtr_secret, proxy):
        """
        Initializes the DtrHandler instance.

        :param partner_dtr_address: The base URL of the partner's DTR.
        :param partner_dtr_secret: The secret key used for authorization with the partner DTR.
        :param proxy: (Optional) The proxy server address for HTTP and HTTPS requests.
        """

        self.partner_dtr_addr = partner_dtr_address
        self.partner_dtr_secret = partner_dtr_secret
        self.proxies = {'http': proxy, 'https': proxy} if proxy != '' else {}

    def get_all_shells(self, limit:int=None) -> list | None:
        """
        Retrieves the shell descriptor for a given asset from the partner's DTR.

        This method sends a GET request to the `shell-descriptors` endpoint of the partner DTR
        and retrieves the shell descriptor as a JSON object.

        :param asset_id: The asset ID for which the shell descriptor is being requested.
        :return: A JSON object containing the shell descriptor details.
        :raises requests.exceptions.RequestException: Raised if the request fails due to network or server issues.
        """

        headers = {
            'Authorization': self.partner_dtr_secret
        }

        base_url=f'{self.partner_dtr_addr}/shell-descriptors'
        
        if(limit is not None):
            base_url += f'?limit={limit}'
        
        result = requests.request(
            'GET',
            base_url,
            headers=headers, proxies=self.proxies, timeout=60).json()
        
        return result

    def dtr_find_shell_descriptor(self, aas_id: str):
        """
        Retrieves the shell descriptor for a given asset from the partner's DTR.

        This method sends a GET request to the `shell-descriptors` endpoint of the partner DTR
        and retrieves the shell descriptor as a JSON object.

        :param asset_id: The asset ID for which the shell descriptor is being requested.
        :return: A JSON object containing the shell descriptor details.
        :raises requests.exceptions.RequestException: Raised if the request fails due to network or server issues.
        """

        headers = {
            'Authorization': self.partner_dtr_secret
        }

        result = requests.request(
            'GET',
            f'{self.partner_dtr_addr}/shell-descriptors/{base64.b64encode(aas_id.encode("utf-8")).decode("utf-8")}',
            headers=headers, proxies=self.proxies, timeout=60).json()

        return result

    def dtr_submodels(self, asset_id: str=''):
        """
        Retrieves the shell descriptor for a given asset from the partner's DTR.

        This method sends a GET request to the `shell-descriptors` endpoint of the partner DTR
        and retrieves the shell descriptor as a JSON object.

        :param asset_id: The asset ID for which the shell descriptor is being requested.
        :return: A JSON object containing the shell descriptor details.
        :raises requests.exceptions.RequestException: Raised if the request fails due to network or server issues.
        """

        headers = {
            'Authorization': self.partner_dtr_secret
        }

        result = requests.request(
            'GET',
            f'{self.partner_dtr_addr}/{base64.b64encode(asset_id.encode("utf-8")).decode("utf-8")}',
            headers=headers, proxies=self.proxies, timeout=60).json()

        return result

    def send_feedback(self, payload: Dict):
        """
        Sends a message for the partner's DTR about the certification status.

        This method sends a POST request to the partner DTR about the status of the certificate

        :return: A JSON object containing the server's response.
        :raises HTTPError: Raised if the request encounters errors such as authentication issues,
                           server unavailability, or unknown errors.
        """

        headers = {
            'Authorization': self.partner_dtr_secret
        }

        result = requests.request(
            'POST',
            f'{self.partner_dtr_addr}/companycertificate/status/',
            headers=headers,
            json=payload,
            proxies=self.proxies,
            timeout=15)

        if result.status_code != 200:
            logger.error(f'Certification status message was not registered: {result.status_code}, {result.text}')

            raise HTTPError(Error.INTERNAL_SERVER_ERROR,
                            message='Certification status message was not registered',
                            details='The data provider was not able to accept the status' + \
                                    'message about the certification validation. ' + \
                                    f'Original error: {result.status_code}, {result.text}')

        return result.json()


    def lookup(self, payload: Dict):
        """
        Performs a shell lookup in the partner's Digital Twin Registry (DTR) using asset link information.
        This method sends a POST request to the `lookup/shellsByAssetLink` endpoint of the partner DTR,
        using the provided payload to identify the relevant shell descriptor.

        :param payload: A dictionary containing asset link information used for the lookup.
        :return: A JSON object representing the shell descriptor retrieved from the partner DTR.
        :raises HTTPError: Raised if the request encounters errors such as authentication issues,
                           server unavailability, or unknown errors.
        """

        headers = {
            'Authorization': self.partner_dtr_secret
        }

        result = requests.request(
            method="POST",
            url=f"{self.partner_dtr_addr}/lookup/shellsByAssetLink",
            json=payload,
            headers=headers,
            timeout=15
        )

        if result.status_code != 200:
            logger.error(f'Lookup based on the given payload failed: {result.status_code}, {result.text}')

            raise HTTPError(Error.INTERNAL_SERVER_ERROR,
                            message='Lookup based on the given payload failed',
                            details=f'Original error: {result.status_code}, {result.text}')

        return result.json()
