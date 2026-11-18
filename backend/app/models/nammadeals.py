from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BusinessRegistrationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class BusinessStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class CampaignApprovalStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class CampaignType(str, Enum):
    DISCOUNT = "DISCOUNT"
    COUPON = "COUPON"
    SCRATCH_CARD = "SCRATCH_CARD"
    AWARENESS = "AWARENESS"


class TargetingStrategy(str, Enum):
    RADIUS = "RADIUS"
    WARD = "WARD"
    CITYWIDE = "CITYWIDE"
    ONLINE = "ONLINE"


class OfferType(str, Enum):
    COUPON = "COUPON"
    SCRATCH_CARD = "SCRATCH_CARD"
    INSTANT_DISCOUNT = "INSTANT_DISCOUNT"


class DiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FLAT = "FLAT"
    FREEBIE = "FREEBIE"
    REWARD = "REWARD"


class PaymentMethod(str, Enum):
    UPI = "UPI"
    CARD = "CARD"
    NETBANKING = "NETBANKING"
    BANK_TRANSFER = "BANK_TRANSFER"


class PaymentVerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PromotionEventType(str, Enum):
    IMPRESSION = "IMPRESSION"
    CLICK = "CLICK"
    CLAIM = "CLAIM"
    REDEMPTION = "REDEMPTION"


class BusinessRegistration(Base):
    """Prospective local business registration submitted by business owners for review."""

    __tablename__ = "nammadeals_business_registrations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    contact_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), server_default="Bengaluru", nullable=False)
    area: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(
        String(30),
        default=BusinessRegistrationStatus.PENDING.value,
        server_default=BusinessRegistrationStatus.PENDING.value,
        index=True,
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    business: Mapped["Business | None"] = relationship(
        "Business",
        back_populates="registration",
        uselist=False,
    )


class Business(Base):
    """Verified and managed local business profile in NammaNexus."""

    __tablename__ = "nammadeals_businesses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    owner_user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    registration_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("nammadeals_business_registrations.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), server_default="Bengaluru", nullable=False)
    area: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(
        String(30),
        default=BusinessStatus.PENDING.value,
        server_default=BusinessStatus.PENDING.value,
        index=True,
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    registration: Mapped[BusinessRegistration | None] = relationship(
        "BusinessRegistration",
        back_populates="business",
    )
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign",
        back_populates="business",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["AdvertiserPayment"]] = relationship(
        "AdvertiserPayment",
        back_populates="business",
        cascade="all, delete-orphan",
    )


class Campaign(Base):
    """Advertising or promotional campaign created by a verified local business."""

    __tablename__ = "nammadeals_campaigns"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    business_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("nammadeals_businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign_type: Mapped[str] = mapped_column(
        String(50),
        default=CampaignType.DISCOUNT.value,
        server_default=CampaignType.DISCOUNT.value,
        nullable=False,
    )

    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    approval_status: Mapped[str] = mapped_column(
        String(30),
        default=CampaignApprovalStatus.DRAFT.value,
        server_default=CampaignApprovalStatus.DRAFT.value,
        index=True,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        index=True,
        nullable=False,
    )

    targeting_strategy: Mapped[str] = mapped_column(
        String(50),
        default=TargetingStrategy.RADIUS.value,
        server_default=TargetingStrategy.RADIUS.value,
        nullable=False,
    )
    targeting_radius_km: Mapped[float] = mapped_column(
        Float,
        default=5.0,
        server_default="5.0",
        nullable=False,
    )
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    priority: Mapped[int] = mapped_column(
        Integer,
        default=10,
        server_default="10",
        nullable=False,
    )
    frequency_limit_per_user: Mapped[int] = mapped_column(
        Integer,
        default=3,
        server_default="3",
        nullable=False,
    )
    placement_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    business: Mapped[Business] = relationship("Business", back_populates="campaigns")
    offers: Mapped[list["Offer"]] = relationship(
        "Offer",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["AdvertiserPayment"]] = relationship(
        "AdvertiserPayment",
        back_populates="campaign",
    )


class Offer(Base):
    """Specific discount, voucher, scratch card or coupon offer within a campaign."""

    __tablename__ = "nammadeals_offers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("nammadeals_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    promotional_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    discount_type: Mapped[str] = mapped_column(
        String(30),
        default=DiscountType.PERCENTAGE.value,
        server_default=DiscountType.PERCENTAGE.value,
        nullable=False,
    )
    discount_value: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0.0",
        nullable=False,
    )
    terms_and_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)

    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    offer_type: Mapped[str] = mapped_column(
        String(30),
        default=OfferType.COUPON.value,
        server_default=OfferType.COUPON.value,
        nullable=False,
    )
    coupon_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    scratch_card_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    max_redemptions: Mapped[int] = mapped_column(
        Integer,
        default=100,
        server_default="100",
        nullable=False,
    )
    redemption_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="offers")


class AdvertiserPayment(Base):
    """Payment records for advertising campaigns and business platform subscriptions."""

    __tablename__ = "nammadeals_payments"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    business_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("nammadeals_businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("nammadeals_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), server_default="INR", nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(50),
        default=PaymentMethod.UPI.value,
        server_default=PaymentMethod.UPI.value,
        nullable=False,
    )
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    verification_status: Mapped[str] = mapped_column(
        String(30),
        default=PaymentVerificationStatus.PENDING.value,
        server_default=PaymentVerificationStatus.PENDING.value,
        index=True,
        nullable=False,
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    business: Mapped[Business] = relationship("Business", back_populates="payments")
    campaign: Mapped[Campaign | None] = relationship("Campaign", back_populates="payments")


class PromotionEvent(Base):
    """Reliable event tracking for impressions, clicks, claims and redemptions."""

    __tablename__ = "nammadeals_promotion_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    event_type: Mapped[str] = mapped_column(
        String(30),
        index=True,
        nullable=False,
    )
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("nammadeals_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    offer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("nammadeals_offers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    citizen_user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    location_source: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    campaign: Mapped[Campaign] = relationship("Campaign")
    offer: Mapped[Offer | None] = relationship("Offer")

