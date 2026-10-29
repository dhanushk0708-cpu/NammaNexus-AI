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
        self.api_key = settings.google_places_api_key if api_key is None else api_key
        self._last_error: str | None = None

    @property
    def name(self) -> str:
        return "Google Places API"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GOOGLE_PLACES

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def get_status(self, results_count: int = 0):
        from app.schemas.nammaserve import ConnectorStatus

        if not self.is_available:
            message = "Google Places API key is not configured."
        elif self._last_error:
            message = f"Google Places request failed: {self._last_error}"
        else:
            message = "Google Places API (New) is configured."
        return ConnectorStatus(
            connector_name=self.name,
            source_type=self.source_type,
            is_available=self.is_available,
            status_message=message,
            results_count=results_count if self._last_error is None else 0,
        )

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        """Search Google Places for local service businesses."""
        if not self.is_available:
            logger.debug("Google Places connector skipped: API key not configured.")
            return []

        self._last_error = None

        # Construct search text
        service_text = query.service or "civic service"
        location_text = query.area or "Bengaluru"
        text_query = f"{service_text} in {location_text}"

        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.location,places.currentOpeningHours,places.websiteUri,places.rating,places.userRatingCount,places.googleMapsUri,places.reviews",
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
                    self._last_error = f"HTTP {response.status_code} {response.reason_phrase}"
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
                        source_url=place.get("googleMapsUri") or website,
                        website=website,
                        external_ids={"google_place_id": place.get("id", "")},
                    )
                    # Google only returns a limited, attributable review sample.
                    # Keep aggregate metrics tied to this place; review text is not
                    # surfaced until a provider-review response contract exists.
                    normalized.rating = place.get("rating")
                    normalized.review_count = place.get("userRatingCount")
                    results.append(normalized)

                return results
        except Exception as exc:
            self._last_error = type(exc).__name__
            logger.error("Error executing Google Places query: %s", self._last_error)
            return []
