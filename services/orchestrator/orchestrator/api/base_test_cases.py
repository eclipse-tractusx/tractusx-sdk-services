"""
Endpoints to run tests on the data returned by the DT Pull Service.

This module includes:
1. `ping-test` endpoint to validate basic catalog requests.
2. `full-test` endpoint for validating shell descriptors and JSON objects.
"""


import logging
from typing import Dict

from fastapi import APIRouter

from orchestrator import config
from orchestrator.errors import Error, HTTPError
from orchestrator.request_handler import make_request
from orchestrator.utils import get_dtr_access

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('/ping-test/',
            response_model=Dict)
async def ping_test(counter_party_address: str,
                    counter_party_id: str):
    """
    This test case executes a catalogue request for the dsp endpoint of a specified connector (counter_party_address)
    to check if the connector is reachable. The test is successful if the test-agent receives a status code 200
    and an (empty) result set from the specified connector.

     - :param counter_party_address: Address of the dsp endpoint of a connector
                                     (ends on api/v1/dsp for DSP version 2024-01).
     - :param counter_party_id: The identifier of the test subject that operates the connector.
                                Unitil at least Catena-X Release 25.09 that is the BPNL of the test subject.
     - :return: A dictionary with the status and a message indicating success.
    """

    try:
        await make_request('GET',
                           f'{config.DT_PULL_SERVICE_ADDRESS}/edr/get-catalog/',
                           params={'operand_left': 'http://purl.org/dc/terms/type',
                                   'operand_right': '%https://w3id.org/catenax/taxonomy%23DigitalTwinRegistry%',
                                   'counter_party_address': counter_party_address,
                                   'counter_party_id': counter_party_id})

    except HTTPError:
        raise HTTPError(Error.CONNECTION_FAILED,
                        message='Connection to the connector was not successful',
                        details='Please check ' + \
                                'https://eclipse-tractusx.github.io/docs-kits/kits/connector-kit/operation-view/ ' +\
                                'for troubleshooting.')

    return {'status': 'ok',
            'message': 'No errors found during the ping request'}


@router.get('/dtr-ping-test/',
            response_model=Dict)
async def dtr_ping_test(counter_party_address: str,
                        counter_party_id: str):
    """
    This test case checks if the digital twin registry (DTR) of the test subject is reachable.
    The test is successful if the test-agent was able to perform the following steps:

    1.	Query for the digital twin registry (DTR) asset in the specified connector (counter_party_address).
    2.	Check for the correctness of all properties of the DTR asset.
    3.	Negotiate access to the DTR asset.
    4.	Access the DTR through the data plane of the connector.

     - :param counter_party_address: Address of the dsp endpoint of a connector
                                     (ends on api/v1/dsp for DSP version 2024-01).
     - :param counter_party_id: The identifier of the test subject that operates the connector.
                                Unitil at least Catena-X Release 25.09 that is the BPNL of the test subject.
     - :param strict_validation: Boolean (true/false) to toggle if the usage policy attached
                                 to the DTR offer is exactly as specified in the DTR KIT.
     - :return: A dictionary containing a success or an error message.
    """

    try:
        dataplane_url, dtr_key, _ = await get_dtr_access(
                counter_party_address,
                counter_party_id,
                operand_left='http://purl.org/dc/terms/type',
                operand_right='%https://w3id.org/catenax/taxonomy#DigitalTwinRegistry%',
                limit=1)

        shell_descriptors = await make_request('GET',
                                               f'{config.DT_PULL_SERVICE_ADDRESS}/dtr/shell-descriptors/',
                                               params={'dataplane_url': dataplane_url},
                                               headers = {'Authorization': dtr_key})
    except HTTPError:
        raise HTTPError(
            Error.CONNECTION_FAILED,
            message='The DTR could not be accessed. Either the EDC asset or the DTR itself is misconfigured.',
            details='Please check ' +\
                    'https://github.com/eclipse-tractusx/sldt-digital-twin-registry/blob/main/INSTALL.md ' +\
                    'for troubleshooting.')

    return {'status': 'ok',
            'message': 'No errors found, the DTR is reachable'}
