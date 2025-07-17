# DT Pull Service - Summary Documentation

## 1. Overview
This application facilitates the retrieval of Digital Twin (DT) data from the Catena-X infrastructure through EDR (Endpoint Data Reference) and DTR (Digital Twin Registry) endpoints. The service is built on the FastAPI framework and provides multiple API endpoints for cataloging, negotiations, and data transfer.

## 2. Main Components
The application consists of the following core components:

EdrHandler: Manages communication with the EDR.

DtrHandler: Manages communication with the DTR.

API Router: Provides endpoints accessible through the FastAPI framework.

App Factory (create_app): Responsible for creating the main application object.

## 3. Key Classes and Methods
### EdrHandler Class
Description: Manages communication with the EDC.

Key Methods:

query_catalog_json: Queries the catalog in JSON format.

initiate_edr_negotiate: Initiates an EDR negotiation.

check_edr_negotiate_state: Checks the state of an EDR negotiation.

get_ddtr_address: Retrieves the DDTR address.

find_sub_model_edr_agreement_id: Retrieves the Digital Twin Registry (DDTR) address.

### DtrHandler Class
Description: Manages communication with the partner's DTR.

Key Methods:

dtr_find_shell_descriptor: Queries a shell descriptor.

send_feedback: Sends a message for the partner's DTR about the certification status.

## 4. Additional Utility Functions
create_app
Description: Initializes the main FastAPI application object, including configurations, exception handling, and endpoint integration.

find_env_file
Description: A utility function to locate an environment file (.env) by checking the ENVFILE_PATH environment variable or falling back to python-dotenv's find_dotenv.

## 5. API Endpoints
### /get-catalog/
Method: GET Description: Retrieves the EDR catalog JSON based on the provided filtering parameters. Parameters:

operand_left: Filtering property.

operand_right: Filtering value.

counter_party_address: Address of the counterparty's EDC.

bpn: Business Partner Number. Returns: A JSON object containing catalog information.

### /init-negotiation/
Method: POST Description: Initiates a negotiation based on the provided catalog JSON. Parameters:

catalog_json: JSON containing catalog information.

counter_party_address: Address of the counterparty's EDC.

bpn: Business Partner Number. Returns: A JSON object containing negotiation details.

### /negotiation-state/
Method: GET Description: Retrieves the current state of an ongoing negotiation. Parameters:

state_id: Negotiation state identifier.

counter_party_address: Address of the counterparty's EDC.

bpn: Business Partner Number. Returns: A JSON object containing the current state of the negotiation.

### /transfer-process/
Method: POST Description: Initiates a transfer process and retrieves its details. Parameters:

data: Transfer specifications JSON.

counter_party_address: Address of the counterparty's EDC.

bpn: Business Partner Number. Returns: A list of JSON objects representing transfer process details.

### /data-address/
Method: GET Description: Retrieves the data address for the provided transfer process ID. Parameters:

transfer_process_id: Transfer process identifier.

counter_party_address: Address of the counterparty's EDC.

bpn: Business Partner Number. Returns: A JSON object containing the data address.

### /shell-descriptors/
Method: GET Description: Retrieves shell descriptors from the partner's DTR. Returns: A JSON object containing shell descriptor details.

### /send-feedback/
Method: Post Description: Sends a feedback about the result of the feedback validation. Returns: JSON information, if the feedback was accepted.

## 6. Developing
Install poetry

Windows:
```
PS: (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py
```

Linux:
```sh
sudo apt install python3-poetry
```
or:
```sh
pipx install poetry
```

Install the dependencies with poetry
```sh
poetry lock
poetry install
```

Create your .env, check for testing.env or config.py to check, which env vars you'll need

### 7. Run the application locally

```sh
poetry run dotenv -f .env run uvicorn dt_pull_service.app:create_app --reload --proxy-headers --factory --port 8001
```
Now you can reach the documents on (change the port, if necessary):
```sh
localhost:8001/docs
```
or:
```sh
localhost:8001/redoc
```
or the openapi json:
```sh
localhost:8001/openapi.json
```

## 8. Testing
Run tests using the following command:

```sh
poetry run dotenv -f testing.env run pytest -vvv tests/
```
Refer to pytest's documentation for more detailed testing strategies.


## 9. Linting
Use pylint to lint Python files.

```sh
poetry run pylint $(git ls-files '*.py')
```
You can find the linting rules in the pyproject.toml file.

### Docker
```sh
sudo docker build -t dt-pull .
```

For the next command to work, you might need to create a network in Docker:
```sh
sudo docker network create my-network
```

To run the application with Docker use this command:
```sh
sudo docker run --network my-network --name dt-pull -p 8001:8000 dt-pull
```

The value of --name is used in the Test Orchestrator's docker.env, if you change it, please keep in mind to change there, too.

## NOTICE

This work is licensed under the [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode).

- SPDX-License-Identifier: CC-BY-4.0
- SPDX-FileCopyrightText: 2025 BMW AG
- SPDX-FileCopyrightText: 2025 Contributors to the Eclipse Foundation
- Source URL: https://github.com/eclipse-tractusx/tractusx-sdk-services

