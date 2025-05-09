# *************************************************************
# Eclipse Tractus-X - Digital Twin Pull Service
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

"""Utility methods for the DT Pull Service
"""


def policy_checker(policies, catalog):
    """
    Checks policies to determine if they are present in the catalog.

    :param policies: A list of policies to be checked.
    :param catalog: The catalog dictionary containing policy information.
    :return: A tuple indicating whether a matching policy was found and its index.
    """

    if len(policies) == 0:
        return True, 0

    if isinstance(catalog['dcat:dataset']['odrl:hasPolicy'], list):
        for idx, item in enumerate(catalog['dcat:dataset']['odrl:hasPolicy']):
            found = policy_check_item(policies, item)

            if found:
                return found, idx

            return False, -1
    else:
        return policy_check_item(policies, catalog), 0


def policy_check_item(policies, item):
    """Checks policies, if they are present in a single catalog item"""

    found = True
    policies_found = []
    results = get_recursively(item, "odrl:leftOperand")
    asset_policies = {item["odrl:leftOperand"]["@id"]: item["odrl:rightOperand"] for item in results}

    for policy in policies:
        for key, value in policy.items():
            found = found and asset_policies.get(key, None) == value

        policies_found.append(found)
        found = True

    return True in policies_found


def get_recursively(search_dict, field):
    """
    Recursively searches for a specified field within a dictionary.

    :param search_dict: The dictionary to search within.
    :param field: The key to search for.
    :return: A list of dictionaries where the field is found.
    """

    fields_found = []

    for key, value in search_dict.items():
        if key == field:
            fields_found.append(search_dict)
        elif isinstance(value, dict):
            results = get_recursively(value, field)
            fields_found.extend(results)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    fields_found.extend(get_recursively(item, field))

    return fields_found
