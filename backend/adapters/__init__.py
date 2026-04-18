"""Provider adapters for external services."""

from backend.adapters.deepseek_client import DeepSeekClient
from backend.adapters.openalex_adapter import OpenAlexAdapter
from backend.adapters.whisper_adapter import WhisperAdapter

__all__ = ["DeepSeekClient", "OpenAlexAdapter", "WhisperAdapter"]

