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

from fastapi import FastAPI, Depends

from fastapi.security import APIKeyHeader

from test_orchestrator.api import (
    asset,
    base_test_cases,
    cert_validation,
    industry_test_cases,
    traceability_test,
    special_characteristics
)
from test_orchestrator.cache import create_cache_provider
from test_orchestrator.errors import (
    HTTPError,
    http_error_handler,
    ValidationException,
    validation_exception_handler
)
from test_orchestrator.logging.log_manager import LoggingManager

logger = LoggingManager.get_logger(__name__)



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
    api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

    async def get_api_key(api_key_header: str = Depends(api_key_header)):
        if api_key_header != "dein_schluessel":
            raise HTTPException(status_code=401)
        return api_key_header
    async def secure_endpoint(key: str = Depends(get_api_key)):
        return {"status": "ok"}

    logger.info('Starting of the Test orchestrator application...')

    app = FastAPI(title='Test orchestrator application',
                  description="This application is used for testing  " +
                              "Catena-X access",
                  contact={'name': 'Dénes Surman (dddenes)',
                           'email': 'surmandenes@yahoo.com'},
                           swagger_ui_parameters={})


    app.add_exception_handler(HTTPError, http_error_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)

    app.include_router(asset.router,
                       prefix='/test-cases/asset/v1',
                       tags=['Asset Tests'])

    app.include_router(base_test_cases.router,
                       prefix='/test-cases/base/v1',
                       tags=['Base Tests'])

    app.include_router(cert_validation.router,
                       prefix='/test-cases/businesspartnerdatamanagement/v1',
                       tags=['Certification Tests'])

    app.include_router(industry_test_cases.router,
                       prefix='/test-cases/industry-core/v1',
                       tags=['Industry Core Tests'])

    app.include_router(traceability_test.router,
                       prefix='/test-cases/traceability/v1',
                       tags=['Traceability Tests'])

    app.include_router(special_characteristics.router,
                       prefix='/test-cases/special-characteristics/v1',
                       tags=['Special Characteristics Tests'])

    app.get('/_/health', status_code=200)(health)

    @app.on_event("startup")
    async def startup():
        app.state.cache_provider = create_cache_provider()

    return app
