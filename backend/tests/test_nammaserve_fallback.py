import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.services.nammaserve.ai.providers.manager import ProviderManager
from app.services.nammaserve.ai.providers.factory import get_primary_and_secondary, get_provider
from app.services.nammaserve.ai.providers.base import MissingProviderCredentialsError
from app.services.nammaserve.ai.assistant import ServiceAssistant
from app.schemas.nammaserve import ServiceIntent


class DummyProvider:
    def __init__(self, name: str, mock_model: Any, model_name: str = "mock-model", is_configured: bool = True):
        self.name = name
        self.mock_model = mock_model
        self.model_name = model_name
        self.is_configured = is_configured
        self.call_count = 0

    def get_chat_model(self):
        self.call_count += 1
        if isinstance(self.mock_model, Exception):
            raise self.mock_model
        return self.mock_model


class CustomHTTPError(Exception):
    def __init__(self, status_code: int, message: str = "HTTP error"):
        super().__init__(message)
        self.status_code = status_code


# --------------------------------------------------------------------
# 1. Groq Primary Default Configuration Tests
# --------------------------------------------------------------------
def test_factory_defaults_to_groq_primary():
    primary, secondary = get_primary_and_secondary()
    assert type(primary).__name__ == "GroqProvider"
    assert type(secondary).__name__ == "GeminiProvider"


# --------------------------------------------------------------------
# 2. Immediate Success Tests
# --------------------------------------------------------------------
def test_groq_succeeds_immediately_no_retry_no_gemini():
    async def _test():
        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(return_value="groq success")

        mock_gemini = MagicMock()
        mock_gemini.ainvoke = AsyncMock(return_value="gemini success")

        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", mock_gemini)

        manager = ProviderManager(primary=p_groq, secondary=p_gemini, max_retries=1)

        async def op(model):
            return await model.ainvoke("test")

        res = await manager.run_with_fallback(op)
        assert res == "groq success"
        assert p_groq.call_count == 1
        assert p_gemini.call_count == 0

    asyncio.run(_test())


# --------------------------------------------------------------------
# 3. Retry on Transient Errors (429, Timeout, 5xx)
# --------------------------------------------------------------------
def test_groq_429_retried_once_then_succeeds():
    async def _test():
        sleep_calls = []

        async def fake_sleep(d):
            sleep_calls.append(d)

        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(
            side_effect=[CustomHTTPError(429, "Rate limit"), "groq recovered"]
        )

        mock_gemini = MagicMock()
        mock_gemini.ainvoke = AsyncMock(return_value="gemini not needed")

        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", mock_gemini)

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            max_retries=1,
            base_delay=0.5,
            sleep_fn=fake_sleep,
        )

        async def op(model):
            return await model.ainvoke("test")

        res = await manager.run_with_fallback(op)
        assert res == "groq recovered"
        assert p_groq.call_count == 2
        assert p_gemini.call_count == 0
        assert len(sleep_calls) == 1
        assert sleep_calls[0] >= 0.5

    asyncio.run(_test())


def test_groq_timeout_retried_then_succeeds():
    async def _test():
        sleep_calls = []

        async def fake_sleep(d):
            sleep_calls.append(d)

        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(
            side_effect=[TimeoutError("Network timeout"), "groq recovered"]
        )

        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", MagicMock())

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            max_retries=1,
            sleep_fn=fake_sleep,
        )

        async def op(model):
            return await model.ainvoke("test")

        res = await manager.run_with_fallback(op)
        assert res == "groq recovered"
        assert p_groq.call_count == 2
        assert p_gemini.call_count == 0
        assert len(sleep_calls) == 1

    asyncio.run(_test())


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
def test_groq_5xx_status_codes_retried(status_code):
    async def _test():
        sleep_calls = []

        async def fake_sleep(d):
            sleep_calls.append(d)

        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(
            side_effect=[CustomHTTPError(status_code, "Server error"), "groq 5xx recovered"]
        )

        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", MagicMock())

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            max_retries=1,
            sleep_fn=fake_sleep,
        )

        async def op(model):
            return await model.ainvoke("test")

        res = await manager.run_with_fallback(op)
        assert res == "groq 5xx recovered"
        assert p_groq.call_count == 2
        assert p_gemini.call_count == 0
        assert len(sleep_calls) == 1

    asyncio.run(_test())


# --------------------------------------------------------------------
# 4. Non-Retryable Errors (400, 401, 403)
# --------------------------------------------------------------------
@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
def test_groq_non_transient_error_no_retry_no_fallback(status_code):
    async def _test():
        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(
            side_effect=CustomHTTPError(status_code, f"Client error {status_code}")
        )

        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", MagicMock())

        manager = ProviderManager(primary=p_groq, secondary=p_gemini, max_retries=2)

        async def op(model):
            return await model.ainvoke("test")

        with pytest.raises(CustomHTTPError) as exc_info:
            await manager.run_with_fallback(op)

        assert exc_info.value.status_code == status_code
        # Exactly 1 attempt on Groq (no retries)
        assert p_groq.call_count == 1
        # Gemini is NOT called because error is non-transient
        assert p_gemini.call_count == 0

    asyncio.run(_test())


# --------------------------------------------------------------------
# 5. Groq Exhausts Retries -> Fallback to Gemini
# --------------------------------------------------------------------
def test_groq_exhausts_retries_then_gemini_succeeds():
    async def _test():
        sleep_calls = []

        async def fake_sleep(d):
            sleep_calls.append(d)

        mock_groq = MagicMock()
        # 1 initial + 1 retry = 2 failures
        mock_groq.ainvoke = AsyncMock(side_effect=CustomHTTPError(429, "Rate limit"))

        mock_gemini = MagicMock()
        mock_gemini.ainvoke = AsyncMock(return_value="gemini fallback success")

        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", mock_gemini)

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            max_retries=1,
            sleep_fn=fake_sleep,
        )

        async def op(model):
            return await model.ainvoke("test")

        res = await manager.run_with_fallback(op)
        assert res == "gemini fallback success"
        assert p_groq.call_count == 2
        assert p_gemini.call_count == 1
        assert len(sleep_calls) == 1

    asyncio.run(_test())


# --------------------------------------------------------------------
# 6. Both Groq & Gemini Exhaust Retries -> Bounded Failure
# --------------------------------------------------------------------
def test_both_providers_exhaust_retries_bounded_no_loop():
    async def _test():
        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(side_effect=CustomHTTPError(503, "Groq unavailable"))

        mock_gemini = MagicMock()
        mock_gemini.ainvoke = AsyncMock(side_effect=CustomHTTPError(500, "Gemini error"))

        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", mock_gemini)

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            max_retries=1,
            sleep_fn=AsyncMock(),
        )

        async def op(model):
            return await model.ainvoke("test")

        with pytest.raises(CustomHTTPError) as exc_info:
            await manager.run_with_fallback(op)

        assert exc_info.value.status_code == 500
        # Groq: 1 initial + 1 retry = 2 attempts
        assert p_groq.call_count == 2
        # Gemini: 1 initial + 1 retry = 2 attempts
        assert p_gemini.call_count == 2

    asyncio.run(_test())


# --------------------------------------------------------------------
# 7. Exponential Backoff & Max Delay Bounds
# --------------------------------------------------------------------
def test_exponential_backoff_and_max_delay_calculation():
    manager = ProviderManager(
        primary=MagicMock(),
        secondary=MagicMock(),
        base_delay=0.5,
        max_delay=2.0,
    )

    # Attempt 0: 0.5 * 2^0 = 0.5 (+ jitter <= 0.05)
    d0 = manager.calculate_backoff(attempt=0, jitter=False)
    assert d0 == 0.5

    # Attempt 1: 0.5 * 2^1 = 1.0
    d1 = manager.calculate_backoff(attempt=1, jitter=False)
    assert d1 == 1.0

    # Attempt 2: 0.5 * 2^2 = 2.0 (capped at max_delay 2.0)
    d2 = manager.calculate_backoff(attempt=2, jitter=False)
    assert d2 == 2.0

    # Attempt 3+: 0.5 * 2^3 = 4.0 -> capped at 2.0
    d3 = manager.calculate_backoff(attempt=3, jitter=False)
    assert d3 == 2.0


# --------------------------------------------------------------------
# 8. ServiceAssistant End-to-End Integration with Fallback
# --------------------------------------------------------------------
def test_service_assistant_intent_recovery_with_groq_retry():
    async def _test():
        mock_groq = MagicMock()
        mock_groq_structured = MagicMock()
        mock_groq_structured.ainvoke = AsyncMock(
            side_effect=[
                CustomHTTPError(429, "Rate limit"),
                ServiceIntent(
                    service="water-tanker",
                    location="Whitefield",
                    urgent=True,
                ),
            ]
        )
        mock_groq.with_structured_output.return_value = mock_groq_structured

        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", MagicMock())

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            max_retries=1,
            sleep_fn=AsyncMock(),
        )

        assistant = ServiceAssistant(db=MagicMock())
        assistant.provider_manager = manager

        intent, fallback_used = await assistant.parse_intent(
            "Emergency water tanker needed in Whitefield"
        )

        assert fallback_used is False
        assert intent.service == "water-tanker"
        assert intent.location == "Whitefield"
        assert intent.urgent is True
        assert p_groq.call_count == 2
        assert p_gemini.call_count == 0

    asyncio.run(_test())


def test_service_assistant_deterministic_fallback_when_both_providers_fail():
    async def _test():
        mock_groq = MagicMock()
        mock_groq_structured = MagicMock()
        mock_groq_structured.ainvoke = AsyncMock(side_effect=CustomHTTPError(503, "Groq down"))
        mock_groq.with_structured_output.return_value = mock_groq_structured

        mock_gemini = MagicMock()
        mock_gemini_structured = MagicMock()
        mock_gemini_structured.ainvoke = AsyncMock(side_effect=CustomHTTPError(500, "Gemini down"))
        mock_gemini.with_structured_output.return_value = mock_gemini_structured

        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", mock_gemini)

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            max_retries=1,
            sleep_fn=AsyncMock(),
        )

        assistant = ServiceAssistant(db=MagicMock())
        assistant.provider_manager = manager

        intent, fallback_used = await assistant.parse_intent(
            "Locked out in Koramangala urgently"
        )

        # Degraded safely to rule-based fallback parser
        assert fallback_used is True
        assert intent.service == "locksmith-emergency"
        assert intent.location == "Koramangala"
        assert intent.urgent is True
        assert p_groq.call_count == 2
        assert p_gemini.call_count == 2

    asyncio.run(_test())


# --------------------------------------------------------------------
# 9. Explicit Core Fallback & Credential Handling Tests
# --------------------------------------------------------------------
def test_explicit_groq_success():
    """Verify Groq succeeds on first attempt without retrying or invoking Gemini."""
    async def _test():
        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(return_value="groq completed successfully")
        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", MagicMock())

        manager = ProviderManager(primary=p_groq, secondary=p_gemini, max_retries=1)
        res = await manager.run_with_fallback(lambda m: m.ainvoke("ping"))

        assert res == "groq completed successfully"
        assert p_groq.call_count == 1
        assert p_gemini.call_count == 0

    asyncio.run(_test())


def test_explicit_groq_transient_failure_followed_by_gemini_success():
    """Verify transient error on Groq exhausts bounded retries, then Gemini succeeds."""
    async def _test():
        sleep_calls = []
        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(side_effect=CustomHTTPError(429, "Rate limit"))
        mock_gemini = MagicMock()
        mock_gemini.ainvoke = AsyncMock(return_value="gemini fallback success")

        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", mock_gemini)

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            max_retries=1,
            sleep_fn=lambda d: sleep_calls.append(d) or asyncio.sleep(0),
        )
        res = await manager.run_with_fallback(lambda m: m.ainvoke("ping"))

        assert res == "gemini fallback success"
        # 1 initial + 1 retry = 2 attempts on Groq
        assert p_groq.call_count == 2
        # 1 attempt on Gemini
        assert p_gemini.call_count == 1
        assert len(sleep_calls) == 1

    asyncio.run(_test())


def test_explicit_missing_groq_credentials_with_gemini_configured():
    """Verify missing Groq credentials fail fast on Groq without retries, and seamlessly fall back to Gemini."""
    async def _test():
        # Groq get_chat_model raises MissingProviderCredentialsError
        p_groq = DummyProvider(
            "groq",
            MissingProviderCredentialsError("Groq API key is not configured in settings"),
            is_configured=False,
        )
        mock_gemini = MagicMock()
        mock_gemini.ainvoke = AsyncMock(return_value="gemini response with groq unconfigured")
        p_gemini = DummyProvider("gemini", mock_gemini, is_configured=True)

        manager = ProviderManager(primary=p_groq, secondary=p_gemini, max_retries=2)
        res = await manager.run_with_fallback(lambda m: m.ainvoke("ping"))

        assert res == "gemini response with groq unconfigured"
        # Exactly 1 call on Groq (no endless retries on missing credentials)
        assert p_groq.call_count == 1
        assert p_gemini.call_count == 1

    asyncio.run(_test())


def test_explicit_both_providers_failing_activates_deterministic_fallback():
    """Verify that when both providers fail, ServiceAssistant activates deterministic fallback."""
    async def _test():
        p_groq = DummyProvider(
            "groq",
            MissingProviderCredentialsError("Groq API key is not configured in settings"),
            is_configured=False,
        )
        p_gemini = DummyProvider(
            "gemini",
            MissingProviderCredentialsError("Gemini API key is not configured in settings"),
            is_configured=False,
        )

        manager = ProviderManager(primary=p_groq, secondary=p_gemini, max_retries=1)

        assistant = ServiceAssistant(db=MagicMock())
        assistant.provider_manager = manager

        intent, fallback_used = await assistant.parse_intent(
            "Book an emergency water tanker in Indiranagar"
        )

        assert fallback_used is True
        assert intent.service == "water-tanker"
        assert intent.location == "Indiranagar"
        assert intent.urgent is True
        assert p_groq.call_count == 1
        assert p_gemini.call_count == 1

    asyncio.run(_test())


def test_explicit_authentication_failure_handling():
    """Verify permanent authentication failure (401) is not retried endlessly, and fails fast safely."""
    async def _test():
        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(side_effect=CustomHTTPError(401, "Unauthorized / Invalid API key"))
        p_groq = DummyProvider("groq", mock_groq)
        p_gemini = DummyProvider("gemini", MagicMock())

        manager = ProviderManager(primary=p_groq, secondary=p_gemini, max_retries=3)

        with pytest.raises(CustomHTTPError) as exc_info:
            await manager.run_with_fallback(lambda m: m.ainvoke("ping"))

        assert exc_info.value.status_code == 401
        # Exactly 1 attempt on Groq - NO retry loop for 401 authentication errors
        assert p_groq.call_count == 1
        assert p_gemini.call_count == 0

        # And in ServiceAssistant, authentication error falls back to deterministic parsing without crashing:
        assistant = ServiceAssistant(db=MagicMock())
        assistant.provider_manager = manager

        intent, fallback_used = await assistant.parse_intent(
            "Need locksmith in Whitefield"
        )
        assert fallback_used is True
        assert intent.service == "locksmith-emergency"
        assert intent.location == "Whitefield"

    asyncio.run(_test())
