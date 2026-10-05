from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    FLAGGED = "FLAGGED"
    OUTDATED = "OUTDATED"


class SourceType(str, Enum):
    LOCAL_DATABASE = "LOCAL_DATABASE"
    DIRECT_PROVIDER = "DIRECT_PROVIDER"
    GOOGLE_PLACES = "GOOGLE_PLACES"
    URBAN_COMPANY = "URBAN_COMPANY"
    NOBROKER = "NOBROKER"
    WEB = "WEB"
    OTHER = "OTHER"


class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    icon_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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

    services: Mapped[list["ProviderService"]] = relationship(
        "ProviderService",
        back_populates="category",
        cascade="all, delete-orphan",
    )


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )
    contact_person: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    alternate_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    primary_area: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    city: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Bengaluru",
    )
    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    service_radius_km: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=5.0,
    )
    operating_hours: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    is_emergency_service: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # Verification metadata
    verification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=VerificationStatus.UNVERIFIED.value,
        index=True,
    )
    source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SourceType.LOCAL_DATABASE.value,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    services: Mapped[list["ProviderService"]] = relationship(
        "ProviderService",
        back_populates="provider",
        cascade="all, delete-orphan",
    )
    service_areas: Mapped[list["ProviderServiceArea"]] = relationship(
        "ProviderServiceArea",
        back_populates="provider",
        cascade="all, delete-orphan",
    )


class ProviderService(Base):
    __tablename__ = "provider_services"
    __table_args__ = (
        UniqueConstraint("provider_id", "category_id", name="uq_provider_category"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("service_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Service-specific facts
    price_min: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    price_max: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    price_unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    minimum_order: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    capacity: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    water_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    availability: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    payment_methods: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Verification metadata
    verification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=VerificationStatus.UNVERIFIED.value,
        index=True,
    )
    source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SourceType.LOCAL_DATABASE.value,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    provider: Mapped["Provider"] = relationship(
        "Provider",
        back_populates="services",
    )
    category: Mapped["ServiceCategory"] = relationship(
        "ServiceCategory",
        back_populates="services",
    )


class ProviderServiceArea(Base):
    __tablename__ = "provider_service_areas"
    __table_args__ = (
        UniqueConstraint("provider_id", "area_name", name="uq_provider_area"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    area_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    ward_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    provider: Mapped["Provider"] = relationship(
        "Provider",
        back_populates="service_areas",
    )
