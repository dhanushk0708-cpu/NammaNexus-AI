from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.seeds.categories import seed_categories
from app.db.seeds.phase_b_import import (
    import_phase_b,
    load_phase_b_records,
    validate_phase_b_records,
)
from app.db.seeds.services import seed_services
from app.models.nammaserve import PlatformListing, ServicePrice


def test_phase_b_artifact_validates_and_imports_idempotently():
    records = load_phase_b_records()
    assert len(records) == 69
    assert validate_phase_b_records(records) == []

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    seed_categories(db)
    seed_services(db)

    first = import_phase_b(db)
    second = import_phase_b(db)

    assert first["validated"] == 69
    assert first["imported"] == 57
    assert first["prices"] == 57
    assert first["needs_review"] == 13
    assert second["imported"] == 0
    assert db.query(PlatformListing).count() == 57
    assert db.query(ServicePrice).count() == 57
    assert db.query(ServicePrice).filter(ServicePrice.research_record_id.is_not(None)).count() == 57
