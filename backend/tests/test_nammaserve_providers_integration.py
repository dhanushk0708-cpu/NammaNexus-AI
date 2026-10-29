import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from app.models.nammaserve import SourceType, VerificationStatus
from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult
from app.services.nammaserve.ai.providers.base import MissingProviderCredentialsError
from app.services.nammaserve.ai.providers.groq import GroqProvider, HTTPXChatGroq
from app.services.nammaserve.discovery.deduplicator import ResultDeduplicator
from app.services.nammaserve.discovery.foursquare import FoursquareDiscoveryConnector
from app.services.nammaserve.discovery.geoapify import GeoapifyDiscoveryConnector
from app.services.nammaserve.discovery.normalizer import ResultNormalizer
from app.services.nammaserve.discovery.service import UnifiedDiscoveryService


# --------------------------------------------------------------------
# 1. Groq Provider Tests
# --------------------------------------------------------------------
def test_groq_missing_credentials_raises_error():
    provider = GroqProvider()
    with patch("app.services.nammaserve.ai.providers.groq.settings.groq_api_key", None):
        assert provider.is_configured is False
        with pytest.raises(MissingProviderCredentialsError):
            provider.get_chat_model()


def test_groq_httpx_chat_groq_structured_output():
    client = HTTPXChatGroq(api_key="mock_key", model_name="qwen/qwen3.8-27b")

    class MockIntentSchema:
        def __init__(self, service: str, location: str, urgent: bool = False):
            self.service = service
            self.location = location
            self.urgent = urgent

    runner = client.with_structured_output(MockIntentSchema)

    async def _test():
        mock_response = MagicMock(
            status_code=200,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": '{"service": "plumbing", "location": "Indiranagar", "urgent": true}'
                        }
                    }
                ],
                "usage": {"total_tokens": 42},
            },
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            res = await runner.ainvoke([MagicMock(content="need emergency plumber in Indiranagar")])
            assert res.service == "plumbing"
            assert res.location == "Indiranagar"
            assert res.urgent is True

    asyncio.run(_test())


# --------------------------------------------------------------------
# 2. Geoapify Places Connector Tests
# --------------------------------------------------------------------
def test_geoapify_missing_credentials():
    connector = GeoapifyDiscoveryConnector(api_key="")
    assert connector.is_available is False

    async def _test():
        query = DiscoveryQuery(service="electrical", lat=12.9177, lng=77.4837)
        results = await connector.search(query)
        assert results == []

    asyncio.run(_test())


def test_geoapify_successful_places_normalization():
    connector = GeoapifyDiscoveryConnector(api_key="mock_geoapify_key")
    assert connector.is_available is True

    mock_geojson = {
        "features": [
            {
                "properties": {
                    "name": "Kengeri Power Solutions",
                    "lat": 12.9180,
                    "lon": 77.4840,
                    "distance": 850,
                    "formatted": "Main Road, Kengeri, Bengaluru 560060",
                    "suburb": "Kengeri",
                    "contact": {"phone": "080-28485555"},
                    "website": "https://kengeripower.example.com",
                    "place_id": "geo_kengeri_123",
                }
            }
        ]
    }

    async def _test():
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_geojson)
            query = DiscoveryQuery(service="electrical", lat=12.9177, lng=77.4837, radius_km=5.0)
            results = await connector.search(query)

            assert len(results) == 1
            item = results[0]
            assert item.name == "Kengeri Power Solutions"
            assert item.source == "Geoapify Places"
            assert item.source_type == SourceType.GEOAPIFY
            assert item.phone == "080-28485555"
            assert item.verification_status == VerificationStatus.UNVERIFIED
            assert item.distance_km == 0.85
            # Never invent prices
            assert item.price_min is None
            assert item.price_max is None

    asyncio.run(_test())


def test_geoapify_handles_timeout_and_429():
    connector = GeoapifyDiscoveryConnector(api_key="mock_key")

    async def _test():
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ReadTimeout("Geoapify timeout")
            query = DiscoveryQuery(service="plumbing", lat=12.9177, lng=77.4837)
            results = await connector.search(query)
            assert results == []

            mock_get.side_effect = None
            mock_get.return_value = MagicMock(status_code=429)
            results_429 = await connector.search(query)
            assert results_429 == []

    asyncio.run(_test())


# --------------------------------------------------------------------
# 3. Foursquare Places Connector Tests
# --------------------------------------------------------------------
def test_foursquare_missing_credentials():
    connector = FoursquareDiscoveryConnector(api_key="")
    assert connector.is_available is False

    async def _test():
        query = DiscoveryQuery(service="plumbing", lat=12.9177, lng=77.4837)
        results = await connector.search(query)
        assert results == []

    asyncio.run(_test())


def test_foursquare_successful_places_normalization():
    connector = FoursquareDiscoveryConnector(api_key="mock_fsq_key")
    assert connector.is_available is True

    mock_fsq_data = {
        "results": [
            {
                "fsq_id": "fsq_plumb_456",
                "name": "Cauvery Plumbing Services",
                "geocodes": {"main": {"latitude": 12.919, "longitude": 77.485}},
                "distance": 1200,
                "location": {
                    "formatted_address": "8th Block, Kengeri, Bengaluru",
                    "locality": "Kengeri",
                },
                "tel": "9845012345",
                "website": "https://cauveryplumbing.example.com",
            }
        ]
    }

    async def _test():
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_fsq_data)
            query = DiscoveryQuery(service="plumbing", lat=12.9177, lng=77.4837)
            results = await connector.search(query)

            assert len(results) == 1
            item = results[0]
            assert item.name == "Cauvery Plumbing Services"
            assert item.source == "Foursquare Places"
            assert item.source_type == SourceType.FOURSQUARE
            assert item.phone == "9845012345"
            assert item.verification_status == VerificationStatus.UNVERIFIED
            assert item.distance_km == 1.2
            assert item.source_url == "https://foursquare.com/v/fsq_plumb_456"

    asyncio.run(_test())


def test_foursquare_handles_401_and_timeout():
    connector = FoursquareDiscoveryConnector(api_key="mock_key")

    async def _test():
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(status_code=401, text="Invalid auth token")
            query = DiscoveryQuery(service="painting", lat=12.9177, lng=77.4837)
            results = await connector.search(query)
            assert results == []

            mock_get.side_effect = httpx.TimeoutException("Timeout")
            results_to = await connector.search(query)
            assert results_to == []

    asyncio.run(_test())


# --------------------------------------------------------------------
# 4. Multi-Provider Deduplication Tests
# --------------------------------------------------------------------
def test_deduplicator_merges_geoapify_foursquare_and_local():
    local_record = ResultNormalizer.from_external_payload(
        name="Sri Balaji Electricals",
        phone="9845099999",
        source_type=SourceType.LOCAL_DATABASE,
        source="Local Verified Database",
        area="Kengeri",
        latitude=12.915,
        longitude=77.485,
    )
    local_record.verification_status = VerificationStatus.VERIFIED

    geoapify_duplicate = ResultNormalizer.from_external_payload(
        name="Sri Balaji Electricals",
        phone="9845099999",
        source_type=SourceType.GEOAPIFY,
        source="Geoapify Places",
        address="Near Metro Station, Kengeri",
        area="Kengeri",
        latitude=12.9151,
        longitude=77.4851,
        source_url="https://geoapify.com/place/123",
    )
    geoapify_duplicate.verification_status = VerificationStatus.UNVERIFIED

    foursquare_duplicate = ResultNormalizer.from_external_payload(
        name="Sri Balaji Electricals",
        phone="080-9845099999",
        source_type=SourceType.FOURSQUARE,
        source="Foursquare Places",
        area="Kengeri",
        latitude=12.9152,
        longitude=77.4852,
        source_url="https://foursquare.com/v/456",
    )
    foursquare_duplicate.verification_status = VerificationStatus.UNVERIFIED

    foursquare_distinct = ResultNormalizer.from_external_payload(
        name="City Plumbing Care",
        phone="9988776655",
        source_type=SourceType.FOURSQUARE,
        source="Foursquare Places",
        area="Kengeri",
        latitude=12.920,
        longitude=77.490,
    )

    merged = ResultDeduplicator.deduplicate([
        geoapify_duplicate,
        foursquare_duplicate,
        local_record,
        foursquare_distinct,
    ])

    # 3 duplicates should merge into 1 + 1 distinct = 2 total
    assert len(merged) == 2
    balaji = next(r for r in merged if "Balaji" in r.name)
    assert balaji.verification_status == VerificationStatus.VERIFIED
    assert balaji.source == "Local Verified Database"
    # Merged missing fields from Geoapify
    assert balaji.address == "Near Metro Station, Kengeri"
