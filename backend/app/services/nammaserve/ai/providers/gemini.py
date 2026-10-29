from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from .base import MissingProviderCredentialsError


class GeminiProvider:
    """Gemini LLM provider."""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return getattr(settings, "gemini_model", "gemini-2.0-flash")

    @property
    def is_configured(self) -> bool:
        """Return True if gemini_api_key is set and non-empty."""
        api_key = getattr(settings, "gemini_api_key", None)
        return bool(api_key and str(api_key).strip())

    def get_chat_model(self) -> Any:
        if not settings.gemini_api_key or not str(settings.gemini_api_key).strip():
            raise MissingProviderCredentialsError("Gemini API key is not configured in settings")
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=settings.gemini_api_key,
            temperature=0.1,
        )
