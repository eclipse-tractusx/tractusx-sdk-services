#################################################################################
# Tractus-X - Industry Flag Service
#
# Copyright (c) 2025 CGI Deutschland B.V. & Co. KG
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
# distributed under the License is distributed on an "AS IS" BASIS
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the
# License for the specific language govern in permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
#################################################################################

import logging
logger = logging.getLogger('staging')
import copy

DATASET_KEY="dcat:dataset"
import sys
class DspUtils:
    """
    Class responsible for doing trivial dsp operations.

    DSP Docs: https://docs.internationaldataspaces.org/ids-knowledgebase/dataspace-protocol
    """
    
    @staticmethod
    def filter_assets_and_policies(catalog:dict, allowed_policies:list=[]) -> list[tuple[str, dict]]:
        """
        Method to select a asset and policy from a DCAT Catalog.

        @returns: Success -> tuple[targetid:str, policy:dict] Fail -> Exception
        
        """

        global DATASET_KEY

        if catalog is None:
            raise Exception("It was not possible to get the policy, because the catalog is empty!")
        
        dataset:list|dict = catalog.get(DATASET_KEY)

        if(allowed_policies is None):
            print("It did not find a policy")
            raise Exception("No policies are allowed for the DCAT Catalog!")
        
        ### Asset Evaluation

        valid_assets:list = []

        ## If just one asset is there
        if isinstance(dataset, dict):
            policy = DspUtils.get_dataset_policy(dataset=dataset, allowed_policies=allowed_policies)
            if policy is None:
                raise ValueError("No valid asset and policy allowed at the DCAT Catalog dataset!")

            valid_assets.append((dataset.get("@id"), policy)) ## Return the assetid and the policy
            return valid_assets
        
        ## In case it is a empty list give error
        if(len(dataset) == 0):
            raise Exception("No dataset was found for the search asset! It is empty!")

        ## More than one asset, the prio is set by the allowed policies order
        for item in dataset:
            policy = DspUtils.get_dataset_policy(dataset=item, allowed_policies=allowed_policies)
            if policy is not None:
                valid_assets.append((item.get("@id"), policy)) ## Return the assetid and the policy

        if len(valid_assets) == 0:
            raise ValueError("No valid policy was found for any item in the list. No valid asset found!")
        
        return valid_assets
    
    @staticmethod
    def is_catalog_empty(catalog:dict) -> bool:
        dataset:list|dict = catalog.get(DATASET_KEY)
        if(dataset is None):
            return False
        
        ## If just one asset is there
        if isinstance(dataset, dict):
            return False if "@id" in dataset else True
        
        return len(dataset) == 0
        
    @staticmethod
    def get_dataset_policy(dataset:dict, allowed_policies:list=[]) -> dict | None:
        """
        Gets a valid policy from an dataset.

        @returns: dict: the selected policy or None if no valid policy was found
        """
        ### Policy Evaluation
        policies:dict|list = dataset.get("odrl:hasPolicy")    

        ## One Policy
        if isinstance(policies, dict):
            return policies if DspUtils.is_policy_valid(policy=policies, allowed_policies=allowed_policies) else None ## Return the policy object if is valid

        ## More than one policy
        for policy in policies:
            ## In case the policy is not valid, continue
            if not DspUtils.is_policy_valid(policy=policy, allowed_policies=allowed_policies):
               continue
            return policy
        
        # In case no policy was selected it will return None
        return None
    
    @staticmethod
    def is_policy_valid(policy:dict, allowed_policies:list=[]) -> bool:
        """
        Checks if a policy is valid, checking if is in the allowed_policies (in operator), so if the order is another one would still be compared.

        @returns: True if the policy is valid, False otherwise
        """
        ## In case the allowed_policies are empty then everything is allowed
        if(allowed_policies is None or len(allowed_policies) == 0):
            return True
        
        to_compare:dict = copy.deepcopy(policy)

        ##  Delete the policy unique attributes 
        del to_compare["@id"],to_compare["@type"]

        ## Check if the policy is in the list of allowed_policies
        ### TODO: This should maybe be enhanced to compare the actual constraints one by one
        if to_compare in allowed_policies:
            return True
        
        return False

if __name__ == "__main__":
    """
        Test policy filter
    """
    sys.path.append("../")
    configured_policies = [
        {
           "odrl:permission": {
                        "odrl:action": {
                            "@id": "odrl:use"
                        },
                        "odrl:constraint": {
                            "odrl:and": [
                                {
                                    "odrl:leftOperand": {
                                        "@id": "cx-policy:Membership"
                                    },
                                    "odrl:operator": {
                                        "@id": "odrl:eq"
                                    },
                                    "odrl:rightOperand": "active"
                                },
                                {
                                    "odrl:leftOperand": {
                                        "@id": "cx-policy:UsagePurpose"
                                    },
                                    "odrl:operator": {
                                        "@id": "odrl:eq"
                                    },
                                    "odrl:rightOperand": "cx.circular.dpp:1"
                                }
                            ]
                        }
                    },
                    "odrl:prohibition": [],
                    "odrl:obligation": []
        }
    ]

    catalog = {
        "@id": "f118963c-bdb9-41bf-81a0-e20443b2e716",
        "@type": "dcat:Catalog",
        "dspace:participantId": "BPNL000000000FV1",
        "dcat:dataset": [
            {
                "@id": "urn:uuid:0c3d2db0-e5c6-27f9-5875-15a9a00e7a27",
                "@type": "dcat:Dataset",
                "odrl:hasPolicy": {
                    "@id": "NzU3YjBjZjQtNmIyYS00MThhLWI3MWEtZjcwMTY2NWJlODg0:dXJuOnV1aWQ6MGMzZDJkYjAtZTVjNi0yN2Y5LTU4NzUtMTVhOWEwMGU3YTI3:NDlhYjY0NGMtN2Y0YS00OTQ5LWI5Y2YtODM0YmRkNWJiMGQ2",
                    "@type": "odrl:Offer",
                    "odrl:permission": {
                        "odrl:action": {
                            "@id": "odrl:use"
                        },
                        "odrl:constraint": {
                            "odrl:and": [
                                {
                                    "odrl:leftOperand": {
                                        "@id": "cx-policy:Membership"
                                    },
                                    "odrl:operator": {
                                        "@id": "odrl:eq"
                                    },
                                    "odrl:rightOperand": "active"
                                },
                                {
                                    "odrl:leftOperand": {
                                        "@id": "cx-policy:UsagePurpose"
                                    },
                                    "odrl:operator": {
                                        "@id": "odrl:eq"
                                    },
                                    "odrl:rightOperand": "cx.circular.dpp:1"
                                }
                            ]
                        }
                    },
                    "odrl:prohibition": [],
                    "odrl:obligation": []
                },
                "dcat:distribution": [
                    {
                        "@type": "dcat:Distribution",
                        "dct:format": {
                            "@id": "AzureStorage-PUSH"
                        },
                        "dcat:accessService": {
                            "@id": "fceb9e9b-6ad6-4b07-87e9-a5a71e49cb94",
                            "@type": "dcat:DataService",
                            "dcat:endpointDescription": "dspace:connector",
                            "dcat:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp",
                            "dct:terms": "dspace:connector",
                            "dct:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp"
                        }
                    },
                    {
                        "@type": "dcat:Distribution",
                        "dct:format": {
                            "@id": "HttpData-PULL"
                        },
                        "dcat:accessService": {
                            "@id": "fceb9e9b-6ad6-4b07-87e9-a5a71e49cb94",
                            "@type": "dcat:DataService",
                            "dcat:endpointDescription": "dspace:connector",
                            "dcat:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp",
                            "dct:terms": "dspace:connector",
                            "dct:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp"
                        }
                    },
                    {
                        "@type": "dcat:Distribution",
                        "dct:format": {
                            "@id": "HttpData-PUSH"
                        },
                        "dcat:accessService": {
                            "@id": "fceb9e9b-6ad6-4b07-87e9-a5a71e49cb94",
                            "@type": "dcat:DataService",
                            "dcat:endpointDescription": "dspace:connector",
                            "dcat:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp",
                            "dct:terms": "dspace:connector",
                            "dct:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp"
                        }
                    },
                    {
                        "@type": "dcat:Distribution",
                        "dct:format": {
                            "@id": "AmazonS3-PUSH"
                        },
                        "dcat:accessService": {
                            "@id": "fceb9e9b-6ad6-4b07-87e9-a5a71e49cb94",
                            "@type": "dcat:DataService",
                            "dcat:endpointDescription": "dspace:connector",
                            "dcat:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp",
                            "dct:terms": "dspace:connector",
                            "dct:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp"
                        }
                    }
                ],
                "type": {
                    "@id": "Asset"
                },
                "id": "urn:uuid:0c3d2db0-e5c6-27f9-5875-15a9a00e7a27"
            },
            {
                "@id": "registry-asset",
                "@type": "dcat:Dataset",
                "odrl:hasPolicy": {
                    "@id": "ZGVmYXVsdC1jb250cmFjdC1kZWZpbml0aW9u:cmVnaXN0cnktYXNzZXQ=:Yzg3YzNjZmEtYzkwZS00NGMzLTlhMWItMDYwOTlmYjIzYjFm",
                    "@type": "odrl:Offer",
                    "odrl:permission": {
                        "odrl:action": {
                            "@id": "odrl:use"
                        },
                        "odrl:constraint": {
                            "odrl:and": [
                                {
                                    "odrl:leftOperand": {
                                        "@id": "cx-policy:Membership"
                                    },
                                    "odrl:operator": {
                                        "@id": "odrl:eq"
                                    },
                                    "odrl:rightOperand": "active"
                                },
                                {
                                    "odrl:leftOperand": {
                                        "@id": "cx-policy:UsagePurpose"
                                    },
                                    "odrl:operator": {
                                        "@id": "odrl:eq"
                                    },
                                    "odrl:rightOperand": "cx.core.digitalTwinRegistry:1"
                                }
                            ]
                        }
                    },
                    "odrl:prohibition": [],
                    "odrl:obligation": []
                },
                "dcat:distribution": [
                    {
                        "@type": "dcat:Distribution",
                        "dct:format": {
                            "@id": "AzureStorage-PUSH"
                        },
                        "dcat:accessService": {
                            "@id": "fceb9e9b-6ad6-4b07-87e9-a5a71e49cb94",
                            "@type": "dcat:DataService",
                            "dcat:endpointDescription": "dspace:connector",
                            "dcat:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp",
                            "dct:terms": "dspace:connector",
                            "dct:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp"
                        }
                    },
                    {
                        "@type": "dcat:Distribution",
                        "dct:format": {
                            "@id": "HttpData-PULL"
                        },
                        "dcat:accessService": {
                            "@id": "fceb9e9b-6ad6-4b07-87e9-a5a71e49cb94",
                            "@type": "dcat:DataService",
                            "dcat:endpointDescription": "dspace:connector",
                            "dcat:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp",
                            "dct:terms": "dspace:connector",
                            "dct:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp"
                        }
                    },
                    {
                        "@type": "dcat:Distribution",
                        "dct:format": {
                            "@id": "HttpData-PUSH"
                        },
                        "dcat:accessService": {
                            "@id": "fceb9e9b-6ad6-4b07-87e9-a5a71e49cb94",
                            "@type": "dcat:DataService",
                            "dcat:endpointDescription": "dspace:connector",
                            "dcat:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp",
                            "dct:terms": "dspace:connector",
                            "dct:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp"
                        }
                    },
                    {
                        "@type": "dcat:Distribution",
                        "dct:format": {
                            "@id": "AmazonS3-PUSH"
                        },
                        "dcat:accessService": {
                            "@id": "fceb9e9b-6ad6-4b07-87e9-a5a71e49cb94",
                            "@type": "dcat:DataService",
                            "dcat:endpointDescription": "dspace:connector",
                            "dcat:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp",
                            "dct:terms": "dspace:connector",
                            "dct:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp"
                        }
                    }
                ],
                "version": "3.0",
                "dct:type": {
                    "@id": "https://w3id.org/catenax/taxonomy#DigitalTwinRegistry"
                },
                "asset:prop:type": "data.core.digitalTwinRegistry",
                "id": "registry-asset"
            }
        ],
        "dcat:service": {
            "@id": "fceb9e9b-6ad6-4b07-87e9-a5a71e49cb94",
            "@type": "dcat:DataService",
            "dcat:endpointDescription": "dspace:connector",
            "dcat:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp",
            "dct:terms": "dspace:connector",
            "dct:endpointUrl": "https://dpp.int.catena-x.net/provider/api/v1/dsp"
        },
        "participantId": "BPNL000000000FV1",
        "@context": {
            "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
            "edc": "https://w3id.org/edc/v0.0.1/ns/",
            "tx": "https://w3id.org/tractusx/v0.0.1/ns/",
            "tx-auth": "https://w3id.org/tractusx/auth/",
            "cx-policy": "https://w3id.org/catenax/policy/",
            "dcat": "http://www.w3.org/ns/dcat#",
            "dct": "http://purl.org/dc/terms/",
            "odrl": "http://www.w3.org/ns/odrl/2/",
            "dspace": "https://w3id.org/dspace/v0.8/"
        }
    }


    valid_assets_policies = DspUtils.filter_assets_and_policies(catalog=catalog, allowed_policies=configured_policies)
    print(valid_assets_policies)
    assert(len(valid_assets_policies) == 1)


