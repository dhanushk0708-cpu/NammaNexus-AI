from io import BytesIO

import pytest
from PIL import Image, ImageFilter

from app.services.image_validation import (
    ImageDimensionsTooSmallError,
    ImageQualityError,
    ImageTooLargeError,
    InvalidImageFileError,
    UnsupportedImageTypeError,
    validate_image_upload,
)


def _make_image_bytes(
    image_format: str,
    size: tuple[int, int] = (100, 100),
    color: tuple[int, int, int] | str = "blue",
) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color=color).save(buffer, format=image_format)
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
    payload = _make_image_bytes(image_format, size=(100, 100))
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


def test_validate_image_upload_rejects_format_mismatch():
    png_bytes = _make_image_bytes("PNG", size=(100, 100))
    with pytest.raises(InvalidImageFileError, match="does not match declared content type"):
        validate_image_upload(png_bytes, "image/jpeg")


def test_validate_image_upload_rejects_small_dimensions():
    small_payload = _make_image_bytes("JPEG", size=(30, 30))
    with pytest.raises(ImageDimensionsTooSmallError, match="too small"):
        validate_image_upload(small_payload, "image/jpeg")


def test_validate_image_upload_rejects_pitch_black_image():
    dark_payload = _make_image_bytes("JPEG", size=(100, 100), color=(1, 1, 1))
    with pytest.raises(ImageQualityError, match="too dark"):
        validate_image_upload(dark_payload, "image/jpeg")


def test_validate_image_upload_rejects_overexposed_image():
    white_payload = _make_image_bytes("JPEG", size=(100, 100), color=(254, 254, 254))
    with pytest.raises(ImageQualityError, match="overexposed"):
        validate_image_upload(white_payload, "image/jpeg")


def test_validate_image_upload_rejects_extremely_blurry_image():
    sharp = Image.new("RGB", (100, 100), (0, 0, 0))
    for x in range(50, 100):
        for y in range(0, 100):
            sharp.putpixel((x, y), (255, 255, 255))

    blurred = sharp.filter(ImageFilter.GaussianBlur(radius=20))
    buf = BytesIO()
    blurred.save(buf, format="JPEG")
    blurry_payload = buf.getvalue()

    with pytest.raises(ImageQualityError, match="too blurry"):
        validate_image_upload(blurry_payload, "image/jpeg")
