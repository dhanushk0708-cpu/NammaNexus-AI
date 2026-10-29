from collections import OrderedDict
from dataclasses import dataclass
import logging
import time
from typing import Any, Callable, Optional

from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult

logger = logging.getLogger("nammaserve.discovery.cache")

DISCOVERY_CACHE_VERSION = "v2"


def make_discovery_cache_key(query: DiscoveryQuery, version: str = DISCOVERY_CACHE_VERSION) -> str:
    """Generate a deterministic versioned cache key for discovery queries."""
    svc = (query.resolved_service_slug or query.resolved_category_slug or query.service or "any").lower().strip()
    lat_str = f"{query.lat:.3f}" if query.lat is not None else "nolat"
    lng_str = f"{query.lng:.3f}" if query.lng is not None else "nolng"
    area_str = (query.area or "noarea").lower().strip()
    rad_str = f"{query.radius_km:.1f}"
    ver_str = "ver" if query.verified_only else "all"
    emg_str = "emg" if query.emergency_only else "std"
    limit_str = str(query.limit)

    return f"disc:{version}:{svc}:{lat_str}:{lng_str}:{area_str}:{rad_str}:{ver_str}:{emg_str}:limit={limit_str}"


@dataclass
class _DiscoveryCacheEntry:
    data: list[dict[str, Any]]
    expires_at: float


class DiscoveryResultCache:
    """Bounded, thread-safe in-process LRU + TTL cache for discovery results."""

    def __init__(
        self,
        max_size: int = 500,
        default_ttl_seconds: int = 900,  # 15 minutes
        enabled: bool = True,
        time_fn: Callable[[], float] = time.monotonic,
    ):
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self.enabled = enabled
        self.time_fn = time_fn
        self._cache: OrderedDict[str, _DiscoveryCacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[list[NormalizedProviderResult]]:
        """Retrieve cached list of NormalizedProviderResult for key."""
        if not self.enabled:
            return None

        try:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]
            now = self.time_fn()

            if now >= entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return None

            self._cache.move_to_end(key)
            self._hits += 1

            # Deserialize a fresh copy
            return [NormalizedProviderResult.model_validate(item) for item in entry.data]
        except Exception as exc:
            logger.warning("DiscoveryResultCache.get failed for key '%s': %s", key, exc)
            return None

    def set(
        self,
        key: str,
        results: list[NormalizedProviderResult],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store list of results in cache with bounded TTL and LRU eviction."""
        if not self.enabled or results is None:
            return

        try:
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
            expires_at = self.time_fn() + ttl
            serialized = [r.model_dump() for r in results]

            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = _DiscoveryCacheEntry(data=serialized, expires_at=expires_at)
            else:
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
                    self._evictions += 1
                self._cache[key] = _DiscoveryCacheEntry(data=serialized, expires_at=expires_at)

            self._sets += 1
        except Exception as exc:
            logger.warning("DiscoveryResultCache.set failed for key '%s': %s", key, exc)

    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._evictions = 0

    @property
    def stats(self) -> dict[str, int]:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "evictions": self._evictions,
            "size": len(self._cache),
        }


# Global singleton
_default_discovery_cache: Optional[DiscoveryResultCache] = None


def get_default_discovery_cache() -> DiscoveryResultCache:
    global _default_discovery_cache
    if _default_discovery_cache is None:
        _default_discovery_cache = DiscoveryResultCache()
    return _default_discovery_cache
