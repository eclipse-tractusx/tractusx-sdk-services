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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
# *************************************************************

"""
All functions necessary for JSON validation.

This module includes:
1. `schema_finder`: Finds and loads JSON schemas based on request names.
2. `json_validator`: Validates a JSON object against a specified schema.
3. `SchemaNotFoundError`: Custom exception for cases where a schema is not found.

Dependencies:
- `json`: For loading and manipulating JSON objects.
- `jsonschema`: For validating JSON data against schemas.
"""

import json

import jsonschema

from orchestrator import config
from orchestrator.errors import Error, HTTPError


# Schema map
schema_map = {
    "shell_descriptors": "shell_descriptors_jsonschema.json",
    "shell_descriptors_spec": "shell_descriptors_spec_jsonschema.json",
}


class SchemaNotFoundError(Exception):
    """
    Custom exception raised when a JSON schema is not found.

    This exception is triggered if the `schema_finder` function fails to find a schema
    corresponding to the requested name in the schema map.
    """


def schema_finder(request_name):
    """
    Finds and loads the schema file based on the request name.

    This function uses a predefined schema map to locate the correct schema file.
    If the schema file is found, it is loaded and returned as a JSON object.
    If the schema cannot be located or the file is missing, an appropriate exception is raised.

    :param request_name: The name of the request for which the schema is needed.
    :raises SchemaNotFoundError: If no schema is mapped to the given request name.
    :raises FileNotFoundError: If the mapped schema file is not found in the specified path.
    :return: The JSON schema object.
    """

    correct_schema = schema_map.get(request_name)

    if correct_schema is None:
        raise SchemaNotFoundError(f'Schema not found for request: {request_name}')

    schema_file = f'{config.SCHEMA_PATH}/{correct_schema}'

    try:
        with open(schema_file, 'r', encoding='utf-8') as file:
            schema = json.load(file)

        return schema

    except FileNotFoundError as exc:
        raise FileNotFoundError(f'Schema file not found: {schema_file}') from exc


def json_validator(schema, json_to_validate, validation_type = 'jsonschema'):
    """
    Validates a JSON object against a given schema.

    This function uses the specified validation type to check whether a JSON object
    conforms to a given schema. Currently, only 'jsonschema' validation is supported.
    Validation errors are recorded with details about the specific violations.

    :param schema: The JSON schema object to validate against.
    :param json_to_validate: The JSON object to be validated.
    :param validation_type: The type of validation to perform. Default is 'jsonschema'.
    :raises HTTPError: Raised if validation errors are found.
    :return: A dictionary indicating the status and message if validation passes successfully.
    """

    error_records = []

    if validation_type == 'jsonschema':
        validator = jsonschema.Draft7Validator(schema)

        for error in validator.iter_errors(json_to_validate):
            error_records.append({
                "path": ".".join(str(p) for p in error.path) if error.path else "root",
                "message": error.message,
                "validator": error.validator,
                "expected": error.schema.get("type", "N/A"),  
                "invalid_value": error.instance  
            })

        if error_records:
            raise HTTPError(Error.UNPROCESSABLE_ENTITY,
                            message='Validation error',
                            details={'validation_errors': error_records})

    return {"status": "ok",
            "message": "Congratulations, your JSON file passed the validation test"}
