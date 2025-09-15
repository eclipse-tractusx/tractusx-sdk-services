# Company Certificate Management (CCM) test-agent – PUSH : Documentation

## 1. Overview

This document provides documentation for the Testbed V2, a service designed to validate Catena-X participants' compliance with the Company Certificate Management API (CCMAPI) standard (CX-0135). The service, built with FastAPI, acts as a "Test Orchestrator" that simulates interactions a business partner would have, allowing suppliers to test and verify their implementations in a controlled environment.

The primary goal is to ensure that a participant's implementation of the Business Partner Certificate and the CCMAPI conforms to the defined standards, facilitating seamless interoperability across the Catena-X network. The testbed validates certificate payloads against their semantic models, tests the setup of CCMAPI offers, verifies the feedback mechanism, and validates the structure of feedback messages.

---

## 2. Core Components

The Testbed V2 consists of two main services:

* **Test Orchestrator**: This is the primary service that exposes the validation endpoints. It contains the business logic for running the tests, orchestrating the validation steps, and providing feedback.
    * `cert_validation.py`: The main file containing the FastAPI router and endpoint definitions for all validation tests.
    * `certificate_utils.py`: A utility module that handles the core logic, such as sending feedback, reading asset policies, and running validation checks against semantic models.

* **Data Pull Service**: An internal service used by the Test Orchestrator to handle outgoing communication to the supplier's connector. It abstracts the complexities of the EDC (Eclipse Dataspace Connector) protocol, such as negotiating contracts and fetching data. The Test Orchestrator calls this service to get the catalog, negotiate access, and send feedback messages to the participant's CCMAPI.

---

## 3. Key Features

* **Semantic Validation**: Validates certificate and feedback message payloads against official Catena-X semantic models.
* **CCMAPI Offer Testing**: Verifies that the CCMAPI asset is correctly published and that its usage policies are configured according to the standard.
* **End-to-End Feedback Simulation**: Tests the entire feedback loop, from negotiating access to the supplier's CCMAPI to successfully sending `RECEIVED`, `ACCEPTED`, and `REJECTED` status messages.
* **Detailed Error Reporting**: Provides clear, actionable error messages to help developers quickly identify and fix issues in their implementation.

---

## 4. Flow

The main validation process is initiated by the `/cert-validation-test/` endpoint. The flow is as follows:

1.  **Receive Certificate**: The client (supplier) sends a `POST` request to `/cert-validation-test/` with the Business Partner Certificate payload they want to validate.
2.  **Initial Feedback (RECEIVED)**: The Test Orchestrator immediately attempts to establish communication with the supplier's connector, as defined by the `senderFeedbackUrl` and `senderBpn` in the certificate header.
    * It calls the **Data Pull Service** to negotiate access to the supplier's CCMAPI asset.
    * If successful, it sends a `RECEIVED` feedback message to the supplier's CCMAPI endpoint to confirm the connection is working.
3.  **CCMAPI Offer Validation**: The testbed checks if the supplier's CCMAPI asset offer and its associated usage policy are correctly configured.
4.  **Certificate Validation**: The certificate payload is validated against the specified semantic model (`urn:samm:io.catenax.business_partner_certificate:3.1.0#BusinessPartnerCertificate`). This includes checking the structure, required fields, and the embedded document (e.g., PDF/PNG).
5.  **Final Feedback (ACCEPTED/REJECTED)**:
    * If all previous steps are successful, the Test Orchestrator sends an `ACCEPTED` feedback message to the supplier's CCMAPI.
    * If any step fails (e.g., schema validation error, incorrect policy), the orchestrator sends a `REJECTED` feedback message. This message includes a detailed error list explaining what went wrong.

---

## 5. Endpoints

The following endpoints are provided by the Test Orchestrator service.

### `GET /ccmapi-offer-test/`

This endpoint validates the setup of the CCMAPI asset offer in the supplier's connector.

* **Description**: Checks if the CCMAPI asset is discoverable and if its properties and usage policy conform to the standard.
* **Flow**:
    1.  Queries the specified connector for the CCMAPI asset.
    2.  Checks for the correctness of all required properties of the CCMAPI asset.
    3.  Validates the usage policy (with or without a contract reference).
* **Parameters**:
    * `counter_party_address` (Query Param): The DSP endpoint address of the supplier's connector. Required field.
    * `counter_party_id` (Query Param): The BPNL of the supplier. Required field.
    * `contract_reference` (Query Param, optional): A boolean (`true`/`false`) to test for a usage policy with or without a contract reference. Defaults to `true`. Optional field.
* **Returns**: A JSON object indicating success or detailing the configuration error.

---

### `POST /feedbackmessage-validation/`

This endpoint validates a given feedback message payload against its semantic models.

* **Description**: Accepts a full feedback message and validates its header and content against their respective semantic models.
* **Parameters**:
    * `payload` (Request Body): A JSON object representing the feedback message. Required body.
    * `semantic_id_header` (Query Param, optional): The semantic model for the message header. Defaults to `urn:samm:io.catenax.shared.message_header:3.0.0#MessageHeaderAspect`. Optional field.
    * `semantic_id_content` (Query Param, optional): The semantic model for the message content. Defaults to `urn:samm:io.catenax.message:1.0.0#MessageContentAspect`. Optional field.
* **Returns**: A JSON object indicating if the payload is valid.

---

### `GET /feedbackmechanism-validation/`

This endpoint specifically tests if the feedback mechanism of a supplier's CCMAPI is working correctly.

* **Description**: Tests if the testbed can negotiate access to the supplier's CCMAPI and send a feedback message.
* **Flow**:
    1.  Negotiates access to the CCMAPI Asset of the test subject.
    2.  Sends the selected feedback type (`RECEIVED`, `ACCEPTED`, or `REJECTED`) to the CCMAPI.
* **Parameters**:
    * `counter_party_address` (Query Param): The DSP endpoint address of the supplier's connector. Required field.
    * `counter_party_id` (Query Param): The BPNL of the supplier. Required field.
    * `message_type` (Query Param, optional): The feedback type to send. Can be `RECEIVED`, `ACCEPTED`, or `REJECTED`. Defaults to `RECEIVED`. Optional field.
* **Returns**: A JSON object with a status message.
### `POST /cert-validation-test/`

---

This is the main endpoint to perform a full validation of a Business Partner Certificate and the associated feedback process.

* **Description**: Validates a certificate against its semantic model and tests the entire feedback delivery loop (`RECEIVED`, `ACCEPTED`/`REJECTED`).
* **Flow**:
    1.  Validates the certificate against the Business Partner Certificate semantic model.
    2.  Negotiates access to the CCMAPI asset defined in the certificate header (`senderFeedbackUrl`, `senderBpn`).
    3.  Sends a `RECEIVED` or `REJECTED` feedback message based on the initial validation result.
* **Parameters**:
    * `payload` (Request Body): A JSON object representing the Business Partner Certificate. Required body.
    * `semantic_id` (Query Param, optional): The semantic model to validate against. Defaults to `urn:samm:io.catenax.business_partner_certificate:3.1.0#BusinessPartnerCertificate`. Optional field.
    * `contract_reference` (Query Param, optional): A boolean (`true`/`false`) to specify if the usage policy being tested includes a contract reference. Defaults to `true`. Optional field.
* **Returns**: A JSON object with a success or error message.

---

## 6. Error Handling

The service uses a standardized error handling mechanism. When a validation fails, the API responds with a non-200 HTTP status code and a JSON body containing:

* `error`: A high-level error code (e.g., `ASSET_NOT_FOUND`).
* `message`: A human-readable summary of the error.
* `details`: A detailed explanation of the error, often including troubleshooting steps and links to relevant documentation.

When the `/cert-validation-test/` endpoint fails, the testbed will also attempt to send a `REJECTED` feedback message to the supplier's CCMAPI. This feedback message will contain a structured list of the validation errors that occurred, allowing the supplier to see the issues directly in their system.

## NOTICE

This work is licensed under the [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode).

- SPDX-License-Identifier: CC-BY-4.0
- SPDX-FileCopyrightText: 2025 BMW AG
- SPDX-FileCopyrightText: 2025 Contributors to the Eclipse Foundation
- Source URL: https://github.com/eclipse-tractusx/tractusx-sdk-services
