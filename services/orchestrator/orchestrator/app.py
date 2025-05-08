"""Application factory
"""

import logging

from fastapi import FastAPI

from orchestrator.api import base_test_cases, industry_test_cases
from orchestrator.errors import HTTPError, http_error_handler

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

    app.include_router(base_test_cases.router,
                       prefix='/test-cases/base/v1',
                       tags=['Tests'])

    app.include_router(industry_test_cases.router,
                       prefix='/test-cases/industry-core/v1',
                       tags=['Tests'])

    app.get('/_/health', status_code=200)(health)

    return app
