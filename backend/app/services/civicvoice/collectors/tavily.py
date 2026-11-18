from datetime import datetime, timezone
import logging
from typing import Any
from urllib.parse import urlparse
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


class TavilyCollector(BaseCollector):
    """Collector for public web articles and discovery material via Tavily Search API."""

    provider_name = "tavily"
    SEARCH_ENDPOINT = "https://api.tavily.com/search"
    EXTRACT_ENDPOINT = "https://api.tavily.com/extract"

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 12.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.tavily_api_key
        self.timeout_seconds = timeout_seconds
        self._client = client

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def extract_content(self, urls: list[str]) -> dict[str, str]:
        """Selectively extracts full page content for URLs when snippets are insufficient."""
        if not self.is_configured() or not urls:
            return {}

        clean_urls = [u.strip() for u in urls if u and isinstance(u, str) and u.startswith("http")][:5]
        if not clean_urls:
            return {}

        payload = {
            "api_key": self.api_key,
            "urls": clean_urls,
        }

        try:
            if self._client is not None:
                resp = await self._client.post(self.EXTRACT_ENDPOINT, json=payload, timeout=self.timeout_seconds)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(self.EXTRACT_ENDPOINT, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                extracted = {}
                for r in results:
                    u = r.get("url")
                    c = r.get("raw_content") or r.get("content")
                    if u and c and isinstance(c, str):
                        extracted[u] = c.strip()
                return extracted
        except Exception as exc:
            logger.debug("Tavily selective extraction notice for %s: %s", clean_urls, exc)

        return {}

    async def collect(
        self,
        query: str,
        limit: int = 10,
        topic: str | None = None,
    ) -> list[NormalizedSourceRecord]:
        """Queries Tavily Search API and returns normalized search snippets."""
        if not self.is_configured():
            logger.warning("Tavily collector invoked but API key is not configured.")
            raise CollectorAuthError("Tavily API key is not configured", provider=self.provider_name)

        if not query or not query.strip():
            return []

        clean_query = query.strip()
        bounded_limit = max(1, min(limit, 50))

        payload = {
            "api_key": self.api_key,
            "query": clean_query,
            "max_results": bounded_limit,
            "search_depth": "basic",
            "include_answer": False,
        }

        records: list[NormalizedSourceRecord] = []
        seen_keys: set[str] = set()

        try:
            if self._client is not None:
                resp = await self._client.post(
                    self.SEARCH_ENDPOINT,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(
                        self.SEARCH_ENDPOINT,
                        json=payload,
                    )

            if resp.status_code == 429:
                raise CollectorQuotaError(
                    "Tavily rate limit exceeded",
                    provider=self.provider_name,
                    status_code=429,
                )
            elif resp.status_code in (401, 403):
                raise CollectorAuthError(
                    "Tavily API authentication failure",
                    provider=self.provider_name,
                    status_code=resp.status_code,
                )
            elif resp.is_error:
                raise CollectorError(
                    f"Tavily API returned HTTP {resp.status_code}",
                    provider=self.provider_name,
                    status_code=resp.status_code,
                )

            data = resp.json()
        except httpx.TimeoutException as exc:
            logger.warning("Tavily collector timeout for query: %s", clean_query)
            raise CollectorNetworkError(f"Tavily network timeout: {exc}", provider=self.provider_name) from exc
        except (httpx.RequestError, httpx.TransportError) as exc:
            logger.warning("Tavily collector transport error: %s", exc)
            raise CollectorNetworkError(f"Tavily network error: {exc}", provider=self.provider_name) from exc
        except (ValueError, TypeError) as exc:
            logger.error("Tavily collector received malformed JSON response: %s", exc)
            raise CollectorError("Malformed JSON received from Tavily API", provider=self.provider_name) from exc

        if not isinstance(data, dict):
            logger.warning("Tavily response was not a JSON object")
            return []

        results = data.get("results")
        if not isinstance(results, list):
            return []

        now = datetime.now(timezone.utc)

        for item in results:
            if not isinstance(item, dict):
                continue

            raw_url = item.get("url")
            if not raw_url or not isinstance(raw_url, str):
                continue

            canonical_url = raw_url.strip()
            title = item.get("title")
            content = item.get("content")
            score = item.get("score")
            published_date = item.get("published_date")

            published_at = parse_iso_datetime(published_date)
            dedup_key = compute_dedup_key(self.provider_name, None, canonical_url)

            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            domain_author = None
            try:
                domain_author = urlparse(canonical_url).netloc or None
            except Exception:
                pass

            metadata: dict[str, Any] = {}
            if score is not None:
                metadata["score"] = score
            if topic:
                metadata["topic"] = topic

            records.append(
                NormalizedSourceRecord(
                    provider=self.provider_name,
                    external_id=None,
                    dedup_key=dedup_key,
                    topic=topic,
                    title=title,
                    content=content,
                    url=canonical_url,
                    author=domain_author,
                    published_at=published_at,
                    collected_at=now,
                    language=None,
                    metadata_json=metadata if metadata else None,
                )
            )

            if len(records) >= bounded_limit:
                break

        # Selective extraction when snippets are insufficient (< 140 chars)
        short_urls = [r.url for r in records if not r.content or len(r.content) < 140][:3]
        if short_urls:
            try:
                extracted_map = await self.extract_content(short_urls)
                for r in records:
                    if r.url in extracted_map and extracted_map[r.url]:
                        r.content = extracted_map[r.url]
            except Exception as exc:
                logger.debug("Selective Tavily extraction notice: %s", exc)

        return records
