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
Traceability JSON Schema package.

This module provides access to JSON schemas for Catena-X traceability data models.
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Union

# Schema file names
SERIAL_PART_SCHEMA = "serialpart.json"
PART_AS_PLANNED_SCHEMA = "partasplanned.json"
PART_AS_BUILT_SCHEMA = "partasbuilt.json"
ASSEMBLY_PART_RELATIONSHIP_SCHEMA = "assemblypartrelationship.json"

# Schema version mappings
# This allows pinning to specific versions of schemas
_SCHEMA_VERSIONS = {
    SERIAL_PART_SCHEMA: "0.1.0",
    PART_AS_PLANNED_SCHEMA: "0.1.0", 
    PART_AS_BUILT_SCHEMA: "0.1.0",
    ASSEMBLY_PART_RELATIONSHIP_SCHEMA: "0.1.0"
}

def get_schema_path(schema_name: str) -> Path:
    """
    Get the path to a schema file.
    
    Args:
        schema_name: The name of the schema file
        
    Returns:
        Path: The path to the schema file
    """
    schema_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    return schema_dir / schema_name


def load_schema(schema_name: str, version: Optional[str] = None) -> Dict:
    """
    Load a JSON schema.
    
    Args:
        schema_name: The name of the schema file
        version: The specific version to load (if None, uses the configured version)
        
    Returns:
        Dict: The loaded schema as a dictionary
        
    Raises:
        FileNotFoundError: If the schema file doesn't exist
        ValueError: If the requested version doesn't match the schema version
    """
    schema_path = get_schema_path(schema_name)
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path, "r") as f:
        schema = json.load(f)
    
    # Verify version if specified
    if version is not None:
        schema_version = schema.get("x-schema-version")
        if schema_version != version:
            raise ValueError(
                f"Schema version mismatch: requested {version}, found {schema_version}"
            )
    
    return schema


def load_serial_part_schema() -> Dict:
    """Load the Serial Part schema."""
    return load_schema(SERIAL_PART_SCHEMA, _SCHEMA_VERSIONS[SERIAL_PART_SCHEMA])


def load_part_as_planned_schema() -> Dict:
    """Load the Part As Planned schema."""
    return load_schema(PART_AS_PLANNED_SCHEMA, _SCHEMA_VERSIONS[PART_AS_PLANNED_SCHEMA])


def load_part_as_built_schema() -> Dict:
    """Load the Part As Built schema."""
    return load_schema(PART_AS_BUILT_SCHEMA, _SCHEMA_VERSIONS[PART_AS_BUILT_SCHEMA])


def load_assembly_part_relationship_schema() -> Dict:
    """Load the Assembly Part Relationship schema."""
    return load_schema(ASSEMBLY_PART_RELATIONSHIP_SCHEMA, _SCHEMA_VERSIONS[ASSEMBLY_PART_RELATIONSHIP_SCHEMA])