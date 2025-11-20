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
Classes and methods for error handling in the application.

This module provides:
1. Custom error enumeration (`Error`) for non-default HTTP response codes.
2. An `HTTPError` class for detailed error handling.
3. A handler (`http_error_handler`) for processing and responding to HTTPError exceptions.
"""

from enum import Enum, auto, unique
from typing import Any, Dict, List, Optional, Union

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
    UNSUPPORTED_MEDIA_TYPE = auto()

    CERTIFICATE_PARSING_ERROR = auto()
    SCHEMA_VALIDATION_ERROR = auto()
    MISSING_DATA = auto()
    FILE_NOT_FOUND = auto()
    MISSING_REQUIRED_FIELD = auto()
    NULL_FOR_REQUIRED_FIELD = auto()
    REGEX_VALIDATION_FAILED = auto()
    INVALID_PAYLOAD_TYPE = auto()
    MULTIPLE_VALIDATION_ERRORS = auto()
    CONNECTOR_UNAVAILABLE = auto()
    FEEDBACK_COULD_NOT_BE_SENT = auto()
    TOO_MANY_ASSETS_FOUND = auto()
    CATALOG_VERSION_VALIDATION_FAILED = auto()


#: A dictionary of non-default error codes.
non_default_http_codes = {
    Error.FORBIDDEN: 403,
    Error.AAS_ID_NOT_FOUND: 404,
    Error.ASSET_NOT_FOUND: 404,
    Error.SUBMODEL_DESCRIPTOR_NOT_FOUND: 404,
    Error.CONTRACT_NEGOTIATION_FAILED: 409,
    Error.UNSUPPORTED_MEDIA_TYPE: 415,
    Error.POLICY_VALIDATION_FAILED: 422,
    Error.SUBMODEL_DESCRIPTOR_MALFORMED: 422,
    Error.SUBMODEL_VALIDATION_FAILED: 422,
    Error.UNPROCESSABLE_ENTITY: 422,
    Error.CATALOG_VERSION_VALIDATION_FAILED: 422,
    Error.NO_SHELLS_FOUND: 422,
    Error.INTERNAL_SERVER_ERROR: 500,
    Error.ASSET_ACCESS_FAILED: 502,
    Error.BAD_GATEWAY: 502,
    Error.CONNECTION_FAILED: 502,
    Error.DATA_TRANSFER_FAILED: 502,
    Error.UNKNOWN_ERROR: 520,

    Error.CERTIFICATE_PARSING_ERROR: 400,
    Error.SCHEMA_VALIDATION_ERROR: 422,
    Error.MISSING_DATA: 400,
    Error.FILE_NOT_FOUND: 404,
    Error.MISSING_REQUIRED_FIELD: 422,
    Error.NULL_FOR_REQUIRED_FIELD: 422,
    Error.REGEX_VALIDATION_FAILED: 422,
    Error.INVALID_PAYLOAD_TYPE: 422,
    Error.MULTIPLE_VALIDATION_ERRORS: 422,
    Error.CONNECTOR_UNAVAILABLE: 502,
    Error.FEEDBACK_COULD_NOT_BE_SENT: 502,
    Error.TOO_MANY_ASSETS_FOUND: 409,
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


class ValidationException(Exception):
    """
    Custom exception to aggregate multiple validation errors.
    """
    def __init__(self, errors: List[Dict]):
        self.errors = errors
        self.message = "Multiple validation errors occurred."
        super().__init__(self.message)


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


async def validation_exception_handler(_: Request, exc: ValidationException) -> JSONResponse:
    """
    Handles ValidationException and returns a JSON response with a list of errors.
    """

    return JSONResponse(
        status_code=non_default_http_codes[Error.MULTIPLE_VALIDATION_ERRORS],
        content={
            "error": Error.MULTIPLE_VALIDATION_ERRORS.name,
            "message": exc.message,
            "details": exc.errors,
        },
    )
