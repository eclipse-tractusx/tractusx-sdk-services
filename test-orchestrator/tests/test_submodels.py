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

""" Tests for the submodel-test function and its sub-functions
"""

import json

from test_orchestrator.utils import fetch_submodel_info, submodel_schema_finder


def test_fetch_submodel_info():
    """ Testing if this function can retrieve the correct submodel information given a
    pre-specified set of inputs
    """

    example_output = {
        'href': 'https://dataplane-example.cloud/public/' + \
                'urn:uuid:fakeuuid/submodel',
        'subm_counterparty': 'https://connector-example.cloud/api/v1/dsp',
        'subm_operandleft': 'https://w3id.org/edc/v0.0.1/ns/id',
        'subm_operandright': 'battery_bundle_slbb'
        }

    correct_element_path = './tests/test_files/correct_element.json'

    with open(correct_element_path, 'r', encoding='utf-8') as file:
        correct_element = json.load(file)
    semantic_id = 'urn:samm:io.catenax.single_level_bom_as_built:3.0.0#SingleLevelBomAsBuilt'

    obtained_output = fetch_submodel_info(correct_element, semantic_id)

    assert obtained_output == example_output


def test_submodel_schema_finder():
    """ Testing if this function files the correct schema in the schema repo
    based on a set of pre-specified inputs
    """

    semantic_id = 'urn:samm:io.catenax.single_level_bom_as_built:3.0.0#SingleLevelBomAsBuilt'

    subm_schema_example_path = './tests/test_files/subm_schema_example.json'

    with open(subm_schema_example_path, 'r', encoding='utf-8') as file:
        subm_schema_example = json.load(file)

    subm_schema_dict = submodel_schema_finder(semantic_id)
    subm_schema = subm_schema_dict['schema']

    assert subm_schema == subm_schema_example
