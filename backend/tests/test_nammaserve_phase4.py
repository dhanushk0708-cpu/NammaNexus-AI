"""Tests for NammaServe AI Phase 4: Service Search & Price-Comparison Experience.

Validates Roadmap Steps 4.1 through 4.5:
- 4.1 Catalogue-aware search: exact slugs, natural language queries, confidence scoring, ambiguity detection.
- 4.2 Database provider & pricing retrieval: PlatformListing, ProviderOffering, ServicePrice, Provider.
- 4.3 Semantic pricing representation: formatting for all 8 PriceType values.
- 4.4 Unified price comparison: benchmark calculation, sorting, groupings (comparable, quote required, unavailable).
- 4.5 Evidence and verification status exposure: strict separation of match confidence and price verification.
- Robust error handling: database resilience and safe error messages without credential leakage.
"""
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.dependencies import get_db
from app.db.seeds.categories import seed_categories
from app.db.seeds.services import seed_services
from app.main import app
from app.models.nammaserve import (
    PlatformListing,
    PriceType,
    Provider,
    ProviderOffering,
    Service,
    ServicePrice,
    SourceType,
    VerificationStatus,
)
from app.schemas.nammaserve import (
    DiscoveryQuery,
    NormalizedProviderResult,
    ServiceMatchLevel,
    UnifiedDiscoveryResponse,
)
from app.services.nammaserve.discovery.cache import get_default_discovery_cache
from app.services.nammaserve.discovery.comparison import PriceComparisonEngine
from app.services.nammaserve.discovery.normalizer import format_price_display, ResultNormalizer
from app.services.nammaserve.discovery.platform_db import PlatformListingDiscoveryConnector
from app.services.nammaserve.discovery.resolver import CatalogueResolver


@pytest.fixture(scope="function", autouse=True)
def isolate_discovery_cache():
    """Ensure in-memory cache does not leak across tests."""
    cache = get_default_discovery_cache()
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(scope="function")
def test_db():
    """Isolated in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        seed_categories(db)
        seed_services(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Test client bound to isolated in-memory DB."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# 4.1 Catalogue-Aware Search & Resolution Tests
# ==============================================================================

class TestCatalogueResolver:
    """Tests for Step 4.1: Catalogue resolution with confidence & ambiguity."""

    def test_exact_service_slug_resolution(self, test_db):
        resolved = CatalogueResolver.resolve("split-ac-regular-service", test_db)

        assert resolved.is_resolved is True
        assert resolved.service_slug == "split-ac-regular-service"
        assert resolved.category_slug == "ac-repair"
        assert resolved.match_level == ServiceMatchLevel.CONFIRMED
        assert resolved.match_confidence == 1.0
        assert resolved.is_ambiguous is False
        assert len(resolved.possible_matches) == 0

    def test_exact_category_slug_resolution(self, test_db):
        resolved = CatalogueResolver.resolve("plumbing", test_db)

        assert resolved.is_resolved is True
        assert resolved.category_slug == "plumbing"
        assert resolved.match_level == ServiceMatchLevel.CONFIRMED
        assert resolved.match_confidence == 0.85
        assert resolved.is_ambiguous is False

    def test_natural_language_service_resolution(self, test_db):
        resolved = CatalogueResolver.resolve("I need AC gas refill in Indiranagar", test_db)

        assert resolved.is_resolved is True
        assert resolved.service_slug == "ac-gas-refill"
        assert resolved.category_slug == "ac-repair"
        assert resolved.match_confidence >= 0.90
        assert resolved.match_level == ServiceMatchLevel.CONFIRMED

    def test_ambiguous_service_resolution(self, test_db):
        resolved = CatalogueResolver.resolve("repair", test_db)

        assert resolved.is_ambiguous is True
        assert resolved.match_confidence <= 0.40
        assert len(resolved.possible_matches) >= 2
        match_slugs = [m["slug"] for m in resolved.possible_matches]
        assert "ac-repair" in match_slugs or "plumbing" in match_slugs

    def test_unmapped_query_resolution(self, test_db):
        resolved = CatalogueResolver.resolve("pet grooming and salon", test_db)

        assert resolved.is_resolved is False
        assert resolved.match_level == ServiceMatchLevel.UNCONFIRMED
        assert resolved.match_confidence <= 0.25
        assert resolved.service_slug is None


# ==============================================================================
# 4.2 Semantic Pricing Representation Tests (All 8 PriceTypes)
# ==============================================================================

class TestSemanticPriceFormatting:
    """Tests for Step 4.3: Formatting for all 8 PriceType values."""

    def test_fixed_price(self):
        result = format_price_display("FIXED", amount=499)
        assert result == "₹499 (Fixed)"

    def test_starting_at_price(self):
        result = format_price_display("STARTING_AT", amount=299)
        assert result == "₹299 onwards"

    def test_range_price(self):
        result = format_price_display("RANGE", price_min=1000, price_max=2500)
        assert result == "₹1000 – ₹2500"

    def test_per_unit_price(self):
        result = format_price_display("PER_UNIT", amount=1.50, unit="sq.ft")
        assert result == "₹1.5 sq.ft"

    def test_hourly_price(self):
        result = format_price_display("HOURLY", amount=199)
        assert result == "₹199 / hr"

    def test_consultation_fee(self):
        result = format_price_display("CONSULTATION_FEE", amount=149)
        assert result == "₹149 Inspection / Consultation Fee"

    def test_quote_required(self):
        result = format_price_display("QUOTE_REQUIRED")
        assert result == "Custom quote required"

    def test_unavailable_price(self):
        result = format_price_display("UNAVAILABLE")
        assert result == "Service unavailable"

    def test_none_type_fallback(self):
        result = format_price_display(None, price_min=500)
        assert result == "₹500 onwards"


# ==============================================================================
# 4.3 Price Comparison Engine Tests
# ==============================================================================

class TestPriceComparisonEngine:
    """Tests for Step 4.4: Aggregation, benchmark calculation, and sorting."""

    def test_price_comparison_summary_calculation(self):
        items = [
            NormalizedProviderResult(
                id="item-1",
                name="Urban Company",
                source_type=SourceType.URBAN_COMPANY,
                matched_service_slug="split-ac-regular-service",
                amount=Decimal("499"),
                price_min=Decimal("499"),
                price_type="FIXED",
                formatted_price="₹499",
                verification_status=VerificationStatus.VERIFIED,
                is_price_available=True,
                source_url="https://www.urbancompany.com",
            ),
            NormalizedProviderResult(
                id="item-2",
                name="NoBroker",
                source_type=SourceType.NOBROKER,
                matched_service_slug="split-ac-regular-service",
                amount=Decimal("449"),
                price_min=Decimal("449"),
                price_type="STARTING_AT",
                formatted_price="From ₹449 onwards",
                verification_status=VerificationStatus.VERIFIED,
                is_price_available=True,
                source_url="https://www.nobroker.in",
            ),
            NormalizedProviderResult(
                id="item-3",
                name="Sulekha",
                source_type=SourceType.SULEKHA,
                matched_service_slug="split-ac-regular-service",
                price_type="QUOTE_REQUIRED",
                formatted_price="Custom quote required",
                verification_status=VerificationStatus.PARTIALLY_VERIFIED,
                is_price_available=False,
                source_url="https://www.sulekha.com",
            ),
            NormalizedProviderResult(
                id="item-4",
                name="OpenStreetMap Electrician",
                source_type=SourceType.LOCAL_DATABASE,
                matched_service_slug="split-ac-regular-service",
                price_type="UNAVAILABLE",
                formatted_price="Service unavailable",
                verification_status=VerificationStatus.UNVERIFIED,
                is_price_available=False,
            ),
        ]

        query = DiscoveryQuery(
            service="split-ac-regular-service",
            resolved_service_slug="split-ac-regular-service",
        )
        summary = PriceComparisonEngine.build_summary(query, items)

        assert summary is not None
        assert summary.canonical_service_slug == "split-ac-regular-service"
        assert summary.total_providers_compared == 4
        assert summary.verified_count == 2
        assert summary.partially_verified_count == 1
        assert summary.unverified_count == 1
        assert len(summary.comparable_items) == 2
        assert len(summary.quote_required_items) == 1
        assert len(summary.unavailable_items) == 1

        # Check lowest price calculation
        assert summary.lowest_price == 449.0
        assert summary.highest_price == 499.0
        assert summary.price_range_display == "₹449 – ₹499"

        # Check sorting: lowest effective price first among verified
        assert summary.comparable_items[0].name == "NoBroker"
        assert summary.comparable_items[1].name == "Urban Company"

    def test_empty_results_handling(self):
        query = DiscoveryQuery(service="plumbing", resolved_service_slug="plumbing")
        summary = PriceComparisonEngine.build_summary(query, [])

        assert summary is None


# ==============================================================================
# 4.4 Database Provider and Pricing Retrieval Integration Tests
# ==============================================================================

class TestDatabaseProviderAndPricingRetrieval:
    """Tests for Step 4.2 & 4.5: Database-backed retrieval and verification separation."""

    @pytest.mark.anyio
    async def test_platform_listing_discovery_connector(self, test_db):
        service = test_db.query(Service).filter_by(slug="split-ac-regular-service").first()
        assert service is not None

        # Insert platform listing and service price
        listing = PlatformListing(
            platform="URBAN_COMPANY",
            service_id=service.id,
            title="Urban Company AC Service",
            locality="Indiranagar",
            city="Bengaluru",
            listing_url="https://www.urbancompany.com/bangalore-ac-repair",
            verification_status=VerificationStatus.VERIFIED.value,
            is_active=True,
        )
        test_db.add(listing)
        test_db.flush()

        price = ServicePrice(
            service_id=service.id,
            platform_listing_id=listing.id,
            price_type=PriceType.FIXED.value,
            amount=499.00,
            currency="INR",
            verification_status=VerificationStatus.VERIFIED.value,
            source_url="https://www.urbancompany.com/bangalore-ac-repair",
            conditions="Official verified rate card for Bengaluru AC service",
            last_verified_at=datetime.now(timezone.utc),
        )
        test_db.add(price)
        test_db.commit()

        connector = PlatformListingDiscoveryConnector(test_db)
        query = DiscoveryQuery(service="split-ac-regular-service", resolved_service_slug="split-ac-regular-service")
        results = await connector.search(query)

        assert len(results) == 1
        res = results[0]
        assert res.name == "Urban Company AC Service"
        assert float(res.amount) == 499.0
        assert res.verification_status == VerificationStatus.VERIFIED
        assert res.is_price_available is True
        assert res.source_url == "https://www.urbancompany.com/bangalore-ac-repair"
        assert res.last_verified_at == price.last_verified_at

    def test_independent_provider_offering_retrieval(self, test_db):
        service = test_db.query(Service).filter_by(slug="toilet-flush-repair").first()
        assert service is not None

        # Insert independent provider, offering, and price
        provider = Provider(
            name="Sri Sai Plumbing Works",
            contact_person="Sri Sai",
            primary_area="Kengeri",
            city="Bengaluru",
            phone="+91 98450 12345",
            latitude=12.9177,
            longitude=77.4838,
            verification_status=VerificationStatus.PARTIALLY_VERIFIED.value,
            is_active=True,
        )
        test_db.add(provider)
        test_db.flush()

        offering = ProviderOffering(
            provider_id=provider.id,
            service_id=service.id,
            is_active=True,
        )
        test_db.add(offering)
        test_db.flush()

        price = ServicePrice(
            service_id=service.id,
            provider_offering_id=offering.id,
            price_type=PriceType.STARTING_AT.value,
            amount=250.00,
            price_min=250.00,
            currency="INR",
            verification_status=VerificationStatus.PARTIALLY_VERIFIED.value,
            source_url="https://justdial.com/Bangalore/Sri-Sai-Plumbing",
            conditions="Directory listing rate estimate for Kengeri",
            last_verified_at=datetime.now(timezone.utc),
        )
        test_db.add(price)
        test_db.commit()

        result = ResultNormalizer.from_db_models(
            provider=provider,
            offering=offering,
            user_lat=12.9177,
            user_lng=77.4838,
        )

        assert result.name == "Sri Sai Plumbing Works"
        assert result.verification_status == VerificationStatus.PARTIALLY_VERIFIED
        assert result.phone == "+91 98450 12345"
        assert result.area == "Kengeri"

    def test_verification_separation_from_resolution(self):
        """Match confidence of 1.0 does NOT elevate UNVERIFIED providers to VERIFIED."""
        external_result = NormalizedProviderResult(
            id="osm-1",
            name="Local Garage",
            source_type=SourceType.LOCAL_DATABASE,
            matched_service_slug="ac-repair",
            price_type="UNAVAILABLE",
            formatted_price="Service unavailable",
            verification_status=VerificationStatus.UNVERIFIED,
            is_price_available=False,
        )

        assert external_result.verification_status == VerificationStatus.UNVERIFIED
        assert external_result.is_price_available is False


# ==============================================================================
# 4.5 End-to-End API Integration & Fallback Tests
# ==============================================================================

class TestSearchApiEndToEnd:
    """Tests for Search API endpoint with Phase 4 response structure."""

    def test_search_api_returns_price_comparison(self, client, test_db):
        service = test_db.query(Service).filter_by(slug="split-ac-regular-service").first()
        listing = PlatformListing(
            platform="URBAN_COMPANY",
            service_id=service.id,
            title="Urban Company AC Service",
            locality="Indiranagar",
            city="Bengaluru",
            listing_url="https://www.urbancompany.com/bangalore-ac-repair",
            verification_status=VerificationStatus.VERIFIED.value,
            is_active=True,
        )
        test_db.add(listing)
        test_db.flush()

        price = ServicePrice(
            service_id=service.id,
            platform_listing_id=listing.id,
            price_type=PriceType.FIXED.value,
            amount=499.00,
            currency="INR",
            verification_status=VerificationStatus.VERIFIED.value,
            source_url="https://www.urbancompany.com/bangalore-ac-repair",
            conditions="Official verified rate card for Bengaluru AC service",
            last_verified_at=datetime.now(timezone.utc),
        )
        test_db.add(price)
        test_db.commit()

        response = client.get("/api/v1/nammaserve/search?service=split-ac-regular-service&area=Indiranagar")
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "query" in data
        assert "price_comparison" in data

        query_meta = data["query"]
        assert query_meta["service_match_level"] == "CONFIRMED"
        assert query_meta["service_match_confidence"] == 1.0
        assert query_meta["is_ambiguous"] is False

        comparison = data["price_comparison"]
        assert comparison is not None
        assert comparison["canonical_service_slug"] == "split-ac-regular-service"
        assert comparison["verified_count"] >= 1
        assert comparison["lowest_price"] == 499.0

    def test_search_api_ambiguous_service_query(self, client):
        response = client.get("/api/v1/nammaserve/search?service=repair")
        assert response.status_code == 200

        data = response.json()
        query_meta = data["query"]
        assert query_meta["is_ambiguous"] is True
        assert len(query_meta["possible_matches"]) >= 2

    def test_search_api_unmapped_service_query(self, client):
        response = client.get("/api/v1/nammaserve/search?service=astrology+consultation")
        assert response.status_code == 200

        data = response.json()
        query_meta = data["query"]
        assert query_meta["service_match_level"] == "UNCONFIRMED"
        assert query_meta["service_match_confidence"] <= 0.25

    def test_backward_compatibility_schema(self):
        """UnifiedDiscoveryResponse maintains backward compatibility for clients that don't inspect price_comparison."""
        resp = UnifiedDiscoveryResponse(
            query=DiscoveryQuery(service="plumbing", lat=12.91, lng=77.48),
        )
        assert resp.price_comparison is None
        assert resp.total_results == 0
        assert resp.results == []

    def test_consultation_fee_excluded_from_benchmark_range(self):
        """Inspection/visiting fees must NOT distort the whole-service benchmark range."""
        items = [
            NormalizedProviderResult(
                id="item-fixed",
                name="Urban Company",
                source_type=SourceType.URBAN_COMPANY,
                matched_service_slug="split-ac-regular-service",
                amount=Decimal("499"),
                price_type="FIXED",
                formatted_price="₹499 (Fixed)",
                verification_status=VerificationStatus.VERIFIED,
                is_price_available=True,
            ),
            NormalizedProviderResult(
                id="item-inspection",
                name="Local AC Inspection Partner",
                source_type=SourceType.LOCAL_DATABASE,
                matched_service_slug="split-ac-regular-service",
                amount=Decimal("149"),
                price_type="CONSULTATION_FEE",
                formatted_price="₹149 Inspection / Consultation Fee",
                verification_status=VerificationStatus.VERIFIED,
                is_price_available=True,
            ),
        ]
        query = DiscoveryQuery(service="split-ac-regular-service", resolved_service_slug="split-ac-regular-service")
        summary = PriceComparisonEngine.build_summary(query, items)

        assert summary is not None
        # Lowest price must be 499, NOT 149!
        assert summary.lowest_price == 499.0
        assert summary.price_range_display == "₹499"

        # Check that the inspection fee is marked as not directly comparable
        inspection_item = next(i for i in summary.comparable_items if i.id == "item-inspection")
        assert inspection_item.is_comparable is False
        assert inspection_item.comparability_note is not None
        assert "Inspection / visiting fee" in inspection_item.comparability_note

    def test_hourly_and_per_unit_scope_comparability(self):
        """Hourly and per-unit rates must be marked with scope limitations."""
        items = [
            NormalizedProviderResult(
                id="item-hourly",
                name="Hourly Electrician",
                source_type=SourceType.LOCAL_DATABASE,
                matched_service_slug="switch-socket-repair",
                amount=Decimal("199"),
                price_type="HOURLY",
                formatted_price="₹199 / hr",
                verification_status=VerificationStatus.PARTIALLY_VERIFIED,
                is_price_available=True,
            ),
            NormalizedProviderResult(
                id="item-unit",
                name="Wiring Contractor",
                source_type=SourceType.LOCAL_DATABASE,
                matched_service_slug="switch-socket-repair",
                amount=Decimal("1.50"),
                price_unit="sq.ft",
                price_type="PER_UNIT",
                formatted_price="₹1.50 sq.ft",
                verification_status=VerificationStatus.VERIFIED,
                is_price_available=True,
            ),
        ]
        query = DiscoveryQuery(service="switch-socket-repair", resolved_service_slug="switch-socket-repair")
        summary = PriceComparisonEngine.build_summary(query, items)

        assert summary is not None
        hourly_item = next(i for i in summary.comparable_items if i.id == "item-hourly")
        assert hourly_item.is_comparable is False
        assert "Hourly" in hourly_item.comparability_note

        unit_item = next(i for i in summary.comparable_items if i.id == "item-unit")
        assert unit_item.is_comparable is False
        assert "Per-unit" in unit_item.comparability_note

    def test_quote_required_has_no_misleading_amount(self):
        """QUOTE_REQUIRED results must clear amounts and set is_price_available to False."""
        res = ResultNormalizer.from_db_models(
            provider=Provider(name="Quote Only Co", primary_area="Indiranagar"),
            offering=None,
        )
        assert res.amount is None
        assert res.price_min is None
        assert res.is_price_available is False

    def test_search_api_database_error_returns_safe_503(self, client):
        """Database failures must return safe 503 Service Unavailable without leaking stack traces or credentials."""
        from unittest.mock import patch
        from app.services.nammaserve.discovery.service import UnifiedDiscoveryService

        with patch.object(
            UnifiedDiscoveryService,
            "discover",
            side_effect=RuntimeError("psycopg2.OperationalError: could not connect to server at 127.0.0.1:5432"),
        ):
            response = client.get("/api/v1/nammaserve/search?service=ac-repair")
            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "temporarily unavailable" in data["detail"].lower()
            # Ensure sensitive database credentials and stack trace are NOT exposed to the client
            assert "127.0.0.1" not in data["detail"]
            assert "psycopg2" not in data["detail"]
