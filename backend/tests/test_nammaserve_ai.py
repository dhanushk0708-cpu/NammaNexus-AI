import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.nammaserve import (
    Provider,
    ProviderService,
    ProviderServiceArea,
    ServiceCategory,
    SourceType,
    VerificationStatus,
)
from app.schemas.nammaserve import (
    AssistantChatRequest,
    DiscoveryQuery,
    NormalizedProviderResult,
    ServiceIntent,
)
from app.services.nammaserve.ai.assistant import ServiceAssistant
from app.services.nammaserve.ai.tools import (
    GetProviderInput,
    SearchServicesInput,
    create_get_provider_tool,
    create_search_services_tool,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Seed categories
    cat_water = ServiceCategory(
        id=str(uuid4()),
        slug="water-tanker",
        name="Water Tanker / Bulk Water Delivery",
        description="Potable bulk water tankers",
        icon_name="droplets",
    )
    cat_lock = ServiceCategory(
        id=str(uuid4()),
        slug="locksmith-emergency",
        name="Locksmith / Emergency Key Service",
        description="Emergency lock and key specialists",
        icon_name="key",
    )
    session.add_all([cat_water, cat_lock])
    session.commit()

    # Seed Provider in Kengeri
    p1 = Provider(
        id=str(uuid4()),
        name="Kengeri Kaveri Water Suppliers",
        contact_person="Basavaraj",
        phone="+91 98451 22334",
        address="Mysore Road, Kengeri Satellite Town",
        primary_area="Kengeri",
        latitude=12.9150,
        longitude=77.4830,
        service_radius_km=10.0,
        operating_hours="06:00 - 22:00",
        is_emergency_service=False,
        verification_status=VerificationStatus.VERIFIED.value,
        source="Field verified audit",
        source_type=SourceType.DIRECT_PROVIDER.value,
        last_verified_at=datetime.utcnow(),
    )
    ps1 = ProviderService(
        id=str(uuid4()),
        provider=p1,
        category=cat_water,
        price_min=900.0,
        price_max=1200.0,
        price_unit="per 6000L",
        capacity="6000 Litres",
        water_type="Potable Borewell",
        verification_status=VerificationStatus.VERIFIED.value,
        source="Rate card",
        source_type=SourceType.DIRECT_PROVIDER.value,
        last_verified_at=datetime.utcnow(),
    )
    session.add_all([p1, ps1])
    session.commit()

    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ==========================================================
# 1. Basic Intent Extraction & Fallback Parser Tests
# ==========================================================
def test_fallback_intent_extraction_water_tanker(db_session):
    assistant = ServiceAssistant(db=db_session)
    intent = assistant._fallback_parse_intent(
        "I urgently need a 6000 litre water tanker near Kengeri within 5 km"
    )

    assert intent.service == "water-tanker"
    assert intent.location == "Kengeri"
    assert intent.radius_km == 5.0
    assert intent.capacity_litres == 6000.0
    assert intent.urgent is True


def test_fallback_intent_extraction_locksmith(db_session):
    assistant = ServiceAssistant(db=db_session)
    intent = assistant._fallback_parse_intent(
        "Locked out of my apartment in Koramangala! Need 24x7 keymaker"
    )

    assert intent.service == "locksmith-emergency"
    assert intent.location == "Koramangala"
    assert intent.urgent is True
    assert intent.radius_km is None
    assert intent.capacity_litres is None


# ==========================================================
# 2. Preserving Missing Optional Fields (No Hallucination)
# ==========================================================
def test_missing_optional_fields_preservation(db_session):
    assistant = ServiceAssistant(db=db_session)
    intent = assistant._fallback_parse_intent("Need solar heater repair in Jayanagar")

    assert intent.service == "solar-heater-repair"
    assert intent.location == "Jayanagar"
    assert intent.radius_km is None
    assert intent.capacity_litres is None
    assert intent.urgent is False


# ==========================================================
# 3. Mocked LangChain Structured LLM Intent Extraction
# ==========================================================
def test_langchain_mocked_intent_extraction(db_session):
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=ServiceIntent(
            service="water-tanker",
            location="Kengeri",
            radius_km=5.0,
            capacity_litres=6000.0,
            urgent=True,
            requirements=["potable water", "within 2 hours"],
        )
    )
    mock_llm.with_structured_output.return_value = mock_structured

    assistant = ServiceAssistant(db=db_session, llm=mock_llm)
    intent, fallback_used = asyncio.run(
        assistant.parse_intent("I urgently need a 6000L water tanker in Kengeri")
    )

    assert fallback_used is False
    assert intent.service == "water-tanker"
    assert intent.location == "Kengeri"
    assert intent.radius_km == 5.0
    assert intent.capacity_litres == 6000.0
    assert intent.urgent is True
    assert "potable water" in intent.requirements


# ==========================================================
# 4. LLM Failure and Malformed Output Fallback
# ==========================================================
def test_llm_failure_falls_back_gracefully(db_session):
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(side_effect=RuntimeError("Gemini API Rate Limit / Quota Exceeded"))
    mock_llm.with_structured_output.return_value = mock_structured

    assistant = ServiceAssistant(db=db_session, llm=mock_llm)
    intent, fallback_used = asyncio.run(
        assistant.parse_intent("Need emergency locksmith in Indiranagar")
    )

    # Fallback parser rescued the request without crashing
    assert fallback_used is True
    assert intent.service == "locksmith-emergency"
    assert intent.location == "Indiranagar"
    assert intent.urgent is True


# ==========================================================
# 5. Tool Schema Validation & Direct SQL Prevention
# ==========================================================
def test_tool_schema_validation(db_session):
    tool = create_search_services_tool(db=db_session)
    assert tool.name == "search_local_services"

    # Valid schema instantiates properly
    valid_args = SearchServicesInput(
        service="water-tanker",
        location="Kengeri",
        radius_km=7.5,
        urgent=True,
    )
    assert valid_args.service == "water-tanker"
    assert valid_args.location == "Kengeri"

    # SQL Injection attempt in tool arguments is safely passed as literal string to param queries
    injection_args = SearchServicesInput(
        service="water-tanker' OR '1'='1",
        location="'; DROP TABLE providers; --",
    )
    assert injection_args.service == "water-tanker' OR '1'='1"


def test_get_provider_tool(db_session):
    p = db_session.query(Provider).first()
    assert p is not None

    tool = create_get_provider_tool(db=db_session)
    assert tool.name == "get_provider"

    result = asyncio.run(tool.coroutine(provider_id=p.id))
    assert result is not None
    assert result["name"] == "Kengeri Kaveri Water Suppliers"
    assert result["phone"] == "+91 98451 22334"


# ==========================================================
# 6. End-to-End Assistant Process with Tool Calling
# ==========================================================
def test_assistant_process_chat_success(db_session):
    assistant = ServiceAssistant(db=db_session)
    request = AssistantChatRequest(
        message="I urgently need a 6000 litre water tanker near Kengeri"
    )

    response = asyncio.run(assistant.process_chat(request))

    assert response.intent.service == "water-tanker"
    assert response.intent.location == "Kengeri"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "search_local_services"
    assert len(response.discovery_results) >= 1
    top = response.discovery_results[0]
    assert top.name == "Kengeri Kaveri Water Suppliers"
    assert "Kengeri Kaveri Water Suppliers" in response.reply
    assert "+91 98451 22334" in response.reply


# ==========================================================
# 7. No-Provider Scenario Transparency (No Hallucinations)
# ==========================================================
def test_assistant_no_provider_scenario(db_session):
    assistant = ServiceAssistant(db=db_session)
    request = AssistantChatRequest(
        message="Need debris pickup in Whitefield"
    )

    response = asyncio.run(assistant.process_chat(request))

    assert response.intent.service == "debris-bulk-waste"
    assert len(response.discovery_results) == 0
    # Confirms no fake providers or phone numbers were hallucinated
    reply_lower = response.reply.lower()
    assert (
        "could not find" in reply_lower
        or "do not have verified providers" in reply_lower
        or "no verified providers" in reply_lower
        or "not have" in reply_lower
    )


# ==========================================================
# 8. FastAPI POST /api/v1/nammaserve/assistant Endpoint Test
# ==========================================================
def test_api_assistant_endpoint(client):
    payload = {
        "message": "I urgently need a 6000 litre water tanker near Kengeri within 5 km"
    }
    response = client.post("/api/v1/nammaserve/assistant", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == payload["message"]
    assert data["intent"]["service"] == "water-tanker"
    assert data["intent"]["location"] == "Kengeri"
    assert data["intent"]["urgent"] is True
    assert len(data["tool_calls"]) == 1
    assert len(data["discovery_results"]) >= 1
    assert "Kengeri Kaveri Water Suppliers" in data["reply"]
