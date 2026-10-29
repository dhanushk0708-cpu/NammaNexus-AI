import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Optional, Protocol

logger = logging.getLogger("nammaserve.ai.telemetry")


@dataclass(frozen=True)
class AIUsageTelemetryEvent:
    """Lightweight, production-minded telemetry event for a single LLM provider attempt."""

    request_id: str
    provider: str
    model: str
    operation: str
    attempt: int
    retry_count: int
    fallback_used: bool
    latency_ms: float
    success: bool
    error_type: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to a sanitized dictionary (no prompts, responses, or secrets)."""
        return {
            "request_id": self.request_id,
            "provider": self.provider,
            "model": self.model,
            "operation": self.operation,
            "attempt": self.attempt,
            "retry_count": self.retry_count,
            "fallback_used": self.fallback_used,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error_type": self.error_type,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "timestamp": self.timestamp.isoformat(),
        }


class TelemetryHandler(Protocol):
    """Protocol for telemetry event sinks."""

    def record(self, event: AIUsageTelemetryEvent) -> None:
        ...


class LoggingTelemetryHandler:
    """Standard structured application logger for AI telemetry events."""

    def __init__(self, logger_instance: logging.Logger | None = None):
        self._logger = logger_instance or logger

    def record(self, event: AIUsageTelemetryEvent) -> None:
        try:
            self._logger.info("AI Provider Attempt: %s", event.to_dict())
        except Exception:
            # Telemetry is strictly best-effort observation; never crash the caller.
            pass


class InMemoryTelemetryHandler:
    """In-memory telemetry sink for testing and programmatic inspection."""

    def __init__(self):
        self.events: list[AIUsageTelemetryEvent] = []

    def record(self, event: AIUsageTelemetryEvent) -> None:
        self.events.append(event)

    def clear(self) -> None:
        self.events.clear()


def classify_error_type(exc: Exception) -> str:
    """Classify an exception into a normalized error_type string for telemetry and reporting."""
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "timeout"

    if hasattr(exc, "status_code"):
        try:
            code = int(getattr(exc, "status_code"))
            if code == 429:
                return "rate_limit"
            if code in (401, 403):
                return "authentication_error"
            if code in (400, 404, 422):
                return "invalid_request"
            if code in (500, 502, 503, 504):
                return "server_error"
        except Exception:
            pass

    # Google API exceptions
    try:
        from google.api_core import exceptions as google_exc
        if isinstance(exc, google_exc.TooManyRequests):
            return "rate_limit"
        if isinstance(exc, google_exc.DeadlineExceeded):
            return "timeout"
        if isinstance(exc, (google_exc.Unauthenticated, google_exc.PermissionDenied)):
            return "authentication_error"
        if isinstance(exc, google_exc.InvalidArgument):
            return "invalid_request"
        if isinstance(exc, (google_exc.InternalServerError, google_exc.ServiceUnavailable)):
            return "server_error"
    except Exception:
        pass

    # HTTPX / Groq exceptions
    if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
        try:
            code = int(exc.response.status_code)
            if code == 429:
                return "rate_limit"
            if code in (401, 403):
                return "authentication_error"
            if code in (400, 404, 422):
                return "invalid_request"
            if code in (500, 502, 503, 504):
                return "server_error"
        except Exception:
            pass

    try:
        import httpx
        if isinstance(exc, httpx.TimeoutException):
            return "timeout"
        if isinstance(exc, (httpx.NetworkError, httpx.ConnectError)):
            return "network_error"
    except Exception:
        pass

    if isinstance(exc, ConnectionError):
        return "network_error"
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return "validation_error"

    return "unknown"


def extract_token_usage(result: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Extract (input_tokens, output_tokens, total_tokens) from result if reliably present.

    Returns (None, None, None) if token counts are unavailable. Never estimates or fakes counts.
    """
    if result is None:
        return None, None, None

    # Case 1: LangChain UsageMetadata object/dict on AIMessage
    usage_meta = getattr(result, "usage_metadata", None)
    if isinstance(usage_meta, dict):
        in_tok = usage_meta.get("input_tokens")
        out_tok = usage_meta.get("output_tokens")
        tot_tok = usage_meta.get("total_tokens")
        if in_tok is not None or out_tok is not None or tot_tok is not None:
            return in_tok, out_tok, tot_tok

    # Case 2: LangChain response_metadata dictionary
    resp_meta = getattr(result, "response_metadata", None)
    if isinstance(resp_meta, dict):
        # Groq / OpenAI style token_usage
        token_usage = resp_meta.get("token_usage") or resp_meta.get("usage")
        if isinstance(token_usage, dict):
            in_tok = token_usage.get("prompt_tokens") or token_usage.get("input_tokens")
            out_tok = token_usage.get("completion_tokens") or token_usage.get("output_tokens")
            tot_tok = token_usage.get("total_tokens")
            if in_tok is not None or out_tok is not None or tot_tok is not None:
                return in_tok, out_tok, tot_tok

        # Google Gemini style usage_metadata
        gemini_usage = resp_meta.get("usage_metadata")
        if isinstance(gemini_usage, dict):
            in_tok = gemini_usage.get("prompt_token_count")
            out_tok = gemini_usage.get("candidates_token_count")
            tot_tok = gemini_usage.get("total_token_count")
            if in_tok is not None or out_tok is not None or tot_tok is not None:
                return in_tok, out_tok, tot_tok

    # Case 3: Wrapped result containing raw AIMessage (e.g., from with_structured_output(include_raw=True))
    if isinstance(result, dict) and "raw" in result:
        return extract_token_usage(result["raw"])

    return None, None, None
