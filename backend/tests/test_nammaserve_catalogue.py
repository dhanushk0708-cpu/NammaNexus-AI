import pytest
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.nammaserve import (
    CitizenReview,
    PlatformListing,
    PlatformType,
    PriceType,
    Provider,
    ProviderOffering,
    Service,
    ServiceCategory,
    ServicePrice,
    ThirdPartyReview,
    VerificationStatus,
)
from app.schemas.nammaserve import ServicePriceCreate, ServicePriceRead
from app.db.seeds.categories import seed_categories
from app.db.seeds.services import seed_services, CANONICAL_SERVICES


from sqlalchemy.pool import StaticPool

@pytest.fixture(scope="function")
def test_db():
    """Create a completely clean in-memory SQLite database for testing."""
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
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def seeded_db(test_db):
    """Seed canonical categories and return db session."""
    seed_categories(test_db)
    return test_db


@pytest.fixture(scope="function")
def client(seeded_db):
    """TestClient overriding get_db dependency with test database."""
    def override_get_db():
        try:
            yield seeded_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============================================================================
# 1. Service Catalogue Model & Relationship Tests
# ============================================================================

def test_service_creation_and_relationships(test_db):
    cat = ServiceCategory(
        id=str(uuid4()),
        slug="test-ac",
        name="Test AC Category",
        is_active=True,
    )
    test_db.add(cat)
    test_db.commit()

    svc = Service(
        id=str(uuid4()),
        category_id=cat.id,
        slug="split-ac-regular-service",
        name="Split AC Regular Service",
        description="Filter cleaning and coil wash",
        unit="per AC unit",
        is_active=True,
    )
    test_db.add(svc)
    test_db.commit()

    # Query back
    queried_cat = test_db.query(ServiceCategory).filter_by(slug="test-ac").first()
    assert len(queried_cat.individual_services) == 1
    assert queried_cat.individual_services[0].slug == "split-ac-regular-service"
    assert queried_cat.individual_services[0].category.slug == "test-ac"


def test_service_slug_uniqueness(test_db):
    cat = ServiceCategory(id=str(uuid4()), slug="cat-1", name="Cat 1")
    test_db.add(cat)
    test_db.commit()

    svc1 = Service(id=str(uuid4()), category_id=cat.id, slug="unique-slug", name="Service 1")
    svc2 = Service(id=str(uuid4()), category_id=cat.id, slug="unique-slug", name="Service 2")
    test_db.add(svc1)
    test_db.commit()

    test_db.add(svc2)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


# ============================================================================
# 2. Provider Offerings & Uniqueness
# ============================================================================

def test_provider_offerings_and_uniqueness(test_db):
    cat = ServiceCategory(id=str(uuid4()), slug="electrical", name="Electrical")
    test_db.add(cat)
    test_db.commit()

    svc = Service(id=str(uuid4()), category_id=cat.id, slug="switch-replacement", name="Switch Replacement")
    provider = Provider(
        id=str(uuid4()),
        name="Bengaluru Sparks Electricians",
        phone="+91 98765 43210",
        primary_area="Indiranagar",
    )
    test_db.add_all([svc, provider])
    test_db.commit()

    # Add offering
    offering = ProviderOffering(
        id=str(uuid4()),
        provider_id=provider.id,
        service_id=svc.id,
        custom_name="Quick Switch Fix",
        is_available=True,
        verification_status=VerificationStatus.VERIFIED.value,
    )
    test_db.add(offering)
    test_db.commit()

    assert len(provider.offerings) == 1
    assert provider.offerings[0].service.slug == "switch-replacement"

    # Test uniqueness constraint (provider_id, service_id)
    dup_offering = ProviderOffering(
        id=str(uuid4()),
        provider_id=provider.id,
        service_id=svc.id,
        custom_name="Duplicate Switch Fix",
    )
    test_db.add(dup_offering)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


# ============================================================================
# 3. Platform Listings Model
# ============================================================================

def test_platform_listing_creation(test_db):
    cat = ServiceCategory(id=str(uuid4()), slug="ac-repair", name="AC Repair")
    svc = Service(id=str(uuid4()), category_id=cat.id, slug="split-ac-regular-service", name="Split AC Service")
    test_db.add_all([cat, svc])
    test_db.commit()

    listing = PlatformListing(
        id=str(uuid4()),
        platform=PlatformType.URBAN_COMPANY.value,
        service_id=svc.id,
        title="Urban Company Split AC Servicing",
        locality="Kengeri",
        listing_url="https://www.urbancompany.com/bangalore/ac-service",
        booking_url="https://www.urbancompany.com/book/ac-service",
        verification_status=VerificationStatus.VERIFIED.value,
    )
    test_db.add(listing)
    test_db.commit()

    queried = test_db.query(PlatformListing).filter_by(id=listing.id).first()
    assert queried.platform == PlatformType.URBAN_COMPANY.value
    assert queried.service.slug == "split-ac-regular-service"
    assert queried.city == "Bengaluru"


# ============================================================================
# 4. Service Pricing Validation Tests
# ============================================================================

def test_fixed_pricing_validation():
    # Valid
    p_valid = ServicePrice(
        service_id="s1",
        price_type=PriceType.FIXED.value,
        amount=499.0,
        currency="INR",
    )
    p_valid.validate_pricing_consistency()

    # Invalid (missing amount)
    p_invalid = ServicePrice(
        service_id="s1",
        price_type=PriceType.FIXED.value,
        amount=None,
        currency="INR",
    )
    with pytest.raises(ValueError, match="FIXED pricing requires a positive amount"):
        p_invalid.validate_pricing_consistency()

    # Invalid (negative amount)
    p_neg = ServicePrice(
        service_id="s1",
        price_type=PriceType.FIXED.value,
        amount=-50.0,
        currency="INR",
    )
    with pytest.raises(ValueError, match="FIXED pricing requires a positive amount"):
        p_neg.validate_pricing_consistency()


def test_range_pricing_validation():
    # Valid
    p_valid = ServicePrice(
        service_id="s1",
        price_type=PriceType.RANGE.value,
        price_min=500.0,
        price_max=1200.0,
        currency="INR",
    )
    p_valid.validate_pricing_consistency()

    # Invalid (min > max)
    p_inverted = ServicePrice(
        service_id="s1",
        price_type=PriceType.RANGE.value,
        price_min=1500.0,
        price_max=1000.0,
        currency="INR",
    )
    with pytest.raises(ValueError, match="cannot exceed price_max"):
        p_inverted.validate_pricing_consistency()

    # Invalid (missing max)
    p_no_max = ServicePrice(
        service_id="s1",
        price_type=PriceType.RANGE.value,
        price_min=500.0,
        price_max=None,
        currency="INR",
    )
    with pytest.raises(ValueError, match="requires both price_min and price_max"):
        p_no_max.validate_pricing_consistency()


def test_per_unit_pricing_validation():
    # Valid
    p_valid = ServicePrice(
        service_id="s1",
        price_type=PriceType.PER_UNIT.value,
        amount=18.0,
        unit="per sq ft",
        currency="INR",
    )
    p_valid.validate_pricing_consistency()

    # Invalid (missing unit)
    p_no_unit = ServicePrice(
        service_id="s1",
        price_type=PriceType.PER_UNIT.value,
        amount=18.0,
        unit=None,
        currency="INR",
    )
    with pytest.raises(ValueError, match="requires a specified unit"):
        p_no_unit.validate_pricing_consistency()


def test_currency_validation():
    p = ServicePrice(
        service_id="s1",
        price_type=PriceType.FIXED.value,
        amount=50.0,
        currency="USD",
    )
    with pytest.raises(ValueError, match="Only INR is supported"):
        p.validate_pricing_consistency()


def test_pydantic_schema_pricing_validation():
    # Pydantic schema validation for API payloads
    valid_payload = ServicePriceCreate(
        service_id="s1",
        price_type=PriceType.STARTING_AT,
        amount=350.0,
        currency="INR",
    )
    assert valid_payload.amount == 350.0

    # Inverted range in Pydantic schema
    with pytest.raises(ValueError):
        ServicePriceCreate(
            service_id="s1",
            price_type=PriceType.RANGE,
            price_min=800.0,
            price_max=400.0,
            currency="INR",
        )


# ============================================================================
# 5. Reviews & Ratings Separation Tests
# ============================================================================

def test_citizen_and_third_party_review_separation(test_db):
    provider = Provider(id=str(uuid4()), name="Local Electrician", phone="+91 80 1234 5678")
    test_db.add(provider)
    test_db.commit()

    # Authentic citizen review
    citizen_review = CitizenReview(
        id=str(uuid4()),
        provider_id=provider.id,
        citizen_user_id="user-123",
        rating=4.5,
        review_title="Fixed fuse quickly",
        review_text="Arrived within 30 minutes in Kengeri and replaced MCB cleanly.",
        locality="Kengeri",
        is_verified_resident=True,
    )

    # Third party aggregated rating
    third_party = ThirdPartyReview(
        id=str(uuid4()),
        provider_id=provider.id,
        source_platform="JUSTDIAL",
        external_rating=4.1,
        external_reviews_count=48,
        source_url="https://justdial.com/sample",
    )

    test_db.add_all([citizen_review, third_party])
    test_db.commit()

    # Verify relationships and strict separation
    assert len(provider.citizen_reviews) == 1
    assert provider.citizen_reviews[0].review_title == "Fixed fuse quickly"
    assert provider.citizen_reviews[0].is_verified_resident is True

    assert len(provider.third_party_reviews) == 1
    assert provider.third_party_reviews[0].source_platform == "JUSTDIAL"
    assert provider.third_party_reviews[0].external_reviews_count == 48


# ============================================================================
# 6. Seed Idempotency Test
# ============================================================================

def test_seed_services_idempotency(seeded_db):
    expected_count = sum(len(items) for items in CANONICAL_SERVICES.values())
    # Pass 1: Initial seed
    res1 = seed_services(seeded_db)
    assert res1["inserted"] == expected_count
    assert res1["updated"] == 0
    assert res1["skipped_no_cat"] == 0

    count_after_pass1 = seeded_db.query(Service).count()
    assert count_after_pass1 == expected_count

    # Pass 2: Repeat seed must be completely idempotent
    res2 = seed_services(seeded_db)
    assert res2["inserted"] == 0
    assert res2["updated"] == expected_count
    assert res2["skipped_no_cat"] == 0

    count_after_pass2 = seeded_db.query(Service).count()
    assert count_after_pass2 == expected_count


# ============================================================================
# 7. API Endpoints Test
# ============================================================================

def test_catalogue_api_endpoints(client, seeded_db):
    seed_services(seeded_db)
    expected_count = sum(len(items) for items in CANONICAL_SERVICES.values())

    # 1. GET /api/v1/nammaserve/catalogue
    res = client.get("/api/v1/nammaserve/catalogue")
    assert res.status_code == 200
    services = res.json()
    assert len(services) == expected_count

    # 2. GET /api/v1/nammaserve/catalogue?category_slug=water-tanker
    res_tanker = client.get("/api/v1/nammaserve/catalogue?category_slug=water-tanker")
    assert res_tanker.status_code == 200
    tanker_services = res_tanker.json()
    assert len(tanker_services) == 3
    slugs = [s["slug"] for s in tanker_services]
    assert "tanker-4000-litres" in slugs
    assert "tanker-6000-litres" in slugs
    assert "tanker-12000-litres" in slugs

    # 3. GET /api/v1/nammaserve/catalogue/split-ac-regular-service
    res_detail = client.get("/api/v1/nammaserve/catalogue/split-ac-regular-service")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["slug"] == "split-ac-regular-service"
    assert detail["category_slug"] == "ac-repair"
    assert "platform_listings" in detail
    assert "provider_offerings" in detail

    # 4. GET invalid service
    res_404 = client.get("/api/v1/nammaserve/catalogue/non-existent-service-slug")
    assert res_404.status_code == 404


def test_submit_citizen_review_api(client, seeded_db):
    seed_services(seeded_db)
    provider = Provider(id=str(uuid4()), name="Indiranagar Plumbers", phone="+91 80 4455 6677")
    seeded_db.add(provider)
    seeded_db.commit()

    svc = seeded_db.query(Service).filter_by(slug="pipe-leakage-drain-unclog").first()

    payload = {
        "provider_id": provider.id,
        "service_id": svc.id,
        "rating": 4.8,
        "review_title": "Fixed pipe burst within 1 hour",
        "review_text": "Very polite plumber. Repaired the joint and tested pressure thoroughly.",
        "locality": "Indiranagar",
    }

    res = client.post("/api/v1/nammaserve/reviews", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["provider_id"] == provider.id
    assert data["rating"] == 4.8
    assert data["review_title"] == "Fixed pipe burst within 1 hour"
    assert data["is_published"] is True


# ============================================================================
# 8. Migration Metadata Test
# ============================================================================

def test_migration_metadata():
    import importlib.util
    from pathlib import Path

    migration_path = Path("alembic/versions/i9j0k1l2m3n4_create_service_catalogue_and_pricing_tables.py")
    assert migration_path.exists(), "Migration file must exist"

    spec = importlib.util.spec_from_file_location("migration_i9", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "i9j0k1l2m3n4"
    assert module.down_revision == "h8i9j0k1l2m3"
    assert callable(module.upgrade)
    assert callable(module.downgrade)
