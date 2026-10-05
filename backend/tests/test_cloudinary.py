from pathlib import Path
import pytest

from app.core.config import settings
from app.services.cloudinary import CloudinaryService, CloudinaryUploadError
from app.services.storage.local import LocalStorageService

storage_service = LocalStorageService(Path("storage/spotfix"))
cloudinary_service = CloudinaryService()


def test_cloudinary_upload_success(monkeypatch):
    monkeypatch.setattr(settings, "cloudinary_cloud_name", "test_cloud")
    monkeypatch.setattr(settings, "cloudinary_api_key", "123456789")
    monkeypatch.setattr(settings, "cloudinary_api_secret", "secret_abc123")

    image_key = "test-cloudinary-image.jpg"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"\xff\xd8\xff\xe0fake_jpeg")

    upload_calls = []

    def mock_upload(file_path, resource_type=None, folder=None):
        upload_calls.append({"file_path": file_path, "resource_type": resource_type, "folder": folder})
        return {"secure_url": "https://res.cloudinary.com/test_cloud/image/upload/v12345/spotfix/test.jpg"}

    monkeypatch.setattr("cloudinary.uploader.upload", mock_upload)

    secure_url = cloudinary_service.upload_image(image_key)

    assert secure_url == "https://res.cloudinary.com/test_cloud/image/upload/v12345/spotfix/test.jpg"
    assert len(upload_calls) == 1
    assert upload_calls[0]["resource_type"] == "image"
    assert upload_calls[0]["folder"] == "spotfix"


def test_cloudinary_upload_missing_credentials(monkeypatch):
    monkeypatch.setattr(settings, "cloudinary_cloud_name", None)
    monkeypatch.setattr(settings, "cloudinary_api_key", None)
    monkeypatch.setattr(settings, "cloudinary_api_secret", None)

    with pytest.raises(CloudinaryUploadError) as exc_info:
        cloudinary_service.upload_image("any-key.jpg")

    assert "credentials not configured" in str(exc_info.value)


def test_cloudinary_upload_error_redacts_secret(monkeypatch):
    secret_key = "super_secret_cloudinary_key_xyz"
    monkeypatch.setattr(settings, "cloudinary_cloud_name", "test_cloud")
    monkeypatch.setattr(settings, "cloudinary_api_key", "123456789")
    monkeypatch.setattr(settings, "cloudinary_api_secret", secret_key)

    def mock_upload_fail(file_path, resource_type=None, folder=None):
        raise RuntimeError(f"Cloudinary error using secret {secret_key}")

    monkeypatch.setattr("cloudinary.uploader.upload", mock_upload_fail)

    image_key = "test-fail-image.jpg"
    storage_service.base_path.mkdir(parents=True, exist_ok=True)
    (storage_service.base_path / image_key).write_bytes(b"data")

    with pytest.raises(CloudinaryUploadError) as exc_info:
        cloudinary_service.upload_image(image_key)

    error_msg = str(exc_info.value)
    assert secret_key not in error_msg
    assert "[REDACTED_CLOUDINARY_SECRET]" in error_msg
