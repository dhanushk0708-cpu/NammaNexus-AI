from datetime import datetime, timezone
import logging
from typing import Any
import httpx

from app.core.config import settings
from app.schemas.civicvoice import NormalizedSourceRecord
from app.services.civicvoice.collectors.base import (
    BaseCollector,
    CollectorAuthError,
    CollectorError,
    CollectorNetworkError,
    CollectorQuotaError,
    compute_dedup_key,
    parse_iso_datetime,
)

logger = logging.getLogger(__name__)


class YouTubeCollector(BaseCollector):
    """Collector for public video metadata from YouTube Data API v3."""

    provider_name = "youtube"
    SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.youtube_api_key
        self.timeout_seconds = timeout_seconds
        self._client = client

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def collect(
        self,
        query: str,
        limit: int = 10,
        topic: str | None = None,
    ) -> list[NormalizedSourceRecord]:
        """Searches YouTube videos matching the query and returns normalized metadata."""
        if not self.is_configured():
            logger.warning("YouTube collector invoked but API key is not configured.")
            raise CollectorAuthError("YouTube API key is not configured", provider=self.provider_name)

        if not query or not query.strip():
            return []

        clean_query = query.strip()
        bounded_limit = max(1, min(limit, 50))

        params = {
            "key": self.api_key,
            "part": "snippet",
            "q": clean_query,
            "type": "video",
            "maxResults": bounded_limit,
        }

        records: list[NormalizedSourceRecord] = []
        seen_keys: set[str] = set()

        try:
            if self._client is not None:
                resp = await self._client.get(
                    self.SEARCH_ENDPOINT,
                    params=params,
                    timeout=self.timeout_seconds,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.get(
                        self.SEARCH_ENDPOINT,
                        params=params,
                    )

            if resp.status_code == 429:
                raise CollectorQuotaError(
                    "YouTube rate limit exceeded",
                    provider=self.provider_name,
                    status_code=429,
                )
            elif resp.status_code == 403:
                # Often quotaExceeded or forbidden
                raise CollectorQuotaError(
                    "YouTube API quota exceeded or forbidden",
                    provider=self.provider_name,
                    status_code=403,
                )
            elif resp.status_code in (400, 401):
                raise CollectorAuthError(
                    "YouTube API invalid credentials or bad request",
                    provider=self.provider_name,
                    status_code=resp.status_code,
                )
            elif resp.is_error:
                raise CollectorError(
                    f"YouTube API returned HTTP {resp.status_code}",
                    provider=self.provider_name,
                    status_code=resp.status_code,
                )

            data = resp.json()
        except httpx.TimeoutException as exc:
            logger.warning("YouTube collector timeout for query: %s", clean_query)
            raise CollectorNetworkError(f"YouTube network timeout: {exc}", provider=self.provider_name) from exc
        except (httpx.RequestError, httpx.TransportError) as exc:
            logger.warning("YouTube collector transport error: %s", exc)
            raise CollectorNetworkError(f"YouTube network error: {exc}", provider=self.provider_name) from exc
        except (ValueError, TypeError) as exc:
            logger.error("YouTube collector received malformed JSON response: %s", exc)
            raise CollectorError("Malformed JSON received from YouTube API", provider=self.provider_name) from exc

        if not isinstance(data, dict):
            logger.warning("YouTube response was not a JSON object")
            return []

        items = data.get("items")
        if not isinstance(items, list):
            return []

        now = datetime.now(timezone.utc)

        for item in items:
            if not isinstance(item, dict):
                continue

            id_data = item.get("id") if isinstance(item.get("id"), dict) else {}
            video_id = id_data.get("videoId")
            if not video_id:
                continue

            snippet = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
            title = snippet.get("title")
            description = snippet.get("description")
            channel_id = snippet.get("channelId")
            channel_title = snippet.get("channelTitle")
            published_at_str = snippet.get("publishedAt")

            canonical_url = f"https://www.youtube.com/watch?v={video_id}"
            published_at = parse_iso_datetime(published_at_str)
            dedup_key = compute_dedup_key(self.provider_name, video_id, canonical_url)

            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            metadata: dict[str, Any] = {
                "video_id": video_id,
            }
            if channel_id:
                metadata["channel_id"] = channel_id
            if channel_title:
                metadata["channel_title"] = channel_title

            records.append(
                NormalizedSourceRecord(
                    provider=self.provider_name,
                    external_id=str(video_id),
                    dedup_key=dedup_key,
                    topic=topic,
                    title=title,
                    content=description,
                    url=canonical_url,
                    author=channel_title or channel_id,
                    published_at=published_at,
                    collected_at=now,
                    language=None,
                    metadata_json=metadata,
                )
            )

            if len(records) >= bounded_limit:
                break

        return records
