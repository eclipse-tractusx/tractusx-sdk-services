# Test Cases for the Test Orchestrator Application

## 1. Overview
The test cases below showcase some of the Test Orchestrator functionality. More details about the application and its functions can be found in the corresponding folders. These tests were written on 2025-04-30 with BMW dummy data included in the database, therefore they may need to be updated if the database's structure or content change at a later point. 
Note: for the tests to run, both the DT Pull Service and Test Orchestrator applications must be set up and running correctly. These tests are sent to the Test Orchestrator. 

## 2. Shell Descriptor Tests
These two tests show an example of when the test fails (test 1) and succeeds (test 2).

### 2. 1. Wrong counter_party_id

```http

GET test-cases/industry-core/v1/shell-descriptors-test/?counter_party_id=BPNL0000000000&counter_party_address=https://edc-controlplane.url/api/v1/dsp
Host: localhost:8000/
```

This test should fail because the counter_party_id does not exist in the database, and produce the following output:

```json

{
    "error": "BAD_GATEWAY",
    "details": "Check the path to the server (counter_party_address), bpn and if the server is available",
    "message": "Connection to the server was not successful"
}

```

### 2. 2. Successful shell_descriptors test

```http

GET test-cases/industry-core/v1/shell-descriptors-test/?&counter_party_id=BPNL00000000000&counter_party_address=https://edc-controlplane.url/api/v1/dsp
Host: localhost:8000/
```

This test should successfully retrieve all data and validate the shell_descriptors output, producing the following message: 

```json

{
    "status": "ok",
    "message": "Shell descriptors validation completed successfully",
    "subm_validation_message": {
        "status": "ok",
        "message": "Congratulations, your JSON file passed the validation test"
    },
    "policy_validation_message": {
        "status": "Warning",
        "message": "The usage policy that is used within the asset is not accurate. ",
        "details": "Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/software-development-view/policies-development-view for troubleshooting."
    }
}
```
Even though the shell_descriptors output was successfully validated as a whole, missing components and / or mistakes in the policy part of the catalog request triggered the returned warning as the default parameter for policy_validation is False. 

## 3. Submodel Tests
These two tests show an example of when the test fails (test 1) and succeeds (test 2).

### 3. 1. Submodel Fails to Validate

This test is an example of what should happen when all previous steps (DTR access, shell_descriptors retrieval, submodel access, submodel retrieval, schema retrieval) run successfully, but the retrieved submodel fails validation against the correctly identified jsonschema. 

```http
GET test-cases/industry-core/v1/submodel-test/?counter_party_id=BPNL00000000000&counter_party_address=https://edc-controlplane.url/api/v1/dsp&semantic_id=urn:samm:io.catenax.serial_part:3.0.0%23SerialPart&aas_id=urn:uuid:da071e28-8cf2-46a1-b5af-65231887c7c5
Host: localhost:8000/
```

This test should run successfully and produce the following output:

```json

{
    "error": "UNPROCESSABLE_ENTITY",
    "details": {
        "validation_errors": [
            {
                "path": "root",
                "message": "'description' is a required property",
                "validator": "required",
                "expected": "object",
                "invalid_value": {
                    "errors": []
                }
            },
            {
                "path": "root",
                "message": "'displayName' is a required property",
                "validator": "required",
                "expected": "object",
                "invalid_value": {
                    "errors": []
                }
            },
            {
                "path": "root",
                "message": "'id' is a required property",
                "validator": "required",
                "expected": "object",
                "invalid_value": {
                    "errors": []
                }
            },
            {
                "path": "root",
                "message": "'specificAssetIds' is a required property",
                "validator": "required",
                "expected": "object",
                "invalid_value": {
                    "errors": []
                }
            },
            {
                "path": "root",
                "message": "'submodelDescriptors' is a required property",
                "validator": "required",
                "expected": "object",
                "invalid_value": {
                    "errors": []
                }
            }
        ]
    },
    "message": "Validation error"
}
```

### 2. 2. Successful Submodel Validation

This test is an example of what should happen when all steps run successfully and the retrieved submodel json is validated against the corresponding jsonschema. 

```http
GET test-cases/industry-core/v1/submodel-test/?counter_party_id=BPNL00000000000&counter_party_address=https://edc-controlplane.url/api/v1/dsp&semantic_id=urn:samm:io.catenax.single_level_bom_as_built:3.0.0%23SingleLevelBomAsBuilt&aas_id=urn:uuid:5bbb6d32-439e-461a-afff-ce6fbadaf29a
Host: localhost:8000/
```

This test should run successfully and produce the following output:

```json

{
    "status": "ok",
    "message": "Submodel validation completed successfully",
    "subm_validation_message": {
        "status": "ok",
        "message": "Congratulations, your JSON file passed the validation test"
    },
    "policy_validation_message": {
        "status": "Warning",
        "message": "The usage policy that is used within the asset is not accurate. ",
        "details": "Please check https://eclipse-tractusx.github.io/docs-kits/kits/industry-core-kit/software-development-view/policies-development-view for troubleshooting."
    }
}

```
Even though the submodel output was successfully validated as a whole, missing components and / or mistakes in the policy part of the catalog request triggered the returned warning as the default parameter for policy_validation is False. 

## NOTICE

This work is licensed under the [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode).

- SPDX-License-Identifier: CC-BY-4.0
- SPDX-FileCopyrightText: 2025 BMW AG
- SPDX-FileCopyrightText: 2025 Contributors to the Eclipse Foundation
- Source URL: https://github.com/eclipse-tractusx/tractusx-sdk-services

