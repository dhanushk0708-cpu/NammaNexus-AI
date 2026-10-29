from typing import Protocol, Any


class MissingProviderCredentialsError(ValueError):
    """Raised when an AI provider's required API key or credentials are not configured."""
    pass


class AIProvider(Protocol):
    """Protocol for AI providers returning a LangChain chat model.

    Implementations expose provider name, configured model name, configuration status,
    and a ``get_chat_model`` method returning a LangChain ``ChatModel`` compatible
    with ``with_structured_output`` and ``ainvoke`` APIs.
    """

    @property
    def name(self) -> str:
        """Normalized provider name (e.g. 'groq', 'gemini')."""
        ...

    @property
    def model_name(self) -> str:
        """Configured model name (e.g. 'llama-3.3-70b-versatile', 'gemini-2.0-flash')."""
        ...

    @property
    def is_configured(self) -> bool:
        """Return True if required API keys/credentials are present."""
        ...

    def get_chat_model(self) -> Any:
        """Return a LangChain chat model instance ready for use."""
        ...
