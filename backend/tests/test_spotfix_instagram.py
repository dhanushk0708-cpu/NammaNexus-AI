from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import io

from app.api.v1.endpoints import spotfix as spotfix_endpoint
from app.core.config import settings
from app.main import app
from app.models.complaint import Complaint
from app.services.cloudinary import CloudinaryUploadError
from app.services.instagram import InstagramPublishError, InstagramService
from app.services.storage.local import LocalStorageService


client = TestClient(app)
storage_service = LocalStorageService(Path("storage/spotfix"))
instagram_service = InstagramService()


def mock_cloudinary_success(image_source):
    return f"https://res.cloudinary.com/test_cloud/image/upload/v12345/spotfix/{Path(str(image_source)).name}"


def test_build_public_image_url():
    url = instagram_service.build_public_image_url("test-image-123.jpg")
    expected = f"{settings.public_base_url.rstrip('/')}/api/v1/spotfix/images/test-image-123.jpg"
    assert url == expected
    assert "localhost" not in url or settings.public_base_url.startswith("http://localhost")


def test_get_public_image_route():
    image_key = "test-public-route-image.jpg"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"fake-image-bytes")

    response = client.get(f"/api/v1/spotfix/images/{image_key}")
    assert response.status_code == 200
    assert response.content == b"fake-image-bytes"
    assert response.headers["content-type"].startswith("image/jpeg")


def test_get_public_image_not_found():
    response = client.get("/api/v1/spotfix/images/nonexistent-image.jpg")
    assert response.status_code == 404
    assert response.json()["detail"] == "Image not found."


def test_build_caption_content_and_privacy():
    complaint = Complaint(
        id="c1234567-89ab-cdef-0123-456789abcdef",
        category="POTHOLE",
        description="Private description containing Citizen Name John Doe 9999999999 john@example.com",
        latitude=12.9716,
        longitude=77.5946,
        confidence=0.92,
        severity="HIGH",
        visual_explanation="Severe crater across the road.",
        impact_score=85,
        priority="CRITICAL",
        impact_reason="Dangerous road safety hazard.",
        authority="BBMP",
        department="Road Infrastructure",
        subject="Public Pothole Subject",
        complaint_text="Public Complaint Text",
    )

    caption = instagram_service.build_caption(complaint)

    # Verify required metadata present
    assert "Category: POTHOLE" in caption
    assert "Severity: HIGH" in caption
    assert "Confidence: 92%" in caption
    assert "Impact Score: 85/100" in caption
    assert "Priority: CRITICAL" in caption
    assert "Authority: BBMP" in caption
    assert "Department: Road Infrastructure" in caption
    assert "Location: 12.9716, 77.5946" in caption
    assert "Impact Assessment: Dangerous road safety hazard." in caption
    assert "Visual Details: Severe crater across the road." in caption
    assert "#NammaNexus" in caption
    assert "#SpotFix" in caption

    # Verify private citizen info is NOT in caption
    assert "John Doe" not in caption
    assert "9999999999" not in caption
    assert "john@example.com" not in caption
    assert "Private description" not in caption


def test_instagram_publish_success(monkeypatch):
    monkeypatch.setattr(settings, "instagram_access_token", "fake_secret_token_123")
    monkeypatch.setattr(settings, "instagram_account_id", "17841400000000000")
    monkeypatch.setattr(instagram_service.cloudinary_service, "upload_image", mock_cloudinary_success)

    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    dummy_img = Image.new("RGB", (10, 10), color=(0, 255, 0))
    buf = io.BytesIO()
    dummy_img.save(buf, format="JPEG")
    (storage_service.base_path / "test-image.jpg").write_bytes(buf.getvalue())

    complaint = Complaint(
        id="c1234567-89ab-cdef-0123-456789abcdef",
        category="POTHOLE",
        image_storage_key="test-image.jpg",
        latitude=12.9716,
        longitude=77.5946,
        confidence=0.9,
        severity="HIGH",
        impact_score=80,
        priority="HIGH",
        authority="BBMP",
        department="Road Infrastructure",
    )

    http_calls = []

    def mock_httpx_post(url, data=None, timeout=None):
        http_calls.append({"url": url, "data": data})
        if "/media_publish" in url:
            return DummyResponse(200, {"id": "18000000000000000"})
        return DummyResponse(200, {"id": "17900000000000000"})

    class DummyResponse:
        def __init__(self, status_code, json_data, text=""):
            self.status_code = status_code
            self._json_data = json_data
            self.text = text or str(json_data)

        def json(self):
            return self._json_data

    monkeypatch.setattr("httpx.post", mock_httpx_post)

    post_id = instagram_service.publish_complaint(complaint)

    assert post_id == "18000000000000000"
    assert len(http_calls) == 2
    assert "17841400000000000/media" in http_calls[0]["url"]
    assert "https://res.cloudinary.com/test_cloud/image/upload" in http_calls[0]["data"]["image_url"]
    assert "media_type" not in http_calls[0]["data"]
    assert set(http_calls[0]["data"].keys()) == {"image_url", "caption", "access_token"}
    assert http_calls[0]["data"]["access_token"] == "fake_secret_token_123"
    assert "17841400000000000/media_publish" in http_calls[1]["url"]
    assert http_calls[1]["data"]["creation_id"] == "17900000000000000"


def test_instagram_publish_api_failure_does_not_leak_token(monkeypatch):
    secret_token = "super_secret_access_token_abc123"
    monkeypatch.setattr(settings, "instagram_access_token", secret_token)
    monkeypatch.setattr(settings, "instagram_account_id", "17841400000000000")
    monkeypatch.setattr(instagram_service.cloudinary_service, "upload_image", mock_cloudinary_success)

    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    dummy_img = Image.new("RGB", (10, 10), color=(0, 255, 0))
    buf = io.BytesIO()
    dummy_img.save(buf, format="JPEG")
    (storage_service.base_path / "test-image.jpg").write_bytes(buf.getvalue())

    complaint = Complaint(
        id="c1234567-89ab-cdef-0123-456789abcdef",
        category="GARBAGE",
        image_storage_key="test-image.jpg",
    )

    class DummyFailResponse:
        status_code = 400
        text = f"Invalid OAuth access token {secret_token} provided."

        def json(self):
            return {"error": {"message": f"Invalid token {secret_token}"}}

    def mock_httpx_post_fail(url, data=None, timeout=None):
        return DummyFailResponse()

    monkeypatch.setattr("httpx.post", mock_httpx_post_fail)

    with pytest.raises(InstagramPublishError) as exc_info:
        instagram_service.publish_complaint(complaint)

    error_str = str(exc_info.value)
    assert secret_token not in error_str
    assert "[REDACTED_ACCESS_TOKEN]" in error_str


def test_submission_triggers_instagram_publish(monkeypatch):
    monkeypatch.setattr(settings, "instagram_access_token", "fake_token")
    monkeypatch.setattr(settings, "instagram_account_id", "fake_account_id")

    payload = {
        "category": "GARBAGE",
        "description": "Garbage near community center.",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }
    create_res = client.post("/api/v1/spotfix/complaints", json=payload)
    complaint_id = create_res.json()["id"]

    # Approve draft
    client.post(f"/api/v1/spotfix/complaints/{complaint_id}/approve")

    # Mock email sending
    monkeypatch.setattr(
        spotfix_endpoint.email_service,
        "send_official_email",
        lambda **kwargs: {"id": "email_123"},
    )

    # Mock instagram publishing
    publish_calls = []

    def mock_publish(complaint):
        publish_calls.append(complaint.id)
        return "ig_post_9999"

    monkeypatch.setattr(
        spotfix_endpoint.instagram_service,
        "publish_complaint",
        mock_publish,
    )

    submit_res = client.post(f"/api/v1/spotfix/complaints/{complaint_id}/submit")
    assert submit_res.status_code == 200
    data = submit_res.json()
    assert data["status"] == "SUBMITTED"
    assert data["instagram_post_id"] == "ig_post_9999"
    assert len(publish_calls) == 1
    assert publish_calls[0] == complaint_id


def test_instagram_publish_uses_cloudinary_cdn(monkeypatch):
    test_token = "EAAB123456789_real_config_test_token"
    test_account_id = "17841435003778735"

    monkeypatch.setattr(settings, "instagram_access_token", test_token)
    monkeypatch.setattr(settings, "instagram_account_id", test_account_id)
    monkeypatch.setattr(instagram_service.cloudinary_service, "upload_image", mock_cloudinary_success)

    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    dummy_img = Image.new("RGB", (10, 10), color=(0, 255, 0))
    buf = io.BytesIO()
    dummy_img.save(buf, format="JPEG")
    (storage_service.base_path / "test-spotfix-image.jpg").write_bytes(buf.getvalue())

    complaint = Complaint(
        id="c1234567-89ab-cdef-0123-456789abcdef",
        category="POTHOLE",
        image_storage_key="test-spotfix-image.jpg",
        latitude=12.9716,
        longitude=77.5946,
        confidence=0.95,
        severity="CRITICAL",
        impact_score=90,
        priority="CRITICAL",
        authority="BBMP",
        department="Road Infrastructure",
    )

    posted_requests = []

    def mock_httpx_post(url, data=None, timeout=None):
        posted_requests.append({"url": url, "data": data})
        if "/media_publish" in url:
            return DummyResponse(200, {"id": "18999999999999999"})
        return DummyResponse(200, {"id": "17999999999999999"})

    class DummyResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data
            self.text = str(json_data)

        def json(self):
            return self._json_data

    monkeypatch.setattr("httpx.post", mock_httpx_post)

    post_id = instagram_service.publish_complaint(complaint)

    assert post_id == "18999999999999999"
    assert len(posted_requests) == 2
    assert f"https://graph.instagram.com/v19.0/{test_account_id}/media" == posted_requests[0]["url"]
    assert "https://res.cloudinary.com/test_cloud/image/upload" in posted_requests[0]["data"]["image_url"]
    assert "ngrok" not in posted_requests[0]["data"]["image_url"]
    assert set(posted_requests[0]["data"].keys()) == {"image_url", "caption", "access_token"}


def test_cloudinary_failure_is_handled_and_non_blocking(monkeypatch):
    monkeypatch.setattr(settings, "instagram_access_token", "fake_token")
    monkeypatch.setattr(settings, "instagram_account_id", "fake_account_id")

    def mock_cloudinary_fail(image_source):
        raise CloudinaryUploadError("Cloudinary upload failed: API key invalid")

    monkeypatch.setattr(instagram_service.cloudinary_service, "upload_image", mock_cloudinary_fail)

    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    dummy_img = Image.new("RGB", (10, 10), color=(0, 255, 0))
    buf = io.BytesIO()
    dummy_img.save(buf, format="JPEG")
    (storage_service.base_path / "test-fail-image.jpg").write_bytes(buf.getvalue())

    complaint = Complaint(
        id="c-fail-12345",
        category="POTHOLE",
        image_storage_key="test-fail-image.jpg",
    )

    with pytest.raises(InstagramPublishError) as exc_info:
        instagram_service.publish_complaint(complaint)

    assert "Cloudinary upload failed" in str(exc_info.value)
