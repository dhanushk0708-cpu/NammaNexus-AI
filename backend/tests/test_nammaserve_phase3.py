"""Tests for NammaServe AI Phase 3: Real Pricing Research & Backend Integration.

Validates:
- All 12 canonical service slugs match catalogue.
- Research JSON and CSV schema validation and row consistency.
- Negative, contradictory, or invalid price handling.
- Mandatory source URLs and INR currency.
- Duplicate record detection.
- Distinction between platform listings and independent providers.
- Idempotent seed execution and preservation of verified records.
- Transaction rollback on simulated database failure.
- Search API backward compatibility and pricing attribute exposure.
"""
import csv
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.dependencies import get_db
from app.db.seeds.categories import seed_categories
from app.db.seeds.pricing_seed import (
    is_safe_local_environment,
    seed_demo_pricing,
    should_update_verification,
    validate_pricing_record,
)
from app.db.seeds.services import CANONICAL_SERVICES, seed_services
from app.main import app
from app.models.nammaserve import (
    PlatformListing,
    PriceType,
    Provider,
    ProviderOffering,
    Service,
    ServicePrice,
    VerificationStatus,
)

# 12 representative services requested in Phase 3
REQUESTED_SERVICES = [
    ("split-ac-regular-service", "ac-repair"),
    ("ac-gas-refill", "ac-repair"),
    ("ac-installation-uninstallation", "ac-repair"),
    ("full-home-deep-cleaning-2bhk", "home-cleaning"),
    ("bathroom-deep-cleaning", "home-cleaning"),
    ("toilet-flush-repair", "plumbing"),
    ("tap-shower-repair", "plumbing"),
    ("switch-socket-repair", "electrical"),
    ("interior-repaint", "painting"),
    ("cockroach-ant-treatment", "pest-control"),
    ("tanker-6000-litres", "water-tanker"),
    ("within-city-1bhk-shifting", "packers-movers"),
]

SOURCE_GROUPS = [
    "Urban Company",
    "NoBroker",
    "Justdial",
    "Sulekha",
    "Independent Provider",
]


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
# 1. Canonical Service Catalogue Mappings
# ==============================================================================

def test_all_selected_services_mapped_to_catalogue():
    """Verify that all 12 requested services exist in CANONICAL_SERVICES catalogue without gaps."""
    catalogue_slugs_by_cat = {
        cat: [s["slug"] for s in services]
        for cat, services in CANONICAL_SERVICES.items()
    }
    all_catalogue_slugs = {s["slug"] for svcs in CANONICAL_SERVICES.values() for s in svcs}

    for slug, expected_cat in REQUESTED_SERVICES:
        assert slug in all_catalogue_slugs, f"Requested slug '{slug}' is missing from catalogue"
        assert slug in catalogue_slugs_by_cat[expected_cat], (
            f"Slug '{slug}' is not in expected category '{expected_cat}'"
        )


# ==============================================================================
# 2. Dataset Artifact Consistency (JSON & CSV)
# ==============================================================================

def test_json_and_csv_artifacts_exist_and_match():
    """Verify that demo_pricing.json and demo_pricing.csv exist and have matching row counts and keys."""
    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "data" / "nammaserve" / "demo_pricing.json"
    csv_path = base_dir / "data" / "nammaserve" / "demo_pricing.csv"

    assert json_path.exists(), f"Missing {json_path}"
    assert csv_path.exists(), f"Missing {csv_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        json_records = json.load(f)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_records = list(reader)

    # 12 services * 5 source groups = 60 records
    assert len(json_records) == 60
    assert len(csv_records) == 60

    for j_row, c_row in zip(json_records, csv_records):
        assert j_row["canonical_service_slug"] == c_row["canonical_service_slug"]
        assert j_row["platform_or_provider_name"] == c_row["platform_or_provider_name"]
        assert j_row["pricing_type"] == c_row["pricing_type"]
        assert j_row["verification_status"] == c_row["verification_status"]


def test_dataset_coverage_matrix():
    """Verify that every one of the 12 requested services is researched across all 5 source groups."""
    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "data" / "nammaserve" / "demo_pricing.json"

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    service_counts = {}
    for r in records:
        slug = r["canonical_service_slug"]
        service_counts[slug] = service_counts.get(slug, 0) + 1

    for slug, _ in REQUESTED_SERVICES:
        assert service_counts.get(slug) == 5, f"Service '{slug}' does not have 5 source entries (found {service_counts.get(slug)})"


# ==============================================================================
# 3. Validation Logic & Invariant Checking
# ==============================================================================

def test_price_type_and_field_invariants():
    """Ensure negative prices, contradictory range bounds, and invalid currencies are rejected."""
    # Negative amount
    invalid_record_1 = {
        "pricing_type": "FIXED",
        "amount": -500.0,
        "currency": "INR",
        "source_url": "https://example.com",
    }
    errors = validate_pricing_record(invalid_record_1)
    assert any("Negative amount" in e for e in errors)

    # Contradictory RANGE bounds (min > max)
    invalid_record_2 = {
        "pricing_type": "RANGE",
        "price_min": 1000.0,
        "price_max": 500.0,
        "currency": "INR",
        "source_url": "https://example.com",
    }
    errors = validate_pricing_record(invalid_record_2)
    assert any("cannot exceed price_max" in e for e in errors)

    # PER_UNIT missing unit
    invalid_record_3 = {
        "pricing_type": "PER_UNIT",
        "amount": 25.0,
        "pricing_unit": "",
        "currency": "INR",
        "source_url": "https://example.com",
    }
    errors = validate_pricing_record(invalid_record_3)
    assert any("requires a meaningful pricing_unit" in e for e in errors)

    # QUOTE_REQUIRED with fixed amount
    invalid_record_4 = {
        "pricing_type": "QUOTE_REQUIRED",
        "amount": 499.0,
        "currency": "INR",
        "source_url": "https://example.com",
    }
    errors = validate_pricing_record(invalid_record_4)
    assert any("cannot have a fixed amount" in e for e in errors)

    # Missing source URL
    invalid_record_5 = {
        "pricing_type": "FIXED",
        "amount": 499.0,
        "currency": "INR",
        "source_url": None,
    }
    errors = validate_pricing_record(invalid_record_5)
    assert any("Missing source_url" in e for e in errors)

    # Non-INR currency
    invalid_record_6 = {
        "pricing_type": "FIXED",
        "amount": 499.0,
        "currency": "USD",
        "source_url": "https://example.com",
    }
    errors = validate_pricing_record(invalid_record_6)
    assert any("Invalid currency" in e for e in errors)


def test_duplicate_records_detection():
    """Verify that the dataset contains no duplicate (provider_name, canonical_slug) pairs."""
    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "data" / "nammaserve" / "demo_pricing.json"

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    seen_pairs = set()
    duplicates = []
    for r in records:
        key = (r["platform_or_provider_name"], r["canonical_service_slug"])
        if key in seen_pairs:
            duplicates.append(key)
        seen_pairs.add(key)

    assert len(duplicates) == 0, f"Found duplicate dataset records: {duplicates}"


def test_unavailable_prices_not_fabricated():
    """Ensure unavailable services (e.g. UC Water Tanker) are marked UNAVAILABLE and not given fixed prices."""
    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "data" / "nammaserve" / "demo_pricing.json"

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    unavailable_records = [r for r in records if r["verification_status"] == "UNAVAILABLE"]
    assert len(unavailable_records) >= 3  # UC water tanker, UC packers, NoBroker water tanker

    for rec in unavailable_records:
        assert rec["amount"] is None
        assert rec["price_min"] is None
        assert rec["price_max"] is None


# ==============================================================================
# 4. Idempotent Seed Execution & Safety Checks
# ==============================================================================

def test_seed_demo_pricing_idempotent(test_db):
    """Seed pricing data twice and verify idempotency and zero duplicate insertions."""
    # First seed execution
    stats1 = seed_demo_pricing(test_db)
    assert stats1["inserted_prices"] > 0
    assert stats1["skipped_unavailable"] >= 3
    assert stats1["rejected"] == 0

    total_prices_run1 = test_db.query(ServicePrice).count()
    total_listings_run1 = test_db.query(PlatformListing).count()

    # Second seed execution (idempotent)
    stats2 = seed_demo_pricing(test_db)
    assert stats2["inserted_prices"] == 0
    assert stats2["inserted_listings"] == 0
    assert stats2["updated_prices"] == total_prices_run1

    total_prices_run2 = test_db.query(ServicePrice).count()
    total_listings_run2 = test_db.query(PlatformListing).count()

    assert total_prices_run1 == total_prices_run2
    assert total_listings_run1 == total_listings_run2


def test_preservation_of_verified_data():
    """Verify that should_update_verification prevents downgrading VERIFIED to PARTIALLY_VERIFIED."""
    # VERIFIED cannot be overwritten by PARTIALLY_VERIFIED or UNVERIFIED
    assert not should_update_verification(
        VerificationStatus.VERIFIED.value,
        VerificationStatus.PARTIALLY_VERIFIED.value,
    )
    assert not should_update_verification(
        VerificationStatus.VERIFIED.value,
        VerificationStatus.UNVERIFIED.value,
    )
    # PARTIALLY_VERIFIED can be upgraded to VERIFIED
    assert should_update_verification(
        VerificationStatus.PARTIALLY_VERIFIED.value,
        VerificationStatus.VERIFIED.value,
    )
    # Same level updates are allowed
    assert should_update_verification(
        VerificationStatus.VERIFIED.value,
        VerificationStatus.VERIFIED.value,
    )


def test_platform_vs_independent_provider_distinction(test_db):
    """Verify that platforms create PlatformListing while independent businesses create Provider records."""
    seed_demo_pricing(test_db)

    # Urban Company & NoBroker must be in PlatformListing
    uc_listings = test_db.query(PlatformListing).filter(PlatformListing.platform == "Urban Company").all()
    assert len(uc_listings) > 0

    # CoolCare must be in Provider (not PlatformListing)
    coolcare = test_db.query(Provider).filter(Provider.name == "CoolCare Air Conditioning Services").first()
    assert coolcare is not None
    assert coolcare.source_type == "INDEPENDENT_PROVIDER"
    assert coolcare.phone is None  # Phone placeholder 'See Source URL' must be absent; nullable phone is None

    # Offering check for CoolCare
    offering = test_db.query(ProviderOffering).filter(ProviderOffering.provider_id == coolcare.id).first()
    assert offering is not None
    assert len(offering.prices) > 0


def test_seed_safety_controls_refuses_remote():
    """Verify that is_safe_local_environment strictly permits only local hosts and rejects cloud providers."""
    with patch("app.db.seeds.pricing_seed.settings") as mock_settings:
        # 1. Permitted local SQLite configurations (tested via database_url attribute)
        mock_settings.database_url = "sqlite:///./local_dev.db"
        mock_settings.DATABASE_URL = None
        assert is_safe_local_environment()
        assert is_safe_local_environment("sqlite:///:memory:")

        # 2. Permitted local PostgreSQL configurations
        mock_settings.database_url = "postgresql://postgres:secret@localhost:5432/postgres"
        assert is_safe_local_environment()
        assert is_safe_local_environment("postgresql+psycopg://postgres:secret@127.0.0.1:5432/postgres")
        assert is_safe_local_environment("postgresql+psycopg://postgres:secret@0.0.0.0:5432/postgres")
        assert is_safe_local_environment("postgresql+psycopg://postgres:secret@host.docker.internal:5432/postgres")
        assert is_safe_local_environment("postgresql://postgres:secret@[::1]:5432/postgres")
        assert is_safe_local_environment("postgresql://postgres:secret@[0:0:0:0:0:0:0:1]:5432/postgres")

        # 3. Uppercase DATABASE_URL fallback support when database_url is empty
        mock_settings.database_url = None
        mock_settings.DATABASE_URL = "sqlite:///./fallback.db"
        assert is_safe_local_environment()

        mock_settings.database_url = ""
        mock_settings.DATABASE_URL = "postgresql://postgres:secret@localhost:5432/postgres"
        assert is_safe_local_environment()

        # 4. Refused remote cloud hosts: Supabase, Neon, AWS RDS, Railway, Render, Fly.io, etc.
        remote_cases = [
            "postgresql://postgres:secret@db.abcxyz.supabase.co:5432/postgres",
            "postgresql://postgres:secret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres",
            "postgresql://postgres:secret@ep-cool-fog-123.neon.tech/neondb",
            "postgresql://postgres:secret@aws.neon.tech/neondb",
            "postgresql://postgres:secret@mydb.123456.ap-south-1.rds.amazonaws.com:5432/prod",
            "postgresql://postgres:secret@junction.proxy.rlwy.net:12345/railway",
            "postgresql://postgres:secret@containers-us-west-1.railway.app:5432/railway",
            "postgresql://postgres:secret@dpg-xxx.oregon-postgres.render.com/mydb",
            "postgresql://postgres:secret@app-db.fly.dev:5432/db",
            "postgresql://postgres:secret@remote-cluster.example.com:5432/db",
            "postgresql://postgres:secret@[2001:db8::1]:5432/remote",  # Arbitrary remote IPv6
        ]
        for remote_url in remote_cases:
            mock_settings.database_url = remote_url
            mock_settings.DATABASE_URL = remote_url
            assert not is_safe_local_environment(), f"Failed to reject remote host in settings: {remote_url}"
            assert not is_safe_local_environment(remote_url), f"Failed to reject remote host via parameter: {remote_url}"
        # 5. Malformed, unsupported, or missing URLs fail closed
        malformed_cases = [
            "",
            "   ",
            None,
            "not-a-valid-url",
            "http://localhost:5432",
            "redis://localhost:6379",
            "mysql://root:pass@localhost:3306/db",
            "postgresql://",
            "postgresql://:5432/db",
            12345,
        ]
        for malformed in malformed_cases:
            mock_settings.database_url = str(malformed) if malformed else ""
            assert not is_safe_local_environment(malformed), f"Failed to fail-closed on: {malformed}"


def test_safety_guard_requires_explicit_development_supabase_opt_in(monkeypatch):
    supabase_url = "postgresql://user:password@db.example.supabase.co:5432/postgres"
    monkeypatch.delenv("NAMMASERVE_ALLOW_DEVELOPMENT_SUPABASE_IMPORT", raising=False)
    assert not is_safe_local_environment(supabase_url)
    assert not is_safe_local_environment(
        supabase_url,
        allow_confirmed_development_supabase=True,
    )

    monkeypatch.setenv("NAMMASERVE_ALLOW_DEVELOPMENT_SUPABASE_IMPORT", "true")
    assert is_safe_local_environment(
        supabase_url,
        allow_confirmed_development_supabase=True,
    )


def test_safety_guard_validates_active_session_and_rejects_remote(test_db):
    """Verify that is_safe_local_environment validates an active SQLAlchemy Session."""
    # test_db is bound to an in-memory SQLite engine
    assert is_safe_local_environment(test_db)

    # Mock a session bound to a remote engine URL
    mock_remote_session = type("MockSession", (), {})()
    mock_bind = type("MockBind", (), {})()
    mock_bind.url = "postgresql://user:pass@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"
    mock_remote_session.get_bind = lambda: mock_bind

    assert not is_safe_local_environment(mock_remote_session)

    # Calling seed_demo_pricing with remote session must raise RuntimeError before any write
    with pytest.raises(RuntimeError, match="Database safety check failed"):
        seed_demo_pricing(mock_remote_session)


def test_cli_confirm_local_never_bypasses_remote_host(monkeypatch):
    """Verify that --confirm-local flag never bypasses remote host safety rejection."""
    import sys
    from app.db.seeds.pricing_seed import main

    monkeypatch.setattr(
        "app.db.seeds.pricing_seed.settings.database_url",
        "postgresql://postgres:secret@db.projectref.supabase.co:5432/postgres",
    )

    # Attempt to run CLI with --confirm-local pointing to remote host
    test_args = ["pricing_seed.py", "--confirm-local"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_cli_requires_confirm_local_or_dry_run(monkeypatch):
    """Verify that running without --confirm-local and without --dry-run exits immediately."""
    import sys
    from app.db.seeds.pricing_seed import main

    test_args = ["pricing_seed.py"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


# ==============================================================================
# 5. API Backward Compatibility & Pricing Attributes
# ==============================================================================

def test_api_search_exposes_phase3_pricing_attributes(client, test_db):
    """Verify that GET /api/v1/nammaserve/search returns Phase 3 pricing attributes without breaking changes."""
    seed_demo_pricing(test_db)

    response = client.get("/api/v1/nammaserve/search?slug=split-ac-regular-service&limit=10")
    assert response.status_code == 200

    data = response.json()
    assert "results" in data
    assert "total_results" in data
    assert len(data["results"]) > 0

    # Inspect the first result for Phase 3 pricing attributes
    first = data["results"][0]
    assert "price_min" in first
    assert "price_type" in first
    assert "inclusions" in first
    assert "exclusions" in first
    assert "source_url" in first
    assert "verification_status" in first


def test_api_search_backward_compatible_query(client, test_db):
    """Verify that querying with ?service= works seamlessly and preserves response contract."""
    seed_demo_pricing(test_db)
    response = client.get("/api/v1/nammaserve/search?service=AC%20Repair&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "total_results" in data
    assert "results" in data
    assert "connectors_contacted" in data
    assert isinstance(data["results"], list)


def test_seed_dry_run_mode(test_db):
    """Verify that dry_run=True performs validation and processing but leaves database empty."""
    stats = seed_demo_pricing(test_db, dry_run=True)
    assert stats["inserted_prices"] > 0
    # In SQLite, after rollback, count should be 0
    assert test_db.query(ServicePrice).count() == 0


def test_seed_rollback_on_error(test_db):
    """Verify that simulated database exception during seed triggers rollback cleanly."""
    initial_prices = test_db.query(ServicePrice).count()
    with patch.object(test_db, "commit", side_effect=RuntimeError("Simulated DB Disk Failure")):
        with pytest.raises(RuntimeError, match="Simulated DB Disk Failure"):
            try:
                seed_demo_pricing(test_db, dry_run=False)
            except RuntimeError:
                test_db.rollback()
                raise

    # Verify no partial uncommitted state remains
    assert test_db.query(ServicePrice).count() == initial_prices


# ==============================================================================
# 6. Targeted Data-Quality Corrections Regression Tests
# ==============================================================================

def test_dataset_reconciled_counts():
    """Verify that verification status and pricing type counts match the reconciled audit baseline."""
    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "data" / "nammaserve" / "demo_pricing.json"

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    v_counts = {}
    for r in records:
        status = r["verification_status"]
        v_counts[status] = v_counts.get(status, 0) + 1

    # Reconciled counts: 27 VERIFIED, 30 PARTIALLY_VERIFIED, 3 UNAVAILABLE
    assert v_counts["VERIFIED"] == 27
    assert v_counts["PARTIALLY_VERIFIED"] == 30
    assert v_counts["UNAVAILABLE"] == 3


def test_independent_provider_downgrades_and_reconciliation():
    """Verify that unverified independent provider rate cards are downgraded to PARTIALLY_VERIFIED."""
    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "data" / "nammaserve" / "demo_pricing.json"

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    records_by_provider = {}
    for r in records:
        records_by_provider.setdefault(r["platform_or_provider_name"], []).append(r)

    # CoolCare (3 records): all must be PARTIALLY_VERIFIED
    coolcare_records = records_by_provider["CoolCare Air Conditioning Services"]
    assert len(coolcare_records) == 3
    for cr in coolcare_records:
        assert cr["verification_status"] == "PARTIALLY_VERIFIED"

    # Fixizzy (2 records): all must be PARTIALLY_VERIFIED
    fixizzy_records = records_by_provider["Fixizzy Home Maintenance"]
    assert len(fixizzy_records) == 2
    for fr in fixizzy_records:
        assert fr["verification_status"] == "PARTIALLY_VERIFIED"

    # Century Packers & Movers (1 record): PARTIALLY_VERIFIED
    century_records = records_by_provider["Century Packers & Movers"]
    assert len(century_records) == 1
    assert century_records[0]["verification_status"] == "PARTIALLY_VERIFIED"
    assert "centurypackersmovers.in" in century_records[0]["source_url"]

    # Nakoda Urban Services (2 records): VERIFIED with confirmed nakodadcs.com URL
    nakoda_records = records_by_provider["Nakoda Urban Services"]
    assert len(nakoda_records) == 2
    for nr in nakoda_records:
        assert nr["verification_status"] == "VERIFIED"
        assert nr["source_url"] == "https://nakodadcs.com/bangalore/home-deep-cleaning-services"


def test_water_tanker_tariff_resolution():
    """Verify that BWSSB Sanchari Cauvery record has the verified ₹740 statutory rate and clear notes."""
    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "data" / "nammaserve" / "demo_pricing.json"

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    bwssb_tanker = next(
        r for r in records
        if r["canonical_service_slug"] == "tanker-6000-litres"
        and r["platform_or_provider_name"] == "BWSSB — Sanchari Cauvery"
    )
    assert bwssb_tanker["verification_status"] == "VERIFIED"
    assert bwssb_tanker["pricing_type"] == "FIXED"
    assert bwssb_tanker["amount"] == 740.0
    assert bwssb_tanker["price_min"] == 740.0
    assert bwssb_tanker["price_max"] == 740.0
    assert "740" in bwssb_tanker["evidence_notes"]
    assert "600" in bwssb_tanker["evidence_notes"]  # references district admin cap


def test_nobroker_cockroach_treatment_range_amount_none():
    """Verify NoBroker cockroach-ant-treatment has amount=None for RANGE pricing type."""
    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "data" / "nammaserve" / "demo_pricing.json"

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    nobroker_pest = next(
        r for r in records
        if r["canonical_service_slug"] == "cockroach-ant-treatment"
        and r["platform_or_provider_name"] == "NoBroker"
    )
    assert nobroker_pest["pricing_type"] == "RANGE"
    assert nobroker_pest["amount"] is None
    assert nobroker_pest["price_min"] == 799.0
    assert nobroker_pest["price_max"] == 1400.0


def test_no_phone_placeholders_seeded_in_database(test_db):
    """Verify that seeded independent providers do not store placeholder phone strings like 'See Source URL'."""
    seed_demo_pricing(test_db)
    providers = test_db.query(Provider).all()
    assert len(providers) > 0
    for p in providers:
        assert p.phone != "See Source URL"
        assert p.phone is None
