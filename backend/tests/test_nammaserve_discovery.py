from datetime import datetime
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
    Provider,
    ProviderService,
    ProviderServiceArea,
    ServiceCategory,
    SourceType,
    VerificationStatus,
)
from app.schemas.nammaserve import (
    DiscoveryQuery,
    NormalizedProviderResult,
)
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector
from app.services.nammaserve.discovery.deduplicator import ResultDeduplicator, normalize_name, normalize_phone
from app.services.nammaserve.discovery.distance import haversine_distance_km
from app.services.nammaserve.discovery.google_places import GooglePlacesDiscoveryConnector
from app.services.nammaserve.discovery.local_db import LocalDBDiscoveryConnector
from app.services.nammaserve.discovery.nobroker import NoBrokerDiscoveryConnector
from app.services.nammaserve.discovery.ranking import DeterministicRankingEngine
from app.services.nammaserve.discovery.service import UnifiedDiscoveryService
from app.services.nammaserve.discovery.urban_company import UrbanCompanyDiscoveryConnector
from app.services.nammaserve.discovery.web_search import WebSearchDiscoveryConnector


# In-memory SQLite DB fixture for isolated deterministic testing
@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Seed 5 standard civic categories
    cat_water = ServiceCategory(
        id=str(uuid4()),
        slug="water-tanker",
        name="Water Tanker / Bulk Water Delivery",
        description="Potable and domestic bulk water delivery tankers",
        icon_name="droplets",
    )
    cat_solar = ServiceCategory(
        id=str(uuid4()),
        slug="solar-heater-repair",
        name="Solar Water-Heater Repair & Maintenance",
        description="Technicians for solar water heating panels and tanks",
        icon_name="sun",
    )
    cat_ewaste = ServiceCategory(
        id=str(uuid4()),
        slug="e-waste-pickup",
        name="E-Waste Pickup & Recycling",
        description="Certified electronic waste collection and disposal",
        icon_name="recycle",
    )
    cat_locksmith = ServiceCategory(
        id=str(uuid4()),
        slug="locksmith-emergency",
        name="Locksmith / Emergency Key Service",
        description="24x7 key makers and lockout emergency specialists",
        icon_name="key",
    )
    cat_debris = ServiceCategory(
        id=str(uuid4()),
        slug="debris-bulk-waste",
        name="Construction Debris & Bulk-Waste Pickup",
        description="Mini-trucks and loaders for construction waste",
        icon_name="truck",
    )
    session.add_all([cat_water, cat_solar, cat_ewaste, cat_locksmith, cat_debris])
    session.commit()

    # Seed Provider 1: Cauvery Springs (HSR Layout - Lat: 12.9116, Lng: 77.6389)
    p1 = Provider(
        id=str(uuid4()),
        name="Cauvery Springs Water Supply",
        contact_person="Ramesh Kumar",
        phone="+91 98450 11223",
        address="14th Main, Sector 2, HSR Layout",
        primary_area="HSR Layout",
        latitude=12.9116,
        longitude=77.6389,
        service_radius_km=7.0,
        operating_hours="06:00 - 22:00",
        is_emergency_service=False,
        verification_status=VerificationStatus.VERIFIED.value,
        source="Direct field verification",
        source_type=SourceType.DIRECT_PROVIDER.value,
        last_verified_at=datetime.utcnow(),
    )
    ps1 = ProviderService(
        id=str(uuid4()),
        provider=p1,
        category=cat_water,
        price_min=850.0,
        price_max=1100.0,
        price_unit="per 6000L tanker",
        minimum_order="6000 Litres",
        capacity="6000L & 12000L",
        water_type="Borewell / Potable (TDS ~350)",
        availability="Within 90 mins",
        payment_methods="UPI, Cash",
        verification_status=VerificationStatus.VERIFIED.value,
        source="Verified rate card",
        source_type=SourceType.DIRECT_PROVIDER.value,
        last_verified_at=datetime.utcnow(),
    )
    pa1 = ProviderServiceArea(
        id=str(uuid4()),
        provider=p1,
        area_name="HSR Layout",
    )
    session.add_all([p1, ps1, pa1])

    # Seed Provider 2: QuickKey Locksmith (Koramangala - Lat: 12.9352, Lng: 77.6245) - 24x7
    p2 = Provider(
        id=str(uuid4()),
        name="QuickKey 24x7 Locksmith",
        contact_person="Manjunath",
        phone="+91 99000 88776",
        address="80ft Road, 4th Block, Koramangala",
        primary_area="Koramangala",
        latitude=12.9352,
        longitude=77.6245,
        service_radius_km=10.0,
        operating_hours="24x7",
        is_emergency_service=True,
        verification_status=VerificationStatus.VERIFIED.value,
        source="Shop audit",
        source_type=SourceType.LOCAL_DATABASE.value,
        last_verified_at=datetime.utcnow(),
    )
    ps2 = ProviderService(
        id=str(uuid4()),
        provider=p2,
        category=cat_locksmith,
        price_min=350.0,
        price_max=800.0,
        price_unit="per visit",
        availability="30 mins",
        payment_methods="UPI, Cash",
        verification_status=VerificationStatus.VERIFIED.value,
        source="Rate card",
        source_type=SourceType.LOCAL_DATABASE.value,
        last_verified_at=datetime.utcnow(),
    )
    session.add_all([p2, ps2])

    # Seed Provider 3: EcoBengaluru Recyclers (Indiranagar - Lat: 12.9784, Lng: 77.6408)
    p3 = Provider(
        id=str(uuid4()),
        name="EcoBengaluru Recyclers",
        contact_person="Ananya",
        phone="+91 80252 56677",
        address="100ft Road, Indiranagar",
        primary_area="Indiranagar",
        latitude=12.9784,
        longitude=77.6408,
        service_radius_km=8.0,
        operating_hours="09:00 - 18:00",
        is_emergency_service=False,
        verification_status=VerificationStatus.VERIFIED.value,
        source="KSPCB Directory",
        source_type=SourceType.LOCAL_DATABASE.value,
        last_verified_at=datetime.utcnow(),
    )
    ps3 = ProviderService(
        id=str(uuid4()),
        provider=p3,
        category=cat_ewaste,
        price_min=0.0,
        price_max=0.0,
        price_unit="Free pickup",
        minimum_order="5 kg",
        verification_status=VerificationStatus.VERIFIED.value,
        source="KSPCB",
        source_type=SourceType.LOCAL_DATABASE.value,
        last_verified_at=datetime.utcnow(),
    )
    session.add_all([p3, ps3])

    # Seed Provider 4: Far-away unverified water provider (Yelahanka - Lat: 13.1007, Lng: 77.5963)
    p4 = Provider(
        id=str(uuid4()),
        name="North Water Tankers",
        phone="+91 91234 56789",
        primary_area="Yelahanka",
        latitude=13.1007,
        longitude=77.5963,
        service_radius_km=5.0,
        verification_status=VerificationStatus.UNVERIFIED.value,
        source="Web listing",
        source_type=SourceType.WEB.value,
    )
    ps4 = ProviderService(
        id=str(uuid4()),
        provider=p4,
        category=cat_water,
        verification_status=VerificationStatus.UNVERIFIED.value,
        source="Web listing",
        source_type=SourceType.WEB.value,
    )
    session.add_all([p4, ps4])

    session.commit()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ==========================================================
# 1. Distance Calculation & Spatial Radius Tests
# ==========================================================
def test_haversine_distance_calculation():
    # Distance between HSR Layout (12.9116, 77.6389) and Koramangala (12.9352, 77.6245) is ~3.0 km
    dist = haversine_distance_km(12.9116, 77.6389, 12.9352, 77.6245)
    assert 2.5 <= dist <= 3.5

    # Same point distance is 0.0
    assert haversine_distance_km(12.9716, 77.5946, 12.9716, 77.5946) == 0.0


def test_local_db_spatial_radius_search(db_session):
    import asyncio

    connector = LocalDBDiscoveryConnector(db_session)

    # Search near HSR Layout (Lat: 12.9116, Lng: 77.6389) with 5km radius for water tanker
    query = DiscoveryQuery(
        service="water-tanker",
        lat=12.9116,
        lng=77.6389,
        radius_km=5.0,
    )
    results = asyncio.run(connector.search(query))

    # Should find Cauvery Springs (in HSR, dist 0.0 km) but NOT North Water Tankers (in Yelahanka, > 20 km)
    assert len(results) == 1
    assert results[0].name == "Cauvery Springs Water Supply"
    assert results[0].distance_km == 0.0
    assert results[0].matched_service_slug == "water-tanker"


# ==========================================================
# 2. Service & Verification Filtering Tests
# ==========================================================
def test_service_category_filtering(db_session):
    import asyncio

    connector = LocalDBDiscoveryConnector(db_session)

    # Search for locksmith
    query = DiscoveryQuery(service="locksmith-emergency")
    results = asyncio.run(connector.search(query))

    assert len(results) == 1
    assert results[0].name == "QuickKey 24x7 Locksmith"
    assert results[0].is_emergency_service is True


def test_verification_filtering(db_session):
    import asyncio

    connector = LocalDBDiscoveryConnector(db_session)

    # Search with verified_only=True for water tanker (no lat/lng, wide search)
    query = DiscoveryQuery(
        service="water-tanker",
        verified_only=True,
    )
    results = asyncio.run(connector.search(query))

    for r in results:
        assert r.verification_status == VerificationStatus.VERIFIED
    assert any(r.name == "Cauvery Springs Water Supply" for r in results)
    assert not any(r.name == "North Water Tankers" for r in results)


# ==========================================================
# 3. Deterministic Ranking Tests
# ==========================================================
def test_deterministic_ranking_scores():
    # Verified, ultra-close provider vs Unverified far provider
    p_verified = NormalizedProviderResult(
        id="1",
        name="Verified Water Pro",
        phone="9876543210",
        distance_km=1.2,
        matched_service_slug="water-tanker",
        matched_service_name="Water Tanker",
        price_min=800.0,
        price_max=1000.0,
        price_unit="per 6000L",
        verification_status=VerificationStatus.VERIFIED,
    )
    p_unverified = NormalizedProviderResult(
        id="2",
        name="Unverified Water Vendor",
        phone="9876543211",
        distance_km=8.5,
        matched_service_slug="water-tanker",
        matched_service_name="Water Tanker",
        verification_status=VerificationStatus.UNVERIFIED,
    )

    query = DiscoveryQuery(service="water-tanker", lat=12.9116, lng=77.6389)
    ranked = DeterministicRankingEngine.rank_results([p_unverified, p_verified], query)

    assert ranked[0].id == "1"
    assert ranked[0].match_score > ranked[1].match_score
    assert "Verified by NammaNexus team" in ranked[0].ranking_reasons
    assert any("Ultra-close proximity" in r for r in ranked[0].ranking_reasons)
    assert any("Transparent pricing" in r for r in ranked[0].ranking_reasons)


# ==========================================================
# 4. Source & Evidence Handling Tests
# ==========================================================
def test_source_evidence_metadata():
    provider = NormalizedProviderResult(
        id="123",
        name="Solar Masters",
        phone="9845012345",
        source="Field verified rate card",
        source_type=SourceType.DIRECT_PROVIDER,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.utcnow(),
    )
    assert provider.source_type == SourceType.DIRECT_PROVIDER
    assert provider.verification_status == VerificationStatus.VERIFIED
    assert provider.source == "Field verified rate card"
    assert provider.last_verified_at is not None


# ==========================================================
# 5. Connector Architecture & Unavailable Behavior Tests
# ==========================================================
def test_connector_interfaces_and_unavailable_status():
    import asyncio

    uc_connector = UrbanCompanyDiscoveryConnector()
    nb_connector = NoBrokerDiscoveryConnector()
    web_connector = WebSearchDiscoveryConnector()
    # Use an explicit empty key so this test remains deterministic even when
    # the developer's local environment has a configured Places credential.
    gp_connector = GooglePlacesDiscoveryConnector(api_key="")

    assert uc_connector.is_available is False
    assert nb_connector.is_available is False
    assert web_connector.is_available is False
    assert gp_connector.is_available is False

    # Calling search on unavailable connectors safely returns empty list
    query = DiscoveryQuery(service="water-tanker")
    assert asyncio.run(uc_connector.search(query)) == []
    assert asyncio.run(nb_connector.search(query)) == []
    assert asyncio.run(web_connector.search(query)) == []
    assert asyncio.run(gp_connector.search(query)) == []

    # Status check reports not configured
    status_uc = uc_connector.get_status()
    assert status_uc.is_available is False
    assert "not configured" in status_uc.status_message


# ==========================================================
# 6. Deduplication Tests
# ==========================================================
def test_phone_and_name_deduplication():
    assert normalize_phone("+91 (98450) 11223") == "9845011223"
    assert normalize_phone("09845011223") == "9845011223"
    assert normalize_name("Cauvery Springs Water Supply!") == "cauveryspringswatersupply"

    r1 = NormalizedProviderResult(
        id="local-1",
        name="Cauvery Springs Water Supply",
        phone="+91 98450 11223",
        verification_status=VerificationStatus.VERIFIED,
        source_type=SourceType.LOCAL_DATABASE,
    )
    r2 = NormalizedProviderResult(
        id="google-1",
        name="Cauvery Springs Water",
        phone="98450 11223",
        verification_status=VerificationStatus.UNVERIFIED,
        source_type=SourceType.GOOGLE_PLACES,
        address="14th Main, HSR Layout",
    )

    deduped = ResultDeduplicator.deduplicate([r1, r2])
    assert len(deduped) == 1
    # Preserves the verified local DB entry and enriches address
    assert deduped[0].id == "local-1"
    assert deduped[0].verification_status == VerificationStatus.VERIFIED
    assert deduped[0].address == "14th Main, HSR Layout"


# ==========================================================
# 7. Unified Discovery Service & API Tests
# ==========================================================
def test_unified_discovery_service(db_session):
    import asyncio

    # Mock connector alongside local DB
    class MockExternalConnector(BaseDiscoveryConnector):
        @property
        def name(self) -> str:
            return "Mock Partner"

        @property
        def source_type(self) -> SourceType:
            return SourceType.OTHER

        async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
            return [
                NormalizedProviderResult(
                    id="ext-1",
                    name="External Solar Specialist",
                    phone="9988776655",
                    matched_service_slug="solar-heater-repair",
                    matched_service_name="Solar Heater Repair",
                    area="Jayanagar",
                    distance_km=3.5,
                    verification_status=VerificationStatus.UNVERIFIED,
                    source="Partner feed",
                    source_type=SourceType.OTHER,
                )
            ]

    service = UnifiedDiscoveryService(
        db=db_session,
        connectors=[
            LocalDBDiscoveryConnector(db=db_session),
            MockExternalConnector(),
            UrbanCompanyDiscoveryConnector(),
        ],
    )

    response = asyncio.run(service.discover(DiscoveryQuery(service="solar-heater-repair")))
    assert response.total_results >= 1
    assert any(r.name == "External Solar Specialist" for r in response.results)
    assert len(response.connectors_contacted) == 3


def test_api_categories_endpoint(client):
    response = client.get("/api/v1/nammaserve/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    slugs = [c["slug"] for c in data]
    assert "water-tanker" in slugs
    assert "locksmith-emergency" in slugs


def test_api_search_endpoint(client):
    # Search for emergency locksmith in Koramangala
    response = client.get(
        "/api/v1/nammaserve/search",
        params={
            "service": "locksmith-emergency",
            "lat": 12.9352,
            "lng": 77.6245,
            "radius_km": 5.0,
            "emergency_only": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] >= 1
    top_result = data["results"][0]
    assert top_result["name"] == "QuickKey 24x7 Locksmith"
    assert top_result["is_emergency_service"] is True
    assert top_result["match_score"] > 50.0
    assert len(top_result["ranking_reasons"]) > 0
    assert len(data["connectors_contacted"]) >= 1


def test_api_provider_details_endpoint(client, db_session):
    p = db_session.query(Provider).first()
    assert p is not None

    response = client.get(f"/api/v1/nammaserve/providers/{p.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == p.id
    assert data["name"] == p.name
    assert "services" in data
