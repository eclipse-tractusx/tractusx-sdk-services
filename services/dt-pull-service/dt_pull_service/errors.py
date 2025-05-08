"""Classes and methods for errorhandling
"""

from enum import Enum, auto, unique
from typing import Any, Dict, Optional

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
    BAD_GATEWAY = auto()
    UNKNOWN_ERROR = auto()


#: A dictionary of non-default error codes.
non_default_http_codes = {
    Error.FORBIDDEN: 403,
    Error.BAD_GATEWAY: 502,
    Error.UNKNOWN_ERROR: 520
}


class HTTPError(HTTPException):
    """
    Class for handling errors in the application.

    :param error_code: The specific error code of type `Error`.
    :param message: A message describing the error.
    :param details: Additional details about the error.
    :param headers: Optional HTTP headers to include in the response.
    :param extra_data: Extra data to include in the error JSON.
    """
    def __init__(self,
                 error_code: Error,
                 message: str,
                 details: str,
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
        """Returns a specific json for the client
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
