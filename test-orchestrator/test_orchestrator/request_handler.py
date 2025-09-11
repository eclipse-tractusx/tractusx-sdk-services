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
# WITHOUT WARRANTIES OR SERVICES OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
# *************************************************************

"""Contains utilities to handle common request parts
"""

import asyncio
import logging

from fastapi import APIRouter
import httpx

from test_orchestrator.errors import Error, HTTPError

router = APIRouter()
logger = logging.getLogger(__name__)


async def make_request(method: str, url: str, timeout:int=80, **kwargs):
    """
    Makes an HTTP request and handles errors consistently.

    :param method: HTTP method (e.g., 'GET', 'POST')
    :param url: The request URL
    :param kwargs: Additional arguments for httpx.request
    :return: Response JSON if successful
    :raises HTTPError: Custom exception if request fails
    """

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(method, url, timeout=timeout, **kwargs)
            try:
                response_json = response.json()
            except ValueError as e:
                logger.error(f'Invalid JSON response from {url}: {e} - {response.content}')
                raise HTTPError(Error.BAD_GATEWAY,
                                message='Received invalid JSON from server',
                                details=str(e)) from e

            if response.status_code != 200:
                error_code = response_json.get('error', 'BAD_GATEWAY')
                message = response_json.get('message', 'Unknown error')
                details = response_json.get('details', 'No additional details provided')
                error_code_enum = Error.__members__.get(error_code, Error.BAD_GATEWAY)
                raise HTTPError(error_code_enum,
                                message=message,
                                details=details)

            return response_json

        except httpx.TimeoutException as e:
            logger.error(f'Request to {url} timed out')

            raise HTTPError(Error.BAD_GATEWAY,
                            message=f'The request to {url} timed out',
                            details='Check if your connector is reachable from' + \
                                    'the internet and if it has enough resources to process the request') from e

        except httpx.ConnectError as e:
            logger.error(f'Request to {url} failed due to the DT Pull Service, it is probably down, or config error')

            raise HTTPError(Error.BAD_GATEWAY,
                            message='Fetching data from DT Pull Service failed',
                            details='Check the config, if the DT Pull Service was set correctly, ' + \
                                     'or if the service is down.') from e

        except httpx.RequestError as e:
            logger.error(f'Request to {url} failed: {e}')

            raise HTTPError(Error.BAD_GATEWAY,
                            message='An unknown error occurred while fetching data',
                            details=str(e)) from e


async def make_request_with_retry(method: str, url: str, retries: int = 3, delay: int = 2, timeout: int = 80, **kwargs):
    """
    Retrieves a response from an HTTP request with retry logic.

    :param method: HTTP method (e.g., 'GET', 'POST')
    :param url: The request URL
    :param retries: The number of retries we try to get the request to work. Default is 3.
    :param delay: Initial delay (in seconds) between retries. Default is 2 seconds.
    :param timeout: Timeout for the request in seconds. Default is 80 seconds.
    :param kwargs: Additional arguments for httpx.request
    :return: Response JSON if successful
    :raises HTTPError: Custom exception if request fails
    """

    attempt = 0

    while attempt < retries:
        try:
            response = await make_request(method, url, timeout=timeout, **kwargs)

            return response

        except (httpx.RequestError, httpx.TimeoutException) as e:
            attempt += 1
            logger.warning(f'Attempt {attempt} failed: {e}. Retrying...')

            if attempt < retries:
                await asyncio.sleep(delay)
            else:
                logger.error(f'Max retries reached. Failed to get response from {url}')

                raise HTTPError(Error.BAD_GATEWAY,
                                message='Max retries reached. Failed to get response from {url}',
                                details=str(e)) from e

    return None
