#################################################################################
# Tractus-X - Industry Flag Service
#
# Copyright (c) 2025 CGI Deutschland B.V. & Co. KG
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
# distributed under the License is distributed on an "AS IS" BASIS
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the
# License for the specific language govern in permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
#################################################################################

import requests
from fastapi.responses import JSONResponse, Response
from fastapi import FastAPI, Request
from io import BytesIO
import logging
import urllib.parse
import collections


logger = logging.getLogger('staging')


class HttpUtils:

    # do get request without session
    def do_get(url, verify=False, headers=None, timeout=None, params=None, allow_redirects=False):
        return requests.get(url=url, verify=verify,
                            timeout=timeout, headers=headers,
                            params=params, allow_redirects=allow_redirects)

    # do get request with session
    def do_get(url, session=None, verify=False, headers=None, timeout=None, params=None, allow_redirects=False):
        if session is None:
            session = requests.Session()
        return session.get(url=url, verify=verify,
                           timeout=timeout, headers=headers,
                           params=params, allow_redirects=allow_redirects)

    # do post request without session
    def do_post(url, data=None, verify=False, headers=None, timeout=None, json=None, allow_redirects=False):
        return requests.post(url=url, verify=verify,
                             timeout=timeout, headers=headers,
                             data=data, json=json,
                             allow_redirects=allow_redirects)

    # do post request with session
    def do_post(url, session=None, data=None, verify=False, headers=None, timeout=None, json=None, allow_redirects=False):
        if session is None:
            session = requests.Session()
        return session.post(url=url, verify=verify,
                            timeout=timeout, headers=headers,
                            data=data, json=json,
                            allow_redirects=allow_redirects)

    # prepare response
    @staticmethod
    def response(data, status=200, content_type='application/json'):
        response = JSONResponse(data, status)
        response.headers["Content-Type"] = content_type
        return response

    @staticmethod
    def get_host(url):
        return HttpUtils.explode_url(url=url).netloc

    @staticmethod
    def explode_url(url):
        return urllib.parse.urlparse(url=url)

    @staticmethod
    def empty_response(status=204):
        return Response(status_code=status)

    @staticmethod
    def proxy(response: requests.Response) -> Response:
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get('content-type', 'application/json')
        )

    @staticmethod
    def file_response(buffer: BytesIO, filename: str, status=200, content_type='application/pdf'):
        headers = {'Content-Disposition': f'inline; filename="{filename}"'}
        return Response(buffer.getvalue(), status_code=status, headers=headers, media_type=content_type)

    # Generates a error response with message
    @staticmethod
    def get_error_response(status=500, message="It was not possible to process/execute this request!"):
        return HttpUtils.response({
            "message": message,
            "status": status
        }, status)

    @staticmethod
    async def get_body(request):
        return await request.json()

    @staticmethod
    def get_not_authorized():
        return HttpUtils.response({
            "message": "Not Authorized",
            "status": 401
        }, 401)

    @staticmethod
    def is_authorized(request, bpn, config):
        if not ("authorization" in config):
            logger.error("No authorization module configuration is available!")
            return False

        # Checks for configuration integrity
        authorization = config["authorization"]

        if "enabled" in authorization and authorization["enabled"] == False:
            return True

        if not ("apiKeys" in authorization):
            logger.error(
                "No apiKeys configuration is available in authorization!")
            return False

        # Get the dictionary with the api keys
        apiKeys = authorization["apiKeys"]

        if not (bpn in apiKeys):
            logger.error("This BPN is not allowed for this wallet!")
            return False

        # Get the BPN Api key
        configApiKey = apiKeys[bpn]

        if (configApiKey is None) or (configApiKey == ""):
            logger.error("The configuration api key is None or empty!")
            return False

        # Get the headers from the request
        headers = request.headers

        if headers is None:
            logger.error("No headers are available!")
            return False

        if not ("X-Api-Key" in headers):
            logger.error(
                "No API Key Header was specified in the request header!")
            return False

        # Get the api key from the headers
        apiKey = headers["X-Api-Key"]

        if (apiKey is None) or (apiKey == ""):
            logger.error("The api key is empty or None!")
            return False

        # Check if the api key and the config key are the same
        if (apiKey != configApiKey):
            logger.error(
                "The api key is not the same as the authorization key configured!")
            return False

        return True

    @staticmethod
    def join_path(url, path):
        return urllib.parse.urljoin(base=url, url=path)
