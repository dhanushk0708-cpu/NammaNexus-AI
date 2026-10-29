"""SQLAlchemy models for NammaServe Provider Research and Customer Booking Requests.

Preserves research candidate data discovered via Gemini research across 4 batches,
64 area-category matrix combinations, and customer booking request workflows.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResearchCandidate(Base):
    """Researched provider candidates for NammaServe home services in Bengaluru.
    
    Contains 128 verified provider-area-category records spanning 8 categories
    and 8 localities, preserving all raw research metadata and review sentiment.
    """
    __tablename__ = "nammaserve_research_candidates"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    batch_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False,
    )
    provider_id: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )
    provider_name: Mapped[str] = mapped_column(
        String(200),
        index=True,
        nullable=False,
    )
    service_category: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    raw_service_category: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    specific_services: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    requested_area: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    area_name: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )
    business_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    public_phone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    public_email: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    website_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    contact_or_booking_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    advertised_service_areas: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    area_coverage_evidence_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    price_type: Mapped[str | None] = mapped_column(
        String(50),
        index=True,
        nullable=True,
    )
    price_amount: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    price_currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
    )
    price_unit: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    price_scope: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    price_source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    rating: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    review_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    rating_platform: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    rating_source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    booking_method: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    availability_status: Mapped[str] = mapped_column(
        String(50),
        default="UNKNOWN",
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        index=True,
        default="DISCOVERED",
        nullable=False,
    )
    primary_source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    secondary_source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    research_date: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    confidence: Mapped[str] = mapped_column(
        String(20),
        default="HIGH",
        nullable=False,
    )
    evidence_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    missing_information: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    duplicate_group_id: Mapped[str | None] = mapped_column(
        String(50),
        index=True,
        nullable=True,
    )
    provider_rank: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Review analysis fields (from Batches 2-4)
    review_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    review_positive_themes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    review_negative_themes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    review_date_range: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    review_summary_source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    review_summary_limitations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Full raw CSV row preserved in JSON
    raw_record: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    booking_requests: Mapped[list["BookingRequest"]] = relationship(
        "BookingRequest",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "provider_name",
            "requested_area",
            "service_category",
            name="uq_research_candidate_prov_area_cat",
        ),
    )


class ResearchCoverage(Base):
    """Area-Category coverage matrix records from the 4 batch matrix files.
    
    Contains the 64 combinations (8 areas x 8 service categories) demonstrating
    thorough research coverage, verified provider counts, and documented limitations.
    """
    __tablename__ = "nammaserve_research_coverage"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    batch_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False,
    )
    area: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    clean_area: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )
    service_category: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )
    research_status: Mapped[str] = mapped_column(
        String(50),
        default="COMPLETED_WITH_RESULTS",
        nullable=False,
    )
    provider_1_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    provider_1_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    provider_1_source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    provider_2_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    provider_2_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    provider_2_source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    providers_found: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
    )
    sources_checked: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    evidence_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    limitations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    research_date: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    raw_record: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "area",
            "service_category",
            name="uq_research_coverage_area_cat",
        ),
    )


class BookingRequest(Base):
    """Customer booking requests for home services.
    
    Protects user safety: explicitly flags research candidates so they require
    direct provider confirmation, preventing simulated accepted bookings.
    """
    __tablename__ = "nammaserve_booking_requests"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("nammaserve_research_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    service_category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    area: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    customer_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    customer_phone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    customer_email: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    customer_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    preferred_date: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    preferred_time_slot: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    issue_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING_CONFIRMATION",
        nullable=False,
    )
    is_research_candidate: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    candidate: Mapped[ResearchCandidate | None] = relationship(
        "ResearchCandidate",
        back_populates="booking_requests",
    )
