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

# Canonical mapping of NammaServe service slugs to Geoapify categories and name hints
GEOAPIFY_SERVICE_MAPPINGS: dict[str, dict[str, Any]] = {
    "ac-repair": {
        "categories": "service,commercial.elektronics,commercial.houseware_and_hardware",
        "name_hint": "ac",
        "display_name": "AC Repair",
    },
    "plumbing": {
        "categories": "service,commercial.houseware_and_hardware",
        "name_hint": "plumb",
        "display_name": "Plumbing",
    },
    "electrical": {
        "categories": "service,commercial.elektronics,commercial.houseware_and_hardware",
        "name_hint": "electric",
        "display_name": "Electrical",
    },
    "home-cleaning": {
        "categories": "service,service.cleaning",
        "name_hint": "clean",
        "display_name": "Home Cleaning",
    },
    "painting": {
        "categories": "service,commercial.houseware_and_hardware",
        "name_hint": "paint",
        "display_name": "Painting",
    },
    "pest-control": {
        "categories": "service",
        "name_hint": "pest",
        "display_name": "Pest Control",
    },
    "water-tanker": {
        "categories": "service",
        "name_hint": "water",
        "display_name": "Water Tanker",
    },
    "packers-movers": {
        "categories": "service",
        "name_hint": "packers",
        "display_name": "Packers & Movers",
    },
    "e-waste": {
        "categories": "service,commercial.elektronics",
        "name_hint": "scrap",
        "display_name": "E-Waste",
    },
}


class GeoapifyDiscoveryConnector(BaseDiscoveryConnector):
    """Geoapify Places API connector for civic place and service discovery.
    
    Adheres strictly to project requirements:
    - Official endpoint: https://api.geoapify.com/v2/places
    - Configured via `settings.geoapify_api_key`.
    - Bounded timeouts (8s) and non-blocking failure handling.
    - Preserves source attribution and place URLs.
    - Data integrity: never fabricates phone numbers, ratings, or prices.
    - External records remain UNVERIFIED.
    """

    def __init__(self, api_key: str | None = None, timeout: float = 12.0):
        self.api_key = api_key if api_key is not None else getattr(settings, "geoapify_api_key", None)
        self.timeout = timeout
        self.endpoint = "https://api.geoapify.com/v2/places"

    @property
    def name(self) -> str:
        return "Geoapify Places"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GEOAPIFY

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and str(self.api_key).strip())

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        """Execute place discovery on Geoapify Places API."""
        if not self.is_available:
            logger.debug("Geoapify Places connector skipped: API key not configured.")
            return []

        # Coordinates check (Geoapify spatial filter requires lon,lat)
        lat = query.lat if query.lat is not None else 12.9716  # Bengaluru center fallback
        lng = query.lng if query.lng is not None else 77.5946

        service_slug = (
            query.resolved_category_slug
            or query.resolved_service_slug
            or query.service
            or ""
        ).lower().strip()
        mapping = GEOAPIFY_SERVICE_MAPPINGS.get(service_slug)
        if not mapping:
            # Service not mapped to supported Geoapify place categories; do not return arbitrary commercial places
            return []

        categories = mapping["categories"]
        display_name = mapping.get("display_name") or query.resolved_service_name or query.service or "Service"

        radius_meters = int(min(query.radius_km * 1000.0, 25000.0))

        params: dict[str, Any] = {
            "categories": categories,
            "filter": f"circle:{lng},{lat},{radius_meters}",
            "bias": f"proximity:{lng},{lat}",
            "limit": min(query.limit, 20),
            "apiKey": str(self.api_key).strip(),
        }

        if mapping.get("name_hint"):
            params["name"] = mapping["name_hint"]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.endpoint, params=params)

                if resp.status_code == 429:
                    logger.warning("Geoapify API rate limit exceeded (HTTP 429).")
                    return []
                if resp.status_code in (401, 403):
                    logger.warning("Geoapify API authentication error (HTTP %s).", resp.status_code)
                    return []
                if resp.status_code != 200:
                    logger.warning("Geoapify returned status %s: %s", resp.status_code, resp.text[:150])
                    return []

                data = resp.json()
                features = data.get("features", [])
                results: list[NormalizedProviderResult] = []

                for f in features:
                    props = f.get("properties", {})
                    name = props.get("name")
                    if not name:
                        continue

                    f_lat = props.get("lat")
                    f_lon = props.get("lon")
                    dist_km = None
                    if props.get("distance") is not None:
                        dist_km = float(props["distance"]) / 1000.0
                    elif query.lat is not None and query.lng is not None and f_lat is not None and f_lon is not None:
                        dist_km = haversine_distance_km(query.lat, query.lng, f_lat, f_lon)

                    # Extract phone if present in contact or datasource raw
                    contact = props.get("contact", {}) or {}
                    raw_ds = props.get("datasource", {}).get("raw", {}) or {}
                    phone = (
                        contact.get("phone")
                        or raw_ds.get("phone")
                        or raw_ds.get("contact:phone")
                        or ""
                    )

                    website = props.get("website") or raw_ds.get("website")
                    address = props.get("formatted") or props.get("address_line1")
                    area = props.get("suburb") or props.get("neighbourhood") or props.get("district") or query.area or "Bengaluru"
                    opening_hours = props.get("opening_hours") or raw_ds.get("opening_hours")
                    place_id = props.get("place_id")
                    source_url = f"https://www.geoapify.com/place/{place_id}" if place_id else "https://www.geoapify.com"
                    ext_ids = {"geoapify_id": str(place_id)} if place_id else {}

                    item = ResultNormalizer.from_external_payload(
                        name=name,
                        phone=phone,
                        source_type=self.source_type,
                        source="Geoapify Places",
                        address=address,
                        area=area,
                        latitude=f_lat,
                        longitude=f_lon,
                        distance_km=dist_km,
                        matched_service_slug=query.resolved_service_slug or service_slug,
                        matched_service_name=display_name,
                        operating_hours=opening_hours,
                        source_url=source_url,
                        service_match_level=ServiceMatchLevel.UNCONFIRMED,
                        service_match_confidence=0.35,
                        sources=["Geoapify Places"],
                        external_ids=ext_ids,
                        website=website,
                        discovered_at=datetime.utcnow(),
                        ranking_reasons=["Public place listing from Geoapify; unverified service capability"],
                    )
                    item.verification_status = VerificationStatus.UNVERIFIED
                    results.append(item)

                return results

        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("Geoapify Places API query timed out or failed: %s", exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error in Geoapify connector: %s", exc)
            return []
