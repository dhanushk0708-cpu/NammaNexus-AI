import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import pytest

from app.db.seeds.categories import seed_categories, CANONICAL_CATEGORIES
from app.models.nammaserve import ServiceCategory, SourceType, VerificationStatus
from app.schemas.nammaserve import DiscoveryQuery
from app.services.nammaserve.discovery.deduplicator import ResultDeduplicator
from app.services.nammaserve.discovery.osm import OpenStreetMapDiscoveryConnector
from app.services.nammaserve.discovery.service import UnifiedDiscoveryService
from app.services.nammaserve.discovery.normalizer import ResultNormalizer


# --------------------------------------------------------------------
# 1. Idempotent Category Seeding Tests
# --------------------------------------------------------------------
def test_seed_categories_idempotent():
    mock_db = MagicMock()
    # Initially empty
    mock_db.query.return_value.filter.return_value.first.return_value = None

    res1 = seed_categories(mock_db)
    assert res1["inserted"] == len(CANONICAL_CATEGORIES)
    assert res1["existing"] == 0

    # Second run: records already exist
    existing_mock = MagicMock(spec=ServiceCategory)
    mock_db.query.return_value.filter.return_value.first.return_value = existing_mock

    res2 = seed_categories(mock_db)
    assert res2["inserted"] == 0
    assert res2["existing"] == len(CANONICAL_CATEGORIES)


# --------------------------------------------------------------------
# 2. OSM Normalization Tests
# --------------------------------------------------------------------
def test_osm_normalization_preserves_unverified_and_unknown_fields():
    item = ResultNormalizer.from_external_payload(
        name="Sri Balaji Electricals",
        phone="",
        source_type=SourceType.OTHER,
        source="OpenStreetMap",
        address="12th Cross, Kengeri Satellite Town",
        area="Kengeri",
        latitude=12.915,
        longitude=77.485,
        distance_km=1.2,
        matched_service_slug="electrical",
        matched_service_name="Electrical",
        source_url="https://www.openstreetmap.org/node/123456",
    )

    assert item.name == "Sri Balaji Electricals"
    assert item.verification_status == VerificationStatus.UNVERIFIED
    assert item.source == "OpenStreetMap"
    assert item.source_url == "https://www.openstreetmap.org/node/123456"
    # Never invent prices
    assert item.price_min is None
    assert item.price_max is None
    assert item.distance_km == 1.2


# --------------------------------------------------------------------
# 3. OSM Connector: Empty Results & Timeouts
# --------------------------------------------------------------------
def test_osm_connector_handles_empty_response():
    connector = OpenStreetMapDiscoveryConnector()

    async def _test():
        with patch("httpx.AsyncClient.post") as mock_post, patch("httpx.AsyncClient.get") as mock_get:
            # Overpass returns 0 elements
            mock_post.return_value = MagicMock(status_code=200, json=lambda: {"elements": []})
            # Nominatim returns empty list
            mock_get.return_value = MagicMock(status_code=200, json=lambda: [])

            query = DiscoveryQuery(service="electrical", lat=12.9177, lng=77.4837, radius_km=5.0)
            res = await connector.search(query)
            assert res == []

    asyncio.run(_test())


def test_osm_connector_handles_timeout_and_429_gracefully():
    connector = OpenStreetMapDiscoveryConnector()

    async def _test():
        with patch("httpx.AsyncClient.post") as mock_post, patch("httpx.AsyncClient.get") as mock_get:
            # Overpass times out
            mock_post.side_effect = httpx.ReadTimeout("Read timed out")
            # Nominatim gets 429
            mock_get.return_value = MagicMock(status_code=429)

            query = DiscoveryQuery(service="plumbing", lat=12.9177, lng=77.4837, radius_km=5.0)
            res = await connector.search(query)
            assert res == []

    asyncio.run(_test())


# --------------------------------------------------------------------
# 4. OSM Deduplication Against Local Database Records
# --------------------------------------------------------------------
def test_osm_deduplication_prefers_verified_local_record():
    local_verified = ResultNormalizer.from_external_payload(
        name="Bangalore Cool Care",
        phone="9876543210",
        source_type=SourceType.LOCAL_DATABASE,
        source="Local Verified Database",
        area="Kengeri",
        latitude=12.9170,
        longitude=77.4830,
        matched_service_slug="ac-repair",
    )
    local_verified.verification_status = VerificationStatus.VERIFIED

    osm_unverified = ResultNormalizer.from_external_payload(
        name="Bangalore Cool Care",
        phone="9876543210",
        source_type=SourceType.OTHER,
        source="OpenStreetMap",
        area="Kengeri",
        latitude=12.9171,
        longitude=77.4831,
        matched_service_slug="ac-repair",
        source_url="https://www.openstreetmap.org/node/999",
    )
    osm_unverified.verification_status = VerificationStatus.UNVERIFIED

    deduped = ResultDeduplicator.deduplicate([osm_unverified, local_verified])
    assert len(deduped) == 1
    # Local verified record must take precedence
    assert deduped[0].verification_status == VerificationStatus.VERIFIED
    assert deduped[0].source == "Local Verified Database"
