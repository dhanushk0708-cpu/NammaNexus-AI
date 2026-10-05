import logging
import httpx

from app.core.config import settings
from app.models.nammaserve import SourceType
from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector
from app.services.nammaserve.discovery.distance import haversine_distance_km
from app.services.nammaserve.discovery.normalizer import ResultNormalizer

logger = logging.getLogger(__name__)


class GooglePlacesDiscoveryConnector(BaseDiscoveryConnector):
    """Connector for querying the Google Places API (Places New API)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.google_places_api_key

    @property
    def name(self) -> str:
        return "Google Places API"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GOOGLE_PLACES

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        """Search Google Places for local service businesses."""
        if not self.is_available:
            logger.debug("Google Places connector skipped: API key not configured.")
            return []

        # Construct search text
        service_text = query.service or "civic service"
        location_text = query.area or "Bengaluru"
        text_query = f"{service_text} in {location_text}"

        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.location,places.currentOpeningHours,places.websiteUri",
        }
        payload = {
            "textQuery": text_query,
            "maxResultCount": min(query.limit, 10),
        }

        # Location bias if coordinates are provided
        if query.lat is not None and query.lng is not None:
            payload["locationBias"] = {
                "circle": {
                    "center": {"latitude": query.lat, "longitude": query.lng},
                    "radius": float(query.radius_km * 1000.0),
                }
            }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code != 200:
                    logger.warning(
                        "Google Places API returned status %s: %s",
                        response.status_code,
                        response.text,
                    )
                    return []

                data = response.json()
                places = data.get("places", [])

                results: list[NormalizedProviderResult] = []
                for place in places:
                    display_name = place.get("displayName", {}).get("text", "Unknown Business")
                    phone = place.get("nationalPhoneNumber") or "Not Available"
                    address = place.get("formattedAddress")
                    location = place.get("location", {})
                    plat = location.get("latitude")
                    plng = location.get("longitude")
                    website = place.get("websiteUri")

                    dist_km = None
                    if (
                        query.lat is not None
                        and query.lng is not None
                        and plat is not None
                        and plng is not None
                    ):
                        dist_km = haversine_distance_km(query.lat, query.lng, plat, plng)
                        if dist_km > query.radius_km:
                            continue

                    normalized = ResultNormalizer.from_external_payload(
                        name=display_name,
                        phone=phone,
                        source_type=SourceType.GOOGLE_PLACES,
                        source="Google Places Public Listing",
                        address=address,
                        area=query.area,
                        latitude=plat,
                        longitude=plng,
                        distance_km=dist_km,
                        matched_service_slug=query.service,
                        matched_service_name=query.service.replace("-", " ").title() if query.service else None,
                        source_url=website,
                    )
                    results.append(normalized)

                return results
        except Exception as exc:
            logger.error("Error executing Google Places query: %s", exc)
            return []
