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

// Get variables that can be empty
let serverUrl = "BACKEND_URL";
let getMyFlags = "ENDPOINT_GET_MY_FLAGS";
let getMyFlagProof = "ENDPOINT_GET_MY_FLAG_PROOF";
let getSearchFlags = "ENDPOINT_SEARCH_FLAGS_BY_BPN";
let getFlagProof = "ENDPOINT_GET_FLAG_PROOF_BY_BPN";
let apiKey = "API_KEY";

// Define constants
const BACKEND_URL = serverUrl;
const ENDPOINT_GET_MY_FLAGS = getMyFlags;
const ENDPOINT_GET_MY_FLAG_PROOF = getMyFlagProof;
const ENDPOINT_SEARCH_FLAGS_BY_BPN = getSearchFlags;
const ENDPOINT_GET_FLAG_PROOF_BY_BPN = getFlagProof;
const API_KEY = apiKey;

export {
  BACKEND_URL,
  ENDPOINT_GET_MY_FLAGS,
  ENDPOINT_GET_MY_FLAG_PROOF,
  ENDPOINT_SEARCH_FLAGS_BY_BPN,
  ENDPOINT_GET_FLAG_PROOF_BY_BPN,
  API_KEY,
};
