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
import { Buffer } from "buffer";

export default class DownloadFlagService {
  backendService = null;
  constructor() {
    this.backendService = new BackendService();
  }

  async downloadPartnerCompanyFlag(method, endpoint, headers, data) {
    try {
      // Download Partner Company Flag
      const response = await this.downloadProof(
        method,
        endpoint,
        headers,
        data
      );

      var buffer = new Buffer(response.data, "binary");

      let content_type = response.headers["content-type"];

      let proof = buffer;
      let filename = data.id + ".txt";
      if (content_type === "application/json") {
        filename = data.id + ".json";
        proof = JSON.stringify(JSON.parse(buffer.toString()), null, 2);
      } else {
        filename = response.headers["content-disposition"]
          .split("filename=")[1]
          .trim('"')
          .replace(/^"(.*)"$/, "$1");
      }
      if (proof) {
        // Create a temporary URL for the Blob
        // Create a temporary <a> element to trigger the download

        const file = new Blob([proof], { type: content_type });
        this.createDownloadElement(file, filename);
        return { status: true, message: proof };
      }
    } catch (error) {
      console.error("Error downloading a flag:", error);
      return { status: false, data: error };
    }
  }

  async downloadMyCompanyFlag(method, endpoint, headers, id) {
    try {
      // Download My Company Flag
      const response = await this.downloadProof(method, endpoint, headers);

      var buffer = new Buffer(response.data, "binary");

      let content_type = response.headers["content-type"];

      let proof = buffer;
      let filename = id + ".txt";
      if (content_type === "application/json") {
        filename = id + ".json";
        proof = JSON.stringify(JSON.parse(buffer.toString()), null, 2);
      } else {
        filename = response.headers["content-disposition"]
          .split("filename=")[1]
          .trim('"')
          .replace(/^"(.*)"$/, "$1");
      }
      if (proof) {
        // Create a temporary URL for the Blob
        // Create a temporary <a> element to trigger the download

        const file = new Blob([proof], { type: content_type });
        this.createDownloadElement(file, filename);
        return { status: true, message: proof };
      }
    } catch (error) {
      console.error("Error downloading a flag:", error);
      return { status: false, message: error };
    }
  }

  createDownloadElement(file, filename) {
    // anchor link
    const element = document.createElement("a");
    const link = URL.createObjectURL(file);
    element.href = link;
    element.download = filename;

    document.body.appendChild(element); // Required for this to work in FireFox
    element.click();
    document.body.removeChild(element);
    window.URL.revokeObjectURL(link);
  }

  async downloadProof(method, endpoint, headers, data = null) {
    return await this.backendService
      .proofApiRequest(method, endpoint, headers, data)
      .then((response) => {
        return response;
      })
      .catch((error) => {
        console.error(error);
        return [];
      });
  }
}
