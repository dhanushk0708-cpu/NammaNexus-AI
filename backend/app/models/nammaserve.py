from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNAVAILABLE = "UNAVAILABLE"
    FLAGGED = "FLAGGED"
    OUTDATED = "OUTDATED"


class SourceType(str, Enum):
    LOCAL_DATABASE = "LOCAL_DATABASE"
    DIRECT_PROVIDER = "DIRECT_PROVIDER"
    INDEPENDENT_PROVIDER = "INDEPENDENT_PROVIDER"
    GOOGLE_PLACES = "GOOGLE_PLACES"
    GEOAPIFY = "GEOAPIFY"
    FOURSQUARE = "FOURSQUARE"
    URBAN_COMPANY = "URBAN_COMPANY"
    NOBROKER = "NOBROKER"
    JUSTDIAL = "JUSTDIAL"
    SULEKHA = "SULEKHA"
    WEB = "WEB"
    OTHER = "OTHER"


class PriceType(str, Enum):
    FIXED = "FIXED"
    STARTING_AT = "STARTING_AT"
    RANGE = "RANGE"
    HOURLY = "HOURLY"
    QUOTE_REQUIRED = "QUOTE_REQUIRED"
    CONSULTATION_FEE = "CONSULTATION_FEE"
    PER_UNIT = "PER_UNIT"
    FIXED_DEFAULT_OPTION = "FIXED_DEFAULT_OPTION"
    FIXED_BY_VARIANT = "FIXED_BY_VARIANT"
    NOT_PUBLISHED = "NOT_PUBLISHED"


class PlatformType(str, Enum):
    URBAN_COMPANY = "URBAN_COMPANY"
    NOBROKER = "NOBROKER"
    JUSTDIAL = "JUSTDIAL"
    SULEKHA = "SULEKHA"
    DIRECT_LOCAL = "DIRECT_LOCAL"
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
    individual_services: Mapped[list["Service"]] = relationship(
        "Service",
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
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
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
    offerings: Mapped[list["ProviderOffering"]] = relationship(
        "ProviderOffering",
        back_populates="provider",
        cascade="all, delete-orphan",
    )
    citizen_reviews: Mapped[list["CitizenReview"]] = relationship(
        "CitizenReview",
        back_populates="provider",
        cascade="all, delete-orphan",
    )
    third_party_reviews: Mapped[list["ThirdPartyReview"]] = relationship(
        "ThirdPartyReview",
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


class Service(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("service_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
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

    category: Mapped["ServiceCategory"] = relationship(
        "ServiceCategory",
        back_populates="individual_services",
    )
    platform_listings: Mapped[list["PlatformListing"]] = relationship(
        "PlatformListing",
        back_populates="service",
        cascade="all, delete-orphan",
    )
    provider_offerings: Mapped[list["ProviderOffering"]] = relationship(
        "ProviderOffering",
        back_populates="service",
        cascade="all, delete-orphan",
    )
    prices: Mapped[list["ServicePrice"]] = relationship(
        "ServicePrice",
        back_populates="service",
        cascade="all, delete-orphan",
    )


class PlatformListing(Base):
    __tablename__ = "platform_listings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    service_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    locality: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    city: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Bengaluru",
    )
    listing_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    booking_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
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
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
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

    service: Mapped["Service"] = relationship(
        "Service",
        back_populates="platform_listings",
    )
    prices: Mapped[list["ServicePrice"]] = relationship(
        "ServicePrice",
        back_populates="platform_listing",
        cascade="all, delete-orphan",
    )
    third_party_reviews: Mapped[list["ThirdPartyReview"]] = relationship(
        "ThirdPartyReview",
        back_populates="platform_listing",
        cascade="all, delete-orphan",
    )


class ProviderOffering(Base):
    __tablename__ = "provider_offerings"
    __table_args__ = (
        UniqueConstraint("provider_id", "service_id", name="uq_provider_individual_service"),
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
    service_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    custom_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
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
        back_populates="offerings",
    )
    service: Mapped["Service"] = relationship(
        "Service",
        back_populates="provider_offerings",
    )
    prices: Mapped[list["ServicePrice"]] = relationship(
        "ServicePrice",
        back_populates="provider_offering",
        cascade="all, delete-orphan",
    )


class ServicePrice(Base):
    __tablename__ = "service_prices"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    service_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    amount: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    price_min: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    price_max: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="INR",
    )
    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    platform_listing_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("platform_listings.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    provider_offering_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("provider_offerings.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    conditions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    inclusions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    exclusions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    verification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=VerificationStatus.UNVERIFIED.value,
        index=True,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    research_record_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    comparison_group: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    comparability_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    comparability_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    service: Mapped["Service"] = relationship(
        "Service",
        back_populates="prices",
    )
    platform_listing: Mapped["PlatformListing | None"] = relationship(
        "PlatformListing",
        back_populates="prices",
    )
    provider_offering: Mapped["ProviderOffering | None"] = relationship(
        "ProviderOffering",
        back_populates="prices",
    )

    def validate_pricing_consistency(self) -> None:
        """Validate price fields according to price_type rules."""
        if self.currency != "INR":
            raise ValueError(f"Unsupported currency: {self.currency}. Only INR is supported.")

        pt = self.price_type
        if pt == PriceType.FIXED.value:
            if self.amount is None or self.amount <= 0:
                raise ValueError("FIXED pricing requires a positive amount.")
        elif pt == PriceType.STARTING_AT.value:
            val = self.amount if self.amount is not None else self.price_min
            if val is None or val <= 0:
                raise ValueError("STARTING_AT pricing requires a positive amount or price_min.")
        elif pt == PriceType.RANGE.value:
            if self.price_min is None or self.price_max is None:
                raise ValueError("RANGE pricing requires both price_min and price_max.")
            if self.price_min <= 0 or self.price_max <= 0:
                raise ValueError("RANGE pricing requires positive bounds.")
            if self.price_min > self.price_max:
                raise ValueError(f"RANGE price_min ({self.price_min}) cannot exceed price_max ({self.price_max}).")
        elif pt == PriceType.CONSULTATION_FEE.value:
            if self.amount is None or self.amount < 0:
                raise ValueError("CONSULTATION_FEE pricing requires a non-negative amount.")
        elif pt == PriceType.PER_UNIT.value:
            val = self.amount if self.amount is not None else self.price_min
            if val is None or val <= 0:
                raise ValueError("PER_UNIT pricing requires a positive amount or price_min.")
            if not self.unit or not self.unit.strip():
                raise ValueError("PER_UNIT pricing requires a specified unit.")
        elif pt == PriceType.QUOTE_REQUIRED.value:
            pass
        elif pt in {
            PriceType.FIXED_DEFAULT_OPTION.value,
            PriceType.FIXED_BY_VARIANT.value,
            PriceType.NOT_PUBLISHED.value,
        }:
            pass
        else:
            raise ValueError(f"Unknown price_type: {pt}")


class CitizenReview(Base):
    __tablename__ = "citizen_reviews"

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
    service_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("services.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    citizen_user_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    rating: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    review_title: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    review_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    locality: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    service_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_verified_resident: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
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
        back_populates="citizen_reviews",
    )
    service: Mapped["Service | None"] = relationship(
        "Service",
    )


class ThirdPartyReview(Base):
    __tablename__ = "third_party_reviews"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    provider_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    platform_listing_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("platform_listings.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    external_rating: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    external_reviews_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    provider: Mapped["Provider | None"] = relationship(
        "Provider",
        back_populates="third_party_reviews",
    )
    platform_listing: Mapped["PlatformListing | None"] = relationship(
        "PlatformListing",
        back_populates="third_party_reviews",
    )
