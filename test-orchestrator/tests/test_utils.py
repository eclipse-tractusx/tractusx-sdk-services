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


"""Test for utility methods
"""

from test_orchestrator.utils import validate_policy


def test_validate_policy_long_form_ok():
    """
    Test for a correct validate policy (has "odrl:and")
    """

    catalog = {
        "dcat:dataset": [
            {
                "dct:type": {"@id": "https://w3id.org/catenax/taxonomy#DigitalTwinRegistry"},
                "odrl:hasPolicy": {
                    "odrl:permission": {
                        "odrl:constraint": {
                            "odrl:and": [
                                {
                                    "odrl:leftOperand": {"@id": "cx-policy:FrameworkAgreement"},
                                    "odrl:operator": {"@id": "odrl:eq"},
                                    "odrl:rightOperand": "DataExchangeGovernance:1.0"
                                },
                                {
                                    "odrl:leftOperand": {"@id": "cx-policy:UsagePurpose"},
                                    "odrl:operator": {"@id": "odrl:eq"},
                                    "odrl:rightOperand": "cx.core.digitalTwinRegistry:1"
                                }
                            ]
                        }
                    }
                }
            }
        ]
    }
    result = validate_policy(catalog)

    assert result["status"] == "ok"


def test_validate_policy_short_form_ok():
    """
    Test for a correct validate policy (constraint is a list)
    """

    catalog = {
        "dcat:dataset": [
            {
                "dct:type": {"@id": "https://w3id.org/catenax/taxonomy#DigitalTwinRegistry"},
                "odrl:hasPolicy": {
                    "odrl:permission": {
                        "odrl:constraint": [
                            {
                                "odrl:leftOperand": {"@id": "cx-policy:FrameworkAgreement"},
                                "odrl:operator": {"@id": "odrl:eq"},
                                "odrl:rightOperand": "DataExchangeGovernance:1.0"
                            },
                            {
                                "odrl:leftOperand": {"@id": "cx-policy:UsagePurpose"},
                                "odrl:operator": {"@id": "odrl:eq"},
                                "odrl:rightOperand": "cx.core.digitalTwinRegistry:1"
                            }
                        ]
                    }
                }
            }
        ]
    }
    result = validate_policy(catalog)

    assert result["status"] == "ok"


def test_validate_policy_warning():
    """
    Test for an incorrect validate policy
    """

    catalog = {
        "dcat:dataset": [
            {
                "dct:type": {"@id": "https://w3id.org/catenax/taxonomy#DigitalTwinRegistry"},
                "odrl:hasPolicy": {
                    "odrl:permission": {
                        "odrl:constraint": [
                            {"odrl:leftOperand": {"@id": "cx-policy:WRONG"}}
                        ]
                    }
                }
            }
        ]
    }
    result = validate_policy(catalog)

    assert result["status"] == "Warning"
