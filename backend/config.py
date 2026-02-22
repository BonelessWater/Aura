from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    write_to_databricks: bool = False
    vllm_base_url: str = ""
    session_ttl_seconds: int = 3600
    max_upload_size_mb: int = 50
    cors_origins: list[str] = ["*"]

    class Config:
        env_prefix = "AURA_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def databricks_available() -> bool:
    return bool(os.environ.get("DATABRICKS_HOST"))
