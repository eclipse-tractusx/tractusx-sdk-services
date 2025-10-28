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

import httpx
from fastapi import APIRouter

from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.logging.log_manager import LoggingManager

router = APIRouter()
logger = LoggingManager.get_logger(__name__)

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
            logger.error(f'Request to {url} failed due to the DT Pull Service, it is probably down, or config error: {e}')

            raise HTTPError(Error.BAD_GATEWAY,
                            message='Fetching data from DT Pull Service failed',
                            details='Check the config, if the DT Pull Service was set correctly, ' + \
                                     'or if the service is down.') from e

        except httpx.RequestError as e:
            logger.error(f'Request to {url} failed: {e}')

            raise HTTPError(Error.BAD_GATEWAY,
                            message='An unknown error occurred while fetching data',
                            details=str(e)) from e


async def make_request_verbose(method: str, url: str, timeout:int=80, **kwargs):
    """
    Makes an HTTP request and handles errors consistently.

    :param method: HTTP method (e.g., 'GET', 'POST')
    :param url: The request URL
    :param kwargs: Additional arguments for httpx.request
    :return: A dictionary containing the original request info, the raw response info, and the parsed response_json on success
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

            # Build a comprehensive result including request and response metadata
            sent_request = response.request if hasattr(response, 'request') else None
            request_info = {
                'method': getattr(sent_request, 'method', method) if sent_request else method,
                'url': str(getattr(sent_request, 'url', url)) if sent_request else url,
                'headers': dict(getattr(sent_request, 'headers', {})) if sent_request else {},
                'content': None
            }
            try:
                # sent_request.content is bytes when available
                if sent_request and getattr(sent_request, 'content', None) is not None:
                    request_info['content'] = sent_request.content.decode('utf-8', errors='ignore')
            except Exception:
                # best-effort only
                pass

            response_info = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text,
            }

            return {
                'request': request_info,
                'response': response_info,
                'response_json': response_json,
            }

        except httpx.TimeoutException as e:
            logger.error(f'Request to {url} timed out')

            raise HTTPError(Error.BAD_GATEWAY,
                            message=f'The request to {url} timed out',
                            details='Check if your connector is reachable from' + \
                                    'the internet and if it has enough resources to process the request') from e

        except httpx.ConnectError as e:
            logger.error(f'Request to {url} failed due to the DT Pull Service, it is probably down, or config error: {e}')

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


async def make_request_status_only(method: str, url: str, timeout: int = 80, **kwargs) -> dict:
    """
    Makes an HTTP request and validates only the HTTP status code, but returns IO metadata.

    - Returns a dict { request, response, response_json } when the status code is 2xx.
      response_json will be None if the response body is not JSON or is empty.
    - For non-2xx responses, raises HTTPError but attaches a details dict that includes
      the same IO metadata: { request, response, response_json } so callers can surface
      it in traceability even on failure.

    :param method: HTTP method (e.g., 'GET', 'POST')
    :param url: The request URL
    :param timeout: Timeout for the request in seconds. Default is 80 seconds.
    :param kwargs: Additional arguments forwarded to httpx.request
    :return: A dictionary with request/response metadata and optional parsed response_json on success
    :raises HTTPError: if the request fails or returns a non-2xx status code
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(method, url, timeout=timeout, **kwargs)

            # Build metadata result, attempt to parse JSON if present (best-effort)
            sent_request = response.request if hasattr(response, 'request') else None
            request_info = {
                'method': getattr(sent_request, 'method', method) if sent_request else method,
                'url': str(getattr(sent_request, 'url', url)) if sent_request else url,
                'headers': dict(getattr(sent_request, 'headers', {})) if sent_request else {},
                'content': None
            }
            try:
                if sent_request and getattr(sent_request, 'content', None) is not None:
                    request_info['content'] = sent_request.content.decode('utf-8', errors='ignore')
            except Exception:
                # best-effort only
                pass

            response_info = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text,
            }

            parsed_json = None
            try:
                parsed_json = response.json()
            except ValueError:
                parsed_json = None

            # Success path for any 2xx status
            if 200 <= response.status_code < 300:
                return {
                    'request': request_info,
                    'response': response_info,
                    'response_json': parsed_json,
                }

            # Non-2xx: raise with rich details including IO metadata
            error_code_enum = Error.BAD_GATEWAY
            message = f'Unexpected status code {response.status_code}'
            details_text = 'No additional details provided'
            if isinstance(parsed_json, dict):
                error_code = parsed_json.get('error', 'BAD_GATEWAY')
                message = parsed_json.get('message', message)
                details_text = parsed_json.get('details', details_text)
                error_code_enum = Error.__members__.get(error_code, Error.BAD_GATEWAY)
            elif response.text:
                details_text = response.text

            raise HTTPError(
                error_code_enum,
                message=message,
                details={
                    'message': details_text,
                    'request': request_info,
                    'response': response_info,
                    'response_json': parsed_json,
                },
            )

        except httpx.TimeoutException as e:
            logger.error(f'Request to {url} timed out')
            raise HTTPError(
                Error.BAD_GATEWAY,
                message=f'The request to {url} timed out',
                details='Check if your connector is reachable from the internet and if it has enough resources to process the request',
            ) from e
        except httpx.ConnectError as e:
            logger.error(f'Request to {url} failed due to the DT Pull Service, it is probably down, or config error: {e}')
            raise HTTPError(
                Error.BAD_GATEWAY,
                message='Fetching data from DT Pull Service failed',
                details='Check the config, if the DT Pull Service was set correctly, or if the service is down.',
            ) from e
        except httpx.RequestError as e:
            logger.error(f'Request to {url} failed: {e}')
            raise HTTPError(
                Error.BAD_GATEWAY,
                message='An unknown error occurred while performing the request',
                details=str(e),
            ) from e
