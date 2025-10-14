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

"""
Provides FastAPI endpoints for validating business partner certificates and related components.

This module defines a set of API endpoints built with FastAPI to test and validate
the implementation of the Business Partner Certificate and the Company Certificate
Management API (CCMAPI) within the Catena-X network. It allows for the validation
of certificate payloads against their semantic models, tests the setup of CCMAPI
offers, verifies the feedback mechanism, and validates the structure of feedback
messages.

The primary goal is to ensure that a participant's implementation conforms to the
defined standards (e.g., CX-0135), facilitating interoperability across the network.

Endpoints:
- GET /feedbackmechanism-validation/: Tests if the feedback mechanism of a test subject works.
- POST /cert-validation-test/: Validates a given certificate against its semantic model and tests feedback delivery.
- GET /ccmapi-offer-test/: Validates the correctness of a CCMAPI asset offer and its associated usage policy.
- POST /feedbackmessage-validation/: Validates a given feedback message against its semantic model.
"""

import logging
from typing import Dict, Literal, Optional
from fastapi import APIRouter, Depends

from test_orchestrator.auth import verify_auth
from test_orchestrator.certificate_utils import (
    send_feedback,
    read_asset_policy,
    validate_policy,
    run_certificate_checks,
    run_feedback_check,
    get_ccmapi_access,
    SEMANTIC_ID_FEEDBACK_MESSAGE_HEADER,
    SEMANTIC_ID_FEEDBACK_MESSAGE_CONTENT,
    SEMANTIC_ID_BUSINESS_PARTNER_CERTIFICATE
    )
from test_orchestrator.errors import HTTPError, Error

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('/ccmapi-offer-test/',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def validate_ccmapi_offer_setup(counter_party_address: str,
                                      counter_party_id: str,
                                      contract_reference: bool = True,
                                      timeout: int = 80) -> Dict:
    """
    This test case validates if the CCMAPI Offer is set up correctly. The test is successful if the test-agent is
    able to perform the following steps:
        1.	Query for the CCMAPI asset in the specified connector (counter_party_address).
        2.	Check for the correctness of all required properties of the CCMAPI.
        3.	Validate if the usage policy (with/without contract reference) is according to the standard.

        •	:param counter_party_address: Address of the dsp endpoint of a connector
        (ends on api/v1/dsp for DSP version 2024-01).
        •	:param counter_party_id: The identifier of the test subject that operates the connector.
        Until at least Catena-X Release 25.09 that is the BPNL of the test subject.
        •	:param contract_reference: Boolean (true/false) to toggle if the usage policy attached to the CCMAPI offer
        is with or without a contract reference.
        •	:return: A dictionary containing a success or an error message.
    """
    asset_id, policies = await read_asset_policy(counter_party_address = counter_party_address,
                                                 counter_party_id = counter_party_id,
                                                 operand_left='http://purl.org/dc/terms/type',
                                                 operand_right='%https://w3id.org/catenax/taxonomy#CCMAPI%',
                                                 timeout=timeout)

    if asset_id is None:
        raise HTTPError(
                Error.ASSET_NOT_FOUND,
                message="Please check asset/policy/contractdefinition configuration",
                details="The CCMAPI asset could not be found in the specified connector. It might be missing or" + \
                        " misconfigured. Check the following: access policy allows access for the testbed BPNL," + \
                        " contract definition includes the CCMAPI asset and the right policies, CCMAPI asset has all" +\
                        " required attributes. Compare https://catenax-ev.github.io/docs/next/standards/" + \
                        "CX-0135-CompanyCertificateManagement#214--data-asset-structure (Release Saturn).")
    exist_policy = validate_policy(policies=policies, contract_reference=contract_reference)

    if not exist_policy:
        return {
            "warning": "POLICY_VALIDATION_FAILED",
            "message": "The usage policy that is used for the asset is not accurate.",
            "details": "Please check https://catenax-ev.github.io/docs/next/standards/" + \
                       "CX-0135-CompanyCertificateManagement#216-usage-policy (Release Saturn) for troubleshooting. " +\
                       "If you set the parameter “contract_reference” to true, make sure your policy contains a " + \
                       "contract reference."
        }
    return {
        'status': 'ok',
        'message': 'CCMAPI Offer is set up correctly'
    }


@router.post('/feedbackmessage-validation/',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def feedback_message_validation(payload: Dict,
                                      semantic_id_header: Optional[str] = SEMANTIC_ID_FEEDBACK_MESSAGE_HEADER,
                                      semantic_id_content: Optional[str] = SEMANTIC_ID_FEEDBACK_MESSAGE_CONTENT,
                                      timeout: int = 80):
    """
        This test case validates if a feedback message that is given as input conforms with the corresponding semantic
        model. It accepts the feedback types for “Status:Received”, “Status:Rejected” and “Status:Accepted”.
        The test case is successful if the validation did not return any errors.
    •	:param semantic_id_header: String. Defaults to urn:samm:io.catenax.shared.message_header:3.0.0#MessageHeaderAspect
    and points to the semantic model against which the feedback header should be validated.
    •	:param semantic_id_content: String. Defaults to urn:samm:io.catenax.message:1.0.0#MessageContentAspect
    and points to the semantic model against which the feedback body should be validated.
    •	:return: A dictionary containing a success or an error message.
        """
    try:
        header_validation_errors, content_validation_errors = run_feedback_check(semantic_id_header=semantic_id_header,
                           semantic_id_content=semantic_id_content,
                           validation_schema=payload)
    
    except HTTPError as e:
        logger.error(f"Feedback validation failed with multiple errors: {e.json}")

        raise

    return {'message': 'Feedback message validation completed.',
            'header_validation_message': header_validation_errors,
            'content_validation_message': content_validation_errors}



@router.get('/feedbackmechanism-validation/',
            response_model=Dict,
            dependencies=[Depends(verify_auth)])
async def feedback_mechanism_validation(counter_party_address: str,
                                        counter_party_id: str,
                                        message_type: Optional[Literal['RECEIVED',
                                                                       'ACCEPTED',
                                                                       'REJECTED']] = 'RECEIVED',
                                        timeout: int = 80):
    """
    This test case validates if the feedback mechanism of the test subject works. The test is successful,
    if the test-agent is able to perform the following steps:
    1.	Negotiate access to the CCMAPI Asset of the test subject.
    2.	Send the selected feedback type (RECEIVED, ACCEPTED, REJECTED) to the CCMAPI.

    •	:param counter_party_address: Address of the dsp endpoint of a connector (ends on api/v1/dsp for
    DSP version 2024-01).
    •	:param counter_party_id: The identifier of the test subject that operates the connector.
    Until at least Catena-X Release 25.09 that is the BPNL of the test subject.
    •	:param contract_reference: Boolean (true/false) to toggle if the usage policy attached to the CCMAPI offer
    is with or without a contract reference.
    •	:param message_type: String – one of “RECEIVED”, “ACCEPTED”, “REJECTED”. Indicates which feedback type
    the testbed should send to the test subject.
    •	:return: A dictionary containing a success or an error message.

    """

    dataplane_url, dataplane_access_key = (
            await get_ccmapi_access(counter_party_address = counter_party_address,
                                    counter_party_id = counter_party_id,
                                    operand_left = 'http://purl.org/dc/terms/type',
                                    operand_right = '%https://w3id.org/catenax/taxonomy#CCMAPI%',
                                    asset_validation=True,
                                    timeout=timeout))

    payload = {'header': {'senderFeedbackUrl': counter_party_address,
                          'receiverBpn': counter_party_id,
                          'senderBpn': counter_party_id
                          },
               'content': {}}

    errors = []

    if message_type == 'REJECTED':
        errors = [
                {
                        "certificateErrors": [
                    {
                        "message": "We do not process certificates on Sunday"
                    },
                    {
                        "message": "Certificate has expired in 2024"
                    },
                    {
                        "message": "Certificate was revoked"
                    },
                    {
                        "message": "Unexpected data format"
                    },
                    {
                        "message": "Unexpected language expected English, received Mandarin"
                    },
                    {
                        "message": "Expected PDF, received JPG"
                    },
                    {
                        "message": "Unknown BPNL000000000000"
                    }
                ],
                "locationErrors": [
                    {
                        "bpn": "BPNS000000000002",
                        "locationErrors": [
                            {
                                "message": "Site BPNS000000000002 has been Rejected"
                            }
                        ]
                    },
                    {
                        "bpn": "BPNS000000000003",
                        "locationErrors": [
                            {
                                "message": "Site BPNS000000000003 is missing"
                            }
                        ]
                    }
                    ]
                }
        ]

    await send_feedback(payload, message_type, dataplane_url, dataplane_access_key, errors=errors, timeout=timeout)

    return {'status': 'ok',
            'message': f'{message_type} feedback sent successfully'}


@router.post('/cert-validation-test/',
             response_model=Dict,
             dependencies=[Depends(verify_auth)])
async def validate_certificate(payload: Dict,
                               semantic_id_header: Optional[str] = SEMANTIC_ID_FEEDBACK_MESSAGE_HEADER,
                               semantic_id_content: Optional[str] = SEMANTIC_ID_BUSINESS_PARTNER_CERTIFICATE,
                               contract_reference: bool = False,
                               timeout: int = 80):
    """
    This test case validates if a certificate that is given as input conforms with the latest
    Business Partner Certificate semantic model
    (urn:samm:io.catenax.business_partner_certificate:3.1.0#BusinessPartnerCertificate).
    It also tries to send out an initial “RECEIVED”  or “REJECTED” feedback message to the connector that’s specified
    in the header of the certificate depending on the semantic model validation result.
    The test is successful if the test-agent was able to perform the following steps:
    1.	Validate the certificate that’s given in the request body against
    the Business Partner Certificate semantic model
    2.	Negotiate access to the CCMAPI asset of the connector and BPNL that are defined in the certificate header as
    “senderFeedbackUrl” and “senderBpn”.
    3.	Send a “RECEIVED”, or “REJECTED” feedback message to the CCMAPI asset dependent on the validation result
    of step 1. and receive a status code 200.
    •	:param semantic_id_content: String. Defaults to
    urn:samm:io.catenax.business_partner_certificate:3.1.0#BusinessPartnerCertificate
    and points to the semantic model against which the certificate should be validated.
    •	:param contract_reference: Boolean (true/false) to toggle if the usage policy attached to the CCMAPI offer is
    with or without a contract reference.
    •	:return: A dictionary containing a success or an error message.
    """

    dataplane_url, dataplane_access_key = await get_ccmapi_access(
                                                counter_party_address=payload.get('header').get('senderFeedbackUrl'),
                                                counter_party_id=payload.get('header').get('senderBpn'),
                                                operand_left='http://purl.org/dc/terms/type',
                                                operand_right='%https://w3id.org/catenax/taxonomy#CCMAPI%',
                                                asset_validation=True,
                                                timeout=timeout)

    await send_feedback(payload, 'RECEIVED', dataplane_url, dataplane_access_key, errors=[], timeout=timeout)

    result_asset_policy = {}
    
    result_asset_policy = await validate_ccmapi_offer_setup(
        counter_party_address=payload.get('header').get('senderFeedbackUrl'),
        counter_party_id=payload.get('header').get('senderBpn'),
        contract_reference=contract_reference,
        timeout=timeout)

    header_validation_errors, cert_validation_errors = run_certificate_checks(semantic_id_header=semantic_id_header,
                            semantic_id_content=semantic_id_content,
                            validation_schema=payload
                            )

    if cert_validation_errors.get('status') == 'nok' or header_validation_errors.get('status') == 'nok': 
        await send_feedback(payload, 'REJECTED', dataplane_url, dataplane_access_key, errors=[cert_validation_errors], timeout=timeout)

    await send_feedback(payload, 'ACCEPTED', dataplane_url, dataplane_access_key, errors=[], timeout=timeout)

    if 'warning' in result_asset_policy:
        return {
            'message': 'Certificate validation completed.',
            'message_header_validation_message': header_validation_errors,
            'certificate_validation_message': cert_validation_errors,
            "policy_validation_message": result_asset_policy,
            'details': 'Validation was successful, but policy is missing or is not accurate. ' + \
            'Please check https://catenax-ev.github.io/docs/next/standards/' + \
            'CX-0135-CompanyCertificateManagement#216-usage-policy (Release Saturn) for troubleshooting. ' + \
            'If you set the parameter “contract_reference” to true, ' + \
            'make sure your policy contains a contract reference.'
        }

    return {
        'message': 'Certificate validation completed.',
        'message_header_validation_message': header_validation_errors,
        'certificate_validation_message': cert_validation_errors,
        "policy_validation_message": result_asset_policy}

            