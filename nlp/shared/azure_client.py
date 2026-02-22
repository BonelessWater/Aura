"""
AzureNLPClient -- shared singleton for Azure OpenAI calls from NLP modules.

Mirrors the DatabricksClient singleton pattern in nlp/shared/databricks_client.py.
Reads credentials from the same env vars used by backend/routers/body_map.py.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class AzureNLPClient:
    """Thread-safe singleton Azure OpenAI client for NLP modules."""

    _instance: Optional[AzureNLPClient] = None

    def __new__(cls) -> AzureNLPClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._client = None
        self.endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        self.api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        self.api_version = os.environ.get("OPENAI_API_VERSION", "2024-12-01-preview")

        self.deployments = {
            "nano": os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT41_NANO", "gpt-4.1-nano"),
            "mini": os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT41_MINI", "gpt-4.1-mini"),
            "4o_mini": os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI", "gpt-4o-mini"),
            "4o": os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT4O", "gpt-4o"),
            "4.1": os.environ.get("AZURE_OPENAI_DEPLOYMENT_GPT41", "gpt-4.1"),
        }

    @property
    def client(self):
        if self._client is None:
            if not self.endpoint or not self.api_key:
                logger.warning("Azure OpenAI credentials not configured")
                return None
            from openai import AzureOpenAI

            self._client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )
        return self._client

    @property
    def available(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def chat(
        self,
        deployment: str,
        messages: list[dict],
        temperature: float = 0,
        max_tokens: int = 800,
    ) -> Optional[str]:
        """Single chat completion. Returns content string or None on failure."""
        c = self.client
        if c is None:
            return None
        try:
            response = c.chat.completions.create(
                model=self.deployments.get(deployment, deployment),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Azure OpenAI call failed (deployment=%s): %s", deployment, e)
            return None

    def chat_with_image(
        self,
        deployment: str,
        system_prompt: str,
        image_b64: str,
        user_text: str = "Describe clinical findings only.",
        temperature: float = 0.1,
        max_tokens: int = 256,
    ) -> Optional[str]:
        """Chat completion with an inline base64 image."""
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": user_text},
                ],
            },
        ]
        return self.chat(deployment, messages, temperature=temperature, max_tokens=max_tokens)


def get_nlp_backend(module_name: str) -> str:
    """Return 'azure' or 'local' for a given module."""
    override = os.environ.get(f"AURA_NLP_BACKEND_{module_name.upper()}")
    if override:
        return override.lower()
    return os.environ.get("AURA_NLP_BACKEND", "local").lower()


def get_azure_nlp_client() -> AzureNLPClient:
    return AzureNLPClient()
