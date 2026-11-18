from io import BytesIO

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MIME_TO_PIL_FORMAT = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MIN_IMAGE_WIDTH = 50
MIN_IMAGE_HEIGHT = 50

# Extreme quality thresholds — carefully calibrated to avoid rejecting genuine civic evidence
MIN_MEAN_BRIGHTNESS = 5.0      # Below this is essentially pitch black
MAX_MEAN_BRIGHTNESS = 250.0    # Above this is completely overexposed/white
MIN_EDGE_VARIANCE = 6.0        # Edge sharpness variance below which image is severely blurred
MIN_CONTRAST_FOR_BLUR = 10.0   # Only evaluate blur when contrast indicates non-uniform scene


class ImageValidationError(ValueError):
    """Base validation error for uploaded images."""


class UnsupportedImageTypeError(ImageValidationError):
    """Raised when the file content type or underlying image format is not supported."""


class ImageTooLargeError(ImageValidationError):
    """Raised when the uploaded image exceeds the size limit."""


class InvalidImageFileError(ImageValidationError):
    """Raised when the uploaded bytes are not a valid or matching image."""


class ImageDimensionsTooSmallError(ImageValidationError):
    """Raised when the image dimensions are below the required minimum resolution."""


class ImageQualityError(ImageValidationError):
    """Raised when the image is extremely blurry, dark, or overexposed."""


def _validate_image_quality(img: Image.Image) -> None:
    """Validate image quality: check for extreme darkness, blowout, or extreme blur."""
    gray = img.convert("L")
    stat = ImageStat.Stat(gray)
    mean_val = stat.mean[0]
    std_val = stat.stddev[0]

    # Extreme darkness check
    if mean_val < MIN_MEAN_BRIGHTNESS:
        raise ImageQualityError("Image is too dark to discern visual evidence.")

    # Extreme overexposure / blowout check
    if mean_val > MAX_MEAN_BRIGHTNESS:
        raise ImageQualityError("Image is overexposed to discern visual evidence.")

    # Extreme blur check: only evaluate when contrast indicates non-uniform scene
    if std_val >= MIN_CONTRAST_FOR_BLUR and gray.width >= 10 and gray.height >= 10:
        edges = gray.filter(ImageFilter.FIND_EDGES).crop((2, 2, gray.width - 2, gray.height - 2))
        edge_var = ImageStat.Stat(edges).var[0]
        if edge_var < MIN_EDGE_VARIANCE:
            raise ImageQualityError("Image is too blurry to identify civic issues.")


def validate_image_upload(file_bytes: bytes, content_type: str | None) -> str:
    """Validate an uploaded image and return the extension for storage."""
    extension = ALLOWED_CONTENT_TYPES.get(content_type)

    if extension is None:
        raise UnsupportedImageTypeError("Only JPEG, PNG, and WebP images are allowed.")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise ImageTooLargeError("Image size must not exceed 10 MB.")

    try:
        with Image.open(BytesIO(file_bytes)) as verified_image:
            actual_format = verified_image.format
            if actual_format not in {"JPEG", "PNG", "WEBP"}:
                raise UnsupportedImageTypeError(
                    f"Unsupported image format: '{actual_format}'. Only JPEG, PNG, and WebP are allowed."
                )

            expected_format = MIME_TO_PIL_FORMAT.get(content_type)
            if expected_format is not None and actual_format != expected_format:
                raise InvalidImageFileError(
                    f"Image format '{actual_format}' does not match declared content type '{content_type}'."
                )

            verified_image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        if isinstance(exc, ImageValidationError):
            raise
        raise InvalidImageFileError("The uploaded file is not a valid image.") from exc

    # Inspect image dimensions and quality after verifying stream integrity
    try:
        with Image.open(BytesIO(file_bytes)) as img:
            img.load()
            width, height = img.size

            if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                raise ImageDimensionsTooSmallError(
                    f"Image dimensions ({width}x{height}) are too small. Minimum required is {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT}."
                )

            _validate_image_quality(img)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        if isinstance(exc, ImageValidationError):
            raise
        raise InvalidImageFileError("The uploaded file is not a valid image.") from exc

    return extension
