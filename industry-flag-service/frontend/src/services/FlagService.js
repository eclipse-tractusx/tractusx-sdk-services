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

import BackendService from "./BackendService";

export default class FlagService {
  backendService = null;
  constructor() {
    this.backendService = new BackendService();
  }

  getCompanyFlags(method, endpoint, headers, data = null) {
    return this.backendService
      .apiRequest(method, endpoint, headers, data)
      .then((response) => {
        // console.log(response.data);
        const dataArray = Object.entries(response.data);
        return dataArray;
      })
      .catch((error) => {
        console.error(error);
        return { message: error.message, status: error.status };
      });
  }
  validateBpn(BpnNumber) {
    const pattern = /^BPNL[A-Z0-9]{12}$/;

    // Check if the input matches the pattern
    return pattern.test(BpnNumber) ? true : false;
  }
}
