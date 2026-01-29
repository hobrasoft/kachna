from __future__ import annotations

import configparser
from pathlib import Path
from typing import ClassVar


class BackendConfig:
    _parser: ClassVar[configparser.ConfigParser | None] = None
    _loaded: ClassVar[bool] = False

    @classmethod
    def _ensure_loaded(cls) -> configparser.ConfigParser:
        if cls._parser is None:
            cls._parser = configparser.ConfigParser()

        if not cls._loaded:
            config_paths = [
                Path("~/.kachna.conf").expanduser(),
                Path("/etc/kachna.conf"),
            ]
            cls._parser.read([str(path) for path in config_paths], encoding="utf-8")
            cls._loaded = True

        return cls._parser

    @classmethod
    def dbHostname(cls) -> str:
        parser = cls._ensure_loaded()
        return parser.get("db", "hostname", fallback="localhost")

    @classmethod
    def dbPort(cls) -> int:
        parser = cls._ensure_loaded()
        return parser.getint("db", "port", fallback=5432)

    @classmethod
    def dbDatabase(cls) -> str:
        parser = cls._ensure_loaded()
        return parser.get("db", "database", fallback="kachna")

    @classmethod
    def corsAllowOrigins(cls) -> list[str]:
        parser = cls._ensure_loaded()
        value = parser.get("cors", "allow_origins", fallback="*")
        origins = [item.strip() for item in value.split(",") if item.strip()]
        return origins or ["*"]

    @classmethod
    def llmBaseUrl(cls) -> str:
        parser = cls._ensure_loaded()
        return parser.get("llm", "base_url", fallback="http://localhost:8097").rstrip("/")

    @classmethod
    def llmTimeoutSeconds(cls) -> float:
        parser = cls._ensure_loaded()
        return parser.getfloat("llm", "timeout_s", fallback=60.0)

    @classmethod
    def llmApiKey(cls) -> str | None:
        parser = cls._ensure_loaded()
        value = parser.get("llm", "api_key", fallback="").strip()
        return value or None
