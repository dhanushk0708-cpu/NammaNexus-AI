import json
import logging
from typing import Any
import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.core.config import settings
from .base import MissingProviderCredentialsError

logger = logging.getLogger(__name__)


class HTTPXChatGroq:
    """Lightweight LangChain-compatible Groq chat model client powered by httpx.
    
    Provides `ainvoke` and `with_structured_output` for high-performance intent
    understanding without requiring external heavy dependencies.
    """

    def __init__(self, api_key: str, model_name: str, timeout: float = 12.0):
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    async def ainvoke(self, messages: list[BaseMessage]) -> AIMessage:
        """Execute chat completion and return AIMessage."""
        groq_messages = []
        for m in messages:
            if isinstance(m, SystemMessage):
                role = "system"
            elif isinstance(m, HumanMessage):
                role = "user"
            elif isinstance(m, AIMessage):
                role = "assistant"
            else:
                role = getattr(m, "role", "user")
            groq_messages.append({"role": role, "content": str(m.content)})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": groq_messages,
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self.endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return AIMessage(
                content=content,
                response_metadata={"token_usage": usage},
                usage_metadata={
                    "input_tokens": usage.get("prompt_tokens"),
                    "output_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                },
            )

    def with_structured_output(self, schema: Any) -> Any:
        """Return a structured output runner conforming to Pydantic schema."""
        parent = self

        class StructuredRunner:
            async def ainvoke(self, messages: list[BaseMessage]) -> Any:
                schema_json = json.dumps(schema.model_json_schema()) if hasattr(schema, "model_json_schema") else ""
                system_instruction = (
                    f"You are a structured intent extraction engine. Respond strictly with valid JSON conforming to this schema:\n{schema_json}"
                )

                groq_messages = [{"role": "system", "content": system_instruction}]
                for m in messages:
                    if isinstance(m, SystemMessage):
                        groq_messages.append({"role": "system", "content": str(m.content)})
                    elif isinstance(m, HumanMessage):
                        groq_messages.append({"role": "user", "content": str(m.content)})
                    elif isinstance(m, AIMessage):
                        groq_messages.append({"role": "assistant", "content": str(m.content)})
                    else:
                        groq_messages.append({"role": getattr(m, "role", "user"), "content": str(m.content)})

                headers = {
                    "Authorization": f"Bearer {parent.api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": parent.model_name,
                    "messages": groq_messages,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                }

                async with httpx.AsyncClient(timeout=parent.timeout) as client:
                    resp = await client.post(parent.endpoint, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    raw_content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(raw_content)
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(parsed)
                    if callable(schema):
                        return schema(**parsed)
                    return parsed

        return StructuredRunner()


class GroqProvider:
    """Groq LLM provider.

    Returns a ``ChatGroq`` or ``HTTPXChatGroq`` instance configured for structured output.
    """

    @property
    def name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return getattr(settings, "groq_model", "qwen/qwen3.8-27b")

    @property
    def is_configured(self) -> bool:
        """Return True if groq_api_key is set and non-empty."""
        api_key = getattr(settings, "groq_api_key", None)
        return bool(api_key and str(api_key).strip())

    def get_chat_model(self) -> Any:
        api_key = getattr(settings, "groq_api_key", None)
        if not api_key or not str(api_key).strip():
            raise MissingProviderCredentialsError("Groq API key is not configured in settings")

        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=self.model_name,
                api_key=api_key,
                temperature=0.1,
                max_retries=0,
                response_format={"type": "json_object"},
            )
        except ImportError:
            return HTTPXChatGroq(api_key=str(api_key).strip(), model_name=self.model_name)
