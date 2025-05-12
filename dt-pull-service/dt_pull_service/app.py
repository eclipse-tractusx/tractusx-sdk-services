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

"""Application factory
"""

import logging

from fastapi import FastAPI

from dt_pull_service.api import dtr, edr
from dt_pull_service.errors import HTTPError, http_error_handler

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

    logger.info('Starting of the DT Pull Service...')

    app = FastAPI(title='DT Pull Service',
                  description="This application is used for pulling DT " +
                              "from Catena-X",
                  contact={'name': 'Dénes Surman (dddenes)',
                           'email': 'surmandenes@yahoo.com'})

    app.add_exception_handler(HTTPError, http_error_handler)

    app.include_router(edr.router,
                       prefix='/edr',
                       tags=['Edr'])

    app.include_router(dtr.router,
                       prefix='/dtr',
                       tags=['Dtr'])

    app.get('/_/health', status_code=200)(health)

    return app
