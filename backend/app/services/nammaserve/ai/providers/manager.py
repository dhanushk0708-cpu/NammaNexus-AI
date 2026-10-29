import asyncio
import logging
import random
import time
from typing import Any, Awaitable, Callable, Optional, TypeVar
from uuid import uuid4

from app.services.nammaserve.ai.providers.base import AIProvider
from app.services.nammaserve.ai.telemetry import (
    AIUsageTelemetryEvent,
    LoggingTelemetryHandler,
    TelemetryHandler,
    classify_error_type,
    extract_token_usage,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ProviderManager:
    """Manages primary and secondary AI providers with bounded retry, exponential backoff, fallback, and telemetry.

    Orchestration:
    1. Primary provider (Groq) is attempted.
    2. On transient errors (429, 500, 502, 503, 504, timeouts, connection drops),
       the operation is retried up to ``max_retries`` times with exponential backoff + jitter.
    3. Non-transient errors (400, 401, 403, validation errors) fail fast with NO retry.
    4. If the primary provider exhausts its retry budget, the secondary provider (Gemini)
       is attempted with the same bounded retry policy.
    5. If both providers fail, the error propagates to allow deterministic application fallback.
    6. Every actual provider attempt emits a structured AIUsageTelemetryEvent. Telemetry is
       purely observational and will never alter flow or fail the request.
    """

    def __init__(
        self,
        primary: AIProvider,
        secondary: AIProvider,
        max_retries: int = 1,
        base_delay: float = 0.5,
        max_delay: float = 2.0,
        sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
        telemetry_handler: Optional[TelemetryHandler] = None,
    ):
        self.primary = primary
        self.secondary = secondary
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.sleep_fn = sleep_fn
        self.telemetry_handler = telemetry_handler or LoggingTelemetryHandler()

    def calculate_backoff(self, attempt: int, jitter: bool = True) -> float:
        """Calculate exponential backoff delay with jitter bounded by max_delay.

        Formula: min(max_delay, base_delay * 2^attempt + jitter)
        """
        delay = self.base_delay * (2 ** attempt)
        if jitter:
            delay += random.uniform(0, 0.1 * self.base_delay)
        return min(self.max_delay, delay)

    def _get_provider_name(self, provider: Any) -> str:
        """Safely extract normalized provider name."""
        if hasattr(provider, "name") and isinstance(provider.name, str):
            return provider.name
        cls_name = type(provider).__name__.lower().replace("provider", "")
        return cls_name or "unknown"

    def _get_provider_model(self, provider: Any) -> str:
        """Safely extract configured provider model name."""
        if hasattr(provider, "model_name") and isinstance(provider.model_name, str):
            return provider.model_name
        return "unknown"

    def _record_telemetry(self, event: AIUsageTelemetryEvent) -> None:
        """Record telemetry event in a safe, non-blocking, exception-swallowed manner."""
        try:
            if self.telemetry_handler is not None:
                self.telemetry_handler.record(event)
        except Exception as exc:
            logger.debug("Failed to record telemetry event: %s", exc)

    async def _execute_with_retry(
        self,
        provider: AIProvider,
        operation: Callable[[Any], Awaitable[T]],
        request_id: str,
        operation_name: str,
        is_fallback: bool,
    ) -> T:
        """Execute *operation* on *provider* with bounded retry, exponential backoff, and attempt telemetry."""
        attempt = 0
        provider_name = self._get_provider_name(provider)
        model_name = self._get_provider_model(provider)

        while True:
            start_time = time.perf_counter()
            try:
                llm = provider.get_chat_model()
                result = await operation(llm)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                # Extract token usage if reliably present on response/result
                input_tokens, output_tokens, total_tokens = extract_token_usage(result)

                # Record successful attempt telemetry
                self._record_telemetry(
                    AIUsageTelemetryEvent(
                        request_id=request_id,
                        provider=provider_name,
                        model=model_name,
                        operation=operation_name,
                        attempt=attempt + 1,
                        retry_count=attempt,
                        fallback_used=is_fallback,
                        latency_ms=round(latency_ms, 2),
                        success=True,
                        error_type=None,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens,
                    )
                )
                return result
            except Exception as exc:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                error_type = classify_error_type(exc)

                # Record failed attempt telemetry
                self._record_telemetry(
                    AIUsageTelemetryEvent(
                        request_id=request_id,
                        provider=provider_name,
                        model=model_name,
                        operation=operation_name,
                        attempt=attempt + 1,
                        retry_count=attempt,
                        fallback_used=is_fallback,
                        latency_ms=round(latency_ms, 2),
                        success=False,
                        error_type=error_type,
                        input_tokens=None,
                        output_tokens=None,
                        total_tokens=None,
                    )
                )

                if not self._is_transient_error(exc):
                    # Non-transient error (e.g., 400, 401, 403, ValueError) -> fail fast
                    logger.warning(
                        "Non-transient error on %s: %s; no retry.",
                        provider_name,
                        exc,
                    )
                    raise exc

                if attempt >= self.max_retries:
                    # Retry budget exhausted for this provider
                    logger.warning(
                        "Transient error on %s; retry budget (%d retries) exhausted: %s",
                        provider_name,
                        self.max_retries,
                        exc,
                    )
                    raise exc

                delay = self.calculate_backoff(attempt)
                logger.warning(
                    "Transient error on %s (attempt %d/%d): %s. Retrying in %.2fs...",
                    provider_name,
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                    delay,
                )
                await self.sleep_fn(delay)
                attempt += 1

    async def run_with_fallback(
        self,
        operation: Callable[[Any], Awaitable[T]],
        request_id: str | None = None,
        operation_name: str = "ai_operation",
    ) -> T:
        """Execute *operation* with the primary provider and fallback to secondary if eligible.

        *operation* receives a LangChain chat model instance and must return an awaitable result.
        """
        req_id = request_id or str(uuid4())

        # 1. Primary provider execution (with bounded retry)
        try:
            return await self._execute_with_retry(
                provider=self.primary,
                operation=operation,
                request_id=req_id,
                operation_name=operation_name,
                is_fallback=False,
            )
        except Exception as exc_primary:
            logger.warning(
                "Primary LLM provider (%s) failed: %s",
                self._get_provider_name(self.primary),
                exc_primary,
            )
            if not self._is_fallback_eligible(exc_primary):
                logger.info("Failure not eligible for fallback; propagating non-transient error.")
                raise exc_primary

            # 2. Secondary fallback execution (with bounded retry)
            try:
                logger.info(
                    "Attempting fallback LLM provider: %s",
                    self._get_provider_name(self.secondary),
                )
                return await self._execute_with_retry(
                    provider=self.secondary,
                    operation=operation,
                    request_id=req_id,
                    operation_name=operation_name,
                    is_fallback=True,
                )
            except Exception as exc_secondary:
                logger.error(
                    "Fallback LLM provider (%s) also failed: %s; propagating.",
                    self._get_provider_name(self.secondary),
                    exc_secondary,
                )
                raise exc_secondary

    def _is_transient_error(self, exc: Exception) -> bool:
        """Return True if *exc* represents a transient error eligible for retry and fallback."""
        # Timeout and connection errors
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError)):
            return True

        # Check explicit status_code attribute on the exception
        if hasattr(exc, "status_code"):
            try:
                code = int(getattr(exc, "status_code"))
                if code in (429, 500, 502, 503, 504):
                    return True
                if code in (400, 401, 403, 404, 422):
                    return False
            except Exception:
                pass

        # Google API exceptions
        try:
            from google.api_core import exceptions as google_exc
        except Exception:
            google_exc = None

        if google_exc:
            if isinstance(
                exc,
                (
                    google_exc.TooManyRequests,
                    google_exc.InternalServerError,
                    google_exc.ServiceUnavailable,
                    google_exc.DeadlineExceeded,
                ),
            ):
                return True
            if isinstance(
                exc,
                (
                    google_exc.InvalidArgument,
                    google_exc.Unauthenticated,
                    google_exc.PermissionDenied,
                    google_exc.NotFound,
                ),
            ):
                return False

        # HTTPX / Groq exceptions
        if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
            try:
                code = int(exc.response.status_code)
                if code in (429, 500, 502, 503, 504):
                    return True
                if code in (400, 401, 403, 404, 422):
                    return False
            except Exception:
                pass

        try:
            import httpx
            if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)):
                return True
        except Exception:
            pass

        return False

    def _is_missing_credentials(self, exc: Exception) -> bool:
        """Return True if *exc* represents missing AI provider credentials."""
        from app.services.nammaserve.ai.providers.base import MissingProviderCredentialsError

        if isinstance(exc, MissingProviderCredentialsError):
            return True
        if isinstance(exc, ValueError) and "api key is not configured" in str(exc).lower():
            return True
        return False

    def _is_fallback_eligible(self, exc: Exception) -> bool:
        """Return True if *exc* on primary provider is eligible for fallback to secondary.

        Eligible conditions:
        1. Transient errors (rate limits, timeouts, 5xx server errors) whose retry budget is exhausted.
        2. Missing provider credentials on primary (allowing configured secondary to take over).
        """
        return self._is_transient_error(exc) or self._is_missing_credentials(exc)
