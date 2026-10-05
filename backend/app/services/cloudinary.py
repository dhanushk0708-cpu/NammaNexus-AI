from __future__ import annotations

import logging
from pathlib import Path
import cloudinary
import cloudinary.uploader

from app.core.config import settings
from app.services.storage.local import LocalStorageService

logger = logging.getLogger(__name__)


class CloudinaryUploadError(Exception):
    """Raised when uploading an image to Cloudinary fails."""

    pass


class CloudinaryService:
    def upload_image(self, image_source: str | Path | bytes) -> str:
        """Uploads a local image file or bytes to Cloudinary with resource_type='image'

        and returns the HTTPS secure_url. Never logs API secrets.
        """
        cloud_name = settings.cloudinary_cloud_name
        api_key = settings.cloudinary_api_key
        api_secret = settings.cloudinary_api_secret

        if not cloud_name or not api_key or not api_secret:
            logger.warning("Cloudinary credentials not fully configured.")
            raise CloudinaryUploadError("Cloudinary credentials not configured.")

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

        try:
            if isinstance(image_source, str):
                storage_service = LocalStorageService(Path("storage/spotfix"))
                file_path = str(storage_service.get_path(image_source))
            elif isinstance(image_source, Path):
                file_path = str(image_source)
            else:
                file_path = image_source

            res = cloudinary.uploader.upload(
                file_path,
                resource_type="image",
                folder="spotfix",
            )

            secure_url = res.get("secure_url")
            if not secure_url:
                raise CloudinaryUploadError("Cloudinary upload response missing secure_url.")

            return secure_url

        except Exception as exc:
            err_text = self._sanitize_log(str(exc), api_secret)
            raise CloudinaryUploadError(f"Cloudinary upload failed: {err_text}") from exc

    def _sanitize_log(self, message: str, secret: str | None) -> str:
        if secret and secret in message:
            return message.replace(secret, "[REDACTED_CLOUDINARY_SECRET]")
        return message
