"""Unit and integration tests for NammaServe Provider Research and Booking Requests.

Validates:
- File discovery (all 12 research files across 4 batches).
- Schema normalization and dry-run validation.
- In-memory SQLite table creation and idempotent database import.
- Filtering candidates by area, category, verification_status, and price_type.
- Honest verification preservation (DISCOVERED, SOURCE_CORROBORATED).
- Customer booking request creation with explicit research candidate disclaimers.
"""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.nammaserve_research import (
    BookingRequest,
    ResearchCandidate,
    ResearchCoverage,
)
from scripts.import_nammaserve_research import ResearchDatasetImporter


@pytest.fixture(scope="function")
def sqlite_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_research_file_discovery():
    importer = ResearchDatasetImporter()
    assert len(importer.provider_files) == 4
    assert len(importer.matrix_files) == 4
    assert len(importer.report_files) == 4


def test_research_dry_run_validation():
    importer = ResearchDatasetImporter()
    stats = importer.dry_run()

    assert stats["total_files_found"] == 12
    assert stats["total_candidates_to_import"] == 128
    assert stats["distinct_provider_ids"] == 112
    assert stats["distinct_business_names"] == 112
    assert stats["total_coverage_cells_to_import"] == 64
    assert stats["published_prices_count"] == 22
    assert stats["published_ratings_count"] == 119
    assert stats["areas_represented"] == 8
    assert stats["categories_represented"] == 8

    # Check 16 candidates per area and per category
    for area, cnt in stats["area_distribution"].items():
        assert cnt == 16, f"Area {area} has {cnt} candidates"
    for cat, cnt in stats["category_distribution"].items():
        assert cnt == 16, f"Category {cat} has {cnt} candidates"


def test_research_dataset_sqlite_import_idempotent(sqlite_db):
    importer = ResearchDatasetImporter()

    # First import: insert 128 candidates and 64 coverage records
    res1 = importer.execute_import(sqlite_db)
    assert res1["candidates_inserted"] == 128
    assert res1["candidates_updated"] == 0
    assert res1["coverage_inserted"] == 64
    assert res1["coverage_updated"] == 0

    total_candidates = sqlite_db.query(ResearchCandidate).count()
    total_coverage = sqlite_db.query(ResearchCoverage).count()
    assert total_candidates == 128
    assert total_coverage == 64

    # Second import: idempotent update, zero new inserts
    res2 = importer.execute_import(sqlite_db)
    assert res2["candidates_inserted"] == 0
    assert res2["candidates_updated"] == 128
    assert res2["coverage_inserted"] == 0
    assert res2["coverage_updated"] == 64

    assert sqlite_db.query(ResearchCandidate).count() == 128
    assert sqlite_db.query(ResearchCoverage).count() == 64


def test_honest_verification_preservation(sqlite_db):
    importer = ResearchDatasetImporter()
    importer.execute_import(sqlite_db)

    # Ensure no record was artificially elevated to production "VERIFIED"
    statuses = set(
        c.verification_status for c in sqlite_db.query(ResearchCandidate.verification_status).all()
    )
    assert statuses == {"SOURCE_CORROBORATED", "DISCOVERED"}

    # Ensure all availability statuses remain UNKNOWN
    availabilities = set(
        c.availability_status for c in sqlite_db.query(ResearchCandidate.availability_status).all()
    )
    assert availabilities == {"UNKNOWN"}


def test_booking_request_creation_and_disclaimer(sqlite_db):
    candidate = ResearchCandidate(
        batch_id="batch1",
        provider_id="PROV_B1_001",
        provider_name="Elite Plumbing Solution",
        service_category="Plumbing",
        raw_service_category="Plumbing",
        requested_area="Kengeri, Bengaluru",
        area_name="Kengeri",
        raw_record={"test": "data"},
    )
    sqlite_db.add(candidate)
    sqlite_db.commit()

    booking = BookingRequest(
        candidate_id=candidate.id,
        provider_name=candidate.provider_name,
        service_category=candidate.service_category,
        area=candidate.area_name,
        customer_name="Priya Sharma",
        customer_phone="+91 98765 43210",
        customer_email="priya@example.com",
        customer_address="12th Cross, Kengeri Satellite Town",
        preferred_date="2026-11-01",
        preferred_time_slot="Morning (9 AM - 12 PM)",
        issue_description="Kitchen pipe leakage under the sink",
        status="PENDING_CONFIRMATION",
        is_research_candidate=True,
    )
    sqlite_db.add(booking)
    sqlite_db.commit()

    fetched = sqlite_db.query(BookingRequest).filter_by(customer_name="Priya Sharma").first()
    assert fetched is not None
    assert fetched.status == "PENDING_CONFIRMATION"
    assert fetched.is_research_candidate is True
    assert fetched.candidate.provider_name == "Elite Plumbing Solution"


@pytest.fixture(scope="function")
def client(sqlite_db):
    from fastapi.testclient import TestClient
    from app.db.dependencies import get_db
    from app.main import app

    def override_get_db():
        try:
            yield sqlite_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_research_overview_endpoint(client, sqlite_db):
    importer = ResearchDatasetImporter()
    importer.execute_import(sqlite_db)

    resp = client.get("/api/v1/nammaserve/research/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_candidates"] == 128
    assert data["distinct_businesses"] == 112
    assert data["total_areas"] == 8
    assert data["total_categories"] == 8
    assert data["total_coverage_cells"] == 64
    assert "disclaimer" in data


def test_api_research_candidates_filtering(client, sqlite_db):
    importer = ResearchDatasetImporter()
    importer.execute_import(sqlite_db)

    # Filter by area and category
    resp = client.get("/api/v1/nammaserve/research/candidates?area=Kengeri&category=Plumbing")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all("Kengeri" in item["area_name"] for item in data["items"])
    assert all(item["service_category"] == "Plumbing" for item in data["items"])


def test_api_research_coverage_endpoint(client, sqlite_db):
    importer = ResearchDatasetImporter()
    importer.execute_import(sqlite_db)

    resp = client.get("/api/v1/nammaserve/research/coverage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cells"] == 64
    assert data["completed_cells"] == 64
    assert len(data["cells"]) == 64


def test_api_booking_request_create_and_disclaimer(client):
    payload = {
        "provider_name": "Kumar Electrical work -kengeri",
        "service_category": "Electrical services",
        "area": "Kengeri",
        "customer_name": "Rohan Gowda",
        "customer_phone": "+91 99887 76655",
        "customer_email": "rohan@example.com",
        "customer_address": "Anchekeri Beedi, Kengeri",
        "preferred_date": "2026-11-02",
        "preferred_time_slot": "Afternoon (12 PM - 3 PM)",
        "issue_description": "MCB tripping on high load",
    }
    resp = client.post("/api/v1/nammaserve/booking-requests", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING_CONFIRMATION"
    assert data["is_research_candidate"] is True
    assert "confirmation_message" in data
    assert "Provider confirmation is required" in data["confirmation_message"]

