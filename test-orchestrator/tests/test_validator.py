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

"""Tests for the validator
"""

import json
import pytest

from test_orchestrator.errors import HTTPError
from test_orchestrator.validator import json_validator

# Part 1 - testing the functionality with schemas and input written by hand
# pylint: disable=R0801

basic_schema = {
    '$schema': 'http://json-schema.org/draft-07/schema#',
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
        'name': {'type': 'string'},
        'email': {'type': 'string', 'format': 'email'},
        'age': {'type': 'integer', 'minimum': 18}
    },
    'required': ['id', 'name', 'email']
}


valid_json = {'status': 'ok',
              'message': 'Congratulations, your JSON file passed the validation test'}

def test_validate_user_schema_valid_json():
    """Validates the user data against the JSON schema. JSON is valid."""

    data = {'id': 1,
            'name': 'John Doe',
            'email': 'john@example.com',
            'age': 25}
    validation_json = json_validator(basic_schema, data)

    assert validation_json == valid_json


def test_validate_user_schema_bad_id_type():
    """Validates the user data against the JSON schema. The id is invalid"""

    data = {'id': 'x',
            'name': 'John Doe',
            'email': 'john@example.com'}

    integer_error_json = {
        'validation_errors': [
            {
                'expected': 'integer',
                'invalid_value': 'x',
                'message': "'x' is not of type 'integer'",
                'path': 'id',
                'validator': 'type',
            },
        ],
    }

    with pytest.raises(HTTPError) as exc_info:
        json_validator(basic_schema, data)

    assert exc_info.value.status_code == 422
    assert exc_info.value.message == 'Validation error'
    assert exc_info.value.details == integer_error_json


def test_validate_user_schema_email_missing():
    """Validates the user data against the JSON schema.
       The required email property is missing."""

    data = {'id': 3,
            'name': 'John Doe'}

    email_missing_json = {
        'validation_errors': [
            {
                'expected': 'object',
                'invalid_value': {
                    'id': 3,
                    'name': 'John Doe',
                },
                'message': "'email' is a required property",
                'path': 'root',
                'validator': 'required',
            },
        ],
    }

    with pytest.raises(HTTPError) as exc_info:
        json_validator(basic_schema, data)

    assert exc_info.value.status_code == 422
    assert exc_info.value.message == 'Validation error'
    assert exc_info.value.details == email_missing_json


def test_validate_user_schema_integer_too_small():
    """Validates the user data against the JSON schema.
       The age property's value is too small."""

    data = {'id': 4,
            'name': 'John Doe',
            'email': 'john@example.com',
            'age': 16}

    error_too_young_json = {
        'validation_errors': [
            {
                'expected': 'integer',
                'invalid_value': 16,
                'message': '16 is less than the minimum of 18',
                'path': 'age',
                'validator': 'minimum',
            },
        ]
    }

    with pytest.raises(HTTPError) as exc_info:
        json_validator(basic_schema, data)

    assert exc_info.value.status_code == 422
    assert exc_info.value.message == 'Validation error'
    assert exc_info.value.details == error_too_young_json



# Part 2 - Testing the functionality with real json input files against the current schema
# Loading the schema, which will be the same across all subsequent tests
SCHEMA_PATH = './test_orchestrator/schema_files/shell_descriptors_jsonschema.json'


with open(SCHEMA_PATH, 'r', encoding='utf-8') as file:
    schema = json.load(file)


def test_validate_correct_file():
    """Successfully validating a correct json input file """

    successful_output = {
        'status': 'ok', 
        'message': 'Congratulations, your JSON file passed the validation test'
        }

    test_file_path = './tests/test_files/test_shell_descriptors_1_full_correct.json'

    with open(test_file_path, 'r', encoding='utf-8') as file:
        json_to_validate = json.load(file)

    validation_output = json_validator(schema, json_to_validate)

    assert validation_output == successful_output


def test_validate_missing_and_incorrect_types():
    """ Returning the right errors for the second test file, which lacks some necessary elements,
    as well as incorrect types
    """

    missing_and_incorrect_errors = {
        'validation_errors': [
            {'path': 'result.0.submodelDescriptors.0.id',
             'message': "3456 is not of type 'string'",
             'validator': 'type',
             'expected': 'string',
             'invalid_value': 3456}, 
            {'path': 'result.0.submodelDescriptors.1.semanticId.type',
             'message': "3456 is not of type 'string'",
             'validator': 'type',
             'expected': 'string',
             'invalid_value': 3456}, 
            {'path': 'result.0.submodelDescriptors.1.semanticId.type',
             'message': "3456 is not one of ['ExternalReference']",
             'validator': 'enum',
             'expected': 'string',
             'invalid_value': 3456}]}

    test_file_path = './tests/test_files/test_shell_descriptors_2_missing_and_incorrect.json'

    with open(test_file_path, 'r', encoding='utf-8') as file:
        json_to_validate = json.load(file)

    with pytest.raises(HTTPError) as exc_info:
        validation_json = json_validator(schema, json_to_validate)

    assert exc_info.value.status_code == 422
    assert exc_info.value.message == 'Validation error'
    assert exc_info.value.details == missing_and_incorrect_errors


def test_validate_incorrect_patterns():
    """ Returning the right errors for the third test file, which contains incorrect pattern matches,
    among other errors, created during the second and third waves of additions to the schema
    """

    incorrect_patterns_errors = {
        'validation_errors': [
            {'path': 'result.0.submodelDescriptors.0.endpoints.0.protocolInformation.href',
             'message': "'www.google.com' does not match '^https://.*?/submodel$'",
             'expected': 'string',
             'invalid_value': 'www.google.com',
             'validator': 'pattern'},
            {'path': 'result.0.submodelDescriptors.0.endpoints.0.protocolInformation.subprotocolBody',
             'message': "'xy=Vehicle_2024-01-01-0001_Submodel_SerialPart;dspEndpoint=" + \
                        "https://connector-release.edc.aws.bmw.cloud/api/v1/dsp' does not match " + \
                        "'^(?=.*dspEndpoint)(?=.*id=)[^;]+;[^;]+$'",
             'validator': 'pattern',
             'expected': 'string',
             'invalid_value': 'xy=Vehicle_2024-01-01-0001_Submodel_SerialPart;dspEndpoint=' + \
                              'https://connector-release.edc.aws.bmw.cloud/api/v1/dsp'
             },
            {'path': 'result.0.submodelDescriptors.0.semanticId.type',
             'message': "'Bela' is not one of ['ExternalReference']",
             'validator': 'enum',
             'expected': 'string',
             'invalid_value': 'Bela'},
            {'path': 'result.0.submodelDescriptors.1.endpoints.0.protocolInformation.href',
             'message': "'xyz' does not match '^https://.*?/submodel$'",
             'validator': 'pattern',
             'expected': 'string',
             'invalid_value': 'xyz'},
            {'path': 'result.0.submodelDescriptors.1.endpoints.0.protocolInformation.endpointProtocol',
             'message': "'GUM' is not one of ['HTTP', 'HTTPS']",
             'validator': 'enum',
             'expected': 'string',
             'invalid_value': 'GUM'},
            {'path': 'result.0.submodelDescriptors.1.endpoints.0.protocolInformation.subprotocolBody',
             'message': "'https://connector; id' does not match '^(?=.*dspEndpoint)(?=.*id=)[^;]+;[^;]+$'",
             'validator': 'pattern',
             'expected': 'string',
             'invalid_value': 'https://connector; id'}
            ]
        }

    test_file_path = './tests/test_files/test_shell_descriptors_3_new_additions.json'

    with open(test_file_path, 'r', encoding='utf-8') as file:
        json_to_validate = json.load(file)

    with pytest.raises(HTTPError) as exc_info:
        json_validator(schema, json_to_validate)

    assert exc_info.value.status_code == 422
    assert exc_info.value.message == 'Validation error'
    assert exc_info.value.details == incorrect_patterns_errors
