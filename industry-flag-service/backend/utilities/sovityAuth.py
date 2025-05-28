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

import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests

logger = logging.getLogger('staging')


class SovityAuth:
    TOKEN_EXPIRATION_MINUTES = 5
    TOKEN_EXPIRATION_BUFFER_SECONDS = 30

    class TokenInfo:
        def __init__(self, token, expiration_time):
            self.token = token
            self.expiration_time = expiration_time

        def is_valid(self):
            return self.token and datetime.now() < self.expiration_time

    def __init__(self):
        self.edc_token_info = self.TokenInfo("", datetime.now())

    def get_edc_token(self, token_url, client_id, client_secret):
        return self._get_token(token_url, client_id, client_secret)

    def _get_token(self, token_url, client_id, client_secret):
        if self.edc_token_info.is_valid():
            return self.edc_token_info.token

        form_data = self._build_form_data(client_id, client_secret)

        try:
            response = self._request_token(token_url, form_data)
            if response is None:
                raise Exception("Failed to get a response from the server")
            self.edc_token_info.token = response.get("access_token")
            if self.edc_token_info.token is None:
                raise Exception("The response does not contain an access_token")

            self.edc_token_info.expiration_time = datetime.now() + timedelta(
                minutes=self.TOKEN_EXPIRATION_MINUTES) - timedelta(
                seconds=self.TOKEN_EXPIRATION_BUFFER_SECONDS)
            return self.edc_token_info.token
        except Exception as e:
            error_message = f"Error getting the token: {str(e)}"
            logger.error(error_message)
            raise

    def _build_form_data(self, client_id, client_secret):
        return urlencode({
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        })

    def _request_token(self, token_url, form_data):
        try:
            return self._send_post_request(token_url, form_data)
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    def _send_post_request(self, token_url, form_data):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(token_url, data=form_data, headers=headers)
        response.raise_for_status()
        return response.json()
