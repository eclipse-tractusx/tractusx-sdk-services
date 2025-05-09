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

# Install runtime dependencies
RUN apt-get update && apt-get install -y curl libpq-dev && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /root/.cache/pypoetry /root/.cache/pypoetry
COPY --from=builder /app /app
COPY . .

# Expose the port for uvicorn
EXPOSE 8000

CMD ["poetry", "run", "dotenv", "-f", "docker.env", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "--factory", "orchestrator.app:create_app", "--proxy-headers"]
