from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AURA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    write_to_databricks: bool = False
    vllm_base_url: str = ""
    session_ttl_seconds: int = 3600
    max_upload_size_mb: int = 50
    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def _load_dotenv_map() -> dict[str, str]:
    env_file = Path(".env")
    if not env_file.exists():
        return {}

    values: dict[str, str] = {}
    try:
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            values[key.strip()] = val.strip().strip('"').strip("'")
    except OSError:
        return {}
    return values


def _read_env(key: str) -> str:
    value = os.environ.get(key)
    if value:
        return value.strip()
    return _load_dotenv_map().get(key, "").strip()


def databricks_available() -> bool:
    return bool(_read_env("DATABRICKS_HOST"))


def vector_search_available() -> bool:
    """
    Vector retrieval is available if either backend is configured:
      - Actian VectorAI (`ACTIAN_HOST`)
      - Databricks Vector Search (`DATABRICKS_HOST`)
    """
    return bool(_read_env("ACTIAN_HOST") or _read_env("DATABRICKS_HOST"))
