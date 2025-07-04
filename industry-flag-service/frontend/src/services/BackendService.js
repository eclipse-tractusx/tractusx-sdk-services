/*
  Tractus-X - Industry Flag Service

  Copyright (c) 2025 CGI Deutschland B.V. & Co. KG
  Copyright (c) 2025 Contributors to the Eclipse Foundation

  See the NOTICE file(s) distributed with this work for additional
  information regarding copyright ownership.

  This program and the accompanying materials are made available under the
  terms of the Apache License, Version 2.0 which is available at
  https://www.apache.org/licenses/LICENSE-2.0.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
  either express or implied. See the
  License for the specific language govern in permissions and limitations
  under the License.

  SPDX-License-Identifier: Apache-2.0
*/

import { BACKEND_URL } from "./service.const.js";
import axios from "axios";

export default class BackendService {
  async apiRequest(method, url, headers, data = null) {
    try {
      const response = await axios({
        method,
        url,
        data: method === "POST" ? data : null, // Only include data for POST requests
        headers,
      });

      return Promise.resolve(response); // Return the API response data
    } catch (error) {
      // Handle errors here. You can return or throw the error, depending on your use case.
      return Promise.reject(
        error.response ? error.response.data : error.message
      );
    }
  }
  async proofApiRequest(method, url, headers, data = null) {
    try {
      const response = await axios({
        method,
        url,
        data: method === "POST" ? data : null, // Only include data for POST requests
        headers,
        responseType: "arraybuffer",
      });

      return Promise.resolve(response); // Return the API response data
    } catch (error) {
      // Handle errors here. You can return or throw the error, depending on your use case.
      return Promise.reject(
        error.response ? error.response.data : error.message
      );
    }
  }

  async searchCompanyFlagsByBpn(body) {
    try {
      return new Promise((resolve) => {
        axios
          .request({
            baseURL: `${BACKEND_URL}/flags/search`,
            method: "POST",
            headers: {
              "X-Api-Key": "ifs-api-key",
              "Content-Type": "application/json",
            },
            data: body,
          })
          .then((response) => {
            resolve(response.data);
          })
          .catch((e) => {
            if (e.response.data) {
              resolve(e.response.data);
            } else if (e.request) {
              resolve(e.request);
            } else {
              resolve(e.message);
            }
          });
      });
    } catch (e) {
      return "Error -> " + e.message;
    }
  }
  async searchCompanyFlagsProof(body) {
    try {
      return new Promise((resolve) => {
        axios
          .request({
            baseURL: `${BACKEND_URL}/flags/proof`,
            method: "POST",
            headers: {
              "X-Api-Key": "ifs-api-key",
              "Content-Type": "application/json",
            },
            data: body,
          })
          .then((response) => {
            resolve(response.data);
          })
          .catch((e) => {
            if (e.response.data) {
              resolve(e.response.data);
            } else if (e.request) {
              resolve(e.request);
            } else {
              resolve(e.message);
            }
          });
      });
    } catch (e) {
      return "Error -> " + e.message;
    }
  }
  async getMyProof(id) {
    return new Promise((resolve) => {
      axios
        .request({
          baseURL: `${BACKEND_URL}/api/flags/${id}`,
          method: "GET",
          headers: {
            "X-Api-Key": "ifs-api-key",
            "Content-Type": "application/json",
          },
        })
        .then((response) => {
          resolve(response.data);
        })
        .catch((e) => {
          if (e.response.data) {
            resolve(e.response.data);
          } else if (e.request) {
            resolve(e.request);
          } else {
            resolve(e.message);
          }
        });
    });
  }
  getErrorMessage(message, status, statusText) {
    return {
      message: message,
      status: status,
      statusText: statusText,
    };
  }
  getHeaders(authentication) {
    return {
      headers: {
        Accept: "application/json",
        Authorization: "Bearer " + authentication.getAccessToken(),
      },
    };
  }
}
