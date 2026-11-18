from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.civicvoice import CivicVoiceSourceRecord
from app.schemas.civicvoice import NormalizedSourceRecord
from app.services.civicvoice.collectors.base import compute_dedup_key
from app.services.civicvoice.service import CivicVoiceService


@pytest.fixture
def db_session():
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


def test_persist_records_normalization_and_provenance(db_session):
    service = CivicVoiceService()
    now = datetime.now(timezone.utc)
    dedup_key = compute_dedup_key("youtube", "vid99", "https://youtube.com/watch?v=vid99")

    record = NormalizedSourceRecord(
        provider="youtube",
        external_id="vid99",
        dedup_key=dedup_key,
        topic="roads",
        title="Bengaluru Roads pothole issue",
        content="Citizen video documenting broken road",
        url="https://youtube.com/watch?v=vid99",
        author="Bengaluru Commuter",
        published_at=now,
        collected_at=now,
        language=None,
        metadata_json={"channel_id": "UC_xyz", "channel_title": "Bengaluru Commuter"},
    )

    persisted, dups = service.persist_records(db_session, [record])
    assert len(persisted) == 1
    assert dups == 0

    saved = db_session.query(CivicVoiceSourceRecord).filter_by(dedup_key=dedup_key).first()
    assert saved is not None
    assert saved.id is not None
    assert saved.provider == "youtube"
    assert saved.external_id == "vid99"
    assert saved.title == "Bengaluru Roads pothole issue"
    assert saved.url == "https://youtube.com/watch?v=vid99"
    assert saved.author == "Bengaluru Commuter"
    assert saved.topic == "roads"
    assert saved.metadata_json == {"channel_id": "UC_xyz", "channel_title": "Bengaluru Commuter"}


def test_duplicate_prevention_same_batch(db_session):
    service = CivicVoiceService()
    now = datetime.now(timezone.utc)
    dedup_key = compute_dedup_key("bluesky", "at://1", "https://bsky.app/profile/user/post/1")

    r1 = NormalizedSourceRecord(
        provider="bluesky",
        external_id="at://1",
        dedup_key=dedup_key,
        content="Post 1",
        url="https://bsky.app/profile/user/post/1",
        collected_at=now,
    )
    r2 = NormalizedSourceRecord(
        provider="bluesky",
        external_id="at://1",
        dedup_key=dedup_key,
        content="Post 1 duplicate in same batch",
        url="https://bsky.app/profile/user/post/1",
        collected_at=now,
    )

    persisted, dups = service.persist_records(db_session, [r1, r2])
    # In-memory batch deduplication catches identical incoming keys
    assert len(persisted) == 1
    count = db_session.query(CivicVoiceSourceRecord).filter_by(dedup_key=dedup_key).count()
    assert count == 1


def test_repeated_collection_idempotent(db_session):
    service = CivicVoiceService()
    now = datetime.now(timezone.utc)
    dedup_key = compute_dedup_key("tavily", None, "https://news.example.com/bengaluru-roads")

    rec = NormalizedSourceRecord(
        provider="tavily",
        external_id=None,
        dedup_key=dedup_key,
        title="News title",
        content="News summary snippet",
        url="https://news.example.com/bengaluru-roads",
        collected_at=now,
    )

    # First run
    p1, d1 = service.persist_records(db_session, [rec])
    assert len(p1) == 1
    assert d1 == 0

    # Repeated collection run
    p2, d2 = service.persist_records(db_session, [rec])
    assert len(p2) == 1
    assert d2 == 1  # Identified duplicate

    total = db_session.query(CivicVoiceSourceRecord).count()
    assert total == 1


def test_preserve_existing_useful_values(db_session):
    service = CivicVoiceService()
    now = datetime.now(timezone.utc)
    dedup_key = compute_dedup_key("bluesky", "at://stable_id", "https://bsky.app/post/1")

    # Initial record has full content and author, but no title or topic
    r1 = NormalizedSourceRecord(
        provider="bluesky",
        external_id="at://stable_id",
        dedup_key=dedup_key,
        topic=None,
        title=None,
        content="Detailed civic commentary on Indiranagar drainage",
        url="https://bsky.app/post/1",
        author="indiranagar_resident",
        published_at=now,
        collected_at=now,
    )
    service.persist_records(db_session, [r1])

    # Second incoming record for the same post has poorer/empty content, but adds a topic
    r2 = NormalizedSourceRecord(
        provider="bluesky",
        external_id="at://stable_id",
        dedup_key=dedup_key,
        topic="drainage",
        title=None,
        content="",  # empty
        url="https://bsky.app/post/1",
        author=None,  # missing
        collected_at=now,
    )
    service.persist_records(db_session, [r2])

    saved = db_session.query(CivicVoiceSourceRecord).filter_by(dedup_key=dedup_key).first()
    # Content must NOT be cleared or overwritten by empty string!
    assert saved.content == "Detailed civic commentary on Indiranagar drainage"
    assert saved.author == "indiranagar_resident"
    # Topic should be updated since existing was None
    assert saved.topic == "drainage"


def test_missing_optional_metadata(db_session):
    service = CivicVoiceService()
    now = datetime.now(timezone.utc)
    dedup_key = compute_dedup_key("tavily", None, "https://minimal.example.com")

    rec = NormalizedSourceRecord(
        provider="tavily",
        external_id=None,
        dedup_key=dedup_key,
        title=None,
        content=None,
        url="https://minimal.example.com",
        author=None,
        published_at=None,
        collected_at=now,
        language=None,
        metadata_json=None,
    )
    persisted, dups = service.persist_records(db_session, [rec])
    assert len(persisted) == 1
    assert persisted[0].title is None
    assert persisted[0].metadata_json is None


def test_list_records_pagination_and_filters(db_session):
    service = CivicVoiceService()
    now = datetime.now(timezone.utc)

    # Create 5 records
    records = []
    for i in range(5):
        provider = "bluesky" if i % 2 == 0 else "youtube"
        topic = "roads" if i < 3 else "waste"
        dedup = compute_dedup_key(provider, f"id_{i}", f"https://example.com/{i}")
        records.append(
            NormalizedSourceRecord(
                provider=provider,
                external_id=f"id_{i}",
                dedup_key=dedup,
                topic=topic,
                title=f"Title {i} issue",
                content=f"Content for item {i}",
                url=f"https://example.com/{i}",
                collected_at=now,
            )
        )
    service.persist_records(db_session, records)

    # Filter by provider
    bsky_res = service.list_records(db_session, provider="bluesky")
    assert bsky_res.total == 3
    assert len(bsky_res.records) == 3

    # Filter by topic
    waste_res = service.list_records(db_session, topic="waste")
    assert waste_res.total == 2

    # Query search
    search_res = service.list_records(db_session, query="Title 2")
    assert search_res.total == 1
    assert search_res.records[0].external_id == "id_2"

    # Bounded pagination
    page1 = service.list_records(db_session, limit=2, offset=0)
    assert page1.limit == 2
    assert page1.offset == 0
    assert len(page1.records) == 2

    page2 = service.list_records(db_session, limit=2, offset=2)
    assert len(page2.records) == 2
    assert page2.records[0].id != page1.records[0].id
