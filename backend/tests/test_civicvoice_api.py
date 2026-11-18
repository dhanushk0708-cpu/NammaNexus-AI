from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models import CivicVoiceSourceRecord
from app.schemas.civicvoice import NormalizedSourceRecord
from app.services.civicvoice.collectors.base import CollectorQuotaError, compute_dedup_key


@pytest.fixture
def test_client_and_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, session

    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)


# ============================================================================
# API Status Endpoint Tests
# ============================================================================


def test_status_endpoint_never_exposes_secrets(test_client_and_db):
    client, _ = test_client_and_db
    resp = client.get("/api/v1/civicvoice/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ok"
    assert "bluesky_configured" in data
    assert "youtube_configured" in data
    assert "tavily_configured" in data
    assert isinstance(data["bluesky_configured"], bool)
    assert isinstance(data["youtube_configured"], bool)
    assert isinstance(data["tavily_configured"], bool)

    # Critical security assertion: No secret or key substring present in payload
    resp_text = resp.text.lower()
    for sensitive_word in ("api_key", "secret", "token", "password"):
        assert sensitive_word not in resp_text


# ============================================================================
# API Collect Endpoint Tests
# ============================================================================


# ============================================================================
# API Collect Endpoint Security & Authorization Tests
# ============================================================================


def test_collect_unauthorized_missing_header_rejected(test_client_and_db):
    """Anonymous requests without authorization credentials must be rejected with HTTP 401."""
    client, _ = test_client_and_db
    payload = {"query": "Silk Board traffic", "limit_per_provider": 5}
    resp = client.post("/api/v1/civicvoice/collect", json=payload)
    assert resp.status_code == 401
    assert "Authorization required" in resp.json()["detail"]
    assert "Bearer" in resp.headers.get("www-authenticate", "")


def test_collect_unauthorized_empty_header_rejected(test_client_and_db):
    """Requests with blank or empty credentials must be rejected with HTTP 401."""
    client, _ = test_client_and_db
    payload = {"query": "Silk Board traffic", "limit_per_provider": 5}
    resp = client.post(
        "/api/v1/civicvoice/collect",
        json=payload,
        headers={"Authorization": "Bearer   "},
    )
    assert resp.status_code == 401


def test_collect_server_unconfigured_token_locked(test_client_and_db, monkeypatch):
    """When the server has no CIVICVOICE_API_TOKEN configured, the collection endpoint is locked (403)."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "civicvoice_api_token", None)
    client, _ = test_client_and_db
    payload = {"query": "Silk Board traffic", "limit_per_provider": 5}
    resp = client.post(
        "/api/v1/civicvoice/collect",
        json=payload,
        headers={"Authorization": "Bearer any_token_attempt"},
    )
    assert resp.status_code == 403
    assert "CIVICVOICE_API_TOKEN in backend environment" in resp.json()["detail"]


def test_collect_unauthorized_invalid_token_rejected(test_client_and_db, monkeypatch):
    """Requests with mismatched tokens must be rejected with HTTP 403."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "civicvoice_api_token", "correct-secret-token")
    client, _ = test_client_and_db
    payload = {"query": "Silk Board traffic", "limit_per_provider": 5}

    # Wrong bearer token
    resp = client.post(
        "/api/v1/civicvoice/collect",
        json=payload,
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 403
    assert "Forbidden: invalid collection authorization credential." in resp.json()["detail"]

    # Wrong X-API-Key
    resp2 = client.post(
        "/api/v1/civicvoice/collect",
        json=payload,
        headers={"X-API-Key": "wrong-token"},
    )
    assert resp2.status_code == 403


def test_collect_authorized_bearer_token_succeeds(test_client_and_db, monkeypatch):
    """Authorized requests with valid Bearer token succeed and trigger collection."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "civicvoice_api_token", "test-auth-token-123")
    client, _ = test_client_and_db
    now = datetime.now(timezone.utc)
    dedup = compute_dedup_key("bluesky", "at://1", "https://bsky.app/post/1")

    mock_rec = NormalizedSourceRecord(
        provider="bluesky",
        external_id="at://1",
        dedup_key=dedup,
        topic="traffic",
        content="Heavy traffic at Silk Board junction",
        url="https://bsky.app/post/1",
        author="commuter",
        published_at=now,
        collected_at=now,
    )

    with patch("app.api.v1.endpoints.civicvoice.civicvoice_service.bluesky.collect", new_callable=AsyncMock) as mock_b:
        mock_b.return_value = [mock_rec]

        payload = {
            "query": "Silk Board traffic",
            "topic": "traffic",
            "providers": ["bluesky"],
            "limit_per_provider": 5,
        }
        resp = client.post(
            "/api/v1/civicvoice/collect",
            json=payload,
            headers={"Authorization": "Bearer test-auth-token-123"},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["query"] == "Silk Board traffic"
        assert data["total_collected"] == 1
        assert data["total_persisted"] == 1


def test_collect_authorized_x_api_key_succeeds(test_client_and_db, monkeypatch):
    """Authorized requests with valid X-API-Key header succeed and trigger collection."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "civicvoice_api_token", "test-api-key-456")
    client, _ = test_client_and_db
    now = datetime.now(timezone.utc)
    dedup = compute_dedup_key("bluesky", "at://2", "https://bsky.app/post/2")

    mock_rec = NormalizedSourceRecord(
        provider="bluesky",
        external_id="at://2",
        dedup_key=dedup,
        topic="traffic",
        content="Post 2 traffic report",
        url="https://bsky.app/post/2",
        author="commuter",
        published_at=now,
        collected_at=now,
    )

    with patch("app.api.v1.endpoints.civicvoice.civicvoice_service.bluesky.collect", new_callable=AsyncMock) as mock_b:
        mock_b.return_value = [mock_rec]

        payload = {
            "query": "Silk Board traffic",
            "providers": ["bluesky"],
            "limit_per_provider": 5,
        }
        resp = client.post(
            "/api/v1/civicvoice/collect",
            json=payload,
            headers={"X-API-Key": "test-api-key-456"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_collected"] == 1


def test_collect_invalid_input_bounds(test_client_and_db, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "civicvoice_api_token", "test-token")
    client, _ = test_client_and_db
    headers = {"Authorization": "Bearer test-token"}

    # Empty query
    resp = client.post("/api/v1/civicvoice/collect", json={"query": "", "limit_per_provider": 10}, headers=headers)
    assert resp.status_code == 422

    # Query too long (>200 characters)
    resp = client.post("/api/v1/civicvoice/collect", json={"query": "A" * 201, "limit_per_provider": 10}, headers=headers)
    assert resp.status_code == 422

    # Limit below 1
    resp = client.post("/api/v1/civicvoice/collect", json={"query": "roads", "limit_per_provider": 0}, headers=headers)
    assert resp.status_code == 422

    # Limit above 50
    resp = client.post("/api/v1/civicvoice/collect", json={"query": "roads", "limit_per_provider": 51}, headers=headers)
    assert resp.status_code == 422


def test_collect_handles_provider_quota_and_errors_gracefully(test_client_and_db, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "civicvoice_api_token", "test-token")
    client, _ = test_client_and_db
    headers = {"Authorization": "Bearer test-token"}

    with patch("app.api.v1.endpoints.civicvoice.civicvoice_service.youtube.collect", new_callable=AsyncMock) as mock_yt:
        mock_yt.side_effect = CollectorQuotaError("YouTube quota exceeded", provider="youtube", status_code=403)

        payload = {
            "query": "Whitefield roads",
            "providers": ["youtube"],
            "limit_per_provider": 5,
        }
        resp = client.post("/api/v1/civicvoice/collect", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_collected"] == 0
        assert data["total_persisted"] == 0
        statuses = data["provider_statuses"]
        assert len(statuses) == 1
        assert statuses[0]["provider"] == "youtube"
        assert statuses[0]["success"] is False
        assert "YouTube quota exceeded" in statuses[0]["error_message"]


# ============================================================================
# API Records Endpoint Tests
# ============================================================================


def test_records_pagination_and_filters(test_client_and_db):
    client, session = test_client_and_db
    now = datetime.now(timezone.utc)

    # Insert test records
    for i in range(10):
        rec = CivicVoiceSourceRecord(
            id=f"rec-{i}",
            provider="bluesky" if i < 5 else "youtube",
            external_id=f"ext-{i}",
            dedup_key=f"dedup-{i}",
            topic="potholes" if i < 3 else "garbage",
            title=f"Bengaluru Issue #{i}",
            content=f"Report about ward {i}",
            url=f"https://example.com/posts/{i}",
            collected_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(rec)
    session.commit()

    # Get records with default limit
    resp = client.get("/api/v1/civicvoice/records")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert len(data["records"]) == 10

    # Filter by provider
    resp = client.get("/api/v1/civicvoice/records?provider=youtube")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    for r in data["records"]:
        assert r["provider"] == "youtube"

    # Filter by topic
    resp = client.get("/api/v1/civicvoice/records?topic=potholes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3

    # Pagination bounds
    resp = client.get("/api/v1/civicvoice/records?limit=3&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 3
    assert len(data["records"]) == 3

    # Invalid pagination bounds (limit > 100 or offset < 0)
    resp = client.get("/api/v1/civicvoice/records?limit=101")
    assert resp.status_code == 422

    resp = client.get("/api/v1/civicvoice/records?offset=-1")
    assert resp.status_code == 422


# ============================================================================
# Integration & Registration Tests
# ============================================================================


def test_model_and_router_registration():
    from app.models import CivicVoiceAnalysisRecord, CivicVoiceSourceRecord
    from app.main import app

    # Check models have table names and Base registration
    assert CivicVoiceSourceRecord.__tablename__ == "civicvoice_source_records"
    assert CivicVoiceAnalysisRecord.__tablename__ == "civicvoice_analysis_records"

    # Check routes in app via openapi schema
    paths = app.openapi()["paths"]
    assert "/api/v1/civicvoice/status" in paths
    assert "/api/v1/civicvoice/search" in paths
    assert "/api/v1/civicvoice/trending" in paths
    assert "/api/v1/civicvoice/collect" in paths
    assert "/api/v1/civicvoice/records" in paths
    assert "/api/v1/civicvoice/analyze" in paths
    assert "/api/v1/civicvoice/analysis" in paths
    assert "/api/v1/civicvoice/themes" in paths
    assert "/api/v1/civicvoice/trends" in paths
    assert "/api/v1/civicvoice/summary" in paths


# ============================================================================
# Search-First & Trending Endpoint Tests
# ============================================================================


def test_search_endpoint_public_and_live(test_client_and_db):
    """Verifies that POST /api/v1/civicvoice/search is open to citizens without admin token,

    triggers collection/analysis for arbitrary topics (e.g. 'Mysore Dasara 2026'),
    and returns structured summary and themes.
    """
    client, session = test_client_and_db
    now = datetime.now(timezone.utc)

    # Pre-seed records matching "Mysore Dasara 2026"
    for i in range(3):
        rec = CivicVoiceSourceRecord(
            id=f"dasara-{i}",
            provider="tavily" if i == 0 else "bluesky",
            dedup_key=f"dasara-dedup-{i}",
            topic="Mysore Dasara 2026",
            title=f"Mysore Dasara 2026 cultural event #{i}",
            content=f"Public discussion regarding Mysore Dasara 2026 festivities and traffic plans item {i}.",
            url=f"https://example.com/dasara/{i}",
            collected_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(rec)
    session.commit()

    # Search without any Authorization header
    with patch("app.api.v1.endpoints.civicvoice.civicvoice_service.bluesky.collect", new_callable=AsyncMock) as m_b, \
         patch("app.api.v1.endpoints.civicvoice.civicvoice_service.youtube.collect", new_callable=AsyncMock) as m_y, \
         patch("app.api.v1.endpoints.civicvoice.civicvoice_service.tavily.collect", new_callable=AsyncMock) as m_t:
        m_b.return_value = []
        m_y.return_value = []
        m_t.return_value = []

        resp = client.post(
            "/api/v1/civicvoice/search",
            json={"query": "Mysore Dasara 2026", "limit_per_provider": 5},
        )
    assert resp.status_code == 200
    data = resp.json()

    assert data["query"] == "Mysore Dasara 2026"
    assert data["total_records"] == 3
    assert len(data["records"]) == 3
    assert "summary" in data
    assert "themes" in data
    assert "provider_statuses" in data
    assert isinstance(data["citizen_submissions_count"], int)
    # Check that URLs are preserved and valid
    for r in data["records"]:
        assert r["url"].startswith("http")


def test_trending_topics_from_actual_data(test_client_and_db):
    """Verifies that GET /api/v1/civicvoice/trending discovers topics solely from actual data

    and never fabricates fake topics.
    """
    client, session = test_client_and_db
    now = datetime.now(timezone.utc)

    # Empty DB should return empty list
    resp = client.get("/api/v1/civicvoice/trending")
    assert resp.status_code == 200
    assert resp.json()["trending_topics"] == []

    # Insert actual records for two distinct topics
    for i in range(4):
        session.add(
            CivicVoiceSourceRecord(
                id=f"src-roads-{i}",
                provider="bluesky",
                dedup_key=f"roads-dedup-{i}",
                topic="Indiranagar Roads",
                title=f"Road repair update {i}",
                content="Potholes on 100ft road",
                url=f"https://example.com/roads/{i}",
                collected_at=now,
                created_at=now,
                updated_at=now,
            )
        )
    for i in range(2):
        session.add(
            CivicVoiceSourceRecord(
                id=f"src-dasara-{i}",
                provider="tavily",
                dedup_key=f"dasara-trend-dedup-{i}",
                topic="Mysore Dasara 2026",
                title=f"Mysore Dasara preparation {i}",
                content="Dasara gold howdah schedule",
                url=f"https://example.com/dasara/{i}",
                collected_at=now,
                created_at=now,
                updated_at=now,
            )
        )
    session.commit()

    resp = client.get("/api/v1/civicvoice/trending?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    topics = data["trending_topics"]
    assert len(topics) >= 2
    # Indiranagar Roads has 4, Mysore Dasara 2026 has 2
    assert topics[0]["topic"] == "Indiranagar Roads"
    assert topics[0]["record_count"] == 4
    assert topics[1]["topic"] == "Mysore Dasara 2026"
    assert topics[1]["record_count"] == 2


def test_search_endpoint_rate_limiting(test_client_and_db):
    """Verifies that rapid excessive search requests trigger HTTP 429."""
    from app.api.v1.endpoints.civicvoice import _search_rate_limiter

    _search_rate_limiter.clear()
    client, _ = test_client_and_db

    # Exceed rate limit (limit is 20 per minute)
    status_codes = []
    with patch("app.api.v1.endpoints.civicvoice.civicvoice_service.bluesky.collect", new_callable=AsyncMock) as m_b, \
         patch("app.api.v1.endpoints.civicvoice.civicvoice_service.youtube.collect", new_callable=AsyncMock) as m_y, \
         patch("app.api.v1.endpoints.civicvoice.civicvoice_service.tavily.collect", new_callable=AsyncMock) as m_t:
        m_b.return_value = []
        m_y.return_value = []
        m_t.return_value = []

        for _ in range(22):
            res = client.post("/api/v1/civicvoice/search", json={"query": "flood control"})
            status_codes.append(res.status_code)

    assert 429 in status_codes
    _search_rate_limiter.clear()

