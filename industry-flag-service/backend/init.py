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

# Set up imports configuration
import argparse
import logging.config
import sys
import time
from io import BytesIO

import requests
import urllib3
import uvicorn
import yaml
from fastapi import FastAPI, Request

from managers.edcManager import EdcManager
from managers.flagManager import FlagManager
from tractusx_sdk.dataspace.managers import AuthManager
from tractusx_sdk.dataspace.managers import OAuth2Manager
from models.requests import EdcRequest, EdcPostRequest
from models.search import Search, SearchProof
from service.edcService import EdcService
from service.flagService import FlagService
from utilities.httpUtils import HttpUtils
from utilities.operators import op
from tractusx_sdk.dataspace.services.connector import ServiceFactory
from tractusx_sdk.dataspace.services.discovery import ConnectorDiscoveryService
from tractusx_sdk.dataspace.services.discovery import DiscoveryFinderService
from utilities.sovityAuth import SovityAuth

op.make_dir("logs")

DEFAULT_CACHE_EXPIRATION: int = 60
DEFAULT_CATALOG_TIMEOUT: int = 10
DEFAULT_APP_CACHE_EXPIRATION: int = 1440
## Declare Global Variables
app_configuration: dict
log_config: dict
edcManager: EdcManager
edcService: EdcService
idpManager: OAuth2Manager
flagService: FlagService
authManager: AuthManager
flagManager: FlagManager
edcDiscoveryService: ConnectorDiscoveryService
discoveryFinderService: DiscoveryFinderService
connectorService: ServiceFactory

urllib3.disable_warnings()
logging.captureWarnings(True)

# Load the logging config file
with open('./config/logging.yml', 'rt') as f:
    # Read the yaml configuration
    log_config = yaml.safe_load(f.read())
    # Set logging filename with datetime
    date = op.get_filedate()
    op.make_dir("logs/" + date)
    log_config["handlers"]["file"]["filename"] = f'logs/{date}/{op.get_filedatetime()}-ifs.log'
    logging.config.dictConfig(log_config)

logger = logging.getLogger('staging')

# Load the configuration for the application
with open('./config/configuration.yml', 'rt') as f:
    # Read the yaml configuration
    app_configuration = yaml.safe_load(f.read())

# Add the previous folder structure to the system path to import the utilities

app = FastAPI(title="main")


@app.get("/health")
async def health():
    """
    Retrieves health information from the server

    Returns:
        response: :obj:`status, timestamp`
    """
    logger.debug("[HEALTH CHECK] Retrieving positive health information!")
    return HttpUtils.response({
        "status": "RUNNING",
        "timestamp": op.timestamp()
    })


## Get offers!
@app.get("/flags")
async def get_my_flags(request: Request):
    """
    Retrieves all the offer information the user is allowed to see

    Returns:
        response: :obj:`Object with offer keys and short descriptions`
    """
    try:
        ## Check if the api key is present and if it is authenticated
        if not authManager.is_authenticated(request=request):
            return HttpUtils.get_not_authorized()
        calling_bpn = request.headers.get('Edc-Bpn', None)

        if calling_bpn is not None:
            logger.info(f"[Flags Request] Receiving request for company flags from [{calling_bpn}] EDC Connector...")

        return flagManager.get_flags()
    except Exception as e:
        logger.exception(str(e))
        return HttpUtils.get_error_response(
            status=500,
            message="It was not possible to get offers!"
        )


## Get my flag proof!
@app.get("/flags/{id}")
async def get_my_proof(id: str, request: Request):
    """
    Retrieves all the offer information the user is allowed to see

    Returns:
        response: :obj:`Object with offer keys and short descriptions`
    """
    try:
        ## Check if the api key is present and if it is authenticated
        if not authManager.is_authenticated(request=request):
            return HttpUtils.get_not_authorized()

        calling_bpn = request.headers.get('Edc-Bpn', None)

        if calling_bpn is not None:
            logger.info(
                f"[Flag Proof Request] Receiving request for my company flag [{id}] proof from [{calling_bpn}] EDC Connector...")
        return flagManager.get_proof(id=id)
    except Exception as e:
        logger.exception(str(e))
        return HttpUtils.get_error_response(
            status=500,
            message="It was not possible to get the flag proof!"
        )


## TODO: PERFORM SEARCH
@app.post("/flags/search")
async def search_flags(search: Search, request: Request):
    """
    Searches one or more offers based on a filter
    Returns:
        response: :obj:`200 with data if Success, 500 if Failure`
    """
    try:
        ## Check if the api key is present and if it is authenticated
        if not authManager.is_authenticated(request=request):
            return HttpUtils.get_not_authorized()
        if not search:
            return HttpUtils.get_error_response(
                status=403,
                message="There was no BPN specified in the search"
            )
        return flagService.get_flags(bpn=search.bpn, raw_response=False)
    except Exception as e:
        logger.exception(str(e))
        return HttpUtils.get_error_response(
            status=500,
            message=str(e)
        )


@app.post("/data/get")
async def data_get(get_request: EdcRequest, request: Request):
    try:
        ## Check if the api key is present and if it is authenticated
        if not authManager.is_authenticated(request=request):
            return HttpUtils.get_not_authorized()
        return HttpUtils.proxy(edcService.do_get(
            counter_party_id=get_request.bpn,
            counter_party_address=get_request.url,
            dct_type=get_request.dct_type,
            path=get_request.path,
            policies=get_request.policies,
            headers=get_request.headers
        ))
    except Exception as e:
        logger.exception(str(e))
        return HttpUtils.get_error_response(
            status=500,
            message=f"It was not possible to do the GET request to the EDC! Reason: [{str(e)}]"
        )


@app.post("/data/post")
async def data_post(post_request: EdcPostRequest, request: Request):
    try:
        ## Check if the api key is present and if it is authenticated
        if not authManager.is_authenticated(request=request):
            return HttpUtils.get_not_authorized()
        return HttpUtils.proxy(edcService.do_post(
            counter_party_id=post_request.bpn,
            counter_party_address=post_request.url,
            dct_type=post_request.dct_type,
            path=post_request.path,
            policies=post_request.policies,
            headers=post_request.headers,
            data=post_request.body,
            content_type=post_request.content_type
        ))
    except Exception as e:
        logger.exception(str(e))
        return HttpUtils.get_error_response(
            status=500,
            message=f"It was not possible to do the POST request to the EDC! Reason: [{str(e)}]"
        )


@app.post("/flags/proof")
async def get_proof(searchProof: SearchProof, request: Request):
    try:
        ## Check if the api key is present and if it is authenticated
        if not authManager.is_authenticated(request=request):
            return HttpUtils.get_not_authorized()
        ## Get details from EDC and return proof
        response: requests.Response = flagService.get_flag_proof(bpn=searchProof.bpn, id=searchProof.id)

        headers = response.headers

        if "content-type" not in headers:
            return HttpUtils.get_error_response(
                status=400,
                message="No content type in response, not able to parse!"
            )

        content_type = headers["content-type"]

        if content_type in flagManager.json_accepted_types:
            return HttpUtils.response(status=200, data=response.json())

        if content_type not in flagManager.application_types:
            return HttpUtils.get_error_response(
                status=400,
                message="File response not supported!"
            )

        filename = f"{searchProof.id}{flagManager.application_types[content_type]}"
        if "content-disposition" in headers:
            filename = headers["content-disposition"].split("filename=")[1].strip('"')

        return HttpUtils.file_response(buffer=BytesIO(response.content), filename=filename, content_type=content_type)
    except Exception as e:
        logger.exception(str(e))
        return HttpUtils.get_error_response(
            status=500,
            message="It was not possible to do the search!"
        )


def init_app(host: str, port: int, log_level: str = "info"):
    global app, app_configuration, flagManager, flagService, edcService, edcManager, edcDiscoveryService, discoveryFinderService, authManager
    ## Load company flags
    flags_config: list = app_configuration["flags"]

    if (flags_config is None) or (len(flags_config) < 0):
        logger.warning("[INIT] No industry flags defined!")

    ifs_config: dict = app_configuration["ifs"]

    flagManager = FlagManager(flags=flags_config,
                              refresh_interval=ifs_config.get("refresh_interval", DEFAULT_APP_CACHE_EXPIRATION))
    logger.info(f"[INIT] [{len(flagManager.my_flags)} of {len(flags_config)}] industry flags loaded!")

    if not ("edc" in app_configuration):
        raise Exception(
            "[INIT] It was not possible to connect to the EDC Connector because there was no configuration available")

    authManager = AuthManager()


    auth_config: dict = app_configuration.get("authorization", {"enabled": False})
    auth_enabled: bool = auth_config.get("enabled", False)

    if auth_enabled:
        api_key: dict = auth_config.get("apiKey", {"key": "X-Api-Key", "value": "password"})
        authManager = AuthManager(api_key_header=api_key.get("key", "X-Api-Key"),
                                  configured_api_key=api_key.get("value", "password"), auth_enabled=True)

    #### [EDC CONNECTION CHECK] [START] ------
    ## Get start config configuration
    startup_config: dict = app_configuration.get("startup", {"checks": True, "refresh_interval": 10})
    startup_config.get("checks", True)
    refresh_interval: int = startup_config.get("refresh_interval", 10)
    edc_config: dict = app_configuration.get("edc", None)
    edc_url: str = edc_config.get("url",None)
    dma_path: str = edc_config.get("dma_path",None)

    logger.info(edc_config)

    connected = False
    while not connected:
        try:
            logger.info("[INIT] Attempting connection to the EDC Connector...")
            edcService = EdcService(config=edc_config)
            connected = True
        except Exception as e:
            logger.critical(str(e))
            logger.critical(
                "[INIT] The EDC connection is not available! Please connect a valid EDC connector and try again...")
            logger.info(f"[INIT] Waiting {str(refresh_interval)} seconds and then retrying connection...")
            time.sleep(refresh_interval)

    #### [EDC CONNECTION CHECK] [END] ------

    ## Configuration checks
    catenax_config: dict = app_configuration.get("catenax", None)
    if catenax_config is None:
        raise Exception("[INIT] No catenax configuration was specified!")

    centralidp_config: dict = catenax_config.get("centralidp", None)
    if centralidp_config is None:
        raise Exception("[INIT] No centralidp config was specified!")

    auth_url: str = centralidp_config.get("url", None)
    if auth_url is None:
        raise Exception("[INIT] No centralidp url config was specified!")

    realm: str = centralidp_config.get("realm", None)
    if auth_url is None:
        raise Exception("[INIT] No centralidp realm config was specified!")

    clientid: str = centralidp_config.get("client_id", None)
    if auth_url is None:
        raise Exception("[INIT] No centralidp clientid config was specified!")

    clientsecret: str = centralidp_config.get("client_secret", None)
    if auth_url is None:
        raise Exception("[INIT] No centralidp clientsecret config was specified!")

    #### [KEYCLOAK AUTH CHECK] [START] ------
    try:
        idpManager = OAuth2Manager(auth_url=auth_url, clientid=clientid, clientsecret=clientsecret, realm=realm)
        logger.info("[INIT] Sucessfully connected to the centralidp server!")
    except Exception as e:
        logger.critical("[INIT] The authentication service has failed! Reason: %s", str(e))

    discovery_config: dict = app_configuration.get("discovery", None)
    if discovery_config is None:
        raise Exception("[INIT] No discovery config was specified!")

    discovery_keys: dict = discovery_config.get("keys",None)
    if discovery_keys is None:
        raise Exception("[INIT] No discovery key was specified!")

    connector_discovery_key: str = discovery_keys.get("edc_discovery", None)

    discoveryFinderService = DiscoveryFinderService(oauth=idpManager, url=discovery_config.get("url",None))
    edcDiscoveryService = ConnectorDiscoveryService(oauth=idpManager, discovery_finder_service=discoveryFinderService, connector_discovery_key=connector_discovery_key)

    ### EDC Manager Config

    cache_config: dict = edc_config.get("cache", {"expiration_time": DEFAULT_CACHE_EXPIRATION})
    edcManager = EdcManager(dct_type=edc_config.get("dct_type", "IndustryFlagService"),
                            edc_discovery=edcDiscoveryService,
                            expiration_time=cache_config.get("expiration_time", DEFAULT_CACHE_EXPIRATION))

    flagService = FlagService(config=ifs_config, edc_service=edcService, edc_manager=edcManager, idp_manager=idpManager,
                              flag_manager=flagManager)

    logger.info("[INIT] Application Startup Initialization Completed!")

    uvicorn.run(app, host=host, port=port, log_level=log_level)

    ## TEST Connect here

    # print("[DO_GET QUERY] =================================================================")
    # config = {
    #         "url": "https://cgi-connector-edc.dataspaceos.preprod.cofinity-x.com",
    #         "apis": {
    #             "readiness": "/api/check/readiness",
    #             "catalog": "/management/v3/catalog/request",
    #             "edr_prefix": "/management/v2/edrs",
    #             "view_edr": "/request",
    #             "transfer_edr": "/dataaddress?auto_refresh=true",
    #             "dsp": "/api/v1/dsp"
    #         },
    #         "apiKey": {
    #             "key": "X-Api-Key",
    #             "value": "54F248FACF914D3B2A48FBC50C7CD8A78ADD726B9256310A773DD56A9059E7CC"
    #         },
    #         "participantId": "BPNL00000001VDGS"
    #     }

    # edc_provider = "https://cgi-prov-edc.dataspaceos.preprod.cofinity-x.com"
    # provider_bpn = "BPNL00000001VDGS"
    # dct_type_key = "https://w3id.org/catenax/taxonomy#DigitalTwinRegistry"
    # start_time = datetime.now()

    # logger.info(edcService.do_get(counter_party_id=provider_bpn,
    #                         edc_provider_url=edc_provider, 
    #                         path="/shell-descriptors", 
    #                         policies=config_policies, 
    #                         dct_type=dct_type_key))

    # end_time = datetime.now()
    # time_difference = (end_time  - start_time).total_seconds() * 10**3
    # print("Negotiation and GET Query", time_difference, "ms", (end_time  - start_time).total_seconds(), "seconds") 

    # print("[DO_POST QUERY] =================================================================")
    # start_time2 = datetime.now()

    # logger.info(edcService.do_post(counter_party_id=provider_bpn,
    #                         edc_provider_url=edc_provider, 
    #                         body = [
    #                             {
    #                                 "name": "partInstanceId",
    #                                 "value": "DPPV-0011"
    #                             }
    #                         ],
    #                         path="/lookup/shellsByAssetLink", 
    #                         policies=config_policies, 
    #                         dct_type=dct_type_key))

    # end_time2 = datetime.now()
    # time_difference2 = (end_time2  - start_time2).total_seconds() * 10**3
    # print("POST Query after GET", time_difference2, "ms", (end_time2  - start_time2).total_seconds(), "seconds") 


def get_arguments():
    """
    Commandline argument handling. Return the populated namespace.

    Returns:
        args: :func:`parser.parse_args`
    """

    parser = argparse.ArgumentParser()

    parser.add_argument("--port", default=8000,
                        help="The server port where it will be available", required=False, type=int)

    parser.add_argument("--host", default="localhost",
                        help="The server host where it will be available", required=False, type=str)

    parser.add_argument("--debug", default=False, action="store_false", \
                        help="Enable and disable the debug", required=False)

    args = parser.parse_args()
    return args


if __name__ == "__main__":

    print("\n" +
          "   ____        __         __             ______            ____             _        \n" +
          "  /  _/__  ___/ /_ _____ / /_______ __  / __/ /__ ____ _  / __/__ _____  __(_)______ \n" +
          " _/ // _ \\/ _  / // (_-</ __/ __/ // / / _// / _ `/ _ `/ _\\ \\/ -_) __/ |/ / / __/ -_)\n" +
          "/___/_//_/\\_,_/\\_,_/___/\\__/_/  \\_, / /_/ /_/\\_,_/\\_, / /___/\\__/_/  |___/_/\\__/\\__/ \n" +
          "                               /___/             /___/                               \n" +
          " \n\n\t\t\t\t\t\t\t\t\t\tv1.0.0")

    print("Application starting, listening to requests...\n")

    # Initialize the server environment and get the comand line arguments
    args = get_arguments()
    # Configure the logging confiuration depending on the configuration stated
    logger = logging.getLogger('staging')
    if args.debug:
        logger = logging.getLogger('development')

    # Init application
    init_app(host=args.host, port=args.port, log_level=("debug" if args.debug else "info"))

    print("\nClosing the application... Thank you for using the Industry Flag Service (IFS)!")
