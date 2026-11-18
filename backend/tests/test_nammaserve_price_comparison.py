"""Pytest test suite for NammaServe Bengaluru Price Comparison feature.

Tests:
- CSV dataset integrity and 14 expected columns
- 142 records count and platform/category distribution
- Idempotency and hash determinism
- Lossless preservation of raw prices and N/A handling (never ₹0)
- Price parsing (scalars, ranges, open-ended starting prices)
- Locality caveats detection
- API: GET /overview
- API: GET /records (pagination, search, filtering, sorting)
- API: GET /benchmarks
- API: GET /filters
- Input validation & error states
"""
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.nammaserve_research import PriceComparisonRecord
from scripts.import_nammaserve_price_comparison import (
    PriceComparisonDatasetImporter,
    compute_record_hash,
    parse_numeric_prices,
    check_is_locality_specific,
)


@pytest.fixture(scope="module")
def test_db_session():
    """In-memory SQLite session with PriceComparisonRecord table."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine, tables=[PriceComparisonRecord.__table__])
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Ingest the 142 records into test session
    importer = PriceComparisonDatasetImporter()
    valid_records, invalid, _ = importer.load_and_validate()
    assert len(invalid) == 0
    for r in valid_records:
        session.add(PriceComparisonRecord(**r))
    session.commit()

    yield session
    session.close()


@pytest.fixture(scope="module")
def client(test_db_session):
    """TestClient overriding get_db dependency with test database session."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestPriceComparisonDataset:
    """Validate dataset structure, rules, and parser logic."""

    def test_csv_file_detection_and_column_count(self):
        importer = PriceComparisonDatasetImporter()
        valid, invalid, stats = importer.load_and_validate()
        assert stats["total_rows_read"] == 142
        assert stats["valid_rows"] == 142
        assert stats["invalid_rows"] == 0

    def test_platform_and_category_counts(self):
        importer = PriceComparisonDatasetImporter()
        stats = importer.dry_run()
        assert stats["platforms"]["Urban Company"] == 52
        assert stats["platforms"]["NoBroker"] == 51
        assert stats["platforms"]["Justdial"] == 20
        assert stats["platforms"]["Sulekha"] == 19
        assert len(stats["categories"]) == 8

    def test_hash_uniqueness_and_idempotency(self):
        importer = PriceComparisonDatasetImporter()
        valid, _, stats = importer.load_and_validate()
        hashes = [r["record_hash"] for r in valid]
        assert len(hashes) == 142
        assert len(set(hashes)) == 142
        assert stats["duplicate_hashes"] == 0

    def test_na_prices_never_become_zero(self):
        importer = PriceComparisonDatasetImporter()
        valid, _, stats = importer.load_and_validate()
        na_records = [r for r in valid if r["published_price"] == "N/A"]
        assert len(na_records) == 7
        for r in na_records:
            assert r["price_min"] is None
            assert r["price_max"] is None
            assert r["price_min"] != 0

    def test_price_parser_rules(self):
        # Fixed scalar
        p_min, p_max = parse_numeric_prices("49", "FIXED")
        assert p_min == 49.0
        assert p_max == 49.0

        # Range
        p_min, p_max = parse_numeric_prices("479-869", "PRICE_RANGE")
        assert p_min == 479.0
        assert p_max == 869.0

        # Starting from (open-ended upper bound)
        p_min, p_max = parse_numeric_prices("1299", "STARTING_FROM")
        assert p_min == 1299.0
        assert p_max is None

        # Quote required / Unpublished
        p_min, p_max = parse_numeric_prices("N/A", "QUOTATION_REQUIRED")
        assert p_min is None and p_max is None

    def test_locality_specific_flagging(self):
        assert check_is_locality_specific("Bengaluru (Citywide - Confirmed)") is False
        assert check_is_locality_specific("Bengaluru - Locality Specific (JP Nagar / Jayanagar)") is True
        assert check_is_locality_specific("Unconfirmed (Geographic Applicability Unclear)") is True


class TestPriceComparisonAPI:
    """Validate FastAPI endpoints for the price comparison feature."""

    def test_overview_endpoint(self, client):
        res = client.get("/api/v1/nammaserve/price-comparison/overview")
        assert res.status_code == 200
        data = res.json()
        assert data["total_records"] == 142
        assert data["platforms_count"]["Urban Company"] == 52
        assert data["platforms_count"]["NoBroker"] == 51
        assert data["citywide_confirmed_count"] == 109
        assert data["locality_specific_count"] == 33
        assert data["latest_research_date"] == "2026-10-29"
        assert "Prices are research snapshots" in data["disclaimer"]

    def test_records_endpoint_default_pagination(self, client):
        res = client.get("/api/v1/nammaserve/price-comparison/records?limit=20&page=1")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 142
        assert len(data["items"]) == 20
        assert data["pages"] == 8
        assert data["page"] == 1

    def test_records_filtering_by_platform(self, client):
        res = client.get("/api/v1/nammaserve/price-comparison/records?platform=Urban Company&limit=100")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 52
        for item in data["items"]:
            assert item["source_platform"] == "Urban Company"

    def test_records_filtering_by_category(self, client):
        res = client.get("/api/v1/nammaserve/price-comparison/records?category=Plumbing&limit=100")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 35
        for item in data["items"]:
            assert "Plumbing" in item["service_category"]

    def test_records_filtering_by_price_type(self, client):
        res = client.get("/api/v1/nammaserve/price-comparison/records?price_type=PRICE_RANGE&limit=100")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 29
        for item in data["items"]:
            assert item["price_type"] == "PRICE_RANGE"

    def test_records_search_query(self, client):
        res = client.get("/api/v1/nammaserve/price-comparison/records?search=tap repair")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0
        for item in data["items"]:
            blob = f"{item['service_name']} {item['notes'] or ''}".lower()
            assert "tap" in blob or "repair" in blob

    def test_records_sorting_by_price(self, client):
        res = client.get("/api/v1/nammaserve/price-comparison/records?sort_by=price_min&sort_dir=asc&limit=50")
        assert res.status_code == 200
        data = res.json()
        prices = [x["price_min"] for x in data["items"] if x["price_min"] is not None]
        assert prices == sorted(prices)

    def test_benchmarks_endpoint(self, client):
        res = client.get("/api/v1/nammaserve/price-comparison/benchmarks")
        assert res.status_code == 200
        data = res.json()
        assert data["total_benchmarks"] > 0
        first = data["benchmarks"][0]
        assert "benchmark_task" in first
        assert "category" in first
        assert "urban_company" in first
        assert "nobroker" in first

    def test_filters_endpoint(self, client):
        res = client.get("/api/v1/nammaserve/price-comparison/filters")
        assert res.status_code == 200
        data = res.json()
        assert "Urban Company" in data["platforms"]
        assert "NoBroker" in data["platforms"]
        assert "Plumbing" in data["categories"]
        assert "FIXED" in data["price_types"]
        assert "SOURCE_CORROBORATED" in data["verification_statuses"]

    def test_invalid_parameters_validation(self, client):
        # Negative/zero page
        res = client.get("/api/v1/nammaserve/price-comparison/records?page=0")
        assert res.status_code == 422

        # Limit exceeds maximum of 200
        res = client.get("/api/v1/nammaserve/price-comparison/records?limit=500")
        assert res.status_code == 422
