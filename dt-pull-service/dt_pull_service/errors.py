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
    INTERNAL_SERVER_ERROR = auto()


#: A dictionary of non-default error codes.
non_default_http_codes = {
    Error.FORBIDDEN: 403,
    Error.INTERNAL_SERVER_ERROR: 500,
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
