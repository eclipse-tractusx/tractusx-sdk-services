"""
Classes and methods for error handling in the application.

This module provides:
1. Custom error enumeration (`Error`) for non-default HTTP response codes.
2. An `HTTPError` class for detailed error handling.
3. A handler (`http_error_handler`) for processing and responding to HTTPError exceptions.
"""

from enum import Enum, auto, unique
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


@unique
class Error(Enum):
    """
    Non-default errors used by the application

    This enum defines custom error codes for HTTP responses.
    """

    BAD_REQUEST = auto()
    FORBIDDEN = auto()
    UNPROCESSABLE_ENTITY = auto()
    INTERNAL_SERVER_ERROR = auto()
    CONNECTION_FAILED = auto()
    BAD_GATEWAY = auto()
    UNKNOWN_ERROR = auto()
    ASSET_NOT_FOUND = auto()
    CONTRACT_NEGOTIATION_FAILED = auto()
    AAS_ID_NOT_FOUND = auto()
    SUBMODEL_DESCRIPTOR_NOT_FOUND = auto()
    SUBMODEL_DESCRIPTOR_MALFORMED = auto()
    ASSET_ACCESS_FAILED = auto()
    POLICY_VALIDATION_FAILED = auto()
    DATA_TRANSFER_FAILED = auto()
    SUBMODEL_VALIDATION_FAILED = auto()
    NO_SHELLS_FOUND = auto()


#: A dictionary of non-default error codes.
non_default_http_codes = {
    Error.FORBIDDEN: 403,
    Error.AAS_ID_NOT_FOUND: 404,
    Error.ASSET_NOT_FOUND: 404,
    Error.SUBMODEL_DESCRIPTOR_NOT_FOUND: 404,
    Error.CONTRACT_NEGOTIATION_FAILED: 409,
    Error.POLICY_VALIDATION_FAILED: 422,
    Error.SUBMODEL_DESCRIPTOR_MALFORMED: 422,
    Error.SUBMODEL_VALIDATION_FAILED: 422,
    Error.UNPROCESSABLE_ENTITY: 422,
    Error.NO_SHELLS_FOUND: 422,
    Error.INTERNAL_SERVER_ERROR: 500,
    Error.ASSET_ACCESS_FAILED: 502,
    Error.BAD_GATEWAY: 502,
    Error.CONNECTION_FAILED: 502,
    Error.DATA_TRANSFER_FAILED: 502,
    Error.UNKNOWN_ERROR: 520
}


class HTTPError(HTTPException):
    """Class for handling errors in the application.

    :param error_code: The specific error code of type `Error`.
    :param message: A message describing the error.
    :param details: Additional details about the error.
    :param headers: Optional HTTP headers to include in the response.
    :param extra_data: Extra data to include in the error JSON.
    """

    def __init__(self,
                 error_code: Error,
                 message: str,
                 details: Union[str, Dict],
                 headers: Optional[Dict[str, Any]] = None,
                 **extra_data):
        status_code = non_default_http_codes.get(error_code, 400)

        super().__init__(status_code=status_code)

        self.error_code = error_code
        self.message = message
        self.details = details
        self.headers = headers
        self.extra_data = extra_data

    @property
    def json(self) -> Dict[str, Any]:
        """
        Generates a JSON object representing the error details.

        :return: A dictionary containing the error code, message, details, and any extra data.
        """
        ret = self.extra_data
        ret.update({
            "error": self.error_code.name,
            "details": self.details,
            "message": self.message
        })

        return ret


async def http_error_handler(_: Request, exc: HTTPError) -> JSONResponse:
    """
    Handles HTTPError exceptions and returns a JSON response.

    :param request: The incoming HTTP request object.
    :param exc: The HTTPError instance containing error details.
    :return: A JSONResponse containing the error details and status code.
    """

    response_kwargs = {
        'status_code': exc.status_code
    }

    if exc.headers:
        response_kwargs['headers'] = exc.headers

    return JSONResponse(exc.json, **response_kwargs)
