import asyncio

from app.schemas.nammaserve import DiscoveryQuery
from app.services.nammaserve.discovery import google_places as google_places_module
from app.services.nammaserve.discovery.google_places import GooglePlacesDiscoveryConnector


class _FakeResponse:
    status_code = 200
    reason_phrase = "OK"

    def json(self):
        return {
            "places": [
                {
                    "id": "places/abc123",
                    "displayName": {"text": "Rajajinagar AC Care"},
                    "formattedAddress": "Rajajinagar, Bengaluru, Karnataka",
                    "location": {"latitude": 12.9918, "longitude": 77.5532},
                    "googleMapsUri": "https://www.google.com/maps/search/?api=1&query=Rajajinagar%20AC%20Care",
                    "rating": 4.4,
                    "userRatingCount": 27,
                }
            ]
        }


class _FakeClient:
    last_request = None

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs["timeout"]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, *, json, headers):
        self.last_request = (url, json, headers)
        _FakeClient.last_request = self.last_request
        return _FakeResponse()


def test_google_places_response_mapping_preserves_place_identity(monkeypatch):
    monkeypatch.setattr(google_places_module.httpx, "AsyncClient", _FakeClient)
    connector = GooglePlacesDiscoveryConnector(api_key="test-key")
    query = DiscoveryQuery(
        service="AC repair",
        area="Rajajinagar, Bengaluru",
        lat=12.9915,
        lng=77.5530,
        radius_km=5,
        limit=5,
    )

    results = asyncio.run(connector.search(query))

    assert len(results) == 1
    assert results[0].external_ids["google_place_id"] == "places/abc123"
    assert results[0].source_url.startswith("https://www.google.com/maps/")
    assert results[0].rating == 4.4
    assert results[0].review_count == 27
    url, body, headers = _FakeClient.last_request
    assert url == "https://places.googleapis.com/v1/places:searchText"
    assert body["textQuery"] == "AC repair in Rajajinagar, Bengaluru"
    assert body["locationBias"]["circle"]["center"] == {"latitude": 12.9915, "longitude": 77.553}
    assert body["locationBias"]["circle"]["radius"] == 5000.0
    assert body["maxResultCount"] == 5
    assert "places.id" in headers["X-Goog-FieldMask"]
