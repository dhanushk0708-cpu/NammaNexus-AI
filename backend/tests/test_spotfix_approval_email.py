import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import spotfix as spotfix_endpoint
from app.core.config import settings
from app.main import app
from app.models.complaint import ComplaintStatus
from app.services.email import EmailDeliveryError, EmailService


client = TestClient(app)
email_service = EmailService()


def create_sample_draft():
    payload = {
        "category": "POTHOLE",
        "description": "Deep pothole causing traffic issues.",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }
    res = client.post("/api/v1/spotfix/complaints", json=payload)
    assert res.status_code == 201
    return res.json()


def test_get_complaint_for_review():
    draft = create_sample_draft()
    complaint_id = draft["id"]

    response = client.get(f"/api/v1/spotfix/complaints/{complaint_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == complaint_id
    assert data["status"] == "DRAFT"
    assert data["subject"] == "Complaint regarding pothole issue"
    assert "Deep pothole causing traffic issues" in data["complaint_text"]


def test_get_nonexistent_complaint_404():
    response = client.get("/api/v1/spotfix/complaints/non-existent-uuid")
    assert response.status_code == 404
    assert response.json()["detail"] == "Complaint not found."


def test_edit_complaint_draft():
    draft = create_sample_draft()
    complaint_id = draft["id"]

    update_payload = {
        "subject": "Urgent: Dangerous pothole near MG Road",
        "complaint_text": "Updated complaint text emphasizing immediate road safety hazard.",
    }

    response = client.patch(
        f"/api/v1/spotfix/complaints/{complaint_id}",
        json=update_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == complaint_id
    assert data["subject"] == "Urgent: Dangerous pothole near MG Road"
    assert data["complaint_text"] == "Updated complaint text emphasizing immediate road safety hazard."

    # Verify persistent retrieval
    get_res = client.get(f"/api/v1/spotfix/complaints/{complaint_id}")
    assert get_res.json()["subject"] == "Urgent: Dangerous pothole near MG Road"


def test_approve_complaint_draft():
    draft = create_sample_draft()
    complaint_id = draft["id"]

    response = client.post(f"/api/v1/spotfix/complaints/{complaint_id}/approve")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"

    # Verify status in database
    get_res = client.get(f"/api/v1/spotfix/complaints/{complaint_id}")
    assert get_res.json()["status"] == "APPROVED"


def test_rejection_of_unapproved_submission():
    draft = create_sample_draft()
    complaint_id = draft["id"]
    assert draft["status"] == "DRAFT"

    response = client.post(f"/api/v1/spotfix/complaints/{complaint_id}/submit")
    assert response.status_code == 400
    assert response.json()["detail"] == "Complaint must be approved before submission."


def test_correct_recipient_selection(monkeypatch):
    monkeypatch.setattr(
        settings,
        "official_email_mapping",
        {
            "BBMP:Road Infrastructure": "bbmp.road@example.com",
            "BBMP:Solid Waste Management": "bbmp.garbage@example.com",
            "BWSSB:Water Supply Maintenance": "bwssb.water@example.com",
            "BESCOM:Street Lighting": "bescom.light@example.com",
        },
    )
    monkeypatch.setattr(settings, "default_official_email", "civic.authority@example.com")

    assert (
        email_service.get_recipient_email("BBMP", "Road Infrastructure")
        == "bbmp.road@example.com"
    )
    assert (
        email_service.get_recipient_email("BBMP", "Solid Waste Management")
        == "bbmp.garbage@example.com"
    )
    assert (
        email_service.get_recipient_email("BWSSB", "Water Supply Maintenance")
        == "bwssb.water@example.com"
    )
    assert (
        email_service.get_recipient_email("BESCOM", "Street Lighting")
        == "bescom.light@example.com"
    )
    assert (
        email_service.get_recipient_email("UNKNOWN", "UNKNOWN")
        == "civic.authority@example.com"
    )


def test_successful_email_submission(monkeypatch):
    monkeypatch.setattr(
        settings,
        "official_email_mapping",
        {"BBMP:Road Infrastructure": "bbmp.road@example.com"},
    )
    draft = create_sample_draft()
    complaint_id = draft["id"]

    # Approve draft first
    app_res = client.post(f"/api/v1/spotfix/complaints/{complaint_id}/approve")
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "APPROVED"

    send_calls = []

    def mock_send_official_email(**kwargs):
        send_calls.append(kwargs)
        return {"id": "msg_123", "status": "sent"}

    monkeypatch.setattr(
        spotfix_endpoint.email_service,
        "send_official_email",
        mock_send_official_email,
    )

    response = client.post(f"/api/v1/spotfix/complaints/{complaint_id}/submit")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUBMITTED"
    assert data["submitted_at"] is not None
    assert data["recipient_email"] == "bbmp.road@example.com"

    assert len(send_calls) == 1
    assert send_calls[0]["complaint_id"] == complaint_id
    assert send_calls[0]["recipient_email"] == "bbmp.road@example.com"
    assert send_calls[0]["authority"] == "BBMP"
    assert send_calls[0]["department"] == "Road Infrastructure"


def test_email_failure_preserves_approved_status(monkeypatch):
    draft = create_sample_draft()
    complaint_id = draft["id"]

    # Approve draft
    client.post(f"/api/v1/spotfix/complaints/{complaint_id}/approve")

    def mock_send_email_fail(**kwargs):
        raise EmailDeliveryError("Provider service connection failure.")

    monkeypatch.setattr(
        spotfix_endpoint.email_service,
        "send_official_email",
        mock_send_email_fail,
    )

    response = client.post(f"/api/v1/spotfix/complaints/{complaint_id}/submit")
    assert response.status_code == 502
    assert "Provider service connection failure" in response.json()["detail"]

    # Verify complaint remains APPROVED and submitted_at is None
    get_res = client.get(f"/api/v1/spotfix/complaints/{complaint_id}")
    data = get_res.json()
    assert data["status"] == "APPROVED"
    assert data["submitted_at"] is None
    assert data["recipient_email"] is None


def test_status_transition_locks(monkeypatch):
    draft = create_sample_draft()
    complaint_id = draft["id"]

    # Approve and submit
    client.post(f"/api/v1/spotfix/complaints/{complaint_id}/approve")
    monkeypatch.setattr(
        spotfix_endpoint.email_service,
        "send_official_email",
        lambda **kwargs: {"id": "test"},
    )
    submit_res = client.post(f"/api/v1/spotfix/complaints/{complaint_id}/submit")
    assert submit_res.status_code == 200

    # Attempt to edit submitted complaint -> 400
    patch_res = client.patch(
        f"/api/v1/spotfix/complaints/{complaint_id}",
        json={"subject": "New Subject"},
    )
    assert patch_res.status_code == 400
    assert patch_res.json()["detail"] == "Submitted complaints cannot be edited."

    # Attempt to re-approve submitted complaint -> 400
    approve_res = client.post(f"/api/v1/spotfix/complaints/{complaint_id}/approve")
    assert approve_res.status_code == 400
    assert approve_res.json()["detail"] == "Submitted complaints cannot be approved again."

    # Attempt to re-submit submitted complaint -> 400
    resubmit_res = client.post(f"/api/v1/spotfix/complaints/{complaint_id}/submit")
    assert resubmit_res.status_code == 400
    assert resubmit_res.json()["detail"] == "Complaint has already been submitted."


def test_send_official_email_uses_configured_resend_from_email(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "re_test_key_123")
    monkeypatch.setattr(
        settings, "resend_from_email", "Onboarding <onboarding@resend.dev>"
    )

    posted_payloads = []

    def mock_httpx_post(url, headers=None, json=None, timeout=None):
        posted_payloads.append(json)

        class DummyResendResponse:
            status_code = 200

            def json(self):
                return {"id": "resend_msg_001"}

        return DummyResendResponse()

    monkeypatch.setattr("httpx.post", mock_httpx_post)

    result = email_service.send_official_email(
        complaint_id="c_test_001",
        subject="Test Subject",
        complaint_text="Test Details",
        authority="BBMP",
        department="Road Infrastructure",
    )

    assert result == {"id": "resend_msg_001"}
    assert len(posted_payloads) == 1
    assert posted_payloads[0]["from"] == "Onboarding <onboarding@resend.dev>"
