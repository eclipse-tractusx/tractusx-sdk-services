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

# BUILD IMAGE
FROM python:3.12.2-slim AS builder

# Set environment variables
ENV POETRY_VERSION=1.6.1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Poetry
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN apt-get update && apt-get install -y curl openssh-client && \
    curl -sSL https://install.python-poetry.org | POETRY_HOME=$POETRY_HOME python3 - && \
    chmod -R 755 $POETRY_HOME && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies using Poetry
RUN poetry install --only=main --no-interaction --no-ansi

COPY . .

# RUNTIME IMAGE
FROM python:3.12.2-slim AS runtime

RUN apt-get update && apt-get install -y curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Poetry installation and dependencies from builder
COPY --from=builder /opt/poetry /opt/poetry
COPY --from=builder /root/.cache/pypoetry /root/.cache/pypoetry
COPY --from=builder /app /app
COPY . .

# Set Poetry environment variables
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV POETRY_CACHE_DIR="/tmp/poetry-cache"
ENV POETRY_VENV_IN_PROJECT=true
ENV POETRY_NO_INTERACTION=1
RUN mkdir -p /tmp/poetry-cache

# Fix permissions for app files, Poetry installation, Poetry cache, and tmp directory BEFORE switching user
RUN chown -R 10000:10001 /app && chmod -R 775 /app/ && \
    chown -R 10000:10001 /opt/poetry && chmod -R 755 /opt/poetry && \
    chown -R 10000:10001 /root/.cache && chmod -R 755 /root/.cache && \
    chown -R 10000:10001 /tmp/poetry-cache && chmod -R 755 /tmp/poetry-cache

## Choose the user
USER 10000:10001 

# Install dependencies and ensure virtual environment is created
RUN poetry install --only=main --no-interaction --no-ansi

# Expose the port for uvicorn
EXPOSE 8001

CMD ["poetry", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8001", "--factory", "dt_pull_service.app:create_app", "--proxy-headers", "--timeout-graceful-shutdown", "30"]
