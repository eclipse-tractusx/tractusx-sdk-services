# How to work with the Catena-X Testbed app

### Developing
Install poetry

Windows:
```
PS: (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python
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

Run the application
```sh
poetry run dotenv -f .env run uvicorn orchestrator.app:create_app --reload --proxy-headers --factory --port 8000
```
Now you can reach the documents on (change the port, if necessary):
```sh
localhost:8000/docs
```
or:
```sh
localhost:8000/redoc
```
or the openapi json:
```sh
localhost:8000/openapi.json
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
To build the application with Docker:
```sh
sudo docker build -t orchestrator .
```

For the next command to work, you might need to create a network in Docker:
```sh
sudo docker network create my-network
```

To run the application with Docker use this command:
```sh
sudo docker run --network my-network --name orchestrator -p 8000:8000 orchestrator
```

### Local Kubernetes deployment

Helm is used in this project to ease Kubernetes deployment.
I use Minikube, but use whatever you have on your machine.

Make sure, that the images are built in the Minikube env:
```sh
eval $(minikube docker-env)
```

Build the Docker image and deploy it to Kubernetes with Helm
```sh
docker build -t orchestrator:latest .
helm upgrade --install orchestrator ./helm --namespace=default
```

To use it from your local machine, dont forget to port forward:
```sh
kubectl --namespace default port-forward $POD_NAME 8000:8000
```
