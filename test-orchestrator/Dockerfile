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

FROM python:3.13.2-slim AS builder

# Set environment variables
ENV POETRY_VERSION=1.6.1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Poetry
RUN apt-get update && apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies using Poetry
RUN poetry install --no-dev --no-interaction --no-ansi

COPY . .

FROM python:3.13.2-slim AS runtime

RUN apt-get update && apt-get install -y curl libpq-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /root/.cache/pypoetry /root/.cache/pypoetry
COPY --from=builder /app /app
COPY . .

# Install Poetry in a location accessible to the non-root user
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=$POETRY_HOME python3 - && \
    chmod -R 755 $POETRY_HOME

# Fix permissions for app files and Poetry cache BEFORE switching user
RUN chown -R 10000:10001 /app && chmod -R 775 /app/ && \
    chown -R 10000:10001 /root/.cache && chmod -R 755 /root/.cache

## Choose the user
USER 10000:10001 
# Expose the port for uvicorn
EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "--factory", "test_orchestrator.app:create_app", "--proxy-headers"]
