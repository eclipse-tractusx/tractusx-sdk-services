import asyncio
from typing import Optional

import httpx

import json

from test_orchestrator import config
from test_orchestrator.errors import Error, HTTPError
from test_orchestrator.request_handler import make_request
from test_orchestrator.auth import get_dt_pull_service_headers


async def validate_puris_policy(asset_id: str, counter_party_address: str, counter_party_id: str):
    operand_left: str = 'https://w3id.org/edc/v0.0.1/ns/id'
    operator: str = 'like'

    catalog_json = await make_request('GET',
                                      f'{config.DT_PULL_SERVICE_ADDRESS}/edr/get-catalog/',
                                      params={'operand_left': operand_left,
                                              'operand_right': asset_id,
                                              'operator': operator,
                                              'counter_party_address': counter_party_address,
                                              'counter_party_id': counter_party_id,
                                              'offset': 0,
                                              'limit': 10},
                                      timeout=80,
                                      headers=get_dt_pull_service_headers())

    if len(catalog_json["dcat:dataset"]) == 0:
        return {'Failure': 'No Asset found for submodel_id'}

    data_exchange_policy = {
        'odrl:leftOperand': {'@id': 'cx-policy:FrameworkAgreement'},
        'odrl:operator': {'@id': 'odrl:eq'},
        'odrl:rightOperand': 'DataExchangeGovernance:1.0'}

    puris_policy = {
        'odrl:leftOperand': {'@id': 'cx-policy:UsagePurpose'},
        'odrl:operator': {'@id': 'odrl:eq'},
        'odrl:rightOperand': 'cx.puris.base:1'}

    policy_validation_outcome = False

    if 'dcat:dataset' in catalog_json:
        if isinstance(catalog_json['dcat:dataset'], dict):
            element = catalog_json['dcat:dataset']
            if 'dct:type' in element:
                if isinstance(element['dct:type'], dict):
                    id_in_dct_type = element['dct:type'].get('@id')

                    if id_in_dct_type:
                        if element['dct:type']['@id'] == "https://w3id.org/catenax/taxonomy#Submodel":
                            if 'odrl:hasPolicy' in element:
                                if 'odrl:permission' in element['odrl:hasPolicy']:
                                    if 'odrl:constraint' in element['odrl:hasPolicy']['odrl:permission']:
                                        spec_part = element['odrl:hasPolicy']['odrl:permission']['odrl:constraint']

                                        if isinstance(spec_part, dict):
                                            if 'odrl:and' in spec_part:
                                                if isinstance(spec_part['odrl:and'], list):
                                                    if data_exchange_policy in spec_part['odrl:and'] and \
                                                            puris_policy in spec_part['odrl:and']:
                                                        policy_validation_outcome = True

    if policy_validation_outcome:
        return {'Success': 'Policy validation was successful.',
                'details': 'The usage policy that is used within the asset was successfully validated.'}

    return {'Warning': 'The usage policy that is used within the asset is not accurate.',
            'details': 'Either the values of the usage policy are not correct or the schema is not accurate.'}
