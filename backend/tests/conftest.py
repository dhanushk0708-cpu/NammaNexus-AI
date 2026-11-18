from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app


@pytest.fixture
def test_client_and_db():
    """Provides a transactional in-memory SQLite database and FastAPI TestClient."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, session

    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def isolate_civicvoice_cache():
    """Ensure CivicVoice in-memory search cache does not leak across test cases."""
    from app.api.v1.endpoints.civicvoice import civicvoice_service
    civicvoice_service.clear_cache()
    yield
    civicvoice_service.clear_cache()
