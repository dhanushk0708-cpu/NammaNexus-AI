import re
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.nammadeals import (
    BusinessRegistrationStatus,
    BusinessStatus,
    CampaignApprovalStatus,
    CampaignType,
    DiscountType,
    OfferType,
    PaymentMethod,
    PaymentVerificationStatus,
    PromotionEventType,
    TargetingStrategy,
    CouponClaimStatus,
)


# --- Business Registration Schemas ---

class BusinessRegistrationCreate(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(None, max_length=2000)
    category: str = Field(..., min_length=2, max_length=100)
    contact_name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", max_length=255)
    phone: str = Field(..., min_length=8, max_length=20)
    address: str = Field(..., min_length=5, max_length=500)
    city: str = Field("Bengaluru", min_length=2, max_length=100)
    area: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., pattern=r"^\d{6}$")
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = "".join(c for c in v if c.isdigit() or c == "+")
        digits_only = "".join(c for c in cleaned if c.isdigit())
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError("Phone number must contain between 10 and 15 digits.")
        return cleaned


class BusinessRegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_name: str
    description: str | None = None
    category: str
    contact_name: str
    email: str
    phone: str
    address: str
    city: str
    area: str
    pincode: str
    latitude: float | None = None
    longitude: float | None = None
    status: BusinessRegistrationStatus
    rejection_reason: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class BusinessRegistrationReviewRequest(BaseModel):
    action: Literal["APPROVE", "REJECT"]
    owner_user_id: str | None = Field(
        None,
        description="Assigned owner user ID when approving registration (e.g. from existing auth/user account)",
    )
    rejection_reason: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def validate_action_fields(self) -> "BusinessRegistrationReviewRequest":
        if self.action == "APPROVE" and not self.owner_user_id:
            raise ValueError("owner_user_id is required when approving a registration.")
        if self.action == "REJECT" and not self.rejection_reason:
            raise ValueError("rejection_reason is required when rejecting a registration.")
        return self


# --- Business Schemas ---

class BusinessCreate(BaseModel):
    owner_user_id: str = Field(..., min_length=1, max_length=100)
    registration_id: str | None = None
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(None, max_length=2000)
    category: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", max_length=255)
    phone: str = Field(..., min_length=8, max_length=20)
    address: str = Field(..., min_length=5, max_length=500)
    city: str = Field("Bengaluru", min_length=2, max_length=100)
    area: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., pattern=r"^\d{6}$")
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)


class BusinessUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = Field(None, max_length=2000)
    category: str | None = Field(None, min_length=2, max_length=100)
    email: str | None = Field(None, pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", max_length=255)
    phone: str | None = Field(None, min_length=8, max_length=20)
    address: str | None = Field(None, min_length=5, max_length=500)
    city: str | None = Field(None, min_length=2, max_length=100)
    area: str | None = Field(None, min_length=2, max_length=100)
    pincode: str | None = Field(None, pattern=r"^\d{6}$")
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)


class BusinessStatusUpdateRequest(BaseModel):
    status: BusinessStatus
    reason: str | None = Field(None, max_length=1000)


class BusinessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_user_id: str
    registration_id: str | None = None
    name: str
    description: str | None = None
    category: str
    email: str
    phone: str
    address: str
    city: str
    area: str
    pincode: str
    latitude: float | None = None
    longitude: float | None = None
    status: BusinessStatus
    verified_at: datetime | None = None
    verified_by: str | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime


# --- Campaign Schemas ---

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(None, max_length=2000)
    campaign_type: CampaignType = CampaignType.DISCOUNT
    start_date: datetime
    end_date: datetime
    targeting_strategy: TargetingStrategy = TargetingStrategy.RADIUS
    targeting_radius_km: float = Field(default=5.0, ge=0.1, le=50.0)
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    priority: int = Field(default=10, ge=1, le=100)
    frequency_limit_per_user: int = Field(default=3, ge=1, le=50)
    placement_config: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "CampaignCreate":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be strictly after start_date.")
        return self


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = Field(None, max_length=2000)
    campaign_type: CampaignType | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    targeting_strategy: TargetingStrategy | None = None
    targeting_radius_km: float | None = Field(None, ge=0.1, le=50.0)
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    priority: int | None = Field(None, ge=1, le=100)
    frequency_limit_per_user: int | None = Field(None, ge=1, le=50)
    placement_config: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_dates_if_both(self) -> "CampaignUpdate":
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date must be strictly after start_date.")
        return self


class CampaignReviewRequest(BaseModel):
    action: Literal["APPROVE", "REJECT", "SUSPEND"]
    rejection_reason: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def validate_review(self) -> "CampaignReviewRequest":
        if self.action == "REJECT" and not self.rejection_reason:
            raise ValueError("rejection_reason is required when rejecting a campaign.")
        return self


class CampaignToggleActiveRequest(BaseModel):
    is_active: bool


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    name: str
    description: str | None = None
    campaign_type: CampaignType
    start_date: datetime
    end_date: datetime
    approval_status: CampaignApprovalStatus
    is_active: bool
    targeting_strategy: TargetingStrategy
    targeting_radius_km: float
    latitude: float | None = None
    longitude: float | None = None
    priority: int
    frequency_limit_per_user: int
    placement_config: dict[str, Any] | None = None
    rejection_reason: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# --- Offer Schemas ---

class OfferCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(None, max_length=2000)
    promotional_image_url: str | None = Field(None, max_length=500)
    discount_type: DiscountType = DiscountType.PERCENTAGE
    discount_value: float = Field(default=0.0, ge=0.0)
    terms_and_conditions: str | None = Field(None, max_length=3000)
    valid_from: datetime
    valid_until: datetime
    offer_type: OfferType = OfferType.COUPON
    coupon_code: str | None = Field(None, min_length=3, max_length=50)
    scratch_card_config: dict[str, Any] | None = None
    max_redemptions: int = Field(default=100, ge=1)

    @model_validator(mode="after")
    def validate_offer(self) -> "OfferCreate":
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be strictly after valid_from.")
        if self.offer_type == OfferType.COUPON and not self.coupon_code:
            raise ValueError("coupon_code is required for COUPON offers.")
        if self.offer_type == OfferType.SCRATCH_CARD and not self.scratch_card_config:
            raise ValueError("scratch_card_config is required for SCRATCH_CARD offers.")
        if self.discount_type == DiscountType.PERCENTAGE and self.discount_value > 100.0:
            raise ValueError("PERCENTAGE discount value cannot exceed 100%.")
        return self


class OfferUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = Field(None, max_length=2000)
    promotional_image_url: str | None = Field(None, max_length=500)
    discount_type: DiscountType | None = None
    discount_value: float | None = Field(None, ge=0.0)
    terms_and_conditions: str | None = Field(None, max_length=3000)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    offer_type: OfferType | None = None
    coupon_code: str | None = Field(None, min_length=3, max_length=50)
    scratch_card_config: dict[str, Any] | None = None
    max_redemptions: int | None = Field(None, ge=1)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_offer_update(self) -> "OfferUpdate":
        if self.valid_from and self.valid_until and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be strictly after valid_from.")
        if self.discount_type == DiscountType.PERCENTAGE and self.discount_value is not None and self.discount_value > 100.0:
            raise ValueError("PERCENTAGE discount value cannot exceed 100%.")
        return self


class OfferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    title: str
    description: str | None = None
    promotional_image_url: str | None = None
    discount_type: DiscountType
    discount_value: float
    terms_and_conditions: str | None = None
    valid_from: datetime
    valid_until: datetime
    offer_type: OfferType
    coupon_code: str | None = None
    scratch_card_config: dict[str, Any] | None = None
    max_redemptions: int
    redemption_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- Advertiser Payment Schemas ---

class AdvertiserPaymentCreate(BaseModel):
    campaign_id: str | None = None
    amount: float = Field(..., gt=0.0)
    currency: str = Field("INR", min_length=3, max_length=10)
    transaction_id: str = Field(..., min_length=3, max_length=100)
    payment_method: PaymentMethod = PaymentMethod.UPI
    payment_date: datetime


class AdvertiserPaymentVerifyRequest(BaseModel):
    action: Literal["VERIFY", "FAIL", "REFUND"]
    admin_notes: str | None = Field(None, max_length=1000)


class AdvertiserPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    campaign_id: str | None = None
    amount: float
    currency: str
    transaction_id: str
    payment_method: PaymentMethod
    payment_date: datetime
    verification_status: PaymentVerificationStatus
    admin_notes: str | None = None
    created_at: datetime
    updated_at: datetime


# --- Promotion Engine Schemas ---

class LocationPolicy(str, Enum):
    PROFILE_ONLY = "PROFILE_ONLY"
    COMPLAINT_ONLY = "COMPLAINT_ONLY"
    PREFER_COMPLAINT = "PREFER_COMPLAINT"
    PREFER_PROFILE = "PREFER_PROFILE"
    COMBINED = "COMBINED"


class CitizenProfileLocation(BaseModel):
    state: str | None = Field(None, max_length=100)
    city: str | None = Field("Bengaluru", max_length=100)
    area: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, pattern=r"^\d{6}$")
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)


class SpotFixComplaintLocation(BaseModel):
    complaint_id: str | None = Field(None, max_length=36, description="Optional SpotFix complaint ID for server-side verification")
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    area: str | None = Field(None, max_length=100)
    ward: str | None = Field(None, max_length=100)


class PromotionSelectionRequest(BaseModel):
    citizen_user_id: str | None = Field(None, max_length=100)
    location_policy: LocationPolicy = LocationPolicy.COMBINED
    profile_location: CitizenProfileLocation | None = None
    complaint_location: SpotFixComplaintLocation | None = None
    limit: int = Field(default=3, ge=1, le=10)


class PromotionOfferItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None = None
    promotional_image_url: str | None = None
    discount_type: DiscountType
    discount_value: float
    terms_and_conditions: str | None = None
    valid_until: datetime
    offer_type: OfferType
    coupon_code: str | None = None


class PromotionItem(BaseModel):
    campaign_id: str
    campaign_name: str
    campaign_type: CampaignType
    business_name: str
    business_category: str
    business_area: str
    matched_location_source: Literal["COMPLAINT", "PROFILE", "NEARBY", "CITYWIDE", "ONLINE"]
    distance_km: float | None = None
    offers: list[PromotionOfferItem] = Field(default_factory=list)


class PromotionSelectionResponse(BaseModel):
    promotions: list[PromotionItem]
    total_selected: int
    location_sources_evaluated: list[str]
    policy_applied: LocationPolicy


# --- Promotion Event Tracking Schemas ---

class PromotionEventCreate(BaseModel):
    event_type: PromotionEventType
    campaign_id: str = Field(..., max_length=36)
    offer_id: str | None = Field(None, max_length=36)
    location_source: str | None = Field(None, max_length=30)
    idempotency_key: str | None = Field(None, max_length=100)
    event_metadata: dict[str, Any] | None = None


class PromotionEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: PromotionEventType
    campaign_id: str
    offer_id: str | None = None
    citizen_user_id: str
    location_source: str | None = None
    idempotency_key: str | None = None
    created_at: datetime


# --- Coupon Claim & Scratch Card Schemas ---

class CouponClaimCreate(BaseModel):
    offer_id: str = Field(..., min_length=1, max_length=36)
    client_notes: str | None = Field(None, max_length=500)


class CouponClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    citizen_user_id: str
    campaign_id: str
    offer_id: str
    unique_coupon_code: str
    status: CouponClaimStatus
    claimed_at: datetime
    redeemed_at: datetime | None = None
    redeemed_by_business_id: str | None = None
    redemption_notes: str | None = None
    scratch_reward_revealed: bool = False
    claim_metadata: dict[str, Any] | None = None

    # Enriched fields for UI convenience (tenant-privacy preserved: no citizen PII to business)
    business_id: str | None = None
    business_name: str | None = None
    business_area: str | None = None
    campaign_name: str | None = None
    offer_title: str | None = None
    offer_description: str | None = None
    offer_type: OfferType | None = None
    discount_type: DiscountType | None = None
    discount_value: float | None = None
    terms_and_conditions: str | None = None
    valid_until: datetime | None = None


class ScratchCardRevealRequest(BaseModel):
    notes: str | None = Field(None, max_length=200)


class ScratchCardRevealRead(BaseModel):
    success: bool = True
    message: str
    claim: CouponClaimRead
    reward_headline: str
    reward_description: str
    discount_percentage: float | None = None
    revealed_at: datetime
    is_already_revealed: bool = False


# --- Coupon Redemption Schemas ---

class CouponRedemptionRequest(BaseModel):
    coupon_code: str = Field(..., min_length=4, max_length=64)
    notes: str | None = Field(None, max_length=500)


class CouponRedemptionRead(BaseModel):
    success: bool = True
    message: str
    unique_coupon_code: str
    redeemed_at: datetime
    business_id: str
    business_name: str
    campaign_id: str
    campaign_name: str
    offer_id: str
    offer_title: str
    discount_summary: str
    redemption_notes: str | None = None
    claim: CouponClaimRead


# --- Analytics & Reporting Schemas ---

class CampaignAnalyticsRead(BaseModel):
    campaign_id: str
    campaign_name: str
    status: str
    impressions: int
    clicks: int
    claims: int
    redemptions: int
    ctr_percentage: float
    claim_rate_percentage: float
    redemption_rate_percentage: float
    budget_allocated: float | None = None


class BusinessAnalyticsRead(BaseModel):
    business_id: str
    business_name: str
    total_campaigns: int
    active_campaigns: int
    total_offers: int
    impressions: int
    clicks: int
    claims: int
    redemptions: int
    overall_ctr_percentage: float
    overall_redemption_rate_percentage: float
    verified_payments_total: float


class AdminPlatformAnalyticsRead(BaseModel):
    total_registrations: int
    pending_registrations: int
    total_businesses: int
    verified_businesses: int
    total_campaigns: int
    active_campaigns: int
    pending_campaign_approvals: int
    total_impressions: int
    total_clicks: int
    total_claims: int
    total_redemptions: int
    overall_ctr_percentage: float
    total_revenue_inr: float
    pending_revenue_inr: float


