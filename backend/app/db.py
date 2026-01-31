from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import asyncpg

from .config import BackendConfig


@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


class Database:
    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self._config.host,
                port=self._config.port,
                database=self._config.database,
                user=self._config.user,
                password=self._config.password,
            )

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.execute(query, *args)


def load_database() -> Database:
    config = DatabaseConfig(
        host=BackendConfig.dbHostname(),
        port=BackendConfig.dbPort(),
        database=BackendConfig.dbDatabase(),
        user=BackendConfig.dbUser(),
        password=BackendConfig.dbPassword(),
    )
    return Database(config)
