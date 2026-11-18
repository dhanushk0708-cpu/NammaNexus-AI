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


class BlueskyCollector(BaseCollector):
    """Collector for public posts from the Bluesky AT Protocol network via public API."""

    provider_name = "bluesky"

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = (base_url or settings.bluesky_api_base_url or "https://api.bsky.app").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = client

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _build_canonical_url(self, uri: str | None, author_handle: str | None, author_did: str | None) -> str:
        """Builds a public canonical web URL from the AT Protocol URI."""
        if uri and "/app.bsky.feed.post/" in uri:
            rkey = uri.split("/")[-1]
            identifier = author_handle or author_did or "profile"
            return f"https://bsky.app/profile/{identifier}/post/{rkey}"
        if author_handle:
            return f"https://bsky.app/profile/{author_handle}"
        return "https://bsky.app"

    async def collect(
        self,
        query: str,
        limit: int = 10,
        topic: str | None = None,
    ) -> list[NormalizedSourceRecord]:
        """Collects public posts matching the query from Bluesky."""
        if not query or not query.strip():
            return []

        clean_query = query.strip()
        bounded_limit = max(1, min(limit, 100))
        url = f"{self.base_url}/xrpc/app.bsky.feed.searchPosts"

        params = {
            "q": clean_query,
            "limit": bounded_limit,
        }

        records: list[NormalizedSourceRecord] = []
        seen_keys: set[str] = set()

        try:
            if self._client is not None:
                resp = await self._client.get(url, params=params, timeout=self.timeout_seconds)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.get(url, params=params)

            if resp.status_code == 429:
                raise CollectorQuotaError("Bluesky rate limit exceeded", provider=self.provider_name, status_code=429)
            elif resp.status_code in (401, 403):
                raise CollectorAuthError("Bluesky authentication error", provider=self.provider_name, status_code=resp.status_code)
            elif resp.is_error:
                raise CollectorError(
                    f"Bluesky HTTP error {resp.status_code}",
                    provider=self.provider_name,
                    status_code=resp.status_code,
                )

            data = resp.json()
        except httpx.TimeoutException as exc:
            logger.warning("Bluesky collector timeout for query: %s", clean_query)
            raise CollectorNetworkError(f"Bluesky network timeout: {exc}", provider=self.provider_name) from exc
        except (httpx.RequestError, httpx.TransportError) as exc:
            logger.warning("Bluesky collector transport error: %s", exc)
            raise CollectorNetworkError(f"Bluesky network error: {exc}", provider=self.provider_name) from exc
        except (ValueError, TypeError) as exc:
            logger.error("Bluesky collector received malformed JSON response: %s", exc)
            raise CollectorError("Malformed JSON received from Bluesky", provider=self.provider_name) from exc

        if not isinstance(data, dict):
            logger.warning("Bluesky response was not a JSON object")
            return []

        posts = data.get("posts")
        if not isinstance(posts, list):
            return []

        now = datetime.now(timezone.utc)

        for post in posts:
            if not isinstance(post, dict):
                continue

            uri = post.get("uri")
            cid = post.get("cid")
            author_data = post.get("author") if isinstance(post.get("author"), dict) else {}
            author_handle = author_data.get("handle")
            author_did = author_data.get("did")
            author_name = author_data.get("displayName")

            record_data = post.get("record") if isinstance(post.get("record"), dict) else {}
            text = record_data.get("text")
            created_at_str = record_data.get("createdAt")
            langs = record_data.get("langs")

            lang = None
            if isinstance(langs, list) and langs:
                lang = str(langs[0])

            canonical_url = self._build_canonical_url(uri, author_handle, author_did)
            published_at = parse_iso_datetime(created_at_str)
            stable_id = str(uri) if uri else (str(cid) if cid else None)
            dedup_key = compute_dedup_key(self.provider_name, stable_id, canonical_url)

            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            metadata: dict[str, Any] = {}
            if uri:
                metadata["uri"] = uri
            if cid:
                metadata["cid"] = cid
            if author_did:
                metadata["author_did"] = author_did
            if author_name:
                metadata["author_display_name"] = author_name

            records.append(
                NormalizedSourceRecord(
                    provider=self.provider_name,
                    external_id=stable_id,
                    dedup_key=dedup_key,
                    topic=topic,
                    title=None,
                    content=text,
                    url=canonical_url,
                    author=author_handle or author_did,
                    published_at=published_at,
                    collected_at=now,
                    language=lang,
                    metadata_json=metadata if metadata else None,
                )
            )

            if len(records) >= bounded_limit:
                break

        return records
