"""
Azure OpenAI client helpers for Chat Completions.

Uses deployment-based Azure OpenAI REST endpoints:
  {AZURE_OPENAI_ENDPOINT}/openai/deployments/{deployment}/chat/completions
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)
_DOTENV_CACHE: Optional[dict[str, str]] = None
_NO_EM_DASH_RULE = "Ensure that the response contains no em dashes."


def _normalize_endpoint(endpoint: str) -> str:
    return endpoint.rstrip("/")


def _flatten_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Handle multimodal content arrays by extracting text parts.
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                txt = item.get("text")
                if isinstance(txt, str):
                    texts.append(txt)
        return "\n".join(texts).strip()
    return ""


def _with_no_em_dash_rule(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure all Azure OpenAI calls include the no-em-dash instruction."""
    for message in messages:
        if message.get("role") != "system":
            continue
        content = message.get("content")
        if isinstance(content, str) and _NO_EM_DASH_RULE in content:
            return messages
    return [{"role": "system", "content": _NO_EM_DASH_RULE}, *messages]


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


def read_env(key: str, default: str = "") -> str:
    value = os.environ.get(key)
    if value:
        return value.strip()

    global _DOTENV_CACHE
    if _DOTENV_CACHE is None:
        _DOTENV_CACHE = _load_dotenv_map()
    return _DOTENV_CACHE.get(key, default).strip()


def chat_completion(
    *,
    messages: list[dict[str, Any]],
    deployment: Optional[str],
    max_tokens: int,
    temperature: float,
    timeout: int = 60,
) -> Optional[str]:
    """
    Call Azure OpenAI Chat Completions and return assistant text content.
    Returns None on configuration or request failure.
    """
    endpoint = read_env("AZURE_OPENAI_ENDPOINT")
    api_key = read_env("AZURE_OPENAI_API_KEY")
    api_version = read_env("AZURE_OPENAI_API_VERSION", "2024-06-01")
    deployment = (deployment or "").strip()

    if not endpoint or not api_key or not deployment:
        logger.warning(
            "Azure OpenAI not fully configured. "
            "Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and deployment env vars."
        )
        return None

    url = (
        f"{_normalize_endpoint(endpoint)}/openai/deployments/{deployment}/chat/completions"
        f"?api-version={api_version}"
    )
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "messages": _with_no_em_dash_rule(messages),
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        return _flatten_content(message.get("content"))
    except Exception as e:
        logger.warning(f"Azure OpenAI chat completion failed: {e}")
        return None
