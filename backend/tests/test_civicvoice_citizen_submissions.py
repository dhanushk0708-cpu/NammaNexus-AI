from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.civicvoice import _submission_rate_limiter
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.civicvoice import CivicVoiceCitizenSubmission, CivicVoiceSourceRecord


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

    # Clear rate limiter state between tests
    _submission_rate_limiter.clear()

    yield client, session

    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_citizen_submission_success_english(test_client_and_db):
    client, db = test_client_and_db
    payload = {
        "topic": "roads",
        "opinion_text": "Severe potholes on 80 Feet Road in Koramangala. Motorcyclists often lose balance at night.",
        "locality": "Koramangala",
        "language": "en",
        "consent_given": True,
    }
    resp = client.post("/api/v1/civicvoice/submissions", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert "id" in data
    assert data["topic"] == "roads"
    assert data["locality"] == "Koramangala"
    assert data["language"] == "en"
    assert "recorded for community intelligence" in data["confirmation_message"]
    assert "does not constitute an official administrative grievance ticket" in data["confirmation_message"]

    # Verify saved in DB
    db_row = db.query(CivicVoiceCitizenSubmission).filter_by(id=data["id"]).first()
    assert db_row is not None
    assert db_row.opinion_text == payload["opinion_text"]


def test_citizen_submission_success_kannada(test_client_and_db):
    client, db = test_client_and_db
    payload = {
        "topic": "waste_management",
        "opinion_text": "ಇಂದಿರಾನಗರದಲ್ಲಿ ಕಸ ವಿಲೇವಾರಿ ಸಮಯಕ್ಕೆ ಸರಿಯಾಗಿ ಆಗುತ್ತಿಲ್ಲ. ದುರ್ವಾಸನೆ ಹೆಚ್ಚಾಗಿದೆ.",
        "locality": "Indiranagar",
        "language": "kn",
        "consent_given": True,
    }
    resp = client.post("/api/v1/civicvoice/submissions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["language"] == "kn"
    assert data["topic"] == "waste_management"


def test_citizen_submission_validation_too_short(test_client_and_db):
    client, _ = test_client_and_db
    payload = {
        "topic": "roads",
        "opinion_text": "Bad road",  # < 10 characters
        "consent_given": True,
    }
    resp = client.post("/api/v1/civicvoice/submissions", json=payload)
    assert resp.status_code == 422


def test_citizen_submission_validation_missing_consent(test_client_and_db):
    client, _ = test_client_and_db
    payload = {
        "topic": "water_supply",
        "opinion_text": "Water pipeline leakage near BTM lake for the last 3 days.",
        "consent_given": False,
    }
    resp = client.post("/api/v1/civicvoice/submissions", json=payload)
    assert resp.status_code == 400
    assert "Consent confirmation is required" in resp.json()["detail"]


def test_citizen_submission_rate_limiting(test_client_and_db):
    client, _ = test_client_and_db
    payload = {
        "topic": "street_lighting",
        "opinion_text": "Dark streetlights near park corner need repair.",
        "consent_given": True,
    }

    # Submit 15 times (up to limit)
    for _ in range(15):
        resp = client.post("/api/v1/civicvoice/submissions", json=payload)
        assert resp.status_code == 201

    # 16th submission should be rate-limited
    resp = client.post("/api/v1/civicvoice/submissions", json=payload)
    assert resp.status_code == 429
    assert "rate limit exceeded" in resp.json()["detail"].lower()


def test_raw_submissions_endpoint_is_protected_against_unauthorized_access(test_client_and_db, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "civicvoice_api_token", "admin-secret-token")
    client, _ = test_client_and_db

    # Unauthorized request to raw submissions must be rejected
    unauth_resp = client.get("/api/v1/civicvoice/submissions")
    assert unauth_resp.status_code == 401

    # Authorized request succeeds
    auth_resp = client.get(
        "/api/v1/civicvoice/submissions",
        headers={"Authorization": "Bearer admin-secret-token"},
    )
    assert auth_resp.status_code == 200


def test_public_aggregated_endpoint_does_not_leak_raw_texts_or_ids(test_client_and_db):
    client, _ = test_client_and_db

    # Submit a citizen opinion
    client.post(
        "/api/v1/civicvoice/submissions",
        json={
            "topic": "water_supply",
            "opinion_text": "Private citizen feedback about specific street water pressure.",
            "locality": "Malleshwaram",
            "language": "kn",
            "consent_given": True,
        },
    )

    # Public aggregated endpoint should be accessible without tokens
    resp = client.get("/api/v1/civicvoice/submissions/aggregated")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_submissions"] == 1
    assert data["topic_distribution"]["water_supply"] == 1
    assert data["locality_distribution"]["Malleshwaram"] == 1
    assert data["language_distribution"]["kn"] == 1

    # Critical Privacy Check: No raw text, IDs, or timestamps in public aggregate output
    resp_text = resp.text.lower()
    assert "private citizen feedback" not in resp_text
    assert "opinion_text" not in resp_text
    assert "created_at" not in resp_text
    assert "id" not in data or isinstance(data.get("id"), type(None))


def test_separation_of_citizen_submissions_from_public_records(test_client_and_db, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "civicvoice_api_token", "test-secret")
    client, db = test_client_and_db

    # 1. Add an external source record
    now = datetime.now(timezone.utc)
    src_rec = CivicVoiceSourceRecord(
        id="src-ext-1",
        provider="bluesky",
        dedup_key="dedup-ext-1",
        topic="roads",
        title="Pothole in HSR",
        content="Public post from bluesky about potholes",
        url="https://bsky.app/post/123",
        collected_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(src_rec)
    db.commit()

    # 2. Submit a citizen opinion
    client.post(
        "/api/v1/civicvoice/submissions",
        json={
            "topic": "roads",
            "opinion_text": "Direct citizen feedback from resident of HSR Layout.",
            "locality": "HSR Layout",
            "consent_given": True,
        },
    )

    # 3. Verify GET /records returns ONLY the external source record
    rec_resp = client.get("/api/v1/civicvoice/records")
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert rec_data["total"] == 1
    assert rec_data["records"][0]["provider"] == "bluesky"
    assert rec_data["records"][0]["id"] == "src-ext-1"

    # 4. Verify authorized GET /submissions returns ONLY the citizen submission
    sub_resp = client.get(
        "/api/v1/civicvoice/submissions",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["total"] == 1
    assert sub_data["submissions"][0]["locality"] == "HSR Layout"
    assert sub_data["submissions"][0]["opinion_text"] == "Direct citizen feedback from resident of HSR Layout."


def test_citizen_submissions_never_leak_private_identity(test_client_and_db, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "civicvoice_api_token", "test-secret")
    client, _ = test_client_and_db
    client.post(
        "/api/v1/civicvoice/submissions",
        json={
            "topic": "parks_and_environment",
            "opinion_text": "Need more tree planting along the main boulevard.",
            "locality": "Jayanagar",
            "consent_given": True,
        },
    )

    resp = client.get(
        "/api/v1/civicvoice/submissions",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    sub = data["submissions"][0]

    # Explicit privacy check: No personal identification fields exist
    assert "email" not in sub
    assert "phone" not in sub
    assert "user_id" not in sub
    assert "ip_address" not in sub
    assert "name" not in sub


def test_status_endpoint_reports_distinct_counts(test_client_and_db):
    client, db = test_client_and_db

    # Initially 0
    resp = client.get("/api/v1/civicvoice/status")
    assert resp.status_code == 200
    d = resp.json()
    assert d["total_source_records"] == 0
    assert d["total_citizen_submissions"] == 0

    # Add 1 source record and 1 citizen submission
    now = datetime.now(timezone.utc)
    db.add(
        CivicVoiceSourceRecord(
            id="src-stat-1",
            provider="youtube",
            dedup_key="dedup-stat-1",
            topic="traffic",
            title="Silk board video",
            content="Video description",
            url="https://youtube.com/watch?v=stat1",
            collected_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()

    client.post(
        "/api/v1/civicvoice/submissions",
        json={
            "topic": "traffic",
            "opinion_text": "Metro feeder buses are needed during peak morning hours.",
            "consent_given": True,
        },
    )

    # Check status endpoint
    resp2 = client.get("/api/v1/civicvoice/status")
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["total_source_records"] == 1
    assert d2["total_citizen_submissions"] == 1
