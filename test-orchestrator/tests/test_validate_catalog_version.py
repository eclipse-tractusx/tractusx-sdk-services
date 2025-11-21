import json
from pathlib import Path

import pytest

from test_orchestrator.checks.catalog_version_validation import validate_catalog_version


def load_catalog_from_file():
    test_file = Path(__file__).parent / 'test_files' / 'catalog-response-422.json'
    with test_file.open('r', encoding='utf-8') as f:
        return json.load(f)


def test_invalid_version_from_file_warning():
    # File contains version 1.2; expecting Warning when expecting 2.0
    catalog = load_catalog_from_file()
    result = validate_catalog_version(catalog, 'UpdateQualityAlertNotification', '2.0')
    assert isinstance(result, dict)
    assert result.get('status') == 'Warning'
    assert 'Invalid API version' in result.get('message', '')


def test_valid_version_after_patch_ok():
    catalog = load_catalog_from_file()
    # Ensure structure like in file: single dataset object
    dataset = catalog.get('dcat:dataset')
    if isinstance(dataset, list):
        target = dataset[0]
    else:
        target = dataset
    # Patch version to expected value
    if isinstance(target, dict):
        target['https://w3id.org/catenax/ontology/common#version'] = '2.0'

    result = validate_catalog_version(catalog, 'UpdateQualityAlertNotification', '2.0')
    assert result.get('status') == 'ok'
    assert 'successfully' in result.get('message', '')


def test_missing_dataset_returns_warning():
    # No dcat:dataset present
    result = validate_catalog_version({}, 'UpdateQualityAlertNotification', '2.0')
    assert result.get('status') == 'Warning'
    assert 'dcat:dataset' in result.get('message', '') or 'dataset' in result.get('message', '')
