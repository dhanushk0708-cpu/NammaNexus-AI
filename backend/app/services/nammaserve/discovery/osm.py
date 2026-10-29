from datetime import datetime
import logging
from typing import Any
from urllib.parse import quote
import httpx

from app.models.nammaserve import SourceType, VerificationStatus
from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult, ServiceMatchLevel
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector
from app.services.nammaserve.discovery.distance import haversine_distance_km
from app.services.nammaserve.discovery.normalizer import ResultNormalizer

logger = logging.getLogger(__name__)

# Canonical tag and search mapping for OSM
OSM_CATEGORY_MAPPINGS: dict[str, dict[str, Any]] = {
    "ac-repair": {
        "search_terms": ["air conditioning repair", "AC repair", "appliance repair"],
        "display_name": "AC Repair",
    },
    "plumbing": {
        "search_terms": ["plumber", "plumbing works", "sanitary hardware"],
        "display_name": "Plumbing",
    },
    "electrical": {
        "search_terms": ["electrician", "electrical repair", "electrical shop"],
        "display_name": "Electrical",
    },
    "home-cleaning": {
        "search_terms": ["cleaning services", "house cleaning", "laundry dry cleaning"],
        "display_name": "Home Cleaning",
    },
    "painting": {
        "search_terms": ["painter", "painting contractor", "paints shop"],
        "display_name": "Painting",
    },
    "pest-control": {
        "search_terms": ["pest control", "pest management"],
        "display_name": "Pest Control",
    },
    "water-tanker": {
        "search_terms": ["water supplier", "water tanker", "drinking water supply"],
        "display_name": "Water Tanker",
    },
    "packers-movers": {
        "search_terms": ["packers and movers", "movers", "relocation service"],
        "display_name": "Packers & Movers",
    },
    "e-waste": {
        "search_terms": ["e-waste recycling", "scrap dealer", "recycling center"],
        "display_name": "E-Waste",
    },
}


class OpenStreetMapDiscoveryConnector(BaseDiscoveryConnector):
    """OpenStreetMap / Overpass connector for civic service discovery.
    
    Adheres strictly to the following requirements:
    - Queries public Overpass API with automatic failover to OSM Nominatim.
    - Rate limits & bounded timeouts (8.0s connect/read max) to prevent blocking the search endpoint.
    - Gracefully handles HTTP 429, timeouts, and server errors (502/503/504).
    - Source attribution: clearly records source as 'OpenStreetMap' and links to OSM place URL.
    - Data integrity: never invents prices, ratings, phone numbers, or fake verification.
    - Does NOT automatically insert external records into the trusted database.
    """

    def __init__(
        self,
        overpass_url: str = "https://overpass-api.de/api/interpreter",
        nominatim_url: str = "https://nominatim.openstreetmap.org/search",
        timeout: float = 6.0,
        user_agent: str = "NammaNexus-AI/1.0 (Bengaluru Civic Intelligence Platform; contact: info@nammanexus.org)",
    ):
        self.overpass_url = overpass_url
        self.nominatim_url = nominatim_url
        self.timeout = timeout
        self.user_agent = user_agent

    @property
    def name(self) -> str:
        return "OpenStreetMap Directory"

    @property
    def source_type(self) -> SourceType:
        # Reuses SourceType.OTHER as allowed by models or SourceType.WEB
        return SourceType.OTHER

    @property
    def is_available(self) -> bool:
        return True

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        """Search OpenStreetMap for nearby service providers."""
        if not query.service and not query.area and not query.lat:
            return []

        # Determine mapped search term using resolved category/service if present
        service_slug = (
            query.resolved_category_slug
            or query.resolved_service_slug
            or query.service
            or ""
        ).lower().strip()
        mapping = OSM_CATEGORY_MAPPINGS.get(service_slug)
        search_terms = mapping["search_terms"] if mapping else [query.resolved_service_name or query.service or "civic service"]
        matched_category_name = mapping["display_name"] if mapping else (query.resolved_service_name or query.service or "Service")

        # 1. Attempt Overpass query if coordinates are available
        results: list[NormalizedProviderResult] = []
        if query.lat is not None and query.lng is not None:
            results = await self._query_overpass(query, search_terms, service_slug, matched_category_name)

        # 2. If Overpass timed out, was empty, or coordinates were not provided, use Nominatim
        if not results:
            results = await self._query_nominatim(query, search_terms, service_slug, matched_category_name)

        return results

    async def _query_overpass(
        self,
        query: DiscoveryQuery,
        search_terms: list[str],
        service_slug: str,
        matched_category_name: str,
    ) -> list[NormalizedProviderResult]:
        """Query Overpass API within spatial radius."""
        lat = query.lat
        lng = query.lng
        radius_meters = int(min(query.radius_km * 1000.0, 15000.0))

        # Build union of regex tags for supported terms
        regex_craft = "|".join([t.split()[0].lower() for t in search_terms])
        overpass_ql = f"""[out:json][timeout:5];
(
  node["craft"~"{regex_craft}",i](around:{radius_meters},{lat},{lng});
  node["shop"~"{regex_craft}",i](around:{radius_meters},{lat},{lng});
);
out body 10;
"""
        headers = {"User-Agent": self.user_agent}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.overpass_url,
                    data={"data": overpass_ql},
                    headers=headers,
                )

                if resp.status_code == 429:
                    logger.warning("Overpass API rate limited (HTTP 429). Falling back to Nominatim.")
                    return []
                if resp.status_code >= 500:
                    logger.warning("Overpass API server error (HTTP %s). Falling back.", resp.status_code)
                    return []
                if resp.status_code != 200:
                    logger.warning("Overpass API unexpected status: %s", resp.status_code)
                    return []

                data = resp.json()
                elements = data.get("elements", [])
                results: list[NormalizedProviderResult] = []

                for el in elements:
                    tags = el.get("tags", {})
                    name = tags.get("name") or tags.get("operator")
                    if not name:
                        continue

                    el_lat = el.get("lat")
                    el_lon = el.get("lon")
                    dist_km = None
                    if lat is not None and lng is not None and el_lat is not None and el_lon is not None:
                        dist_km = haversine_distance_km(lat, lng, el_lat, el_lon)

                    phone = tags.get("phone") or tags.get("contact:phone") or ""
                    osm_id = el.get("id")
                    source_url = f"https://www.openstreetmap.org/node/{osm_id}" if osm_id else "https://www.openstreetmap.org"
                    ext_ids = {"osm_id": str(osm_id)} if osm_id else {}

                    item = ResultNormalizer.from_external_payload(
                        name=name,
                        phone=phone,
                        source_type=self.source_type,
                        source="OpenStreetMap",
                        address=tags.get("addr:street") or tags.get("address"),
                        area=tags.get("addr:suburb") or query.area or "Bengaluru",
                        latitude=el_lat,
                        longitude=el_lon,
                        distance_km=dist_km,
                        matched_service_slug=query.resolved_service_slug or service_slug,
                        matched_service_name=matched_category_name,
                        operating_hours=tags.get("opening_hours"),
                        source_url=source_url,
                        service_match_level=ServiceMatchLevel.UNCONFIRMED,
                        service_match_confidence=0.30,
                        sources=["OpenStreetMap"],
                        external_ids=ext_ids,
                        website=tags.get("website"),
                        discovered_at=datetime.utcnow(),
                        ranking_reasons=["Public place listing from OpenStreetMap; unverified service capability"],
                    )
                    # Verification status MUST remain UNVERIFIED for external OSM nodes
                    item.verification_status = VerificationStatus.UNVERIFIED
                    results.append(item)

                return results

        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("Overpass API query timed out or failed: %s. Using Nominatim fallback.", exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error querying Overpass API: %s", exc)
            return []

    async def _query_nominatim(
        self,
        query: DiscoveryQuery,
        search_terms: list[str],
        service_slug: str,
        matched_category_name: str,
    ) -> list[NormalizedProviderResult]:
        """Query OSM Nominatim API as a reliable fallback."""
        area_str = query.area or "Bengaluru"
        primary_term = search_terms[0] if search_terms else (query.service or "service")
        q = f"{primary_term} {area_str}"

        params: dict[str, Any] = {
            "q": q,
            "format": "jsonv2",
            "addressdetails": "1",
            "extratags": "1",
            "limit": min(query.limit, 10),
        }

        # If coordinates provided, bias search with a bounding box
        if query.lat is not None and query.lng is not None:
            # Approx 0.045 deg per 5km
            delta = (query.radius_km / 111.0)
            min_lat = query.lat - delta
            max_lat = query.lat + delta
            min_lon = query.lng - delta
            max_lon = query.lng + delta
            params["viewbox"] = f"{min_lon:.4f},{max_lat:.4f},{max_lon:.4f},{min_lat:.4f}"

        headers = {"User-Agent": self.user_agent}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    self.nominatim_url,
                    params=params,
                    headers=headers,
                )

                if resp.status_code == 429:
                    logger.warning("OSM Nominatim rate limited (HTTP 429).")
                    return []
                if resp.status_code != 200:
                    logger.warning("OSM Nominatim returned HTTP %s", resp.status_code)
                    return []

                data = resp.json()
                if not isinstance(data, list):
                    return []

                results: list[NormalizedProviderResult] = []
                for item in data:
                    display_name = item.get("name") or item.get("display_name", "")
                    # Clean title from long display name
                    name = display_name.split(",")[0].strip()
                    if not name:
                        continue

                    try:
                        el_lat = float(item.get("lat")) if item.get("lat") else None
                        el_lon = float(item.get("lon")) if item.get("lon") else None
                    except (ValueError, TypeError):
                        el_lat, el_lon = None, None

                    dist_km = None
                    if query.lat is not None and query.lng is not None and el_lat is not None and el_lon is not None:
                        dist_km = haversine_distance_km(query.lat, query.lng, el_lat, el_lon)

                    address_obj = item.get("address", {})
                    suburb = address_obj.get("suburb") or address_obj.get("neighbourhood") or query.area
                    osm_type = item.get("osm_type", "node")
                    osm_id = item.get("osm_id")
                    source_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}" if osm_id else "https://www.openstreetmap.org"
                    ext_ids = {"osm_id": str(osm_id)} if osm_id else {}

                    normalized = ResultNormalizer.from_external_payload(
                        name=name,
                        phone="",  # Nominatim search does not include verified phones
                        source_type=self.source_type,
                        source="OpenStreetMap",
                        address=item.get("display_name"),
                        area=suburb,
                        latitude=el_lat,
                        longitude=el_lon,
                        distance_km=dist_km,
                        matched_service_slug=query.resolved_service_slug or service_slug,
                        matched_service_name=matched_category_name,
                        source_url=source_url,
                        service_match_level=ServiceMatchLevel.UNCONFIRMED,
                        service_match_confidence=0.30,
                        sources=["OpenStreetMap"],
                        external_ids=ext_ids,
                        discovered_at=datetime.utcnow(),
                        ranking_reasons=["Public place listing from OpenStreetMap (Nominatim); unverified service capability"],
                    )
                    normalized.verification_status = VerificationStatus.UNVERIFIED
                    results.append(normalized)

                return results

        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("OSM Nominatim query timed out or failed: %s", exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error querying OSM Nominatim: %s", exc)
            return []
