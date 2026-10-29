from collections import OrderedDict
from dataclasses import dataclass
import logging
import re
import time
from typing import Any, Callable, Optional

from app.core.config import settings
from app.schemas.nammaserve import ServiceIntent

logger = logging.getLogger("nammaserve.ai.cache")

INTENT_CACHE_VERSION = "v1"


def normalize_intent_cache_key(query: str, version: str = INTENT_CACHE_VERSION) -> str:
    """Normalize citizen query text into a deterministic, versioned cache key.

    Normalization steps:
    1. Strip leading and trailing whitespace.
    2. Collapse internal consecutive whitespace runs to single space.
    3. Convert to lowercase.
    4. Prefix with cache domain and schema version.
    """
    cleaned = re.sub(r"\s+", " ", query.strip().lower())
    return f"intent:{version}:{cleaned}"


@dataclass
class _CacheEntry:
    data: dict[str, Any]
    expires_at: float


class IntentCache:
    """Lightweight, bounded in-process LRU + TTL cache for extracted ServiceIntents."""

    def __init__(
        self,
        max_size: int | None = None,
        default_ttl_seconds: int | None = None,
        enabled: bool | None = None,
        time_fn: Callable[[], float] = time.monotonic,
    ):
        self.max_size = (
            max_size
            if max_size is not None
            else getattr(settings, "intent_cache_max_size", 1000)
        )
        self.default_ttl_seconds = (
            default_ttl_seconds
            if default_ttl_seconds is not None
            else getattr(settings, "intent_cache_ttl_seconds", 3600)
        )
        self.enabled = (
            enabled
            if enabled is not None
            else getattr(settings, "intent_cache_enabled", True)
        )
        self.time_fn = time_fn
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()

        # Observability stats (hits/misses)
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[ServiceIntent]:
        """Retrieve cached ServiceIntent for *key*.

        Returns None on cache miss, expired entry, or if caching is disabled.
        Never throws; failures degrade gracefully.
        """
        if not self.enabled:
            return None

        try:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]
            now = self.time_fn()

            if now >= entry.expires_at:
                # Expired -> prune
                del self._cache[key]
                self._misses += 1
                return None

            # Mark as MRU (move to end)
            self._cache.move_to_end(key)
            self._hits += 1

            # Deserialize a fresh copy so mutations do not affect cached state
            return ServiceIntent.model_validate(entry.data)
        except Exception as exc:
            logger.warning("IntentCache.get failed for key '%s': %s", key, exc)
            return None

    def set(
        self,
        key: str,
        value: ServiceIntent,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store a ServiceIntent in cache with bounded TTL and LRU eviction.

        Never throws; failures degrade gracefully.
        """
        if not self.enabled or value is None:
            return

        try:
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
            expires_at = self.time_fn() + ttl

            # Serialize to dict for deep isolation
            serialized = value.model_dump()

            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = _CacheEntry(data=serialized, expires_at=expires_at)
            else:
                if len(self._cache) >= self.max_size:
                    # Evict oldest entry (LRU - first item in OrderedDict)
                    self._cache.popitem(last=False)
                    self._evictions += 1
                self._cache[key] = _CacheEntry(data=serialized, expires_at=expires_at)

            self._sets += 1
        except Exception as exc:
            logger.warning("IntentCache.set failed for key '%s': %s", key, exc)

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._evictions = 0

    def size(self) -> int:
        """Return number of raw entries currently in cache."""
        return len(self._cache)

    @property
    def stats(self) -> dict[str, int]:
        """Return cache access statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "evictions": self._evictions,
            "size": len(self._cache),
        }


# Global default singleton for application runtime
_default_intent_cache: Optional[IntentCache] = None


def get_default_intent_cache() -> IntentCache:
    """Return application default IntentCache singleton."""
    global _default_intent_cache
    if _default_intent_cache is None:
        _default_intent_cache = IntentCache()
    return _default_intent_cache
