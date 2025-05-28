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

from utilities.httpUtils import HttpUtils
from requests import Response
import uuid
from utilities.operators import op
import logging
logger = logging.getLogger('staging')


class FlagManager:
    """
    Class responsible for managing the flag storage and applications administration.

    """

    my_flags: dict
    my_proofs: dict
    json_accepted_types: list
    application_types: dict
    known_apps: dict
    REFRESH_INTERVAL_KEY: str
    EDC_LIST_KEY: str

    # Every day refresh the flag storage
    def __init__(self, flags: list, refresh_interval=1440):

        self.json_accepted_types = [
            "application/json",
            "application/ld+json",
            "application/vc"
        ]

        self.application_types = {
            "application/json": ".json",
            "application/vc": ".jsonld",
            "application/ld+json": ".jsonld"
        }

        # Cache for own flags and proof storage
        self.my_flags, self.my_proofs = self.load_flags(flags=flags)

        # Cache memory for known applications behind edcs
        self.known_apps = {}

        self.refresh_interval = refresh_interval

        # Configuration of cache keys
        self.REFRESH_INTERVAL_KEY = "refresh_interval"
        self.EDC_LIST_KEY = "edcs"

    def load_flags(self, flags: list):
        try:
            my_industry_flags: dict = {}
            proofs: dict = {}
            for i, flag in enumerate(flags):
                # If the industry is not specified there will be an error and nothing will be stored, since it is mandatory!
                if ("industry" not in flag or flag["industry"] is None or flag["industry"] == ""):
                    logger.error(
                        f"[Flag Manager] The industry of the flag [{i+1}] was not specified! It will be ignored!")
                    continue

                # If type is not specified convert it to document
                if ("type" not in flag or flag["type"] is None or flag["type"] == ""):
                    logger.warning(
                        f"[Flag Manager] The type of the flag [{i+1}] was not specified! It will be substituted by Document!")
                    flag["type"] = "Document"

                # Create an unique id for the flag
                new_id = str(uuid.uuid4())
                # Substitute the type for Document when not available
                new_type = flag["type"]

                # If the type of file is not boolean and has no mimetype it will become a boolean.
                if (new_type != "Boolean" and "mimetype" not in flag):
                    logger.warning(
                        f"[Flag Manager] The mimetype of the flag [{i+1}] was not specified! It will be marked as Boolean and no proof will be stored!")
                    new_type = "Boolean"

                # Default flat when no
                my_flag = {
                    "industry": flag["industry"],
                    "type": new_type,
                }

                # If type is boolean and has mimetype it will be ignored
                if (new_type == "Boolean" and "mimetype" in flag):
                    logger.warning(
                        f"[Flag Manager] The mimetype in the boolean flag [{i+1}] will be ignored! No proof will be stored!")

                # The type of the flag boolean does not contain proof
                if (new_type == "Boolean"):
                    my_industry_flags[new_id] = my_flag
                    continue

                # Evaluate Mimetype

                mimetype = flag["mimetype"]

                # If no proof or location are specified the flag will be stored as default boolean
                if ((mimetype is None) or (mimetype == "") or ("proof" not in flag and "location" not in flag)):
                    logger.warning(
                        f"[Flag Manager] The mimetype is empty or the proof or location of the flag [{i+1}] were not specified! It will be marked as Boolean and no proof will be stored!")
                    my_flag["type"] = "Boolean"
                    my_industry_flags[new_id] = my_flag
                    continue

                # Get mimetype of flag and store it
                my_flag["mimetype"] = mimetype

                # If location is specified in the flag but the location is not valid and there is no proof specified, proof will be ignored
                if ("location" in flag) and not (op.path_exists(flag["location"])) and "proof" not in flag:
                    logger.error(
                        f"[Flag Manager] Invalid location at [{i+1}] flag, the path does not exists! The proof will not be stored!")
                    my_flag["type"] = "Boolean"
                    my_industry_flags[new_id] = my_flag
                    continue

                # If location is in the flag, then the path will exist, so it can be stored
                if ("location" in flag):
                    proofs[new_id] = flag["location"]
                    my_industry_flags[new_id] = my_flag
                    continue

                # Here there is no location in the flag, so proof will be taken if exists

                # If the proof is not available then no proof is there.
                if ("proof" not in flag):
                    logger.error(
                        f"[Flag Manager] The proof was not specified in the [{i+1}] flag, and was required when not specifing location! No proof will be stored!")
                    my_flag["type"] = "Boolean"
                    my_industry_flags[new_id] = my_flag
                    continue

                # The proof exists, but needs to be parsed
                # If is not json parsable it will be converted to text
                if (mimetype not in self.json_accepted_types):
                    proofs[new_id] = str(flag["proof"])  # Text Proofs
                    my_industry_flags[new_id] = my_flag
                    continue

                # Parse the JSON type proof and store it
                proofs[new_id] = op.json_string_to_object(
                    flag["proof"])  # JSON Proofs
                my_industry_flags[new_id] = my_flag

            # Return the flags and the proofs
            return my_industry_flags, proofs

        except Exception as e:
            raise Exception(
                "There was an error when parsing the flags configuration! Exception: ", e)

    def get_proof(self, id: str) -> Response:
        """
        Retrieves and returns the proof associated with the given ID.

        This function attempts to locate and return the proof associated with the provided ID.
        It handles various scenarios such as missing proofs, empty proofs, and different content types.

        Args:
            id (str): The unique identifier for the proof to be retrieved.

        Returns:
            Response: An HTTP response object containing either:
                - The requested proof file or data
                - An error response with an appropriate status code and message

        The function performs the following steps:
        1. Checks if the proof exists for the given ID
        2. Retrieves the proof data
        3. Determines the content type and file suffix
        4. Handles JSON content separately
        5. Verifies the existence of file-based proofs
        6. Returns the proof as a file response or an error response if any step fails
        """

        if (id not in self.my_flags):
            return HttpUtils.get_error_response(
                status=404,
                message="The flag was not found!"
            )

        if (self.my_flags[id]["type"] == "Boolean"):
            return HttpUtils.empty_response(status=204)

        if (id not in self.my_proofs):
            return HttpUtils.get_error_response(
                status=404,
                message="The proof was not found!"
            )
        # Resolve location. Get proof
        proof = self.my_proofs[id]

        if (proof == None or proof == ""):
            return HttpUtils.get_error_response(
                status=400,
                message="The proof is empty or is not available!"
            )

        content_type = self.my_flags[id]["mimetype"]
        suffix = ".txt"
        if (content_type == "application/json"):
            return HttpUtils.response(proof)

        if (content_type in self.application_types):
            suffix = self.application_types[content_type]
        else:
            content_type = "text/plain"

        if (not op.path_exists(proof)):
            return HttpUtils.get_error_response(
                status=404,
                message="The proof reference was not found!"
            )

        return HttpUtils.file_response(buffer=op.load_file(proof), filename=f"{id}{suffix}", content_type=content_type)

    def get_flags(self) -> dict:
        return self.my_flags

    def add_apps(self, bpn: str, edc_urls: list):

        if (bpn not in self.known_apps):
            self.known_apps[bpn] = {}

        partner: dict = self.known_apps[bpn]

        if (self.EDC_LIST_KEY not in partner):
            partner[self.EDC_LIST_KEY] = []

        # Add new edc to the list of known apps
        partner[self.EDC_LIST_KEY] = edc_urls
        partner[self.REFRESH_INTERVAL_KEY] = op.get_future_timestamp(
            minutes=self.refresh_interval)

    def get_apps(self, bpn) -> list:

        if (bpn not in self.known_apps):
            return []

        apps_info = self.known_apps[bpn]

        if (self.REFRESH_INTERVAL_KEY not in apps_info):
            return []

        refresh_interval = apps_info[self.REFRESH_INTERVAL_KEY]

        if (self.EDC_LIST_KEY not in apps_info):
            return []

        edcs = apps_info[self.EDC_LIST_KEY]

        # Invalidate the cache if the apps dont exist or if the interval has been reached
        if (len(edcs) == 0 or op.is_interval_reached(refresh_interval)):
            del self.known_apps[bpn]
            return []

        return edcs
