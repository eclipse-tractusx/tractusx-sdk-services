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

"""Utility methods for certification validation
"""
import base64
import copy
from datetime import datetime, UTC
import json
import logging
import uuid
from typing import Dict, List, Literal, Optional

from test_orchestrator import config
from test_orchestrator.errors import HTTPError, Error
from test_orchestrator.request_handler import make_request
from test_orchestrator.utils import submodel_schema_finder, fetch_transfer_process
from test_orchestrator.validator import json_validator
from test_orchestrator.auth import get_dt_pull_service_headers


SEMANTIC_ID_FEEDBACK_MESSAGE_HEADER = "urn:samm:io.catenax.shared.message_header:3.0.0#MessageHeaderAspect"
SEMANTIC_ID_FEEDBACK_MESSAGE_CONTENT = "urn:samm:io.catenax.message:1.0.0#MessageContentAspect"
SEMANTIC_ID_BUSINESS_PARTNER_CERTIFICATE = (
    "urn:samm:io.catenax.business_partner_certificate:3.1.0#BusinessPartnerCertificate"
)

logger = logging.getLogger(__name__)

async def send_feedback(payload: Dict,
                        status: Literal['SUCCESS', 'REJECTED', 'RECEIVED'],
                        dataplane_url: str,
                        dataplane_access_key: str,
                        errors: List,
                        timeout: int = 80
                        ) -> Dict:
    """
    Sends a feedback message via the DTR endpoint using information extracted from the given payload.

    This function performs the following steps:
    1. Parses the feedback message header from the input payload.
    2. Retrieves access credentials and endpoint URL from the DTR.
    3. Constructs the feedback message with updated metadata and provided status.
    4. Sends the feedback to the designated DTR endpoint using an authenticated POST request.

    :param payload: A dictionary containing the feedback message, expected to include a 'header' section.
    :param status: The certificate status string to include in the outgoing feedback message.
    :return: A dictionary representing the response from the DTR feedback.
    """

    header = copy.deepcopy(payload.get('header'))
    content = {}
    sender_bpn = header.get('senderBpn')
    receiver_bpn = header.get('receiverBpn')

    header['senderBpn'] = receiver_bpn
    header['senderFeedbackUrl'] = "https://domain.tld/path/to/api"
    header['relatedMessageId'] = str(uuid.uuid4())
    header['context'] = "CompanyCertificateManagement-CCMAPI-Status:1.0.0"
    header['messageId'] = str(uuid.uuid4())
    header['receiverBpn'] = sender_bpn
    header['sentDateTime'] = datetime.now(UTC).isoformat()
    header['version'] = '3.1.0'

    content['documentId'] = payload.get('content', {}).get('document', {}).get('documentID', {})
    content['certificateStatus'] = status
    content['locationBpns'] = [
        "BPNS000000000001",
        "BPNS000000000002",
        "BPNS000000000003",
        "BPNA000000000001",
        "BPNA000000000002",
        "BPNA000000000003"
    ]

    content['documentId'] = payload.get('content', {}).get('document', {}).get('documentID', {})

    if errors:
        content['errors'] = errors

    message_body = {'header': header,
                    'content': content}

    try:
        send_feedback = await make_request(
            'POST',
            f'{config.DT_PULL_SERVICE_ADDRESS}/dtr/send-feedback/',
            params={'dataplane_url': dataplane_url},
            json=message_body,
            headers=get_dt_pull_service_headers(headers={'Authorization': dataplane_access_key}),
            timeout=timeout)
    except HTTPError:
        raise HTTPError(
            Error.FEEDBACK_COULD_NOT_BE_SENT,
            message="Your CCM API returned a status code outside of 200.",
            details="The testbed could not send the corresponding feedback message. " + \
                    "Make sure your backend system accepts that message. " + \
                    "Compare https://catenax-ev.github.io/docs/next/standards/CX-0135-CompanyCertificateManagement " + \
                    "(Release Saturn) for the various feedback types that must be processed by your CCMAPI"
        )

    return send_feedback


def check_for_single_ccmapi_asset(catalog_json: dict):
    """
    Checks a catalog JSON for a single asset with the ID "CCMAPI".

    Args:
        catalog_json: The catalog as a Python dictionary.

    Raises:
        ValueError: If the number of assets with the ID "CCMAPI" is not exactly one.
    """
    datasets = catalog_json.get("dcat:dataset", [])

    # If there's only one asset, it might not be in a list
    if isinstance(datasets, dict):
        datasets = [datasets]

    # Count how many assets match the desired ID
    ccmapi_assets = [
        asset for asset in datasets if "ccmapi" in asset.get("@id").lower()
    ]

    if len(ccmapi_assets) != 1:
        raise HTTPError(
            Error.TOO_MANY_ASSETS_FOUND,
            message="More than one CCMAPI Asset was found in the connector. According to the standard, " + \
                    "there may only be one asset.",
            details='Compare https://catenax-ev.github.io/docs/next/standards/' + \
                    'CX-0135-CompanyCertificateManagement#214--data-asset-structure (Release Saturn)) for details.'
        )


async def read_asset_policy(counter_party_address: str,
                            counter_party_id: str,
                            operand_left: Optional[str] = None,
                            operator: Optional[str] = 'like',
                            operand_right: Optional[str] = None,
                            offset: Optional[int] = 0,
                            limit: Optional[int] = 100,
                            timeout: int = 80):
    """Fetches asset and policy data from the catalog service.

    This function queries an external catalog service to retrieve the asset ID
    and associated policies based on specified filter criteria.

    Args:
        counter_party_address: The address of the counterparty.
        counter_party_id: The BPN (Business Partner Number) of the counterparty.
        operand_left: The left operand for the catalog query filter.
        operator: The operator for the catalog query (e.g., 'like', 'eq').
        operand_right: The right operand for the catalog query filter.
        offset: The starting point for pagination.
        limit: The maximum number of items to return.

    Returns:
        A tuple containing the asset ID and its associated policies.
        Returns (asset_id, None) if policies cannot be retrieved.
        Returns (None, None) if the asset ID cannot be found.
    """
    try:
        catalog_json = await make_request('GET',
                                          f'{config.DT_PULL_SERVICE_ADDRESS}/edr/get-catalog/',
                                          params={'operand_left': operand_left,
                                                  'operand_right': operand_right,
                                                  'operator': operator,
                                                  'counter_party_address': counter_party_address,
                                                  'counter_party_id': counter_party_id,
                                                  'offset': offset,
                                                  'limit': limit},
                                          headers=get_dt_pull_service_headers(),
                                          timeout=timeout)
    except Exception as e:
        logger.info(f"counter_party_address or counter_party_id might be invalid. Exception: {e}")
        raise HTTPError(
            Error.CONNECTOR_UNAVAILABLE,
            message="Connection to your connector was not successful.",
            details="The testbed can't access the specified connector. Make sure the counter_party_address points " + \
                    "to the DSP endpoint of your connector and the counter_party_id is correct. Please check " + \
                    "https://eclipse-tractusx.github.io/docs-kits/kits/connector-kit/operation-view/ " + \
                    "for troubleshooting.")

    check_for_single_ccmapi_asset(catalog_json)

    try:
        asset_id = catalog_json['dcat:dataset']['@id']
    except Exception as e:
        logger.error(f'Error getting asset ID: {e}')
        return None, None

    try:
        policies = catalog_json['dcat:dataset']['odrl:hasPolicy']
    except Exception as e:
        logger.error(f'Error getting policy: {e}')
        return asset_id, None

    return asset_id, policies


def validate_policy(policies: list[dict] | dict, contract_reference: bool) -> bool:
    """
    Validates if a specific type of policy exists given one or more policies.

    This function is updated to handle three input scenarios:
    1. A single policy object (dict) without a contract reference.
    2. A single policy object (dict) with a contract reference.
    3. A list of policy objects (list[dict]).

    It checks for the presence of a policy "with contract" or "without contract"
    based on the value of the 'contract_reference' flag.

    - If 'contract_reference' is True, it checks for a policy that includes a
      constraint with '@id' of 'cx-policy:ContractReference'.
    - If 'contract_reference' is False, it checks for a policy that does NOT
      include a 'cx-policy:ContractReference' constraint.

    Args:
        policies: A policy dictionary or a list of policy dictionaries.
        contract_reference: A boolean indicating which policy type to validate.
                            True for "with contract", False for "without contract".

    Returns:
        True if the specified policy type is found, False otherwise.
    """

    # input is a single policy dictionary instead of a list of them.
    if isinstance(policies, dict):
        policies = [policies]

    # Ensure policies is a list to prevent errors in the loop
    if not isinstance(policies, list):
        return False

    def _has_contract_reference(policy: dict) -> bool:
        """Checks if a single policy has a contract reference constraint."""
        try:
            constraints = policy.get('odrl:permission', {}) \
                .get('odrl:constraint', {}) \
                .get('odrl:and', [])

            # Ensure constraints is a list before iterating
            if not isinstance(constraints, list):
                return False

            for constraint in constraints:
                if isinstance(constraint, dict) and constraint.get('odrl:leftOperand', {}).get(
                        '@id') == 'cx-policy:ContractReference':
                    return True
        except (AttributeError, TypeError):
            # Handles cases where the path doesn't exist or is not a dict/list
            return False
        return False

    # The logic can be simplified using any() for better readability
    if contract_reference:
        # We need a policy WITH a contract ref, return True if any policy has one.
        return any(_has_contract_reference(p) for p in policies)

    # We need a policy WITHOUT a contract ref, return True if any policy lacks one.
    return any(not _has_contract_reference(p) for p in policies)


def decode_and_validate_document(content_base64: Optional[str],
                                 expected_mime: Optional[str]) -> bytes:
    """
    Decodes a base64-encoded document and validates its MIME type based on magic bytes.

    Supports only PDF ("application/pdf") and PNG ("image/png") formats.
    Raises an HTTPError if the base64 is invalid, the file format is unsupported,
    or the detected MIME type does not match the expected one.

    Parameters:
        content_base64 (str): The base64-encoded content of the file.
        expected_mime (str): The expected MIME type ("application/pdf" or "image/png").

    Returns:
        bytes: The decoded binary content of the file.

    Raises:
        HTTPError: If any validation step fails.
    """
    if not content_base64 or not expected_mime:
        raise HTTPError(Error.MISSING_DATA,
                        message='Document content or type is missing.',
                        details='The fields contentBase64 and contentType are required for document validation.')

    try:
        binary_data = base64.b64decode(content_base64)
    except Exception:
        raise HTTPError(Error.BAD_REQUEST,
                        message='Invalid base64 encoding',
                        details='The attached document cannot be decoded.')

    detected_mime = None
    if binary_data.startswith(b'%PDF-'):
        detected_mime = 'application/pdf'
    elif binary_data.startswith(b'\x89PNG\r\n\x1a\n'):
        detected_mime = "image/png"
    else:
        raise HTTPError(Error.UNSUPPORTED_MEDIA_TYPE,
                        message='Unsupported document format',
                        details='Only PNG and PDF documents are supported.')

    if detected_mime != expected_mime:
        raise HTTPError(Error.BAD_REQUEST,
                        message='Mismatching file type and file header',
                        details=f'MIME type mismatch: expected {expected_mime}, got {detected_mime}')

    return binary_data


def run_certificate_checks(validation_schema: Dict,
                          semantic_id: str):
    """Validates the structure of a submodel and the certificate document it contains.

    This function performs two main validation steps:
    1.  It retrieves a JSON schema using the provided semantic_id and validates
        the structure of the validation_schema['content'] against it.
    2.  It decodes a Base64 encoded document found within the validation_schema
        and validates its content and type.

    Args:
        validation_schema (Dict): A dictionary containing the submodel content to be
            validated. It is expected to have a nested structure like:
            {'content': {'document': {'contentBase64': '...', 'contentType': '...'}}}
        semantic_id (str): The semantic ID used to look up the correct
            validation schema for the submodel.

    Raises:
        HTTPError: If the submodel schema cannot be found for the given
            semantic_id.
        # Add other potential exceptions from json_validator or decode_and_validate_document
        # e.g., ValidationError: If the JSON validation fails.
    """
    try:
        certificate_schema = submodel_schema_finder(semantic_id=semantic_id)
        rules_schema = certificate_schema['schema']

    except Exception:
        raise HTTPError(
            Error.SUBMODEL_VALIDATION_FAILED,
            message=f'The validation of the requested submodel for semanticID {semantic_id} failed: ' + \
                    'Could not find the submodel schema based on the semantic_id provided.',
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                    'software-development-view/aspect-models' + \
                    'for troubleshooting and samples.')

    cert_validation_errors = json_validator(rules_schema, validation_schema['content'])

    content_base64 = validation_schema.get('content').get('document').get('contentBase64')
    content_type = validation_schema.get('content').get('document').get('contentType')

    decode_and_validate_document(content_base64, content_type)

    return cert_validation_errors

def read_feedback_rules_schema():
    """Reads feedback rules from local file"""
    file_path_feedback = "test_orchestrator/schema_files/MessageContentAspect-schema.json"

    with open(file_path_feedback, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_feedback_check(semantic_id_header, semantic_id_content, validation_schema):
    """
        Performs validation of a feedback payload against its header and content schemas.

        This function orchestrates the validation of a feedback message by retrieving
        two separate schemas based on the provided semantic IDs: one for the header
        and one for the content.

        It first attempts to find the header's validation schema using
        semantic_id_header. If this schema cannot be found, the function
        immediately fails and raises an error.

        Next, it tries to find the content's validation schema using
        semantic_id_content. If a specific schema for the content isn't found,
        it gracefully falls back to a default feedback rules schema.

        Finally, the function validates the provided validation_schema (the payload)
        against both the header and content schemas to ensure full compliance.

        Args:
            semantic_id_header (str): The semantic identifier used to look up the
                validation schema for the message header.
            semantic_id_content (str): The semantic identifier used to look up the
                validation schema for the message content.
            validation_schema (Dict): The JSON-like dictionary payload of the
                feedback message that needs to be validated.
            message_type (str): The type of feedback message (e.g., 'RECEIVED').
                Note: This parameter is reserved for context or future logic extensions.

        Raises:
            HTTPError: Raised if the submodel schema for the semantic_id_header
                       cannot be found and loaded.
        """
    # Read semantic schema for Header Feedback
    try:
        certificate_schema_header = submodel_schema_finder(semantic_id=semantic_id_header)
        rules_schema_header = certificate_schema_header['schema']

    except Exception:
        raise HTTPError(
            Error.SUBMODEL_VALIDATION_FAILED,
            message=f'The validation of the requested submodel for semanticID {semantic_id_header} failed: ' + \
                    'Could not find the submodel schema based on the semantic_id provided.',
            details='Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/' + \
                    'software-development-view/aspect-models' + \
                    'for troubleshooting and samples.')

    # Read semantic schema for Content Feedback
    try:
        certificate_schema_content = submodel_schema_finder(semantic_id=semantic_id_content)
        rules_schema_content = certificate_schema_content['schema']
    except (HTTPError, KeyError, TypeError) as e:
        rules_schema_content = read_feedback_rules_schema()

    header_validation_errors = json_validator(rules_schema_header, validation_schema)
    content_validation_errors = json_validator(rules_schema_content, validation_schema)

    return header_validation_errors, content_validation_errors

async def get_ccmapi_access(counter_party_address: str,
                            counter_party_id: str,
                            operand_left: Optional[str] = None,
                            operator: Optional[str] = 'like',
                            operand_right: Optional[str] = None,
                            offset: Optional[int] = 0,
                            limit: Optional[int] = 100,
                            asset_validation: Optional[bool] = None,
                            timeout: int = 80):
    """
    Retrieves DTR access credentials for a CCMAPI asset by querying the remote catalog.

    This function:
    - Sends a catalog request to the counterparty's connector.
    - Optionally validates the presence of a single CCMAPI asset in the response.
    - Extracts the EDR endpoint and authorization token for data access.

    :param counter_party_address: URL of the counterparty’s EDC DSP endpoint.
    :param counter_party_id: Business Partner Number (BPN) of the counterparty.
    :param operand_left: Left operand used to filter the catalog (usually semantic type URI).
    :param operator: Operator for the catalog filter (default is 'like').
    :param operand_right: Right operand used in the filter expression.
    :param offset: Result pagination offset.
    :param limit: Maximum number of results to retrieve.
    :param asset_validation: Flag to validate presence of a CCMAPI asset in the catalog.
    :raises HTTPError: If the connector is unavailable or the asset cannot be found.
    :return: A tuple containing the EDR endpoint URL and its authorization token.
    """

    try:
        catalog_json = await make_request('GET',
                                          f'{config.DT_PULL_SERVICE_ADDRESS}/edr/get-catalog/',
                                          params={'operand_left': operand_left,
                                                  'operand_right': operand_right,
                                                  'operator': operator,
                                                  'counter_party_address': counter_party_address,
                                                  'counter_party_id': counter_party_id,
                                                  'offset': offset,
                                                  'limit': limit},
                                          headers=get_dt_pull_service_headers(),
                                          timeout=timeout)
    except Exception as e:
        logger.info(f"counter_party_address or counter_party_id might be invalid. Exception: {e}")

        raise HTTPError(
            Error.CONNECTOR_UNAVAILABLE,
            message="Connection to your connector was not successful.",
            details="The testbed can't access the specified connector. Make sure the counter_party_address points " + \
                    "to the DSP endpoint of your connector and the counter_party_id is correct. Please check " + \
                    "https://eclipse-tractusx.github.io/docs-kits/kits/connector-kit/operation-view/ " + \
                    "for troubleshooting.")

    check_for_single_ccmapi_asset(catalog_json)

    # Validate result of the policy from the catalog if required
    if asset_validation:
        try:
            catalog_json['dcat:dataset']['@id']
        except Exception as e:
            logger.warning(f'''Asset is missing. Error: {e}''')

            raise HTTPError(
                Error.ASSET_NOT_FOUND,
                message="Please check asset/policy/contractdefinition configuration and make sure to first execute " + \
                        "the ccmapi-offer-test",
                details="The CCMAPI asset could not be found in the specified connector. It might be missing or " + \
                        "misconfigured. Check the following: access policy allows access for the " + \
                        "testbed BPNL, contract definition includes the CCMAPI asset and the right policies, " + \
                        "CCMAPI asset has all required attributes. Compare " + \
                        "https://catenax-ev.github.io/docs/next/standards/CX-0135-" + \
                        "CompanyCertificateManagement#214--data-asset-structure (Release Saturn)."
            )
    try:
        init_negotiation = await make_request('POST',
                                              f'{config.DT_PULL_SERVICE_ADDRESS}/edr/init-negotiation/',
                                              params={'counter_party_address': counter_party_address,
                                                      'counter_party_id': counter_party_id},
                                              json=catalog_json,
                                              headers=get_dt_pull_service_headers(),
                                              timeout=timeout)
    except HTTPError:
        raise HTTPError(
            Error.CONTRACT_NEGOTIATION_FAILED,
            message="Access to the CCMAPI asset could not be negotiated.",
            details="Check if the usage policy is according to the standard. Also check your connector logs.")

    edr_state_id = init_negotiation.get('@id')

    await make_request('GET',
                       f'{config.DT_PULL_SERVICE_ADDRESS}/edr/negotiation-state/',
                       params={'counter_party_address': counter_party_address,
                               'counter_party_id': counter_party_id,
                               'state_id': edr_state_id},
                        headers=get_dt_pull_service_headers(),
                        timeout=timeout)

    data = {
        '@context': {'@vocab': 'https://w3id.org/edc/v0.0.1/ns/'},
        '@type': 'QuerySpec',
        'filterExpression': [{
            'operandLeft': 'contractNegotiationId',
            'operator': '=',
            'operandRight': edr_state_id
        }]
    }

    transfer_process = await fetch_transfer_process(
        counter_party_address=counter_party_address,
        counter_party_id=counter_party_id,
        data=data
    )
    transfer_process_id = transfer_process[0]['transferProcessId']

    edr_data_address = await make_request('GET',
                                          f'{config.DT_PULL_SERVICE_ADDRESS}/edr/data-address/',
                                          params={'counter_party_address': counter_party_address,
                                                  'counter_party_id': counter_party_id,
                                                  'transfer_process_id': transfer_process_id},
                                          headers=get_dt_pull_service_headers(),
                                          timeout=timeout)

    return edr_data_address.get('endpoint'), edr_data_address.get('authorization')
