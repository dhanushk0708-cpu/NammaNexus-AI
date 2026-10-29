import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.services.nammaserve.ai.cache import (
    INTENT_CACHE_VERSION,
    IntentCache,
    normalize_intent_cache_key,
)
from app.services.nammaserve.ai.providers.manager import ProviderManager
from app.services.nammaserve.ai.telemetry import InMemoryTelemetryHandler
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


# --------------------------------------------------------------------
# 1. Key Normalization & Versioning Tests
# --------------------------------------------------------------------
def test_normalize_intent_cache_key_whitespace_and_case():
    q1 = "I need a WATER tanker near Kengeri"
    q2 = "  i  need   a water   tanker  near kengeri  "
    k1 = normalize_intent_cache_key(q1)
    k2 = normalize_intent_cache_key(q2)

    assert k1 == k2
    assert k1 == f"intent:{INTENT_CACHE_VERSION}:i need a water tanker near kengeri"


def test_normalize_intent_cache_key_different_queries():
    k1 = normalize_intent_cache_key("water tanker in Kengeri")
    k2 = normalize_intent_cache_key("water tanker in Indiranagar")
    assert k1 != k2


def test_normalize_intent_cache_key_custom_version():
    k = normalize_intent_cache_key("water tanker", version="v2")
    assert k == "intent:v2:water tanker"


# --------------------------------------------------------------------
# 2. IntentCache Basic Operations, TTL & LRU Eviction
# --------------------------------------------------------------------
def test_intent_cache_set_and_get():
    cache = IntentCache(max_size=10, default_ttl_seconds=3600)
    intent = ServiceIntent(service="water-tanker", location="Kengeri", urgent=True)

    cache.set("intent:v1:test", intent)
    retrieved = cache.get("intent:v1:test")

    assert retrieved is not None
    assert retrieved.service == "water-tanker"
    assert retrieved.location == "Kengeri"
    assert retrieved.urgent is True
    assert cache.stats["hits"] == 1
    assert cache.stats["misses"] == 0


def test_intent_cache_miss():
    cache = IntentCache(max_size=10, default_ttl_seconds=3600)
    assert cache.get("intent:v1:nonexistent") is None
    assert cache.stats["misses"] == 1


def test_intent_cache_ttl_expiration():
    fake_time = 1000.0

    def mock_time():
        return fake_time

    cache = IntentCache(max_size=10, default_ttl_seconds=60, time_fn=mock_time)
    intent = ServiceIntent(service="locksmith-emergency", location="Koramangala")

    cache.set("key1", intent, ttl_seconds=60)
    assert cache.get("key1") is not None

    # Advance time beyond TTL
    fake_time += 61.0
    assert cache.get("key1") is None
    assert cache.size() == 0


def test_intent_cache_lru_eviction():
    cache = IntentCache(max_size=2, default_ttl_seconds=3600)
    i1 = ServiceIntent(service="water-tanker", location="Loc1")
    i2 = ServiceIntent(service="locksmith-emergency", location="Loc2")
    i3 = ServiceIntent(service="solar-heater-repair", location="Loc3")

    cache.set("k1", i1)
    cache.set("k2", i2)
    assert cache.size() == 2

    # Access k1 to make it MRU
    _ = cache.get("k1")

    # Add k3 -> k2 should be evicted (least recently used)
    cache.set("k3", i3)
    assert cache.size() == 2
    assert cache.get("k2") is None  # Evicted
    assert cache.get("k1") is not None
    assert cache.get("k3") is not None
    assert cache.stats["evictions"] == 1


# --------------------------------------------------------------------
# 3. Data Safety & Mutation Isolation
# --------------------------------------------------------------------
def test_cached_intent_mutation_does_not_affect_subsequent_reads():
    cache = IntentCache(max_size=10, default_ttl_seconds=3600)
    original = ServiceIntent(
        service="water-tanker",
        location="Kengeri",
        requirements=["potable"],
    )

    cache.set("k1", original)

    # First retrieval -> mutate returned instance
    first = cache.get("k1")
    assert first is not None
    first.requirements.append("MUTATED_IN_MEMORY")
    first.location = "MUTATED_LOCATION"

    # Second retrieval -> must remain untouched
    second = cache.get("k1")
    assert second is not None
    assert second.location == "Kengeri"
    assert second.requirements == ["potable"]
    assert "MUTATED_IN_MEMORY" not in second.requirements


# --------------------------------------------------------------------
# 4. ServiceAssistant End-to-End Cache Hit vs Miss & Telemetry
# --------------------------------------------------------------------
def test_assistant_first_call_misses_second_call_hits_without_ai_or_telemetry():
    async def _test():
        cache = IntentCache(max_size=10, default_ttl_seconds=3600)
        telemetry = InMemoryTelemetryHandler()

        mock_groq_llm = MagicMock()
        mock_groq_structured = MagicMock()
        mock_groq_structured.ainvoke = AsyncMock(
            return_value=ServiceIntent(
                service="water-tanker",
                location="Kengeri",
                urgent=True,
            )
        )
        mock_groq_llm.with_structured_output.return_value = mock_groq_structured

        p_groq = DummyProvider("groq", "llama-3.3-70b-versatile", mock_groq_llm)
        p_gemini = DummyProvider("gemini", "gemini-2.0-flash", MagicMock())

        manager = ProviderManager(
            primary=p_groq,
            secondary=p_gemini,
            telemetry_handler=telemetry,
        )

        assistant = ServiceAssistant(
            db=MagicMock(),
            intent_cache=cache,
        )
        assistant.provider_manager = manager

        query = "  I need a WATER tanker near Kengeri urgently "

        # Call 1: Cache MISS -> ProviderManager invoked -> AI called -> Telemetry emitted
        intent1, fallback1 = await assistant.parse_intent(query, request_id="req-1")
        assert fallback1 is False
        assert intent1.service == "water-tanker"
        assert intent1.location == "Kengeri"
        assert intent1.urgent is True
        assert p_groq.call_count == 1
        assert len(telemetry.events) == 1
        assert telemetry.events[0].request_id == "req-1"

        # Call 2: Identical normalized query -> Cache HIT -> AI NOT called -> No new telemetry
        query2 = "i need a water tanker near kengeri urgently"
        intent2, fallback2 = await assistant.parse_intent(query2, request_id="req-2")
        assert fallback2 is False
        assert intent2.service == "water-tanker"
        assert intent2.location == "Kengeri"
        assert intent2.urgent is True
        # Provider count and telemetry count must remain strictly 1!
        assert p_groq.call_count == 1
        assert len(telemetry.events) == 1

        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 1

    asyncio.run(_test())


# --------------------------------------------------------------------
# 5. Fault Tolerance / Resilience Tests
# --------------------------------------------------------------------
def test_cache_get_failure_degrades_gracefully_to_ai():
    async def _test():
        class BrokenCache(IntentCache):
            def get(self, key):
                raise RuntimeError("Corrupted in-memory index")

        mock_groq_llm = MagicMock()
        mock_groq_structured = MagicMock()
        mock_groq_structured.ainvoke = AsyncMock(
            return_value=ServiceIntent(service="e-waste-pickup", location="Whitefield")
        )
        mock_groq_llm.with_structured_output.return_value = mock_groq_structured

        p_groq = DummyProvider("groq", "llama-3.3-70b-versatile", mock_groq_llm)
        manager = ProviderManager(primary=p_groq, secondary=MagicMock())

        assistant = ServiceAssistant(db=MagicMock(), intent_cache=BrokenCache())
        assistant.provider_manager = manager

        # Must succeed without throwing
        intent, fallback = await assistant.parse_intent("Pickup old laptop in Whitefield")
        assert fallback is False
        assert intent.service == "e-waste-pickup"
        assert p_groq.call_count == 1

    asyncio.run(_test())


def test_cache_set_failure_does_not_fail_ai_request():
    async def _test():
        class FailingSetCache(IntentCache):
            def set(self, key, value, ttl_seconds=None):
                raise RuntimeError("Write lock error")

        mock_groq_llm = MagicMock()
        mock_groq_structured = MagicMock()
        mock_groq_structured.ainvoke = AsyncMock(
            return_value=ServiceIntent(service="debris-bulk-waste", location="Hebbal")
        )
        mock_groq_llm.with_structured_output.return_value = mock_groq_structured

        p_groq = DummyProvider("groq", "llama-3.3-70b-versatile", mock_groq_llm)
        manager = ProviderManager(primary=p_groq, secondary=MagicMock())

        assistant = ServiceAssistant(db=MagicMock(), intent_cache=FailingSetCache())
        assistant.provider_manager = manager

        # Must succeed without throwing
        intent, fallback = await assistant.parse_intent("Need debris waste pickup in Hebbal")
        assert fallback is False
        assert intent.service == "debris-bulk-waste"
        assert p_groq.call_count == 1

    asyncio.run(_test())
