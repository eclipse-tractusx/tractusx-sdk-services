# How to work with the Catena-X Testbed DT Pull Service

### Developing
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

Create your .env, check for testing.env or config.py to check, which env vars you'll need.

### Run the application locally

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

### Testing

For running the tests:
```sh
poetry run dotenv -f testing.env run pytest -vvv tests/
```
For more in-depth knowledge how to run tests, check pytest's documentation

### Linting
```sh
poetry run pylint $(git ls-files '*.py')
```

### Docker
```sh
docker build -t dt-pull .
```

For the next command to work, you might need to create a network in Docker:
```sh
docker network create my-network
```

To run the application with Docker use this command:
```sh
docker run --network my-network --name dt-pull -p 8001:8000 dt-pull
```

The value of --name is used in the Test Orchestrator's docker.env, if you change it, please keep in mind to change there, too.


## NOTICE

This work is licensed under the [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode).

- SPDX-License-Identifier: CC-BY-4.0
- SPDX-FileCopyrightText: 2025 BMW AG
- SPDX-FileCopyrightText: 2025 Contributors to the Eclipse Foundation
- Source URL: https://github.com/eclipse-tractusx/tractusx-sdk-services

