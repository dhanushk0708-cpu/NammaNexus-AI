"""Tests for CivicVoice Verified Official Reporting (Prompt 4).

Covers:
- Department mapping (verified BBMP/BWSSB/BESCOM/BTP vs unverified fallbacks).
- Civic report generation from persisted analysis and citizen submissions.
- Empty data and sample-size warnings without hallucination.
- Citizen privacy and k-anonymity small-group suppression.
- Authorization protection on all report endpoints.
- Approval workflow, SHA-256 hash binding, and automatic approval invalidation upon edits.
- Prevention of sending without approval or to unverified recipients.
- Email delivery, idempotency duplicate prevention, and provider error handling.
- Report export in markdown format.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.civicvoice import _submission_rate_limiter
from app.core.config import settings
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.civicvoice import (
    CivicVoiceAnalysisRecord,
    CivicVoiceCitizenSubmission,
    CivicVoiceReport,
    CivicVoiceReportAudit,
    CivicVoiceSourceRecord,
)
from app.schemas.civicvoice import ReportStatus
from app.services.civicvoice.department_mapper import (
    list_verified_departments,
    resolve_department_mapping,
)
from app.services.civicvoice.privacy import (
    build_safe_citizen_report_metrics,
    suppress_small_groups,
)
from app.services.civicvoice.report_delivery import (
    CivicVoiceReportDeliveryService,
    ReportWorkflowError,
)
from app.services.civicvoice.report_generator import (
    CivicVoiceReportGenerator,
    compute_report_content_hash,
)

AUTH_TOKEN = "cv-verified-test-secret-2026"
AUTH_HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"}


@pytest.fixture
def test_db_and_client(monkeypatch):
    monkeypatch.setattr(settings, "civicvoice_api_token", AUTH_TOKEN)
    _submission_rate_limiter.clear()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, db

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    db.close()


# ============================================================================
# 1. Department Mapping Tests
# ============================================================================


def test_department_mapper_verified_catalogs():
    """Verifies that core Bengaluru civic topics map to verified government departments."""
    # Roads -> BBMP Road Infrastructure
    roads_map = resolve_department_mapping("roads_infrastructure")
    assert roads_map.is_verified is True
    assert roads_map.verification_status == "verified"
    assert "BBMP" in roads_map.authority_name
    assert "bbmp.gov.in/road-infrastructure" in roads_map.official_portal_url
    assert roads_map.last_verified_date == "2026-10-25"
    assert roads_map.requires_manual_review is False

    # Waste -> BBMP SWM
    waste_map = resolve_department_mapping("solid_waste")
    assert waste_map.is_verified is True
    assert "Solid Waste Management" in waste_map.department_name
    assert "bbmp.gov.in" in waste_map.verification_source_url

    # Water -> BWSSB
    water_map = resolve_department_mapping("water_drainage")
    assert water_map.is_verified is True
    assert "BWSSB" in water_map.authority_name
    assert "1916" in water_map.submission_channel

    # Electricity -> BESCOM
    bescom_map = resolve_department_mapping("electricity_lighting")
    assert bescom_map.is_verified is True
    assert "BESCOM" in bescom_map.authority_name
    assert "1912" in bescom_map.submission_channel

    # Traffic -> BTP
    btp_map = resolve_department_mapping("traffic_and_transport")
    assert btp_map.is_verified is True
    assert "Traffic Police" in btp_map.authority_name
    assert "btp.karnataka.gov.in" in btp_map.verification_source_url

    # Check verified list returns all
    all_depts = list_verified_departments()
    assert len(all_depts) >= 5


def test_department_mapper_unverified_fallback():
    """Unrecognized or speculative topics must be marked unverified with no invented contacts."""
    unverified = resolve_department_mapping("unrecognized_alien_spaceport_topic")
    assert unverified.is_verified is False
    assert unverified.verification_status == "unverified"
    assert unverified.requires_manual_review is True
    assert unverified.recipient_email is None
    assert unverified.official_portal_url is None
    assert unverified.verification_source_url is None
    assert "Unassigned" in unverified.authority_name


# ============================================================================
# 2. Report Generation Tests (Persisted Data & Evidence Grounding)
# ============================================================================


def test_report_generation_from_persisted_analysis_and_submissions(test_db_and_client):
    """Verifies report generation correctly synthesizes real database records and distinguishes sources."""
    client, db = test_db_and_client
    now = datetime.now(timezone.utc)

    # 1. Add public source records
    src1 = CivicVoiceSourceRecord(
        provider="bluesky",
        external_id="bsky-101",
        dedup_key="hash-101",
        topic="roads",
        title="Severe pothole near Indiranagar 100ft road",
        content="Deep dangerous pothole causing massive two-wheeler skids on 100 Feet Road.",
        url="https://bsky.app/profile/user1/post/101",
        collected_at=now,
    )
    src2 = CivicVoiceSourceRecord(
        provider="youtube",
        external_id="yt-102",
        dedup_key="hash-102",
        topic="roads",
        title="Bengaluru road crater investigation",
        content="Video report showing unpaved stretches and lack of asphalt on main road.",
        url="https://youtube.com/watch?v=102",
        collected_at=now,
    )
    db.add_all([src1, src2])
    db.flush()

    # 2. Add structured analysis
    an1 = CivicVoiceAnalysisRecord(
        source_record_id=src1.id,
        category="roads_infrastructure",
        sentiment="negative",
        confidence="high",
        has_complaint=True,
        extracted_complaint="Deep dangerous pothole causing massive two-wheeler skids on 100 Feet Road",
        has_suggestion=False,
        theme_id="road_damage",
        theme_label="Potholes and Road Surface Damage",
    )
    an2 = CivicVoiceAnalysisRecord(
        source_record_id=src2.id,
        category="roads_infrastructure",
        sentiment="negative",
        confidence="high",
        has_complaint=True,
        extracted_complaint="Unpaved stretches and lack of asphalt on main road",
        has_suggestion=True,
        extracted_suggestion="Expedite resurfacing and white-topping of damaged arterial stretch",
        theme_id="road_damage",
        theme_label="Potholes and Road Surface Damage",
    )
    db.add_all([an1, an2])

    # 3. Add direct citizen submissions (3 submissions in Indiranagar)
    for i in range(3):
        db.add(CivicVoiceCitizenSubmission(
            topic="roads",
            opinion_text=f"Citizen {i} reporting pothole issue near Indiranagar metro station.",
            locality="Indiranagar",
            language="en",
            consent_given=True,
            created_at=now,
        ))
    db.commit()

    # 4. Generate report via API
    resp = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "roads_infrastructure", "reporting_period_days": 14},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 201
    report = resp.json()

    assert report["topic"] == "roads_infrastructure"
    assert report["status"] == "draft"
    assert report["authority_name"] == "Bruhat Bengaluru Mahanagara Palike (BBMP)"
    assert report["mapping_verified"] is True
    assert report["source_records_count"] == 2
    assert report["citizen_submissions_count"] == 3

    # Evidence URLs must link to original public material
    assert "https://bsky.app/profile/user1/post/101" in report["evidence_urls"]
    assert "https://youtube.com/watch?v=102" in report["evidence_urls"]

    # Content hash must be populated
    assert report["content_hash"] is not None
    assert len(report["content_hash"]) == 64

    # Summary must clearly separate citizen submissions from web sources
    summary = report["summary_content"]
    assert "**Public Web & Social Sources Analyzed**: 2 records" in summary
    assert "**Direct Citizen Community Submissions**: 3" in summary
    assert "Indiranagar: 3 submissions" in summary


def test_report_generation_empty_data_handles_without_hallucination(test_db_and_client):
    """Verifies that an empty dataset produces honest sample warnings and 0 counts without inventing findings."""
    client, db = test_db_and_client

    resp = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "solid_waste", "reporting_period_days": 7},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 201
    report = resp.json()

    assert report["source_records_count"] == 0
    assert report["citizen_submissions_count"] == 0
    assert report["evidence_urls"] == []

    # Limitations section must include sample warnings
    limitations = report["limitations"]
    assert "Low public-source sample size warning" in limitations
    assert "Privacy and small sample suppression" in limitations


# ============================================================================
# 3. Citizen Privacy & k-Anonymity Suppression Tests
# ============================================================================


def test_small_group_suppression_logic():
    """Unit test for k-anonymity suppression in privacy.py."""
    distribution = {
        "Indiranagar": 5,      # >= 3: safe
        "Koramangala": 3,     # >= 3: safe
        "Jayanagar": 2,       # < 3: suppressed
        "Frazer Town": 1,     # < 3: suppressed
    }
    suppressed = suppress_small_groups(distribution, threshold=3)

    assert suppressed["Indiranagar"] == 5
    assert suppressed["Koramangala"] == 3
    assert "Jayanagar" not in suppressed
    assert "Frazer Town" not in suppressed
    assert suppressed["Other / Suppressed (< 3)"] == 3  # 2 + 1


def test_build_safe_citizen_report_metrics_under_threshold():
    """When total citizen submissions < 3, granular breakdowns must be withheld entirely."""
    metrics = build_safe_citizen_report_metrics(
        total_submissions=2,
        topic_distribution={"roads": 2},
        locality_distribution={"Kengeri": 2},
        threshold=3,
    )
    assert metrics["total_represented"] == 2
    assert metrics["sample_warning"] is not None
    assert "below privacy threshold" in metrics["sample_warning"]
    assert metrics["topic_distribution"] == {}
    assert metrics["locality_distribution"] == {}


def test_public_aggregated_endpoint_with_suppression_flag(test_db_and_client):
    """Verifies the public aggregated endpoint supports small-group suppression when requested."""
    client, db = test_db_and_client
    now = datetime.now(timezone.utc)

    # Add 1 Malleshwaram submission (count 1 < 3) and 3 Whitefield submissions (count 3 >= 3)
    db.add(CivicVoiceCitizenSubmission(
        topic="water_supply",
        opinion_text="Malleshwaram pressure low",
        locality="Malleshwaram",
        consent_given=True,
        created_at=now,
    ))
    for _ in range(3):
        db.add(CivicVoiceCitizenSubmission(
            topic="water_supply",
            opinion_text="Whitefield tanker pricing issue",
            locality="Whitefield",
            consent_given=True,
            created_at=now,
        ))
    db.commit()

    # Query with suppress_small_groups=true
    resp = client.get("/api/v1/civicvoice/submissions/aggregated?suppress_small_groups=true")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_submissions"] == 4
    # Whitefield (3) preserved; Malleshwaram (1) suppressed
    assert data["locality_distribution"]["Whitefield"] == 3
    assert "Malleshwaram" not in data["locality_distribution"]
    assert data["locality_distribution"]["Other / Suppressed (< 3)"] == 1


# ============================================================================
# 4. Authentication & Security Protection Tests
# ============================================================================


def test_report_endpoints_reject_unauthorized(test_db_and_client):
    """All report management endpoints must reject missing or invalid authorization tokens."""
    client, _ = test_db_and_client

    # Generate
    assert client.post("/api/v1/civicvoice/reports/generate", json={"topic": "roads"}).status_code == 401
    assert client.post("/api/v1/civicvoice/reports/generate", json={"topic": "roads"}, headers={"Authorization": "Bearer bad-token"}).status_code == 403

    # List
    assert client.get("/api/v1/civicvoice/reports").status_code == 401

    # Get single
    assert client.get("/api/v1/civicvoice/reports/rep-123").status_code == 401

    # Approve
    assert client.post("/api/v1/civicvoice/reports/rep-123/approve").status_code == 401

    # Reject
    assert client.post("/api/v1/civicvoice/reports/rep-123/reject", json={"reason": "Need more data"}).status_code == 401

    # Send
    assert client.post("/api/v1/civicvoice/reports/rep-123/send").status_code == 401

    # Export
    assert client.get("/api/v1/civicvoice/reports/rep-123/export").status_code == 401


# ============================================================================
# 5. Human Approval Workflow & Hash Binding Tests
# ============================================================================


def test_approval_workflow_and_audit_trail(test_db_and_client):
    """Verifies draft -> approve -> reject workflow states and audit trail logging."""
    client, db = test_db_and_client

    # 1. Generate a report
    gen_resp = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "roads", "title": "Initial Road Quality Assessment"},
        headers=AUTH_HEADERS,
    )
    report_id = gen_resp.json()["id"]

    # 2. Approve the report
    appr_resp = client.post(
        f"/api/v1/civicvoice/reports/{report_id}/approve",
        json={"notes": "Reviewed and verified against field inspector notes."},
        headers=AUTH_HEADERS,
    )
    assert appr_resp.status_code == 200
    approved_data = appr_resp.json()
    assert approved_data["status"] == "approved"
    assert approved_data["approved_by"] == "authorized_reviewer"
    assert approved_data["approved_at"] is not None

    # Check audit trail
    report_obj = db.get(CivicVoiceReport, report_id)
    assert len(report_obj.audits) == 2  # created, approved
    assert report_obj.audits[0].action == "approved"
    assert report_obj.audits[0].performed_by == "authorized_reviewer"

    # 3. Reject a different report
    gen2 = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "water_drainage"},
        headers=AUTH_HEADERS,
    ).json()
    rej_resp = client.post(
        f"/api/v1/civicvoice/reports/{gen2['id']}/reject",
        json={"reason": "Sample size too small; re-run collection across Tavily first."},
        headers=AUTH_HEADERS,
    )
    assert rej_resp.status_code == 200
    rej_data = rej_resp.json()
    assert rej_data["status"] == "rejected"
    assert "Sample size too small" in rej_data["rejection_reason"]


def test_approval_invalidated_upon_report_content_or_recipient_edit(test_db_and_client):
    """CRITICAL TEST: Editing an approved report's content or recipient MUST invalidate approval."""
    client, db = test_db_and_client

    # 1. Generate and approve a report
    gen = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "roads_infrastructure"},
        headers=AUTH_HEADERS,
    ).json()
    report_id = gen["id"]

    client.post(f"/api/v1/civicvoice/reports/{report_id}/approve", headers=AUTH_HEADERS)
    approved_report = client.get(f"/api/v1/civicvoice/reports/{report_id}", headers=AUTH_HEADERS).json()
    assert approved_report["status"] == "approved"
    old_hash = approved_report["content_hash"]

    # 2. Modify the recommendations in the report
    patch_resp = client.patch(
        f"/api/v1/civicvoice/reports/{report_id}",
        json={"recommendations": "Modified administrative recommendations after unauthorized change."},
        headers=AUTH_HEADERS,
    )
    assert patch_resp.status_code == 200
    updated_report = patch_resp.json()

    # Status must automatically revert from approved to pending_review!
    assert updated_report["status"] == "pending_review"
    assert updated_report["approved_by"] is None
    assert updated_report["approved_at"] is None
    assert updated_report["content_hash"] != old_hash

    # Verify audit trail records the invalidation event
    report_obj = db.get(CivicVoiceReport, report_id)
    actions = [a.action for a in report_obj.audits]
    assert "approval_invalidated" in actions


# ============================================================================
# 6. Delivery, Idempotency & Provider Error Tests
# ============================================================================


def test_send_blocked_without_explicit_human_approval(test_db_and_client):
    """Attempting to dispatch a report in 'draft' or 'pending_review' status must be rejected."""
    client, _ = test_db_and_client

    gen = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "roads"},
        headers=AUTH_HEADERS,
    ).json()

    resp = client.post(
        f"/api/v1/civicvoice/reports/{gen['id']}/send",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400
    assert "must be explicitly approved" in resp.json()["detail"].lower()


def test_send_blocked_for_unverified_recipient(test_db_and_client):
    """Attempting to dispatch a report with an unverified recipient must be rejected."""
    client, _ = test_db_and_client

    # Generate for an unverified topic
    gen = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "unverified_speculative_monorail"},
        headers=AUTH_HEADERS,
    ).json()
    report_id = gen["id"]

    # Approve it
    client.post(f"/api/v1/civicvoice/reports/{report_id}/approve", headers=AUTH_HEADERS)

    # Attempt send
    resp = client.post(
        f"/api/v1/civicvoice/reports/{report_id}/send",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400
    assert "unverified recipient" in resp.json()["detail"].lower()


def test_send_safe_preview_export_when_resend_unconfigured(test_db_and_client, monkeypatch):
    """When Resend is not configured, send endpoint returns honest preview/export response."""
    monkeypatch.setattr(settings, "resend_api_key", None)
    client, _ = test_db_and_client

    gen = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "roads"},
        headers=AUTH_HEADERS,
    ).json()
    report_id = gen["id"]

    client.post(f"/api/v1/civicvoice/reports/{report_id}/approve", headers=AUTH_HEADERS)

    send_resp = client.post(f"/api/v1/civicvoice/reports/{report_id}/send", headers=AUTH_HEADERS)
    assert send_resp.status_code == 200
    data = send_resp.json()

    assert data["delivery_mode"] == "preview_export_only"
    assert "not configured" in data["message"].lower()
    # Status remains approved and ready for export
    assert data["status"] == "approved"


def test_send_successful_dispatch_and_idempotency_prevention(test_db_and_client, monkeypatch):
    """When Resend is configured, dispatches report and prevents duplicate sends."""
    monkeypatch.setattr(settings, "resend_api_key", "re_test_dummy_key_12345")
    client, db = test_db_and_client

    gen = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "roads"},
        headers=AUTH_HEADERS,
    ).json()
    report_id = gen["id"]

    client.post(f"/api/v1/civicvoice/reports/{report_id}/approve", headers=AUTH_HEADERS)

    # Mock httpx.post to simulate successful Resend delivery
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "resend-msg-999"}

    with patch("httpx.post", return_value=mock_response) as mock_post:
        # First send
        send1 = client.post(
            f"/api/v1/civicvoice/reports/{report_id}/send",
            json={"idempotency_key": "idemp-key-001"},
            headers=AUTH_HEADERS,
        )
        assert send1.status_code == 200
        data1 = send1.json()
        assert data1["status"] == "sent"
        assert data1["delivery_mode"] == "resend_api"
        assert mock_post.call_count == 1

        # Second send with same report (idempotency check)
        send2 = client.post(
            f"/api/v1/civicvoice/reports/{report_id}/send",
            json={"idempotency_key": "idemp-key-001"},
            headers=AUTH_HEADERS,
        )
        assert send2.status_code == 200
        data2 = send2.json()
        assert data2["status"] == "sent"
        assert "already been delivered" in data2["message"].lower()

        # Provider must NOT have been called again!
        assert mock_post.call_count == 1


def test_send_handles_provider_errors_gracefully(test_db_and_client, monkeypatch):
    """Simulates email provider failure and verifies status transitions to send_failed."""
    monkeypatch.setattr(settings, "resend_api_key", "re_test_dummy_key_12345")
    client, _ = test_db_and_client

    gen = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "roads"},
        headers=AUTH_HEADERS,
    ).json()
    report_id = gen["id"]

    client.post(f"/api/v1/civicvoice/reports/{report_id}/approve", headers=AUTH_HEADERS)

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Provider Error"

    with patch("httpx.post", return_value=mock_response):
        resp = client.post(f"/api/v1/civicvoice/reports/{report_id}/send", headers=AUTH_HEADERS)
        assert resp.status_code == 400
        assert "provider error" in resp.json()["detail"].lower()

    # Report status must be updated to send_failed
    rep = client.get(f"/api/v1/civicvoice/reports/{report_id}", headers=AUTH_HEADERS).json()
    assert rep["status"] == "send_failed"


# ============================================================================
# 7. Report Export Tests
# ============================================================================


def test_export_report_markdown(test_db_and_client):
    """Verifies that export returns a complete, clean markdown document."""
    client, _ = test_db_and_client

    gen = client.post(
        "/api/v1/civicvoice/reports/generate",
        json={"topic": "roads"},
        headers=AUTH_HEADERS,
    ).json()
    report_id = gen["id"]

    export_resp = client.get(f"/api/v1/civicvoice/reports/{report_id}/export", headers=AUTH_HEADERS)
    assert export_resp.status_code == 200
    data = export_resp.json()

    assert data["format"] == "markdown"
    content = data["content"]
    assert "# Civic Priority Brief" in content
    assert "Bruhat Bengaluru Mahanagara Palike" in content
    assert "Official Verification & Routing Metadata" in content
    assert "Recommended Administrative Actions" in content
    assert "Methodology, Sample Size & Privacy Limitations" in content
