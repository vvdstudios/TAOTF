"""
TAOTF LLM Client — Unified interface for Ollama (default) or OpenAI (fallback).

Uses the OpenAI Python SDK with configurable base_url. Ollama exposes an
OpenAI-compatible API at http://localhost:11434/v1, so no new dependencies needed.

Configuration via environment variables:
    TAOTF_LLM_BACKEND  - "ollama" (default) or "openai"
    TAOTF_LLM_MODEL    - Model name (default: "qwen2.5" for Ollama, "gpt-4o-mini" for OpenAI)
    TAOTF_LLM_BASE_URL - Override base URL (e.g. "http://remote-server:11434/v1")
    OPENAI_API_KEY      - Required only when TAOTF_LLM_BACKEND=openai

By Vivid Studio (https://vividstudio.me)
"""
from __future__ import annotations

import os

from openai import AsyncOpenAI

_DEFAULTS = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5",
        "api_key": "ollama",  # Ollama doesn't need a real key but the SDK requires one
    },
    "openai": {
        "base_url": None,  # Use OpenAI default
        "model": "gpt-4o-mini",
        "api_key": None,  # From OPENAI_API_KEY env
    },
}


def get_backend() -> str:
    """Return the configured LLM backend name."""
    return os.environ.get("TAOTF_LLM_BACKEND", "ollama").lower()


def get_model_name() -> str:
    """Return the configured model name."""
    backend = get_backend()
    default_model = _DEFAULTS.get(backend, _DEFAULTS["ollama"])["model"]
    return os.environ.get("TAOTF_LLM_MODEL", default_model)


def get_llm_client() -> AsyncOpenAI:
    """
    Return an AsyncOpenAI client configured for the chosen backend.

    For Ollama: points to localhost:11434/v1 with a dummy API key.
    For OpenAI: uses the standard OpenAI API with OPENAI_API_KEY.
    """
    backend = get_backend()
    defaults = _DEFAULTS.get(backend, _DEFAULTS["ollama"])

    base_url = os.environ.get("TAOTF_LLM_BASE_URL", defaults["base_url"])
    api_key = defaults["api_key"] or os.environ.get("OPENAI_API_KEY", "")

    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    return AsyncOpenAI(**kwargs)
