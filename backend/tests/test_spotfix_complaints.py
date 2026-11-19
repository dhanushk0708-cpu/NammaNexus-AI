from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import spotfix as spotfix_endpoint
from app.db.session import SessionLocal
from app.main import app
from app.models.complaint import Complaint
from app.schemas.ai import (
    ComplaintWriterResult,
    PredictiveImpactResult,
    RoutingResult,
    SpotFixImageAnalysisResult,
    ValidationStatus,
)
from app.services.gemini_vision import (
    GeminiResponseValidationError,
    GeminiVisionServiceError,
)
from app.services.storage.local import (
    LocalStorageService,
    StorageKeyNotFoundError,
    StorageKeyValidationError,
)


client = TestClient(app)
storage_service = LocalStorageService(Path("storage/spotfix"))


def test_create_complaint_draft_without_image_storage_key():
    payload = {
        "category": "POTHOLE",
        "description": "Large pothole near the bus stop.",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }

    response = client.post("/api/v1/spotfix/complaints", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "DRAFT"
    assert data["category"] == "POTHOLE"
    assert data["description"] == "Large pothole near the bus stop."
    assert data["latitude"] == 12.9716
    assert data["longitude"] == 77.5946
    assert data["image_storage_key"] is None
    assert data["impact_score"] is not None
    assert data["priority"] is not None
    assert data["impact_reason"]
    assert data["authority"] == "BBMP"
    assert data["department"] == "Road Infrastructure"
    assert data["routing_reason"]
    assert data["subject"] == "Complaint regarding pothole issue"
    assert data["complaint_text"]
    assert data["id"]


def test_create_complaint_draft_forces_draft_status():
    payload = {
        "category": "POTHOLE",
        "description": "Client attempted to set another status.",
        "status": "SUBMITTED",
    }

    response = client.post("/api/v1/spotfix/complaints", json=payload)

    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"


def test_create_complaint_draft_with_existing_image_storage_key(monkeypatch):
    analysis = SpotFixImageAnalysisResult(
        category="GARBAGE",
        confidence=0.81,
        severity="MEDIUM",
        visual_explanation="Overflowing bins along the roadside.",
    )

    monkeypatch.setattr(
        spotfix_endpoint.GeminiVisionService,
        "analyze_image",
        lambda self, image_bytes, mime_type=None: analysis,
    )

    image_key = "existing-upload-test.png"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"fake image bytes")

    payload = {
        "category": "GARBAGE",
        "description": "Overflowing bins.",
        "image_storage_key": image_key,
    }

    response = client.post("/api/v1/spotfix/complaints", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["image_storage_key"] == image_key
    assert data["status"] == "DRAFT"
    assert data["category"] == "GARBAGE"
    assert data["confidence"] == 0.81
    assert data["severity"] == "MEDIUM"
    assert data["visual_explanation"] == "Overflowing bins along the roadside."
    assert data["authority"] == "BBMP"
    assert data["department"] == "Solid Waste Management"
    assert data["routing_reason"]
    assert data["subject"] == "Complaint regarding garbage/waste issue"
    assert data["complaint_text"]


def test_create_complaint_draft_with_nonexistent_image_storage_key():
    payload = {
        "category": "WATER_LEAKAGE",
        "description": "Leakage near the lane.",
        "image_storage_key": "missing-image.png",
    }

    response = client.post("/api/v1/spotfix/complaints", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Referenced image does not exist."


def test_create_complaint_draft_with_invalid_storage_key():
    payload = {
        "category": "POTHOLE",
        "description": "Unsafe path.",
        "image_storage_key": "../secret.txt",
    }

    response = client.post("/api/v1/spotfix/complaints", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid storage key."


def test_storage_read_existing_image_success():
    image_key = "read-existing-test.png"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"stored image bytes")

    assert storage_service.read_image(image_key) == b"stored image bytes"


def test_storage_read_missing_image_raises():
    with pytest.raises(
        StorageKeyNotFoundError, match="Referenced image does not exist."
    ):
        storage_service.read_image("missing-image.png")


def test_storage_read_unsafe_key_raises():
    with pytest.raises(StorageKeyValidationError, match="Invalid storage key."):
        storage_service.read_image("../secret.txt")


def test_create_complaint_draft_uses_ai_for_category_and_persistence(
    monkeypatch,
):
    call_log = {}
    analysis = SpotFixImageAnalysisResult(
        category="POTHOLE",
        confidence=0.94,
        severity="HIGH",
        visual_explanation="Large pothole across the lane.",
    )
    impact = PredictiveImpactResult(
        impact_score=73,
        priority="HIGH",
        impact_reason="Calculated HIGH priority (score 73/100) based on severity HIGH.",
    )
    routing = RoutingResult(
        authority="BBMP",
        department="Road Infrastructure",
        routing_reason="Pothole-related road issue routed to BBMP road infrastructure.",
    )
    draft = ComplaintWriterResult(
        subject="Complaint regarding pothole issue",
        complaint_text="Template complaint draft for citizen review.",
    )

    monkeypatch.setattr(
        spotfix_endpoint.GeminiVisionService,
        "analyze_image",
        lambda self, image_bytes, mime_type=None: analysis,
    )

    def fake_calculate_predictive_impact(**kwargs):
        call_log["impact_args"] = kwargs
        return impact

    def fake_route_complaint(**kwargs):
        call_log["routing_args"] = kwargs
        return routing

    def fake_write_complaint_draft(**kwargs):
        call_log["writer_args"] = kwargs
        return draft

    monkeypatch.setattr(
        spotfix_endpoint,
        "calculate_predictive_impact",
        fake_calculate_predictive_impact,
    )
    monkeypatch.setattr(
        spotfix_endpoint,
        "route_complaint",
        fake_route_complaint,
    )
    monkeypatch.setattr(
        spotfix_endpoint,
        "write_complaint_draft",
        fake_write_complaint_draft,
    )

    image_key = "ai-assisted-test.png"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"stored-image-bytes")

    payload = {
        "category": "GARBAGE",
        "description": "Initial description from user.",
        "image_storage_key": image_key,
        "latitude": 12.9716,
        "longitude": 77.5946,
    }

    response = client.post("/api/v1/spotfix/complaints", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "DRAFT"
    assert data["category"] == "POTHOLE"
    assert data["description"] == "Initial description from user."
    assert data["confidence"] == 0.94
    assert data["severity"] == "HIGH"
    assert data["visual_explanation"] == "Large pothole across the lane."
    assert data["image_storage_key"] == image_key
    assert data["impact_score"] == 73
    assert data["priority"] == "HIGH"
    assert data["impact_reason"] == impact.impact_reason
    assert data["authority"] == "BBMP"
    assert data["department"] == "Road Infrastructure"
    assert data["routing_reason"] == routing.routing_reason
    assert data["subject"] == draft.subject
    assert data["complaint_text"] == draft.complaint_text
    assert call_log["impact_args"] == {
        "severity": analysis.severity,
        "confidence": analysis.confidence,
        "category": analysis.category,
        "latitude": 12.9716,
        "longitude": 77.5946,
    }
    assert call_log["routing_args"] == {
        "category": analysis.category,
        "severity": analysis.severity,
        "priority": impact.priority,
        "impact_score": impact.impact_score,
        "latitude": 12.9716,
        "longitude": 77.5946,
    }
    assert call_log["writer_args"] == {
        "category": analysis.category,
        "description": "Initial description from user.",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "severity": analysis.severity,
        "confidence": analysis.confidence,
        "visual_explanation": analysis.visual_explanation,
        "impact_score": impact.impact_score,
        "priority": impact.priority,
        "impact_reason": impact.impact_reason,
        "authority": routing.authority,
        "department": routing.department,
        "routing_reason": routing.routing_reason,
    }


def test_create_complaint_draft_with_gemini_validation_failure(monkeypatch):
    def fake_analyze(self, image_bytes, *, mime_type=None):
        raise GeminiResponseValidationError("AI response failed schema validation.")

    monkeypatch.setattr(
        spotfix_endpoint.GeminiVisionService,
        "analyze_image",
        fake_analyze,
    )

    image_key = "ai-failure-test.png"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"stored-image-bytes")

    response = client.post(
        "/api/v1/spotfix/complaints",
        json={
            "description": "This should fail in AI analysis.",
            "image_storage_key": image_key,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "AI response failed schema validation."


def test_create_complaint_draft_validation_error():
    response = client.post(
        "/api/v1/spotfix/complaints",
        json={
            "latitude": 100,
            "longitude": -200,
        },
    )

    assert response.status_code == 422


def test_create_complaint_draft_rejected_normal_road_no_db_record(monkeypatch):
    analysis = SpotFixImageAnalysisResult(
        validation_status=ValidationStatus.REJECTED,
        is_civic_issue=False,
        category=None,
        confidence=0.96,
        severity=None,
        visual_explanation="Clear asphalt roadway with no civic defects.",
        rejection_reason="No civic issue detected. Road in good condition.",
    )

    monkeypatch.setattr(
        spotfix_endpoint.GeminiVisionService,
        "analyze_image",
        lambda self, image_bytes, mime_type=None: analysis,
    )

    image_key = "normal-road-test.png"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"normal-road-bytes")

    db = SessionLocal()
    count_before = db.query(Complaint).count()
    db.close()

    response = client.post(
        "/api/v1/spotfix/complaints",
        json={
            "description": "Submitting a road photo.",
            "image_storage_key": image_key,
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "IMAGE_REJECTED"
    assert detail["validation_status"] == "REJECTED"
    assert detail["is_civic_issue"] is False
    assert detail["category"] is None
    assert detail["severity"] is None
    assert "No civic issue detected" in detail["rejection_reason"]

    db = SessionLocal()
    count_after = db.query(Complaint).count()
    db.close()
    assert count_after == count_before


def test_create_complaint_draft_rejected_unsupported_category_no_db_record(monkeypatch):
    analysis = SpotFixImageAnalysisResult(
        validation_status=ValidationStatus.REJECTED,
        is_civic_issue=False,
        category=None,
        confidence=0.91,
        severity=None,
        visual_explanation="Car illegally parked on public walkway.",
        rejection_reason="Unsupported issue: illegal parking is not covered by SpotFix.",
    )

    monkeypatch.setattr(
        spotfix_endpoint.GeminiVisionService,
        "analyze_image",
        lambda self, image_bytes, mime_type=None: analysis,
    )

    image_key = "unsupported-issue-test.png"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"unsupported-issue-bytes")

    db = SessionLocal()
    count_before = db.query(Complaint).count()
    db.close()

    response = client.post(
        "/api/v1/spotfix/complaints",
        json={
            "description": "Illegal parking complaint.",
            "image_storage_key": image_key,
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "IMAGE_REJECTED"
    assert detail["validation_status"] == "REJECTED"
    assert detail["is_civic_issue"] is False
    assert "illegal parking" in detail["rejection_reason"]

    db = SessionLocal()
    count_after = db.query(Complaint).count()
    db.close()
    assert count_after == count_before


def test_create_complaint_draft_unclear_image_no_db_record(monkeypatch):
    analysis = SpotFixImageAnalysisResult(
        validation_status=ValidationStatus.UNCLEAR,
        is_civic_issue=False,
        category=None,
        confidence=0.20,
        severity=None,
        visual_explanation="Extreme blur makes road condition indiscernible.",
        rejection_reason="Image quality is insufficient to verify a civic issue.",
    )

    monkeypatch.setattr(
        spotfix_endpoint.GeminiVisionService,
        "analyze_image",
        lambda self, image_bytes, mime_type=None: analysis,
    )

    image_key = "unclear-blur-test.png"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"blurry-bytes")

    db = SessionLocal()
    count_before = db.query(Complaint).count()
    db.close()

    response = client.post(
        "/api/v1/spotfix/complaints",
        json={
            "description": "Blurry pothole photo.",
            "image_storage_key": image_key,
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "IMAGE_UNCLEAR"
    assert detail["validation_status"] == "UNCLEAR"
    assert detail["is_civic_issue"] is False
    assert "Image quality is insufficient" in detail["rejection_reason"]

    db = SessionLocal()
    count_after = db.query(Complaint).count()
    db.close()
    assert count_after == count_before


def test_create_complaint_draft_gemini_api_failure_fails_safely_no_db_record(monkeypatch):
    def fake_analyze(self, image_bytes, *, mime_type=None):
        raise GeminiVisionServiceError("Gemini API call timed out.")

    monkeypatch.setattr(
        spotfix_endpoint.GeminiVisionService,
        "analyze_image",
        fake_analyze,
    )

    image_key = "gemini-failure-test.png"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"image-bytes")

    db = SessionLocal()
    count_before = db.query(Complaint).count()
    db.close()

    response = client.post(
        "/api/v1/spotfix/complaints",
        json={
            "description": "Attempt complaint while Gemini is down.",
            "image_storage_key": image_key,
        },
    )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()

    db = SessionLocal()
    count_after = db.query(Complaint).count()
    db.close()
    assert count_after == count_before


def test_create_complaint_draft_genuine_low_severity_issue_succeeds(monkeypatch):
    analysis = SpotFixImageAnalysisResult(
        validation_status=ValidationStatus.ACCEPTED,
        is_civic_issue=True,
        category="POTHOLE",
        confidence=0.35,
        severity="LOW",
        visual_explanation="Small shallow road surface wearing on side of road.",
    )

    monkeypatch.setattr(
        spotfix_endpoint.GeminiVisionService,
        "analyze_image",
        lambda self, image_bytes, mime_type=None: analysis,
    )

    image_key = "low-severity-test.png"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"low-severity-bytes")

    response = client.post(
        "/api/v1/spotfix/complaints",
        json={
            "description": "Minor surface wear.",
            "image_storage_key": image_key,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "DRAFT"
    assert data["category"] == "POTHOLE"
    assert data["severity"] == "LOW"
    assert data["confidence"] == 0.35
    assert data["id"] is not None
