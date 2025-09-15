# Company Certificate Mangement (CCM) test-agent – PUSH : Documentation User Guide
## 1. Why Use This Service?

Welcome, supplier! This testbed is a crucial tool for ensuring that your **Company Certificate Management API (CCMAPI)** implementation is compliant with the Catena-X standard **<a href = "https://catenax-ev.github.io/docs/next/standards/CX-0135-CompanyCertificateManagement">CX-0135</a>**.

By using this service, you can:

* **Verify Compliance**: Automatically check if your certificate payloads and API setup meet the network's technical requirements.
* **Prevent Integration Issues**: Identify and fix problems *before* you connect with real partners, ensuring smooth and reliable communication.
* **Debug with Confidence**: Receive clear, actionable feedback that helps you pinpoint the exact cause of an issue and tells you how to fix it.

Essentially, this service acts as a friendly partner who tests your setup and tells you exactly what needs to be adjusted.

---
## 2. Understanding Feedback Message Structure

When our testbed communicates with your CCMAPI, it sends feedback messages. Your system needs to be able to receive and understand these. A feedback message consists of a `header` and `content`. The structure of the `content` part changes based on the validation status.

This is governed by the `urn:samm:io.catenax.message:1.0.0#MessageContentAspect` <a href = "https://github.com/eclipse-tractusx/sldt-semantic-models/blob/main/io.catenax.shared.message_header/3.0.0/gen/MessageHeaderAspect-schema.json">schema</a>.

* **Mandatory Fields for header**:
  * `messageId` (string)
  * `context` (string)
  * `sentDateTime` (timestamp)
  * `senderBpn` (string)
  * `receiverBpn` (string)
  * `version` (string)

**Example `header`:**
```json
{
  "header" : {
    "senderBpn" : "BPNL0000000001AB",
    "senderFeedbackUrl": "https://domain.tld/path/to/api",
    "relatedMessageId" : "d9452f24-3bf3-4134-b3eb-68858f1b2362",
    "context" : "CompanyCertificateManagement-CCMAPI-Status:1.0.0",
    "messageId" : "3b4edc05-e214-47a1-b0c2-1d831cdd9ba9",
    "receiverBpn" : "BPNL0000000002CD",
    "sentDateTime" : "2025-05-04T00:00:00-07:00",
    "version" : "3.1.0"
  }
}
```


### Case 1: Status is `RECEIVED` or `ACCEPTED`

For positive feedback, the `content` payload is simple and confirms receipt and validity.

* **Mandatory Fields for content**:
    * `documentId` (string): The UUID of the original certificate document being referenced.
    * `certificateStatus` (string): The status, either `"RECEIVED"` or `"ACCEPTED"`.
    * `locationBpns` (array of strings): A list of site/address BPNs (`BPNS` or `BPNA`) that are accepted.

**Example `content` for `ACCEPTED`:**
```json
{
  "content": {
    "documentId": "3b4edc05-e214-47a1-b0c2-1d831cdd9ba9",
    "certificateStatus": "ACCEPTED",
    "locationBpns": [
      "BPNS000000000001",
      "BPNS000000000002"
    ]
  }
}
```
### Case 2: Status is REJECTED
When a validation fails, the feedback is much more detailed to help you debug. In addition to the fields above, two error fields become mandatory.

* **Mandatory Fields**:
* All fields from the success case (`documentId`, `certificateStatus`, `locationBpns`).
* `certificateErrors` (array of objects): A list of general errors related to the certificate itself. Each object must have a message key.
* `locationErrors` (array of objects): A list of errors specific to certain BPNs. Each object must have a bpn and a locationErrors array.

**Example `content` for `REJECTED`:**
```json
{
  "content": {
    "documentId": "3b4edc05-e214-47a1-b0c2-1d831cdd9ba9",
    "certificateStatus": "REJECTED",
    "locationBpns": [
      "BPNS000000000001"
    ],
    "certificateErrors": [
      { "message": "Certificate has expired." },
      { "message": "Unexpected data format." }
    ],
    "locationErrors": [
      {
        "bpn": "BPNS000000000002",
        "locationErrors": [
          { "message": "Site BPNS000000000002 has been Rejected." }
        ]
      },
      {
        "bpn": "BPNS000000000003",
        "locationErrors": [
          { "message": "Site BPNS000000000003 is missing." }
        ]
      }
    ]
  }
}
```

---

## 3. How to Use the Testbed

The primary way to use the service is by submitting your <a href = "https://github.com/eclipse-tractusx/sldt-semantic-models/blob/main/io.catenax.business_partner_certificate/3.1.0/gen/BusinessPartnerCertificate-schema.json">Business Partner Certificate</a> for a full, end-to-end validation.

### Step-by-Step Guide for `/cert-validation-test/` (main endpoint)

1.  **Prepare Your Certificate**: Create a JSON payload that represents your Business Partner Certificate. The most important fields are in the `header`:
    * `senderFeedbackUrl`: This **must** be the DSP endpoint of your connector (e.g., `https://your-connector.com/api/v1/dsp`).
    * `senderBpn`: This **must** be the BPNL of your company.

2.  **Send the Request**: Make a `POST` request to the `/cert-validation-test/` endpoint with your JSON payload in the request body.

    **Example Request:**
    Of course. Here is your cURL command formatted for a Markdown (`.md`) file.

````markdown
```bash
curl --location 'localhost:8000/test-cases/businesspartnerdatamanagement/v1/cert-validation-test/?semantic_id=urn%3Asamm%3Aio.catenax.business_partner_certificate%3A3.1.0%23BusinessPartnerCertificate&contract_reference=true' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--data '{
  "header" : {
    "senderBpn" : "BPNL0000000001AB",
    "senderFeedbackUrl": "[https://domain.tld/path/to/api](https://domain.tld/path/to/api)",
    "context" : "CompanyCertificateManagement-CCMAPI-Push:1.0.0",
    "messageId" : "3b4edc05-e214-47a1-b0c2-1d831cdd9ba9",
    "receiverBpn" : "BPNL0000000002CD",
    "sentDateTime" : "2025-05-04T00:00:00-07:00",
    "version" : "3.1.0"
  },
  "content": {
    "businessPartnerNumber" : "BPNL0000000001AB",
    "enclosedSites" : [ {
      "areaOfApplication" : "Development, Marketing und Sales and also Procurement for interior components",
      "enclosedSiteBpn" : "BPNS00000003AYRE"
    } ],
    "registrationNumber" : "12 198 54182 TMS",
    "uploader" : "BPNL0000000001AB",
    "document" : {
      "documentID" : "UUID--123456789",
      "creationDate" : "2024-08-23T13:19:00.280+02:00",
      "contentType" : "application/pdf",
      "contentBase64" : "iVBORw0KGgoAAdsfwerTETEfdgd"
    },
    "validator" : {
      "validatorName" : "Data service provider X",
      "validatorBpn" : "BPNL00000007YREZ"
    },
    "validUntil" : "2026-01-24",
    "validFrom" : "2023-01-25",
    "trustLevel" : "none",
    "type" : {
      "certificateVersion" : "2015",
      "certificateType" : "ISO9001"
    },
    "areaOfApplication" : "Development, Marketing und Sales and also Procurement for interior components",
    "issuer" : {
      "issuerName" : "TÜV",
      "issuerBpn" : "BPNL133631123120"
    }
  }
}'
```
````

3.  **Check the Response & Your System**:
    * The API will immediately return a response. A `200 OK` status with `{"status": "ok", "message": "Validation was successful"}` means everything passed!
    * You should also check your own system. The testbed will have sent feedback messages (`RECEIVED`, `ACCEPTED`) to your CCMAPI.
    * If the validation fails, you will receive an error response from the API and a `REJECTED` feedback message in your system.

* **Mandatory Fields for Header**:
  * `documentId` (string)
  * `creationDate` (timestamp)
  * `contentType` (string: png/pdf)
  * `contentBase64` (string: png/pdf base64 encoded)

* **Mandatory Fields for Content**:
  * `businessPartnerNumber` (string)
  * `type` (string)
  * `registrationNumber` (string)
  * `validFrom` (timestamp)
  * `validUntil` (timestamp)
  * `trustLevel` (string)
  * `document` (json object)

**Example `payload`:**
```json
{
  "header" : {
    "senderBpn" : "BPNL0000000001AB",
    "senderFeedbackUrl": "https://domain.tld/path/to/api",
    "context" : "CompanyCertificateManagement-CCMAPI-Push:1.0.0",
    "messageId" : "3b4edc05-e214-47a1-b0c2-1d831cdd9ba9",
    "receiverBpn" : "BPNL0000000002CD",
    "sentDateTime" : "2025-05-04T00:00:00-07:00",
    "version" : "3.1.0"
  },
  "content": {
    "businessPartnerNumber" : "BPNL0000000001AB",
    "enclosedSites" : [ {
      "areaOfApplication" : "Development, Marketing und Sales and also Procurement for interior components",
      "enclosedSiteBpn" : "BPNS00000003AYRE"
    } ],
    "registrationNumber" : "12 198 54182 TMS",
    "uploader" : "BPNL0000000001AB",
    "document" : {
      "documentID" : "UUID--123456789",
      "creationDate" : "2024-08-23T13:19:00.280+02:00",
      "contentType" : "application/pdf",
      "contentBase64" : "iVBORw0KGgoAAdsfwerTETEfdgd"
    },
    "validator" : {
      "validatorName" : "Data service provider X",
      "validatorBpn" : "BPNL00000007YREZ"
    },
    "validUntil" : "2026-01-24",
    "validFrom" : "2023-01-25",
    "trustLevel" : "none",
    "type" : {
      "certificateVersion" : "2015",
      "certificateType" : "ISO9001"
    },
    "areaOfApplication" : "Development, Marketing und Sales and also Procurement for interior components",
    "issuer" : {
      "issuerName" : "TÜV",
      "issuerBpn" : "BPNL133631123120"
    }
  }
}
```

---

## 4. Understanding Errors and How to Fix Them

Errors are opportunities to improve! The testbed provides detailed error messages to guide you. Here are the most common ones and what they mean.

### Error: `CONNECTOR_UNAVAILABLE`

* **Message**: "Connection to your connector was not successful."
* **Why it Happens**: The testbed could not reach your connector at the `counter_party_address` you provided.
* **How to Fix It**:
    1.  **Check the URL**: Make sure the `counter_party_address` points to the DSP endpoint of your connector and the counter_party_id is correct. Please check https://eclipse-tractusx.github.io/docs-kits/kits/connector-kit/operation-view/ for troubleshooting.
    2.  **Check Your Connector**: Make sure your connector is running, healthy, and not blocked by a firewall.

---

### Error: `ASSET_NOT_FOUND`

* **Message**: "The CCMAPI asset could not be found in the specified connector."
* **Why it Happens**: The testbed connected to your connector but couldn't find the CCMAPI asset. This is a very common configuration issue.
* **How to Fix It**:
    1.  **Check Asset Properties**: Ensure your CCMAPI asset has the correct property: `http://purl.org/dc/terms/type` must be `https://w3id.org/catenax/taxonomy#CCMAPI`.
    2.  **Check Contract Definition**: Verify that your Contract Definition includes this asset.
    3.  **Check Access Policy**: The Access Policy linked to the Contract Definition must allow access for the testbed's BPNL. Make sure the policy rules are not too restrictive.

---

### Error: `POLICY_VALIDATION_FAILED` (Warning in Response)

* **Message**: "The usage policy that is used for the asset is not accurate."
* **Why it Happens**: Your CCMAPI asset was found, but the usage policy attached to it doesn't match the Catena-X standard. This often happens when testing for policies `with` or `without` a contract reference.
* **How to Fix It**:
    * Review the standard policy definitions at [CX-0135 Usage Policy](https://catenax-ev.github.io/docs/next/standards/CX-0135-CompanyCertificateManagement#216-usage-policy).
    * If you set `contract_reference=true` in your test, your policy **must** contain a constraint for `cx-policy:ContractReference`.
    * If you set `contract_reference=false`, your policy **must not** contain this constraint. Ensure you have two separate policies defined if you need to support both cases.

---

### Error: `SUBMODEL_VALIDATION_FAILED`

* **Message**: "The validation of the requested submodel ... failed"
* **Why it Happens**: The structure or content of the JSON payload you sent is incorrect. It does not conform to the official semantic model.
* **How to Fix It**:
    1.  **Check the Schema**: The `REJECTED` feedback sent to your CCMAPI will contain detailed validation errors (e.g., "Field 'X' is required but was not found").
    2.  **Compare with Models**: Carefully compare your JSON payload against the official aspect models provided in the Catena-X documentation. Look for missing fields, incorrect data types, or wrong nesting.

---

### Error: `FEEDBACK_COULD_NOT_BE_SENT`

* **Message**: "Your CCM API returned a status code outside of 200."
* **Why it Happens**: The testbed successfully negotiated access to your CCMAPI asset but failed when it tried to `POST` a feedback message. This means your backend endpoint for receiving feedback is not working correctly.
* **How to Fix It**:
    1.  **Check Your Endpoint**: Ensure your CCMAPI can handle `POST` requests and can correctly process all three feedback types (`RECEIVED`, `ACCEPTED`, `REJECTED`).
    2.  **Check for Errors**: Look at the logs of your backend application right after the testbed tries to send feedback. It likely threw an exception that needs to be fixed.
    3.  **Return `200 OK`**: Your endpoint must return a `200 OK` (or another 2xx status code) to acknowledge receipt of the feedback message.

---
### 5. Endpoint Usage & Examples

Here are practical examples for each test case endpoint.

---

### `POST /cert-validation-test/`

This is the main endpoint for a full, end-to-end test.

#### ✅ Success Case: Validation Works

* **Request**: A `POST` request with a fully valid certificate payload.

    ```bash
    curl -X POST "http://localhost:8000/cert-validation-test/" \
         -H "Content-Type: application/json" \
         -d '{
               "header": {
                 "senderBpn": "BPNL0000SAMPLE",
                 "senderFeedbackUrl": "[https://your-connector.com/api/v1/dsp](https://your-connector.com/api/v1/dsp)",
                 "messageId": "3b4edc05-e214-47a1-b0c2-1d831cdd9ba9",
                 "receiverBpn": "BPNL00000000TEST",
                 "sentDateTime": "2025-05-04T00:00:00Z",
                 "version": "3.1.0"
               },
               "content": {
                 "businessPartnerNumber": "BPNL0000SAMPLE",
                 "document": {
                   "documentID": "3b4edc05-e214-47a1-b0c2-1d831cdd9ba9",
                   "contentType": "application/pdf",
                   "contentBase64": "JVBERi0xLjQKJ..."
                 },
                 "validUntil": "2028-01-01",
                 "validFrom": "2025-01-01",
                 "type": { "certificateType": "ISO 9001" }
               }
             }'
    ```

* **Expected Outcome**:
    * API returns `200 OK` with `{"status": "ok", "message": "Validation was successful"}`.
    * Your CCMAPI receives `RECEIVED` and `ACCEPTED` feedback messages.

#### ❌ Failure Case: Missing a Required Field

* **Request**: The `content` payload is missing a mandatory field, like `businessPartnerNumber`.

    ```json
    {
      "header": { "...": "..." },
      "content": {
        "document": { "...": "..." },
        "validUntil": "2028-01-01"
      }
    }
    ```

* **Why it Fails**: The payload does not conform to the `BusinessPartnerCertificate` semantic model.
* **Expected Outcome**:
    * API returns `422 Unprocessable Entity` with a `SUBMODEL_VALIDATION_FAILED` error.
    * Your CCMAPI receives a `REJECTED` feedback containing the specific schema validation error (e.g., `'businessPartnerNumber' is a required property`).

#### ❌ Failure Case: Mismatching File Type

* **Request**: `contentType` is `"image/png"`, but the `contentBase64` is actually a PDF document.

    ```json
     "document": {
       "documentID": "...",
       "contentType": "image/png",
       "contentBase64": "JVBERi0xLjQKJ..."
     }
    ```

* **Why it Fails**: The testbed decodes the base64 content and checks its "magic bytes." It will detect a PDF signature (`%PDF-`) which does not match the claimed `contentType`.
* **Expected Outcome**:
    * API returns `400 Bad Request` with an error message like `"Mismatching file type and file header"`.
    * Your CCMAPI receives a `REJECTED` feedback with the same error.

---

### `GET /ccmapi-offer-test/`

Use this to quickly check if your asset is published correctly.

#### ✅ Success Case: Asset and Policy Exist

* **Request**:

    ```bash
    curl -X GET "http://localhost:8000/ccmapi-offer-test/?counter_party_id=BPNL0000SAMPLE&counter_party_address=[https://your-connector.com/api/v1/dsp](https://your-connector.com/api/v1/dsp)"
    ```

* **Expected Outcome**:
    * API returns `200 OK` with `{"status": "ok", "message": "CCMAPI Offer is set up correctly"}`.

#### ❌ Failure Case: Asset is Missing

* **Request**: Same as the success case, but your connector does not have the CCMAPI asset correctly configured (e.g., wrong properties, not included in a contract definition).
* **Why it Fails**: The testbed queries your connector's catalog but finds no asset matching the CCMAPI criteria.
* **Expected Outcome**:
    * API returns `404 Not Found` with an `ASSET_NOT_FOUND` error, providing details on what to check in your connector configuration.

---

### `GET /feedbackmechanism-validation/`

A targeted test to see if your system can receive feedback.

#### ✅ Success Case: Send a REJECTED Message

* **Request**: You can test different feedback types by changing the `message_type` parameter.

    ```bash
    curl -X GET "http://localhost:8000/feedbackmechanism-validation/?counter_party_id=BPNL0000SAMPLE&counter_party_address=[https://your-connector.com/api/v1/dsp&message_type=REJECTED](https://your-connector.com/api/v1/dsp&message_type=REJECTED)"
    ```

* **Expected Outcome**:
    * API returns `200 OK` with `{"status": "ok", "message": "REJECTED feedback sent successfully"}`.
    * You should see a valid `REJECTED` feedback message arrive at your CCMAPI endpoint.

---

### `POST /feedbackmessage-validation/`

Validate your own feedback message payloads against the official schema.

#### ✅ Success Case: Valid REJECTED message

* **Request**: A `POST` request with a payload that correctly follows the rules for a `REJECTED` message.

    ```bash
    curl -X POST "http://localhost:8000/feedbackmessage-validation/" \
         -H "Content-Type: application/json" \
         -d '{
               "header": { "...": "..." },
               "content": {
                 "documentId": "00000000-0000-0000-0000-000000000003",
                 "certificateStatus": "REJECTED",
                 "locationBpns": ["BPNS000000000001"],
                 "certificateErrors": [{"message": "Certificate was revoked"}],
                 "locationErrors": [{
                   "bpn": "BPNS000000000003",
                   "locationErrors": [{"message": "Site BPNS000000000003 is missing"}]
                 }]
               }
             }'
    ```

* **Expected Outcome**:
    * API returns `200 OK` with `{"status": "ok", "message": "Validation successful..."}`.

#### ❌ Failure Case: Missing Required Field in REJECTED message

* **Request**: The `certificateStatus` is `"REJECTED"`, but a required error field is missing, like the `bpn` inside a `locationErrors` entry.

    ```json
    "locationErrors": [
        {
            "locationErrors": [
                {"message": "Site BPNS000000000002 has been Rejected"}
            ]
        }
    ]
    ```

* **Why it Fails**: The JSON schema has a conditional requirement. If `certificateStatus` is `"REJECTED"`, then `certificateErrors` and `locationErrors` (with all their nested required fields like `bpn`) are mandatory.
* **Expected Outcome**:
    * API returns `422 Unprocessable Entity` with a detailed schema validation error explaining that the `bpn` field is required.

---

By using these test cases, you can systematically debug and perfect your CCMAPI implementation, ensuring you're a compliant and reliable partner in the Catena-X network. Happy testing!

## NOTICE

This work is licensed under the [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode).

- SPDX-License-Identifier: CC-BY-4.0
- SPDX-FileCopyrightText: 2025 BMW AG
- SPDX-FileCopyrightText: 2025 Contributors to the Eclipse Foundation
- Source URL: https://github.com/eclipse-tractusx/tractusx-sdk-services
