from io import BytesIO

from PIL import Image, UnidentifiedImageError

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


class ImageValidationError(ValueError):
    """Base validation error for uploaded images."""


class UnsupportedImageTypeError(ImageValidationError):
    """Raised when the file content type is not supported."""


class ImageTooLargeError(ImageValidationError):
    """Raised when the uploaded image exceeds the size limit."""


class InvalidImageFileError(ImageValidationError):
    """Raised when the uploaded bytes are not a valid image."""


def validate_image_upload(file_bytes: bytes, content_type: str | None) -> str:
    """Validate an uploaded image and return the extension for storage."""
    extension = ALLOWED_CONTENT_TYPES.get(content_type)

    if extension is None:
        raise UnsupportedImageTypeError("Only JPEG, PNG, and WebP images are allowed.")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise ImageTooLargeError("Image size must not exceed 10 MB.")

    try:
        with Image.open(BytesIO(file_bytes)) as verified_image:
            verified_image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise InvalidImageFileError("The uploaded file is not a valid image.")

    return extension
