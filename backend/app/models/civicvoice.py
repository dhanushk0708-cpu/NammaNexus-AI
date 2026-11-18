from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CivicVoiceSourceRecord(Base):
    """Normalized public opinion source records collected from external providers

    (Bluesky, YouTube Data API, Tavily Search API).
    """

    __tablename__ = "civicvoice_source_records"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    provider: Mapped[str] = mapped_column(
        String(30),
        index=True,
        nullable=False,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    dedup_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    topic: Mapped[str | None] = mapped_column(
        String(200),
        index=True,
        nullable=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    author: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    language: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    analyses: Mapped[list["CivicVoiceAnalysisRecord"]] = relationship(
        "CivicVoiceAnalysisRecord",
        back_populates="source_record",
        cascade="all, delete-orphan",
    )


class CivicVoiceAnalysisRecord(Base):
    """Structured opinion analysis result for a specific collected source record."""

    __tablename__ = "civicvoice_analysis_records"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    source_record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("civicvoice_source_records.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )

    sentiment: Mapped[str | None] = mapped_column(
        String(20),
        index=True,
        nullable=True,
    )

    content_intent: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    confidence: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    detected_language: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    has_complaint: Mapped[bool] = mapped_column(
        Boolean,
        index=True,
        nullable=False,
        default=False,
    )

    extracted_complaint: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    has_suggestion: Mapped[bool] = mapped_column(
        Boolean,
        index=True,
        nullable=False,
        default=False,
    )

    extracted_suggestion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    theme_id: Mapped[str | None] = mapped_column(
        String(50),
        index=True,
        nullable=True,
    )

    theme_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    analysis_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="rule_based_multilingual",
    )

    analysis_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="v1.0",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    source_record: Mapped["CivicVoiceSourceRecord"] = relationship(
        "CivicVoiceSourceRecord",
        back_populates="analyses",
    )


class CivicVoiceCitizenSubmission(Base):
    """Citizen-submitted community opinion or feedback.

    Persisted separately from externally collected source records to guarantee
    data provenance, privacy isolation, and clear distinction between public web
    sources and local resident submissions.
    """

    __tablename__ = "civicvoice_citizen_submissions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    topic: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    opinion_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    locality: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        default="en",
    )

    consent_given: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CivicVoiceReport(Base):
    """Evidence-backed civic intelligence report for official department communication.

    Synthesizes public opinion analysis and aggregate resident feedback into an
    audited, human-reviewed civic priority report.
    """

    __tablename__ = "civicvoice_reports"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    topic: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    geographic_scope: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        default="Bengaluru Urban (BBMP Wards)",
    )

    reporting_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reporting_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        index=True,
        nullable=False,
        default="draft",
    )

    # Department & Official-Channel Mapping
    authority_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    department_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    recipient_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    official_portal_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    mapping_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    mapping_source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    mapping_last_verified: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Aggregated Evidence Counts & Content
    source_records_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    citizen_submissions_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    summary_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recommendations: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    themes_summary: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    sentiment_summary: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    evidence_urls: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    limitations: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Audit, Hash Binding & Review Integrity
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    approved_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Official Delivery & Idempotency
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
        nullable=True,
    )

    delivery_details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    audits: Mapped[list["CivicVoiceReportAudit"]] = relationship(
        "CivicVoiceReportAudit",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="CivicVoiceReportAudit.created_at.desc()",
    )


class CivicVoiceReportAudit(Base):
    """Immutable audit trail of review actions, status changes, and dispatch operations."""

    __tablename__ = "civicvoice_report_audits"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("civicvoice_reports.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    performed_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    previous_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    new_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    details_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    report: Mapped["CivicVoiceReport"] = relationship(
        "CivicVoiceReport",
        back_populates="audits",
    )


