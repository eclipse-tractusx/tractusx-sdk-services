"""API endpoints for DTR
"""

from typing import Dict, Optional

from fastapi import APIRouter, Header

from dt_pull_service.dtr_helper import get_dtr_handler

router = APIRouter()


@router.get('/shell-descriptors/',
            response_model=Dict)
async def shell_descriptors(dataplane_url: str,
                            agreement_id: Optional[str] = '',
                            authorization: str = Header(None)):
    """
    Retrieves the shell descriptors from the partner's DTR.

     - :param dataplane_url: The URL for getting the DTR handler.
     - :param agreement_id: The aggrement_id (asset) to get the shell descriptor for.
     - :return: A JSON object containing the shell descriptor details.
    """

    dtr_handler = get_dtr_handler(dataplane_url, authorization)

    return dtr_handler.dtr_find_shell_descriptor(agreement_id)
