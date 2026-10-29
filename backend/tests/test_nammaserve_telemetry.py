import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.services.nammaserve.ai.providers.manager import ProviderManager
from app.services.nammaserve.ai.telemetry import (
    AIUsageTelemetryEvent,
    InMemoryTelemetryHandler,
    LoggingTelemetryHandler,
    classify_error_type,
    extract_token_usage,
)
from app.services.nammaserve.ai.assistant import ServiceAssistant
from app.schemas.nammaserve import ServiceIntent


class DummyProvider:
    def __init__(self, name: str, model_name: str, mock_model: MagicMock):
        self.name = name
        self.model_name = model_name
        self.mock_model = mock_model
        self.call_count = 0

    def get_chat_model(self):
        self.call_count += 1
        return self.mock_model


class CustomHTTPError(Exception):
    def __init__(self, status_code: int, message: str = "HTTP error"):
        super().__init__(message)
        self.status_code = status_code


# --------------------------------------------------------------------
# 1. Successful Groq Call Records Telemetry
# --------------------------------------------------------------------
def test_successful_groq_call_records_telemetry():
    async def _test():
        telemetry = InMemoryTelemetryHandler()
        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(return_value="groq response")

        p_groq = DummyProvider("groq", "llama-3.3-70b-versatile", mock_groq)
        p_gemini = DummyProvider("gemini", "gemini-2.0-flash", MagicMock())

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            telemetry_handler=telemetry,
        )

        async def op(model):
            return await model.ainvoke("test query")

        res = await manager.run_with_fallback(
            operation=op,
            request_id="req-123",
            operation_name="intent_extraction",
        )

        assert res == "groq response"
        assert len(telemetry.events) == 1
        ev = telemetry.events[0]
        assert ev.request_id == "req-123"
        assert ev.provider == "groq"
        assert ev.model == "llama-3.3-70b-versatile"
        assert ev.operation == "intent_extraction"
        assert ev.attempt == 1
        assert ev.retry_count == 0
        assert ev.fallback_used is False
        assert ev.success is True
        assert ev.error_type is None
        assert ev.latency_ms >= 0.0

    asyncio.run(_test())


# --------------------------------------------------------------------
# 2. Groq Retry Records Separate Telemetry Events
# --------------------------------------------------------------------
def test_groq_retry_records_separate_events():
    async def _test():
        telemetry = InMemoryTelemetryHandler()
        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(
            side_effect=[CustomHTTPError(429, "Rate limit"), "groq retry success"]
        )

        p_groq = DummyProvider("groq", "llama-3.3-70b-versatile", mock_groq)
        p_gemini = DummyProvider("gemini", "gemini-2.0-flash", MagicMock())

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            max_retries=1,
            sleep_fn=AsyncMock(),
            telemetry_handler=telemetry,
        )

        async def op(model):
            return await model.ainvoke("test query")

        res = await manager.run_with_fallback(
            operation=op,
            request_id="req-retry-1",
            operation_name="intent_extraction",
        )

        assert res == "groq retry success"
        assert len(telemetry.events) == 2

        # Event 1: Failed attempt
        ev1 = telemetry.events[0]
        assert ev1.request_id == "req-retry-1"
        assert ev1.provider == "groq"
        assert ev1.attempt == 1
        assert ev1.retry_count == 0
        assert ev1.fallback_used is False
        assert ev1.success is False
        assert ev1.error_type == "rate_limit"

        # Event 2: Successful retry
        ev2 = telemetry.events[1]
        assert ev2.request_id == "req-retry-1"
        assert ev2.provider == "groq"
        assert ev2.attempt == 2
        assert ev2.retry_count == 1
        assert ev2.fallback_used is False
        assert ev2.success is True
        assert ev2.error_type is None

    asyncio.run(_test())


# --------------------------------------------------------------------
# 3. Groq Fallback to Gemini Records Separate Provider Events
# --------------------------------------------------------------------
def test_groq_fallback_to_gemini_records_events():
    async def _test():
        telemetry = InMemoryTelemetryHandler()
        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(side_effect=CustomHTTPError(503, "Groq 503"))

        mock_gemini = MagicMock()
        mock_gemini.ainvoke = AsyncMock(return_value="gemini fallback success")

        p_groq = DummyProvider("groq", "llama-3.3-70b-versatile", mock_groq)
        p_gemini = DummyProvider("gemini", "gemini-2.0-flash", mock_gemini)

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            max_retries=1,
            sleep_fn=AsyncMock(),
            telemetry_handler=telemetry,
        )

        async def op(model):
            return await model.ainvoke("test query")

        res = await manager.run_with_fallback(
            operation=op,
            request_id="req-fallback-1",
            operation_name="grounded_response",
        )

        assert res == "gemini fallback success"
        # 2 Groq attempts (initial + 1 retry) + 1 Gemini attempt = 3 events
        assert len(telemetry.events) == 3

        ev1 = telemetry.events[0]
        assert ev1.request_id == "req-fallback-1"
        assert ev1.provider == "groq"
        assert ev1.attempt == 1
        assert ev1.retry_count == 0
        assert ev1.fallback_used is False
        assert ev1.success is False
        assert ev1.error_type == "server_error"

        ev2 = telemetry.events[1]
        assert ev2.request_id == "req-fallback-1"
        assert ev2.provider == "groq"
        assert ev2.attempt == 2
        assert ev2.retry_count == 1
        assert ev2.fallback_used is False
        assert ev2.success is False
        assert ev2.error_type == "server_error"

        ev3 = telemetry.events[2]
        assert ev3.request_id == "req-fallback-1"
        assert ev3.provider == "gemini"
        assert ev3.model == "gemini-2.0-flash"
        assert ev3.attempt == 1
        assert ev3.retry_count == 0
        assert ev3.fallback_used is True
        assert ev3.success is True
        assert ev3.error_type is None

    asyncio.run(_test())


# --------------------------------------------------------------------
# 4. Token Usage Extraction Tests
# --------------------------------------------------------------------
def test_token_usage_extraction_langchain_usage_metadata():
    class MockAIMessage:
        usage_metadata = {"input_tokens": 120, "output_tokens": 45, "total_tokens": 165}

    in_tok, out_tok, tot_tok = extract_token_usage(MockAIMessage())
    assert in_tok == 120
    assert out_tok == 45
    assert tot_tok == 165


def test_token_usage_extraction_groq_response_metadata():
    class MockAIMessage:
        response_metadata = {
            "token_usage": {
                "prompt_tokens": 200,
                "completion_tokens": 80,
                "total_tokens": 280,
            }
        }

    in_tok, out_tok, tot_tok = extract_token_usage(MockAIMessage())
    assert in_tok == 200
    assert out_tok == 80
    assert tot_tok == 280


def test_token_usage_extraction_gemini_response_metadata():
    class MockAIMessage:
        response_metadata = {
            "usage_metadata": {
                "prompt_token_count": 95,
                "candidates_token_count": 35,
                "total_token_count": 130,
            }
        }

    in_tok, out_tok, tot_tok = extract_token_usage(MockAIMessage())
    assert in_tok == 95
    assert out_tok == 35
    assert tot_tok == 130


def test_missing_token_metadata_returns_none():
    in_tok, out_tok, tot_tok = extract_token_usage("string response without metadata")
    assert in_tok is None
    assert out_tok is None
    assert tot_tok is None

    in_tok, out_tok, tot_tok = extract_token_usage(None)
    assert in_tok is None
    assert out_tok is None
    assert tot_tok is None


# --------------------------------------------------------------------
# 5. Error Classification Normalization Tests
# --------------------------------------------------------------------
@pytest.mark.parametrize(
    "status_code,expected_type",
    [
        (429, "rate_limit"),
        (400, "invalid_request"),
        (401, "authentication_error"),
        (403, "authentication_error"),
        (404, "invalid_request"),
        (422, "invalid_request"),
        (500, "server_error"),
        (502, "server_error"),
        (503, "server_error"),
        (504, "server_error"),
    ],
)
def test_error_classification_http_status_codes(status_code, expected_type):
    exc = CustomHTTPError(status_code)
    assert classify_error_type(exc) == expected_type


def test_error_classification_timeouts_and_network():
    assert classify_error_type(TimeoutError()) == "timeout"
    assert classify_error_type(ConnectionError()) == "network_error"
    assert classify_error_type(ValueError("invalid format")) == "validation_error"


# --------------------------------------------------------------------
# 6. Faulty Telemetry Handler Does Not Crash AI Request
# --------------------------------------------------------------------
def test_telemetry_failure_is_best_effort_and_does_not_fail_request():
    async def _test():
        class BrokenTelemetryHandler:
            def record(self, event):
                raise RuntimeError("Telemetry DB connection crashed")

        mock_groq = MagicMock()
        mock_groq.ainvoke = AsyncMock(return_value="groq success despite telemetry crash")

        p_groq = DummyProvider("groq", "llama-3.3-70b-versatile", mock_groq)
        p_gemini = DummyProvider("gemini", "gemini-2.0-flash", MagicMock())

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            telemetry_handler=BrokenTelemetryHandler(),
        )

        async def op(model):
            return await model.ainvoke("test query")

        # Must succeed safely
        res = await manager.run_with_fallback(op, request_id="req-safe")
        assert res == "groq success despite telemetry crash"

    asyncio.run(_test())


# --------------------------------------------------------------------
# 7. Privacy & Security: No Secrets in Telemetry Event Dict
# --------------------------------------------------------------------
def test_telemetry_event_sanitization_no_secrets():
    event = AIUsageTelemetryEvent(
        request_id="req-sec-1",
        provider="groq",
        model="llama-3.3-70b-versatile",
        operation="intent_extraction",
        attempt=1,
        retry_count=0,
        fallback_used=False,
        latency_ms=150.25,
        success=True,
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
    )

    data = event.to_dict()
    # Check that forbidden fields are not in data
    assert "prompt" not in data
    assert "response" not in data
    assert "api_key" not in data
    assert "token" not in data
    assert "authorization" not in data
    assert data["request_id"] == "req-sec-1"
    assert data["provider"] == "groq"
    assert data["latency_ms"] == 150.25


# --------------------------------------------------------------------
# 8. ServiceAssistant Correlation ID Consistency
# --------------------------------------------------------------------
def test_service_assistant_request_id_correlation():
    async def _test():
        telemetry = InMemoryTelemetryHandler()
        mock_groq = MagicMock()
        mock_groq_structured = MagicMock()
        mock_groq_structured.ainvoke = AsyncMock(
            return_value=ServiceIntent(
                service="water-tanker",
                location="Kengeri",
                urgent=True,
            )
        )
        mock_groq.with_structured_output.return_value = mock_groq_structured
        mock_groq.ainvoke = AsyncMock(return_value="Grounded reply text")

        p_groq = DummyProvider("groq", "llama-3.3-70b-versatile", mock_groq)
        p_gemini = DummyProvider("gemini", "gemini-2.0-flash", MagicMock())

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            telemetry_handler=telemetry,
        )

        assistant = ServiceAssistant(db=MagicMock())
        assistant.provider_manager = manager

        # Process chat with explicit request_id
        from app.schemas.nammaserve import AssistantChatRequest
        req = AssistantChatRequest(message="Need water tanker in Kengeri")
        resp = await assistant.process_chat(req, request_id="custom-req-999")

        assert resp.intent.service == "water-tanker"
        assert len(telemetry.events) == 2

        # Both intent_extraction and grounded_response share custom-req-999
        ev_intent = telemetry.events[0]
        ev_reply = telemetry.events[1]

        assert ev_intent.request_id == "custom-req-999"
        assert ev_intent.operation == "intent_extraction"
        assert ev_reply.request_id == "custom-req-999"
        assert ev_reply.operation == "grounded_response"

    asyncio.run(_test())
