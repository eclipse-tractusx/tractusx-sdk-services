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

"""Application factory
"""

import logging

from fastapi import FastAPI

from test_orchestrator.api import base_test_cases, cert_validation, industry_test_cases
from test_orchestrator.errors import (
    HTTPError,
    http_error_handler,
    ValidationException,
    validation_exception_handler
)

logger = logging.getLogger(__name__)


async def health():
    """
    Health check endpoint.

    This endpoint is used to verify the application's health status.
    It currently returns no data but responds with a status code of 200 to indicate
    that the service is up and running.
    """

    return


def create_app():
    """
    Creates the main FastAPI application object.

    This function initializes the FastAPI application, sets up exception handlers,
    includes the API routers, and adds a health check endpoint.

    :return: The FastAPI application instance.
    """

    logger.info('Starting of the Test orchestrator application...')

    app = FastAPI(title='Test orchestrator application',
                  description="This application is used for testing  " +
                              "Catena-X access",
                  contact={'name': 'Dénes Surman (dddenes)',
                           'email': 'surmandenes@yahoo.com'})

    app.add_exception_handler(HTTPError, http_error_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)

    app.include_router(base_test_cases.router,
                       prefix='/test-cases/base/v1',
                       tags=['Base Tests'])

    app.include_router(cert_validation.router,
                       prefix='/test-cases/businesspartnerdatamanagement/v1',
                       tags=['Certification Tests'])

    app.include_router(industry_test_cases.router,
                       prefix='/test-cases/industry-core/v1',
                       tags=['Industry Core Tests'])

    app.get('/_/health', status_code=200)(health)

    return app
