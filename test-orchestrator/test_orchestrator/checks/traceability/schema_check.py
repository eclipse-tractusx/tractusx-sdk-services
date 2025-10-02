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
Schema check module for traceability testing.

This module validates traceability data against schemas.
"""

import logging
import jsonschema
from typing import Dict, List, Any, Optional

from test_orchestrator import config
from test_orchestrator.auth import get_dt_pull_service_headers
from test_orchestrator.request_handler import make_request
from test_orchestrator.utils import submodel_schema_finder, fetch_submodel_info, get_dtr_access


async def run(input: Dict) -> Dict:
    """
    Pulls submodel payloads via the dt-pull client, validates each against 
    the matching JSON Schema using jsonschema.validate, and returns results.
    
    Args:
        input: Dictionary containing input parameters including:
            - shell_ids: List of shell IDs to process
            - dataplane_url: URL for the data plane
            - counter_party_id: Business Partner Number of the counterparty
            - counter_party_address: Address of the counterparty's EDC
        
    Returns:
        dict: Results of the schema validation with format:
            {
                step: 'schema_check',
                status: 'pass' or 'fail',
                details: [
                    {
                        shellId: ID of the shell that was validated,
                        submodel: ID of the submodel that was validated,
                        errorPath: Path to the error in case of validation failure,
                        message: Validation error message
                    }
                ]
            }
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting schema validation check")
    
    validation_details = []
    overall_status = "pass"
    
    # Extract input parameters
    shell_ids = input.get('shell_ids', [])
    dataplane_url = input.get('dataplane_url')
    counter_party_id = input.get('counter_party_id')
    counter_party_address = input.get('counter_party_address')
    
    if not shell_ids:
        logger.warning("No shell IDs provided for validation")
        return {
            "step": "schema_check", 
            "status": "fail",
            "details": [{
                "shellId": "N/A",
                "submodel": "N/A",
                "errorPath": "input",
                "message": "No shell IDs provided for validation"
            }]
        }
    
    # Process each shell ID
    for shell_id in shell_ids:
        logger.info(f"Processing shell ID: {shell_id}")
        
        try:
            # Get shell descriptor
            shell_descriptors = await make_request(
                'GET',
                f'{config.DT_PULL_SERVICE_ADDRESS}/dtr/shell-descriptors/',
                params={'dataplane_url': dataplane_url, 'aas_id': shell_id},
                headers=get_dt_pull_service_headers(),
                timeout=60
            )
            
            # Process each submodel in the shell
            if isinstance(shell_descriptors, dict):
                submodel_descriptors = shell_descriptors.get('submodelDescriptors', [])
            elif isinstance(shell_descriptors, list) and len(shell_descriptors) > 0:
                submodel_descriptors = shell_descriptors[0].get('submodelDescriptors', [])
            else:
                submodel_descriptors = []
            
            for submodel in submodel_descriptors:
                submodel_id = submodel.get('identification', 'unknown')
                semantic_id = submodel.get('semanticId', {}).get('value', [''])[0] if isinstance(submodel.get('semanticId', {}).get('value', []), list) else ''
                
                logger.info(f"Processing submodel: {submodel_id} with semantic ID: {semantic_id}")
                
                if not semantic_id:
                    validation_details.append({
                        "shellId": shell_id,
                        "submodel": submodel_id,
                        "errorPath": "semanticId",
                        "message": "Missing semantic ID"
                    })
                    overall_status = "fail"
                    continue
                
                try:
                    # Get the schema for this semantic ID
                    schema_result = submodel_schema_finder(semantic_id)
                    if schema_result.get('status') != 'ok' or 'schema' not in schema_result:
                        validation_details.append({
                            "shellId": shell_id,
                            "submodel": submodel_id,
                            "errorPath": "schema",
                            "message": f"Failed to retrieve schema: {schema_result.get('message', 'Unknown error')}"
                        })
                        overall_status = "fail"
                        continue
                    
                    json_schema = schema_result['schema']
                    
                    # Extract the endpoint information from the submodel
                    try:
                        submodel_endpoint_info = fetch_submodel_info([submodel], semantic_id)
                        href = submodel_endpoint_info.get('href')
                        subm_counterparty = submodel_endpoint_info.get('subm_counterparty')
                        subm_operandleft = submodel_endpoint_info.get('subm_operandleft')
                        subm_operandright = submodel_endpoint_info.get('subm_operandright')
                        
                        if not all([href, subm_counterparty, subm_operandleft, subm_operandright]):
                            validation_details.append({
                                "shellId": shell_id,
                                "submodel": submodel_id,
                                "errorPath": "endpoint",
                                "message": "Missing endpoint information in submodel"
                            })
                            overall_status = "fail"
                            continue
                        
                        # Get data from the submodel
                        endpoint, authorization, _ = await get_dtr_access(
                            counter_party_address=counter_party_address,
                            counter_party_id=counter_party_id,
                            operand_left=subm_operandleft,
                            operand_right=subm_operandright,
                            timeout=60
                        )
                        
                        # Fetch the submodel data
                        if not endpoint:
                            validation_details.append({
                                "shellId": shell_id,
                                "submodel": submodel_id,
                                "errorPath": "access",
                                "message": "Failed to get data access endpoint"
                            })
                            overall_status = "fail"
                            continue
                        
                        headers = {"Authorization": authorization} if authorization else {}
                        payload_response = await make_request(
                            'GET', 
                            endpoint,
                            headers=headers, 
                            timeout=60
                        )
                        
                        # Validate the payload against the schema
                        validator = jsonschema.Draft7Validator(json_schema)
                        errors = list(validator.iter_errors(payload_response))
                        
                        if errors:
                            overall_status = "fail"
                            for error in errors:
                                error_path = ".".join(str(p) for p in error.path) if error.path else "root"
                                validation_details.append({
                                    "shellId": shell_id,
                                    "submodel": submodel_id,
                                    "errorPath": error_path,
                                    "message": error.message
                                })
                        else:
                            validation_details.append({
                                "shellId": shell_id,
                                "submodel": submodel_id,
                                "errorPath": "",
                                "message": "Schema validation successful"
                            })
                            
                    except Exception as e:
                        logger.error(f"Error fetching or validating submodel data: {str(e)}")
                        validation_details.append({
                            "shellId": shell_id,
                            "submodel": submodel_id,
                            "errorPath": "processing",
                            "message": f"Error: {str(e)}"
                        })
                        overall_status = "fail"
                        
                except Exception as e:
                    logger.error(f"Error processing schema for semantic ID {semantic_id}: {str(e)}")
                    validation_details.append({
                        "shellId": shell_id,
                        "submodel": submodel_id,
                        "errorPath": "schema",
                        "message": f"Error: {str(e)}"
                    })
                    overall_status = "fail"
            
        except Exception as e:
            logger.error(f"Error processing shell ID {shell_id}: {str(e)}")
            validation_details.append({
                "shellId": shell_id,
                "submodel": "N/A",
                "errorPath": "shell",
                "message": f"Error: {str(e)}"
            })
            overall_status = "fail"
    
    logger.info(f"Schema validation complete. Status: {overall_status}")
    return {
        "step": "schema_check",
        "status": overall_status,
        "details": validation_details
    }


async def run_schema_check(config, logger):
    """
    Run schema validation for traceability data.
    
    Args:
        config: Configuration parameters for the check
        logger: Logger instance for logging validation results
        
    Returns:
        dict: Results of the schema validation
    """
    return await run(config)