from app.core.config import settings
from .base import AIProvider
from .gemini import GeminiProvider
from .groq import GroqProvider


def get_provider(name: str) -> AIProvider:
    """Return an AIProvider instance based on *name*.

    Supported names (case‑insensitive): ``"gemini"`` and ``"groq"``.
    Raises ``ValueError`` for unknown names.
    """
    name = name.lower()
    if name == "gemini":
        return GeminiProvider()
    if name == "groq":
        return GroqProvider()
    raise ValueError(f"Unsupported AI provider: {name}")


def get_primary_and_secondary() -> tuple[AIProvider, AIProvider]:
    """Determine primary and secondary providers based on configuration.

    Primary is the provider specified via ``settings.llm_provider`` (default
    ``"groq"``). Secondary is the *other* supported provider (default ``"gemini"``).
    """
    primary_name = getattr(settings, "llm_provider", "groq")
    primary = get_provider(primary_name)
    secondary_name = "gemini" if primary_name.lower() == "groq" else "groq"
    secondary = get_provider(secondary_name)
    return primary, secondary
