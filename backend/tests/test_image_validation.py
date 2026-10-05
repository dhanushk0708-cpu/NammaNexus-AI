from io import BytesIO

import pytest
from PIL import Image

from app.services.image_validation import (
    ImageTooLargeError,
    InvalidImageFileError,
    UnsupportedImageTypeError,
    validate_image_upload,
)


def _make_image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format=image_format)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "content_type, image_format, expected_extension",
    [
        ("image/jpeg", "JPEG", ".jpg"),
        ("image/png", "PNG", ".png"),
        ("image/webp", "WEBP", ".webp"),
    ],
)
def test_validate_image_upload_accepts_supported_types(
    content_type, image_format, expected_extension
):
    payload = _make_image_bytes(image_format)
    result = validate_image_upload(payload, content_type)
    assert result == expected_extension


def test_validate_image_upload_rejects_unsupported_content_type():
    with pytest.raises(UnsupportedImageTypeError):
        validate_image_upload(b"not-an-image", "image/gif")


def test_validate_image_upload_rejects_large_files():
    large_payload = b"a" * (10 * 1024 * 1024 + 1)
    with pytest.raises(ImageTooLargeError):
        validate_image_upload(large_payload, "image/jpeg")


def test_validate_image_upload_rejects_corrupted_image_bytes():
    with pytest.raises(InvalidImageFileError):
        validate_image_upload(b"this is not an image", "image/jpeg")
