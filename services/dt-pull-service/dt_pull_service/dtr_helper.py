"""Helper methods for DtrHandler class
"""

from dt_pull_service.models import DtrHandler


def get_dtr_handler(dtr_url: str, authorization: str):
    """
    Creates and returns an instance of the DtrHandler.

    This function initializes an DtrHandler object to interact with the Digital Twin Registry (DTR).

    :param dtr_url: The URL to access the DTR.
    :param authorization: The negotiated key to access the DTR.
    :return: An initialized DtrHandler instance.
    """

    dtr_handler = DtrHandler(
            dtr_url,
            authorization,
            '',
    )

    return dtr_handler
