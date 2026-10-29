import asyncio
from datetime import datetime
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.nammaserve import (
    PlatformListing,
    Provider,
    ProviderOffering,
    ProviderService,
    ProviderServiceArea,
    Service,
    ServiceCategory,
    ServicePrice,
    SourceType,
    VerificationStatus,
)
from app.schemas.nammaserve import (
    DiscoveryQuery,
    NormalizedProviderResult,
    ServiceMatchLevel,
)
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector
from app.services.nammaserve.discovery.cache import (
    DiscoveryResultCache,
    make_discovery_cache_key,
)
from app.services.nammaserve.discovery.deduplicator import ResultDeduplicator
from app.services.nammaserve.discovery.justdial import JustdialDiscoveryConnector
from app.services.nammaserve.discovery.local_db import LocalDBDiscoveryConnector
from app.services.nammaserve.discovery.nobroker import NoBrokerDiscoveryConnector
from app.services.nammaserve.discovery.normalizer import ResultNormalizer
from app.services.nammaserve.discovery.platform_db import PlatformListingDiscoveryConnector
from app.services.nammaserve.discovery.resolver import CatalogueResolver
from app.services.nammaserve.discovery.service import UnifiedDiscoveryService
from app.services.nammaserve.discovery.sulekha import SulekhaDiscoveryConnector
from app.services.nammaserve.discovery.urban_company import UrbanCompanyDiscoveryConnector


# ==========================================================
# In-memory SQLite Database Fixture
# ==========================================================
@pytest.fixture
def phase2_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # 1. Categories
    cat_ac = ServiceCategory(
        id=str(uuid4()),
        slug="ac-repair",
        name="Air Conditioner Repair & Servicing",
        description="AC maintenance and repair",
        icon_name="wind",
    )
    cat_plumbing = ServiceCategory(
        id=str(uuid4()),
        slug="plumbing",
        name="Plumbing & Sanitary Works",
        description="Plumbing services",
        icon_name="wrench",
    )
    cat_cleaning = ServiceCategory(
        id=str(uuid4()),
        slug="home-cleaning",
        name="Home Deep Cleaning",
        description="Residential cleaning",
        icon_name="sparkles",
    )
    session.add_all([cat_ac, cat_plumbing, cat_cleaning])
    session.commit()

    # 2. Individual Services
    svc_split_ac = Service(
        id=str(uuid4()),
        category_id=cat_ac.id,
        slug="split-ac-regular-service",
        name="Split AC Regular Servicing",
        description="Filter and indoor coil cleaning",
        unit="per AC unit",
    )
    svc_flush = Service(
        id=str(uuid4()),
        category_id=cat_plumbing.id,
        slug="toilet-flush-repair",
        name="Toilet Flush & Cistern Repair",
        description="Repair dual flush and internal siphon",
        unit="per fixture",
    )
    session.add_all([svc_split_ac, svc_flush])
    session.commit()

    # 3. Provider A: Offers verified Split AC Regular Servicing (Individual Offering)
    prov_a = Provider(
        id=str(uuid4()),
        name="CoolAir Experts Indiranagar",
        phone="+91 98450 11223",
        address="100ft Road, Indiranagar",
        primary_area="Indiranagar",
        latitude=12.9784,
        longitude=77.6408,
        service_radius_km=10.0,
        verification_status=VerificationStatus.VERIFIED.value,
        source="Field audit",
        last_verified_at=datetime.utcnow(),
    )
    offering_a = ProviderOffering(
        id=str(uuid4()),
        provider=prov_a,
        service=svc_split_ac,
        verification_status=VerificationStatus.VERIFIED.value,
        source="Field audit",
        last_verified_at=datetime.utcnow(),
    )
    price_a = ServicePrice(
        id=str(uuid4()),
        service=svc_split_ac,
        provider_offering=offering_a,
        amount=599.0,
        unit="per unit",
        price_type="fixed",
    )
    session.add_all([prov_a, offering_a, price_a])

    # 4. Provider B: General AC repair provider (Category-level only, no specific offering)
    prov_b = Provider(
        id=str(uuid4()),
        name="Bengaluru General AC Techs",
        phone="+91 98450 99887",
        address="Old Airport Road",
        primary_area="Indiranagar",
        latitude=12.9600,
        longitude=77.6500,
        service_radius_km=8.0,
        verification_status=VerificationStatus.VERIFIED.value,
        source="Phone verified",
        last_verified_at=datetime.utcnow(),
    )
    svc_b = ProviderService(
        id=str(uuid4()),
        provider=prov_b,
        category=cat_ac,
        verification_status=VerificationStatus.VERIFIED.value,
        source="Phone verified",
        last_verified_at=datetime.utcnow(),
    )
    session.add_all([prov_b, svc_b])

    # 5. Provider C: Unrelated Plumbing Provider
    prov_c = Provider(
        id=str(uuid4()),
        name="Quick Plumbers Koramangala",
        phone="+91 97400 33445",
        address="5th Block, Koramangala",
        primary_area="Koramangala",
        latitude=12.9352,
        longitude=77.6245,
        service_radius_km=5.0,
        verification_status=VerificationStatus.VERIFIED.value,
        source="Field audit",
        last_verified_at=datetime.utcnow(),
    )
    svc_c = ProviderService(
        id=str(uuid4()),
        provider=prov_c,
        category=cat_plumbing,
        verification_status=VerificationStatus.VERIFIED.value,
    )
    session.add_all([prov_c, svc_c])

    # 6. Platform Listing: Authentic comparative platform listing for Urban Company
    pl_uc = PlatformListing(
        id=str(uuid4()),
        platform="Urban Company",
        service=svc_split_ac,
        title="Urban Company - Split AC Service (Standard)",
        description="Comprehensive filter wash and indoor unit jet cleaning",
        locality="Indiranagar",
        city="Bengaluru",
        booking_url="https://www.urbancompany.com/bangalore-ac-service",
        verification_status=VerificationStatus.VERIFIED.value,
        source="Urban Company Public Rate Card",
        last_checked_at=datetime.utcnow(),
    )
    pl_price = ServicePrice(
        id=str(uuid4()),
        service=svc_split_ac,
        platform_listing=pl_uc,
        amount=549.0,
        unit="per AC",
        price_type="fixed",
    )
    session.add_all([pl_uc, pl_price])

    session.commit()
    yield session
    session.close()


@pytest.fixture
def phase2_client(phase2_db):
    def override_get_db():
        try:
            yield phase2_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ==========================================================
# 1. Catalogue Slug & Natural Language Query Resolution Tests
# ==========================================================
def test_catalogue_resolver_canonical_slugs(phase2_db):
    """Verify resolution of canonical slugs to specific services and parent categories."""
    r1 = CatalogueResolver.resolve("split-ac-regular-service", db=phase2_db)
    assert r1.is_specific_service is True
    assert r1.service_slug == "split-ac-regular-service"
    assert r1.category_slug == "ac-repair"

    r2 = CatalogueResolver.resolve("toilet-flush-repair", db=phase2_db)
    assert r2.is_specific_service is True
    assert r2.service_slug == "toilet-flush-repair"
    assert r2.category_slug == "plumbing"

    r3 = CatalogueResolver.resolve("ac-repair", db=phase2_db)
    assert r3.is_specific_service is False
    assert r3.category_slug == "ac-repair"


def test_catalogue_resolver_natural_language_queries(phase2_db):
    """Verify resolution of real user queries to canonical catalogue items."""
    # split AC servicing
    res_ac = CatalogueResolver.resolve("split AC regular servicing", db=phase2_db)
    assert res_ac.is_specific_service is True
    assert res_ac.service_slug == "split-ac-regular-service"
    assert res_ac.category_slug == "ac-repair"

    # AC gas refill
    res_gas = CatalogueResolver.resolve("AC gas refill", db=phase2_db)
    assert res_gas.is_specific_service is True
    assert res_gas.service_slug == "ac-gas-refill"
    assert res_gas.category_slug == "ac-repair"

    # 2BHK deep cleaning
    res_clean = CatalogueResolver.resolve("2BHK deep cleaning", db=phase2_db)
    assert res_clean.is_specific_service is True
    assert res_clean.service_slug == "full-home-deep-cleaning-2bhk"
    assert res_clean.category_slug == "home-cleaning"

    # electrical switch replacement
    res_elec = CatalogueResolver.resolve("electrical switch replacement", db=phase2_db)
    assert res_elec.is_specific_service is True
    assert res_elec.service_slug == "switch-socket-repair"
    assert res_elec.category_slug == "electrical"

    # water tanker delivery
    res_tanker = CatalogueResolver.resolve("water tanker delivery", db=phase2_db)
    assert res_tanker.is_specific_service is True
    assert res_tanker.category_slug == "water-tanker"


# ==========================================================
# 2. Provider-to-Service Matching (CONFIRMED vs PROBABLE vs UNCONFIRMED)
# ==========================================================
def test_catalogue_aware_provider_matching(phase2_db):
    """Ensure LocalDB connector distinguishes confirmed offering from probable category match."""
    connector = LocalDBDiscoveryConnector(db=phase2_db)

    query = DiscoveryQuery(
        service="split-ac-regular-service",
        resolved_service_slug="split-ac-regular-service",
        resolved_category_slug="ac-repair",
        area="Indiranagar",
        radius_km=15.0,
    )

    results = asyncio.run(connector.search(query))

    # Should find Prov A (Confirmed) and Prov B (Probable), but NOT Prov C (Plumbing)
    names = [r.name for r in results]
    assert "CoolAir Experts Indiranagar" in names
    assert "Bengaluru General AC Techs" in names
    assert "Quick Plumbers Koramangala" not in names

    # Provider A has exact offering -> CONFIRMED (confidence 1.0) with verified price
    prov_a_result = next(r for r in results if r.name == "CoolAir Experts Indiranagar")
    assert prov_a_result.service_match_level == ServiceMatchLevel.CONFIRMED
    assert prov_a_result.service_match_confidence == 1.0
    assert prov_a_result.price_min == 599.0
    assert prov_a_result.price_unit == "per unit"

    # Provider B has category-level coverage -> PROBABLE (confidence 0.65)
    prov_b_result = next(r for r in results if r.name == "Bengaluru General AC Techs")
    assert prov_b_result.service_match_level == ServiceMatchLevel.PROBABLE
    assert prov_b_result.service_match_confidence == 0.65


# ==========================================================
# 3. Conservative Deduplication and Provenance Preservation
# ==========================================================
def test_conservative_deduplication_external_id_match():
    """Verify deduplication via stable external IDs."""
    r1 = NormalizedProviderResult(
        id="res-1",
        name="SRS Travels Water Tanker",
        phone="9845012345",
        external_ids={"geoapify_id": "geo-12345"},
        sources=["Geoapify Places"],
        verification_status=VerificationStatus.UNVERIFIED,
    )
    r2 = NormalizedProviderResult(
        id="res-2",
        name="SRS Travels Tanker Service",
        phone="9845099999",  # different phone format
        external_ids={"geoapify_id": "geo-12345"},  # matching external ID
        sources=["OpenStreetMap"],
        verification_status=VerificationStatus.UNVERIFIED,
    )

    deduped = ResultDeduplicator.deduplicate([r1, r2])
    assert len(deduped) == 1
    # Both sources preserved in provenance
    assert "Geoapify Places" in deduped[0].sources
    assert "OpenStreetMap" in deduped[0].sources


def test_conservative_deduplication_spatial_boundary():
    """Verify conservative spatial matching: <= 100m merges, > 100m stays distinct."""
    # Base location (Indiranagar 100ft Rd): 12.9784, 77.6408
    r_base = NormalizedProviderResult(
        id="base-1",
        name="Classic Electricals",
        phone="",
        latitude=12.9784,
        longitude=77.6408,
        verification_status=VerificationStatus.UNVERIFIED,
        source="OSM",
    )

    # Identical name ~40 meters away -> should merge
    r_near = NormalizedProviderResult(
        id="near-1",
        name="Classic Electricals",
        phone="",
        latitude=12.9786,
        longitude=77.6410,
        verification_status=VerificationStatus.UNVERIFIED,
        source="Geoapify",
    )

    # Identical generic name ~350 meters away -> MUST NOT merge
    r_far = NormalizedProviderResult(
        id="far-1",
        name="Classic Electricals",
        phone="",
        latitude=12.9815,
        longitude=77.6408,
        verification_status=VerificationStatus.UNVERIFIED,
        source="Foursquare",
    )

    merged_near = ResultDeduplicator.deduplicate([r_base, r_near])
    assert len(merged_near) == 1

    distinct_far = ResultDeduplicator.deduplicate([r_base, r_far])
    assert len(distinct_far) == 2


def test_provenance_preservation_and_verification_protection():
    """Ensure verified provider information is NEVER overwritten by lower-confidence discovery data."""
    verified_local = NormalizedProviderResult(
        id="local-prov-1",
        name="Apex AC Repairs",
        phone="9845011111",
        address="Shop 4, CMH Road, Indiranagar",
        area="Indiranagar",
        verification_status=VerificationStatus.VERIFIED,
        source="Field Audit",
        sources=["Local Verified Database"],
        service_match_level=ServiceMatchLevel.CONFIRMED,
        service_match_confidence=1.0,
    )

    unverified_external = NormalizedProviderResult(
        id="ext-prov-1",
        name="Apex AC Repairs",
        phone="9845011111",  # Same phone
        address="Opposite Metro Station, Indiranagar",  # Lower confidence external description
        area="Indiranagar",
        verification_status=VerificationStatus.UNVERIFIED,
        source="Geoapify Places",
        sources=["Geoapify Places"],
        external_ids={"geoapify_id": "geo-999"},
        website="https://apexac.example.com",  # Enriched field
        service_match_level=ServiceMatchLevel.UNCONFIRMED,
        service_match_confidence=0.35,
    )

    merged = ResultDeduplicator.deduplicate([verified_local, unverified_external])
    assert len(merged) == 1
    winner = merged[0]

    # Verification status remained VERIFIED
    assert winner.verification_status == VerificationStatus.VERIFIED
    # Verified address was not overwritten
    assert winner.address == "Shop 4, CMH Road, Indiranagar"
    # Higher match level preserved
    assert winner.service_match_level == ServiceMatchLevel.CONFIRMED
    assert winner.service_match_confidence == 1.0
    # Provenance tracked both sources
    assert "Local Verified Database" in winner.sources
    assert "Geoapify Places" in winner.sources
    # External ID attached
    assert winner.external_ids.get("geoapify_id") == "geo-999"
    # Missing website enriched
    assert winner.website == "https://apexac.example.com"


# ==========================================================
# 4. Result Normalization & No Fabricated Data
# ==========================================================
def test_normalization_no_fabricated_data():
    """Ensure external normalization never invents missing phones, prices, or ratings."""
    normalized = ResultNormalizer.from_external_payload(
        name="Bengaluru AC Care",
        phone="",  # Missing phone
        source_type=SourceType.GEOAPIFY,
        source="Geoapify Places",
        latitude=12.9716,
        longitude=77.5946,
    )

    assert normalized.phone == ""
    assert normalized.price_min is None
    assert normalized.price_max is None
    assert normalized.price_unit is None
    assert normalized.rating is None
    assert normalized.review_count is None
    assert normalized.verification_status == VerificationStatus.UNVERIFIED
    assert normalized.last_verified_at is None
    assert normalized.service_match_level == ServiceMatchLevel.UNCONFIRMED


# ==========================================================
# 5. Platform Connectors Audit & Database Platform Listings
# ==========================================================
def test_platform_connectors_honest_status():
    """Audit platform connectors to verify they do not perform unauthorized scraping."""
    uc = UrbanCompanyDiscoveryConnector()
    nb = NoBrokerDiscoveryConnector()
    jd = JustdialDiscoveryConnector()
    sul = SulekhaDiscoveryConnector()

    for conn in [uc, nb, jd, sul]:
        assert conn.is_available is False
        status = conn.get_status()
        assert status.is_available is False
        assert len(status.status_message) > 10

        # Must return empty list on search without throwing or making external calls
        res = asyncio.run(conn.search(DiscoveryQuery(service="ac-repair")))
        assert res == []


def test_platform_listing_database_connector(phase2_db):
    """Verify that legitimate platform listings from the database are surfaced honestly."""
    conn = PlatformListingDiscoveryConnector(db=phase2_db)
    query = DiscoveryQuery(
        service="split-ac-regular-service",
        resolved_service_slug="split-ac-regular-service",
    )

    results = asyncio.run(conn.search(query))
    assert len(results) >= 1

    uc_listing = results[0]
    assert "Urban Company" in uc_listing.name
    assert uc_listing.price_min == 549.0
    assert uc_listing.price_unit == "per AC"
    assert uc_listing.service_match_level == ServiceMatchLevel.CONFIRMED
    assert "Urban Company Verified Listing" in uc_listing.sources
    assert uc_listing.source_url == "https://www.urbancompany.com/bangalore-ac-service"


# ==========================================================
# 6. Discovery Cache & Performance Controls
# ==========================================================
def test_discovery_result_cache_lru_and_ttl():
    """Verify cache key determinism, hits, misses, TTL, and LRU eviction."""
    cache = DiscoveryResultCache(max_size=2, default_ttl_seconds=10, enabled=True)

    q1 = DiscoveryQuery(service="split-ac-regular-service", lat=12.9716, lng=77.5946, radius_km=5.0)
    k1 = make_discovery_cache_key(q1)

    r1 = [
        NormalizedProviderResult(
            id="item-1",
            name="Test Provider 1",
            phone="9845011111",
            verification_status=VerificationStatus.UNVERIFIED,
        )
    ]

    # Miss initially
    assert cache.get(k1) is None
    assert cache.stats["misses"] == 1

    # Set and hit
    cache.set(k1, r1)
    hit_res = cache.get(k1)
    assert hit_res is not None
    assert len(hit_res) == 1
    assert hit_res[0].name == "Test Provider 1"
    assert cache.stats["hits"] == 1

    # Bounded size test (max_size=2)
    q2 = DiscoveryQuery(service="toilet-flush-repair", lat=12.9352, lng=77.6245)
    q3 = DiscoveryQuery(service="water-tanker", lat=12.9116, lng=77.6389)
    k2 = make_discovery_cache_key(q2)
    k3 = make_discovery_cache_key(q3)

    cache.set(k2, r1)
    cache.set(k3, r1)  # triggers eviction of oldest key (k1)

    assert cache.stats["evictions"] == 1
    assert cache.get(k1) is None  # evicted


def test_discovery_cache_ttl_expiration():
    """Verify TTL expiry with custom time function."""
    current_time = 1000.0
    cache = DiscoveryResultCache(
        max_size=10,
        default_ttl_seconds=5,
        time_fn=lambda: current_time,
    )

    q = DiscoveryQuery(service="ac-repair")
    k = make_discovery_cache_key(q)
    r = [NormalizedProviderResult(id="1", name="AC", phone="123", verification_status=VerificationStatus.UNVERIFIED)]

    cache.set(k, r)
    assert cache.get(k) is not None

    # Advance time past TTL
    current_time = 1006.0
    assert cache.get(k) is None


# ==========================================================
# 7. Resilient Orchestration & Partial Connector Failures
# ==========================================================
def test_unified_discovery_resilience_on_connector_failure(phase2_db):
    """Verify that a failing connector does not break discovery for other connectors."""
    class FailingConnector(BaseDiscoveryConnector):
        @property
        def name(self) -> str:
            return "Broken External Partner"

        @property
        def source_type(self) -> SourceType:
            return SourceType.OTHER

        async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
            raise RuntimeError("Connection timed out or network error")

    local_conn = LocalDBDiscoveryConnector(db=phase2_db)
    failing_conn = FailingConnector()

    service = UnifiedDiscoveryService(
        db=phase2_db,
        connectors=[local_conn, failing_conn],
        cache=DiscoveryResultCache(enabled=False),
    )

    query = DiscoveryQuery(service="split-ac-regular-service", area="Indiranagar")
    resp = asyncio.run(service.discover(query))

    assert resp.total_results >= 1
    assert any(c.connector_name == "Broken External Partner" for c in resp.connectors_contacted)
    assert any(r.name == "CoolAir Experts Indiranagar" for r in resp.results)


# ==========================================================
# 8. Search API Compatibility & Response Contract
# ==========================================================
def test_search_endpoint_with_canonical_slug(phase2_client):
    """Verify GET /api/v1/nammaserve/search supports ?slug= and ?service= seamlessly."""
    # Test with ?slug=
    resp1 = phase2_client.get(
        "/api/v1/nammaserve/search",
        params={"slug": "split-ac-regular-service", "area": "Indiranagar"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["total_results"] >= 1
    assert "connectors_contacted" in data1
    assert "results" in data1

    first_item = data1["results"][0]
    assert "service_match_level" in first_item
    assert "service_match_confidence" in first_item
    assert "sources" in first_item
    assert "verification_status" in first_item

    # Test backward compatibility with ?service=
    resp2 = phase2_client.get(
        "/api/v1/nammaserve/search",
        params={"service": "split AC regular servicing", "area": "Indiranagar"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total_results"] >= 1
