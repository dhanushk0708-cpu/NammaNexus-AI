from datetime import datetime
import logging
from typing import Any
import httpx

from app.core.config import settings
from app.models.nammaserve import SourceType, VerificationStatus
from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult, ServiceMatchLevel
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector
from app.services.nammaserve.discovery.distance import haversine_distance_km
from app.services.nammaserve.discovery.normalizer import ResultNormalizer

logger = logging.getLogger(__name__)

# Canonical mapping of NammaServe service slugs to Foursquare search keywords
FOURSQUARE_QUERY_MAPPINGS: dict[str, str] = {
    "ac-repair": "AC repair service",
    "plumbing": "plumber plumbing service",
    "electrical": "electrician electrical repair",
    "home-cleaning": "cleaning service home cleaning",
    "painting": "painting contractor painter",
    "pest-control": "pest control",
    "water-tanker": "water supplier water tanker",
    "packers-movers": "packers and movers",
    "e-waste": "e-waste recycling scrap",
}


class FoursquareDiscoveryConnector(BaseDiscoveryConnector):
    """Foursquare Places API connector for local civic service discovery.
    
    Adheres strictly to project requirements:
    - Official modern endpoint: https://places-api.foursquare.com/places/search
    - Configured via `settings.foursquare_api_key`.
    - Modern authentication via `Authorization: Bearer <KEY>` and `X-Places-Api-Version` header.
    - Handles missing credentials gracefully (is_available=False, returns []).
    - Respects bounded timeouts (10s) and handles 401/403/429/500 without crashing.
    - Preserves source attribution (source='Foursquare Places', source_url).
    - Data integrity: never fabricates phone numbers, ratings, or prices.
    - External records remain UNVERIFIED.
    """

    def __init__(self, api_key: str | None = None, timeout: float = 10.0):
        self.api_key = api_key if api_key is not None else getattr(settings, "foursquare_api_key", None)
        self.timeout = timeout
        self.endpoint = "https://places-api.foursquare.com/places/search"
        self.api_version = "2025-06-17"

    @property
    def name(self) -> str:
        return "Foursquare Places"

    @property
    def source_type(self) -> SourceType:
        return SourceType.FOURSQUARE

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and str(self.api_key).strip())

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        """Execute place search on Foursquare Places API."""
        if not self.is_available:
            logger.debug("Foursquare connector skipped: API key not configured.")
            return []

        service_slug = (
            query.resolved_category_slug
            or query.resolved_service_slug
            or query.service
            or ""
        ).lower().strip()
        search_term = (
            FOURSQUARE_QUERY_MAPPINGS.get(service_slug)
            or query.resolved_service_name
            or query.service
            or "repair service"
        )

        params: dict[str, Any] = {
            "query": search_term,
            "limit": min(query.limit, 20),
        }

        # Spatial search filter
        if query.lat is not None and query.lng is not None:
            params["ll"] = f"{query.lat},{query.lng}"
            radius_m = int(min(query.radius_km * 1000.0, 50000.0))
            params["radius"] = radius_m
        elif query.area:
            params["near"] = f"{query.area}, Bengaluru"
        else:
            params["near"] = "Bengaluru, Karnataka, India"

        clean_key = str(self.api_key).strip()
        headers = {
            "Authorization": f"Bearer {clean_key}",
            "X-Places-Api-Version": self.api_version,
            "Accept": "application/json",
            "User-Agent": "NammaNexus-AI/1.0 (Bengaluru Civic Intelligence Platform)",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.endpoint, params=params, headers=headers)

                if resp.status_code == 429:
                    logger.warning("Foursquare Places API rate limited (HTTP 429).")
                    return []
                if resp.status_code in (401, 403):
                    logger.warning("Foursquare Places API authentication error (HTTP %s).", resp.status_code)
                    return []
                if resp.status_code != 200:
                    logger.warning("Foursquare Places API returned status %s: %s", resp.status_code, resp.text[:150])
                    return []

                data = resp.json()
                results_raw = data.get("results", [])
                normalized_results: list[NormalizedProviderResult] = []

                for item in results_raw:
                    name = item.get("name")
                    if not name:
                        continue

                    fsq_id = item.get("fsq_id")
                    geocodes = item.get("geocodes", {}).get("main", {})
                    lat = geocodes.get("latitude")
                    lng = geocodes.get("longitude")

                    dist_km = None
                    if item.get("distance") is not None:
                        dist_km = float(item["distance"]) / 1000.0
                    elif query.lat is not None and query.lng is not None and lat is not None and lng is not None:
                        dist_km = haversine_distance_km(query.lat, query.lng, lat, lng)

                    loc = item.get("location", {})
                    address = loc.get("formatted_address") or loc.get("address")
                    neighborhood_list = loc.get("neighborhood") or []
                    area = (
                        loc.get("locality")
                        or (neighborhood_list[0] if neighborhood_list else None)
                        or query.area
                        or "Bengaluru"
                    )

                    phone = item.get("tel") or ""
                    website = item.get("website")
                    hours_obj = item.get("hours", {})
                    opening_hours = hours_obj.get("display") if isinstance(hours_obj, dict) else None

                    source_url = f"https://foursquare.com/v/{fsq_id}" if fsq_id else "https://foursquare.com"
                    ext_ids = {"fsq_id": str(fsq_id)} if fsq_id else {}

                    normalized = ResultNormalizer.from_external_payload(
                        name=name,
                        phone=phone,
                        source_type=self.source_type,
                        source="Foursquare Places",
                        address=address,
                        area=area,
                        latitude=lat,
                        longitude=lng,
                        distance_km=dist_km,
                        matched_service_slug=query.resolved_service_slug or service_slug,
                        matched_service_name=query.resolved_service_name or (service_slug.title() if service_slug else "Service"),
                        operating_hours=opening_hours,
                        source_url=source_url,
                        service_match_level=ServiceMatchLevel.UNCONFIRMED,
                        service_match_confidence=0.35,
                        sources=["Foursquare Places"],
                        external_ids=ext_ids,
                        website=website,
                        discovered_at=datetime.utcnow(),
                        ranking_reasons=["Public place listing from Foursquare; unverified service capability"],
                    )
                    normalized.verification_status = VerificationStatus.UNVERIFIED
                    normalized_results.append(normalized)

                return normalized_results

        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("Foursquare Places API query timed out or failed: %s", exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error in Foursquare connector: %s", exc)
            return []
