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
Traceability check handlers package.

This module includes handlers for traceability testing:
1. Schema check - Validates traceability data against schemas
2. Graph check - Validates graph consistency for traceability data
3. EDC smoke - Validates EDC connectivity for traceability
4. Recall scenario - Tests recall process functionality
"""

from test_orchestrator.checks.traceability.schema_check import run_schema_check
from test_orchestrator.checks.traceability.graph_check import run_graph_check
from test_orchestrator.checks.traceability.edc_smoke import run_edc_smoke
from test_orchestrator.checks.traceability.recall_scenario import run_recall_scenario

__all__ = [
    'run_schema_check',
    'run_graph_check',
    'run_edc_smoke',
    'run_recall_scenario'
]