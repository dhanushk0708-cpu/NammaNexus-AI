from __future__ import annotations

import io
import logging
from pathlib import Path
import httpx
from PIL import Image

from app.core.config import settings
from app.models.complaint import Complaint
from app.services.cloudinary import CloudinaryService, CloudinaryUploadError
from app.services.storage.local import LocalStorageService

logger = logging.getLogger(__name__)


class InstagramPublishError(Exception):
    """Raised when publishing a complaint to Instagram fails."""

    pass


class InstagramService:
    def __init__(self, cloudinary_service: CloudinaryService | None = None) -> None:
        self.cloudinary_service = cloudinary_service or CloudinaryService()

    def build_public_image_url(self, image_key: str) -> str:
        base_url = settings.public_base_url.rstrip("/")
        return f"{base_url}/api/v1/spotfix/images/{image_key}"

    def normalize_image_for_instagram(self, image_storage_key: str) -> str:
        """Reads stored image bytes, converts to RGB JPEG with quality=90 and optimize=True,

        stores the re-encoded file as ig_<key_stem>.jpg, and returns the new storage key.
        The original citizen upload is preserved untouched.
        """
        storage_service = LocalStorageService(Path("storage/spotfix"))
        raw_bytes = storage_service.read_image(image_storage_key)

        with Image.open(io.BytesIO(raw_bytes)) as img:
            rgb_img = img.convert("RGB")
            out_buf = io.BytesIO()
            rgb_img.save(out_buf, format="JPEG", quality=90, optimize=True)
            normalized_bytes = out_buf.getvalue()

        stem = Path(image_storage_key).stem
        normalized_key = f"ig_{stem}.jpg"
        target_path = storage_service.get_path(normalized_key)
        target_path.write_bytes(normalized_bytes)

        return normalized_key

    def build_caption(self, complaint: Complaint) -> str:
        confidence_str = (
            f"{int(complaint.confidence * 100)}%"
            if complaint.confidence is not None
            else "N/A"
        )
        lat_str = f"{complaint.latitude:.4f}" if complaint.latitude is not None else "N/A"
        lng_str = f"{complaint.longitude:.4f}" if complaint.longitude is not None else "N/A"

        lines = [
            "🚨 NAMMANEXUS SPOTFIX CIVIC ALERT",
            f"Category: {complaint.category or 'N/A'}",
            f"Severity: {complaint.severity or 'N/A'}",
            f"Confidence: {confidence_str}",
            f"Impact Score: {complaint.impact_score if complaint.impact_score is not None else 'N/A'}/100",
            f"Priority: {complaint.priority or 'N/A'}",
            f"Authority: {complaint.authority or 'N/A'}",
            f"Department: {complaint.department or 'N/A'}",
            f"Location: {lat_str}, {lng_str}",
        ]

        if complaint.impact_reason:
            lines.append(f"Impact Assessment: {complaint.impact_reason}")
        if complaint.visual_explanation:
            lines.append(f"Visual Details: {complaint.visual_explanation}")

        hashtags = [
            "#NammaNexus",
            "#SpotFix",
            "#BengaluruCivic",
            f"#{complaint.authority or 'Civic'}",
            "#CivicIntelligence",
            "#Bengaluru",
        ]
        lines.append("")
        lines.append(" ".join(hashtags))

        return "\n".join(lines)

    def publish_complaint(self, complaint: Complaint) -> str | None:
        if not complaint.image_storage_key:
            logger.warning("Complaint %s has no image; skipping Instagram publish.", complaint.id)
            return None

        token = settings.instagram_access_token
        account_id = settings.instagram_account_id

        if not token or not account_id:
            logger.warning("Instagram API credentials not configured; skipping publish.")
            raise InstagramPublishError("Instagram credentials not configured.")

        # 1. Normalize intake image into clean RGB JPEG
        try:
            normalized_key = self.normalize_image_for_instagram(complaint.image_storage_key)
        except Exception as exc:
            logger.warning("Failed to normalize image for complaint %s: %s", complaint.id, exc)
            normalized_key = complaint.image_storage_key

        # 2. Upload normalized JPEG to Cloudinary CDN for Instagram publishing
        try:
            image_url = self.cloudinary_service.upload_image(normalized_key)
        except CloudinaryUploadError as exc:
            logger.warning("Cloudinary upload failed for complaint %s: %s", complaint.id, exc)
            raise InstagramPublishError(f"Cloudinary upload failed: {exc}") from exc

        caption = self.build_caption(complaint)

        try:
            # Step 1: Create media container using Cloudinary CDN secure_url
            container_res = httpx.post(
                f"https://graph.instagram.com/v19.0/{account_id}/media",
                data={
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": token,
                },
                timeout=15.0,
            )

            if container_res.status_code not in (200, 201):
                err_text = self._sanitize_log(container_res.text, token)
                raise InstagramPublishError(
                    f"Instagram media container creation failed (status {container_res.status_code}): {err_text}"
                )

            container_data = container_res.json()
            creation_id = container_data.get("id")
            if not creation_id:
                raise InstagramPublishError("Instagram media container response missing creation ID.")

            # Step 2: Publish media container
            publish_res = httpx.post(
                f"https://graph.instagram.com/v19.0/{account_id}/media_publish",
                data={
                    "creation_id": creation_id,
                    "access_token": token,
                },
                timeout=15.0,
            )

            if publish_res.status_code not in (200, 201):
                err_text = self._sanitize_log(publish_res.text, token)
                raise InstagramPublishError(
                    f"Instagram media publish failed (status {publish_res.status_code}): {err_text}"
                )

            publish_data = publish_res.json()
            post_id = publish_data.get("id")
            if not post_id:
                raise InstagramPublishError("Instagram publish response missing post ID.")

            return post_id

        except httpx.RequestError as exc:
            err_msg = self._sanitize_log(str(exc), token)
            raise InstagramPublishError(
                f"Network error communicating with Meta Instagram API: {err_msg}"
            ) from exc

    def _sanitize_log(self, message: str, token: str | None) -> str:
        if token and token in message:
            return message.replace(token, "[REDACTED_ACCESS_TOKEN]")
        return message
