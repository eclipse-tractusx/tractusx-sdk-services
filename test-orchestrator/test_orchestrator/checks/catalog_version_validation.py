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

"""Catalog version validation utilities.

This module provides a helper to validate that the dataset for a given
`dct:type` in a catalog contains the expected API version specified at
`https://w3id.org/catenax/ontology/common#version`.
"""

from test_orchestrator.logging.log_manager import LoggingManager

logger = LoggingManager.get_logger(__name__)


def validate_catalog_version(catalog_json: dict, dct_type_id: str, expected_version: str = '2.0') -> dict:
    """Validate catalog dataset version for a given dct:type.

    Args:
        catalog_json: The catalog response JSON.
        dct_type_id: The taxonomy id (without prefix), e.g. "ReceiveQualityInvestigationNotification".
        expected_version: The expected version string, defaults to '2.0'.

    Returns:
        dict with keys: status ('ok' or 'Warning'), message, details
    """
    logger.info('validating catalog version')

    datasets = (catalog_json or {}).get('dcat:dataset')
    if datasets is None:
        return {
            'status': 'Warning',
            'message': 'Catalog response does not contain dcat:dataset.',
            'details': 'The catalog response must include a dcat:dataset element.'
        }

    if not isinstance(datasets, list):
        datasets = [datasets]

    target_type_id = f"https://w3id.org/catenax/taxonomy#{dct_type_id}"

    # Select dataset by matching dct:type, otherwise fall back to first element
    target_dataset = None
    for ds in datasets:
        if isinstance(ds, dict):
            dct_type = ds.get('dct:type', {})
            if isinstance(dct_type, dict) and dct_type.get('@id') == target_type_id:
                target_dataset = ds
                break

    if target_dataset is None and datasets:
        target_dataset = datasets[0] if isinstance(datasets[0], dict) else None

    if not isinstance(target_dataset, dict):
        return {
            'status': 'Warning',
            'message': 'Catalog dataset is malformed or missing.',
            'details': 'Expected dataset object with dct:type and version fields.'
        }

    version = target_dataset.get('https://w3id.org/catenax/ontology/common#version')

    if version == expected_version:
        logger.info('Catalog version validation outcome: True')
        return {
            'status': 'ok',
            'message': 'Catalog dataset API version was successfully validated.',
            'details': f"Version matches expected '{expected_version}'."
        }

    logger.info('Catalog version validation outcome: False')
    return {
        'status': 'Warning',
        'message': 'Invalid API version in catalog dataset.',
        'details': (
            "Expected https://w3id.org/catenax/ontology/common#version to be "
            f"'{expected_version}' but got '{version}'."
        )
    }
