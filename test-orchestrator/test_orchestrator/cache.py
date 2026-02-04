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

from abc import ABC, abstractmethod
from typing import Any, Optional

from fastapi import Request
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from test_orchestrator import config


class CacheProvider(ABC):
    """
    Abstract base class for cache providers.

    All cache implementations must provide asynchronous `get` and `set` methods
    that handle simple key–value operations with optional expiration support.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a cached value for the given key.
        Args:
            key: The cache key to look up.
        Returns:
            The cached value if present, otherwise None.
        """

    @abstractmethod
    async def set(self, key: str, value: Any, expire: int = None):
        """
        Store a value in the cache under the given key.

        Args:
            key: The key under which the value will be cached.
            value: The value to cache.
            expire: Optional expiration time in seconds. If None, no TTL is applied.
        """

    @abstractmethod
    async def delete(self, key: str):
        """Delete a cached value for the given key."""
        pass

class LocalCache(CacheProvider):
    """
    Local in-memory cache provider using FastAPI-Cache.
    This implementation is suitable for local development and testing.
    It initializes an in-memory backend and proxies calls to FastAPI-Cache.
    """

    def __init__(self):
        """Initialize the in-memory cache backend."""
        FastAPICache.init(InMemoryBackend())

    async def get(self, key: str):
        """See CacheProvider.get"""
        return await FastAPICache.get_backend().get(key)

    async def set(self, key: str, value, expire: int = None):
        """See CacheProvider.set"""
        await FastAPICache.get_backend().set(key, value, expire)

    async def delete(self, key: str):
        """Delete cached value"""
        await FastAPICache.get_backend().delete(key)


def create_cache_provider() -> CacheProvider:
    """
    Create and return the appropriate cache provider based on configuration.
    Returns:
        An instance of `CacheProvider` based on `config.CACHE_BACKEND`.
    Raises:
        ValueError: If the `CACHE_BACKEND` configuration value is unknown.
    """

    if config.CACHE_BACKEND == 'local':
        return LocalCache()

    raise ValueError(f'Unknown CACHE_BACKEND: {config.CACHE_BACKEND}')


def get_cache_provider(request: Request) -> CacheProvider:
    """
    Dependency function for retrieving the active cache provider from app state.
    Args:
        request: FastAPI request object, containing application state.
    Returns:
        The cache provider instance stored in `app.state.cache_provider`.
    """

    return request.app.state.cache_provider
