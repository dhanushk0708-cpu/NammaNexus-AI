from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import logging
from typing import Any

from app.schemas.civicvoice import NormalizedSourceRecord

logger = logging.getLogger(__name__)


def compute_dedup_key(provider: str, external_id: str | None, url: str) -> str:
    """Computes a deterministic, collision-free SHA-256 deduplication key.

    Uses the stable external identifier if available; falls back to the normalized canonical URL.
    """
    prov = (provider or "").strip().lower()
    if external_id and external_id.strip():
        raw_key = f"{prov}:{external_id.strip()}"
    else:
        norm_url = (url or "").strip().lower()
        raw_key = f"{prov}:{norm_url}"

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def parse_iso_datetime(date_str: str | None) -> datetime | None:
    """Parses an ISO 8601 datetime string safely, ensuring timezone awareness (UTC)."""
    if not date_str or not isinstance(date_str, str):
        return None
    cleaned = date_str.strip()
    if not cleaned:
        return None
    try:
        # Normalize trailing 'Z' to '+00:00' for standard fromisoformat
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        logger.debug("Failed to parse datetime string: %s", date_str)
        return None


class CollectorError(Exception):
    """Base exception for collector failures."""

    def __init__(self, message: str, provider: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code


class CollectorAuthError(CollectorError):
    """Raised when authentication or authorization fails with an external provider."""

    pass


class CollectorQuotaError(CollectorError):
    """Raised when provider rate limits or quotas are exceeded."""

    pass


class CollectorNetworkError(CollectorError):
    """Raised on network timeout, DNS, or transport failures."""

    pass


class BaseCollector(ABC):
    """Abstract interface for public opinion data collectors."""

    provider_name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if required configuration/keys are present."""
        pass

    @abstractmethod
    async def collect(
        self,
        query: str,
        limit: int = 10,
        topic: str | None = None,
    ) -> list[NormalizedSourceRecord]:
        """Collects, parses, and normalizes public opinion items from the provider.

        Must return a list of NormalizedSourceRecord.
        """
        pass
