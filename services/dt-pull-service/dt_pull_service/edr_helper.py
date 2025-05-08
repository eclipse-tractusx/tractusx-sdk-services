"""Helper methods for EdrHandler class
"""

from dt_pull_service import config
from dt_pull_service.models import EdrHandler


def get_edr_handler(bpn: str, counter_party_address: str):
    """
    Creates and returns an instance of the EdrHandler.

    This function initializes an EdrHandler object to interact with the Endpoint Data Reference (EDR).
    The handler is configured with essential details such as the Business Partner Number (BPN),
    counterparty address, and API credentials.

    :param bpn: The Business Partner Number of the counterparty.
    :param counter_party_address: The address of the counterparty's EDC (Eclipse Dataspace Connector).
    :return: An initialized EdrHandler instance.
    """

    edr_handler = EdrHandler(
            bpn,
            counter_party_address,
            config.BASE_URL,
            config.API_KEY
    )

    return edr_handler
