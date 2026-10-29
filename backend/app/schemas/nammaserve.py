from __future__ import annotations

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.nammaserve import PlatformType, PriceType, SourceType, VerificationStatus


class ServiceMatchLevel(str, Enum):
    CONFIRMED = "CONFIRMED"
    PROBABLE = "PROBABLE"
    UNCONFIRMED = "UNCONFIRMED"


class SourceEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str | None = None
    source_type: SourceType = SourceType.LOCAL_DATABASE
    source_url: str | None = None
    last_verified_at: datetime | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    notes: str | None = None


class ServiceCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    description: str | None = None
    icon_name: str | None = None
    is_active: bool = True


class ProviderServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str
    category_slug: str | None = None
    category_name: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    price_unit: str | None = None
    minimum_order: str | None = None
    capacity: str | None = None
    water_type: str | None = None
    availability: str | None = None
    payment_methods: str | None = None
    notes: str | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    source: str | None = None
    source_type: SourceType = SourceType.LOCAL_DATABASE
    source_url: str | None = None
    last_verified_at: datetime | None = None


class ProviderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    contact_person: str | None = None
    phone: str | None = None
    alternate_phone: str | None = None
    address: str | None = None
    primary_area: str | None = None
    city: str = "Bengaluru"
    latitude: float | None = None
    longitude: float | None = None
    service_radius_km: float = 5.0
    operating_hours: str | None = None
    is_emergency_service: bool = False
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    source: str | None = None
    source_type: SourceType = SourceType.LOCAL_DATABASE
    source_url: str | None = None
    last_verified_at: datetime | None = None
    services: list[ProviderServiceRead] = []
    serviced_areas: list[str] = []


class DiscoveryQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    service: str | None = Field(default=None, description="Category slug or keyword (e.g. water-tanker, locksmith)")
    lat: float | None = Field(default=None, ge=-90, le=90, description="Citizen latitude")
    lng: float | None = Field(default=None, ge=-180, le=180, description="Citizen longitude")
    radius_km: float = Field(default=5.0, gt=0, le=50.0, description="Search radius in kilometers")
    area: str | None = Field(default=None, description="Named area / locality filter (e.g. Indiranagar, HSR Layout)")
    verified_only: bool = Field(default=False, description="Filter only verified providers")
    emergency_only: bool = Field(default=False, description="Filter only emergency / 24x7 providers")
    limit: int = Field(default=20, ge=1, le=100)
    resolved_service_slug: str | None = Field(default=None, description="Resolved individual service slug")
    resolved_category_slug: str | None = Field(default=None, description="Resolved parent category slug")
    resolved_service_name: str | None = Field(default=None, description="Resolved human-readable service name")
    resolved_category_name: str | None = Field(default=None, description="Resolved parent category name")
    service_match_level: ServiceMatchLevel = ServiceMatchLevel.UNCONFIRMED
    service_match_confidence: float = 0.0
    is_ambiguous: bool = False
    possible_matches: list[dict[str, str]] = Field(default_factory=list)


class NormalizedProviderResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str | None = None
    alternate_phone: str | None = None
    contact_person: str | None = None
    address: str | None = None
    area: str | None = None
    city: str = "Bengaluru"
    latitude: float | None = None
    longitude: float | None = None
    distance_km: float | None = None

    # Service-specific matched info
    matched_service_slug: str | None = None
    matched_service_name: str | None = None
    amount: float | None = None
    price_min: float | None = None
    price_max: float | None = None
    price_unit: str | None = None
    price_type: str | None = None
    currency: str = "INR"
    formatted_price: str | None = None
    is_price_available: bool = True
    inclusions: str | None = None
    exclusions: str | None = None
    conditions: str | None = None
    evidence_notes: str | None = None
    minimum_order: str | None = None
    capacity: str | None = None
    water_type: str | None = None
    availability: str | None = None
    payment_methods: str | None = None
    operating_hours: str | None = None
    is_emergency_service: bool = False
    notes: str | None = None

    # Rating and review metrics (if published legitimately by source)
    rating: float | None = None
    review_count: int | None = None

    # Phase 2: Service-matching confidence & provenance
    service_match_level: ServiceMatchLevel = ServiceMatchLevel.UNCONFIRMED
    service_match_confidence: float = Field(default=0.0, description="Match confidence between 0.0 and 1.0")
    service_match_reason: str | None = None
    sources: list[str] = Field(default_factory=list, description="All discovery sources contributing to this record")
    external_ids: dict[str, str] = Field(default_factory=dict, description="Platform identifiers (e.g. geoapify_id, fsq_id, osm_id)")
    website: str | None = None
    discovered_at: datetime | None = None
    last_checked_at: datetime | None = None

    # Evidence & Verification
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    source: str | None = None
    source_type: SourceType = SourceType.LOCAL_DATABASE
    source_url: str | None = None
    last_verified_at: datetime | None = None
    research_record_id: str | None = None
    comparison_group: str | None = None
    comparability_label: str | None = None
    comparability_reason: str | None = None

    # Ranking & Explainability
    match_score: float = Field(default=0.0, description="Deterministic match score between 0 and 100")
    ranking_reasons: list[str] = Field(default_factory=list, description="Explainable reasons why this provider was ranked")


class ConnectorStatus(BaseModel):
    connector_name: str
    source_type: SourceType
    is_available: bool
    status_message: str
    results_count: int = 0


class PriceComparisonItem(BaseModel):
    """Normalized comparative pricing entry for a platform or provider offering."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    provider_type: str = "PLATFORM"  # "PLATFORM" or "INDEPENDENT_PROVIDER"
    pricing_type: str | None = None
    amount: float | None = None
    price_min: float | None = None
    price_max: float | None = None
    price_unit: str | None = None
    currency: str = "INR"
    formatted_price: str
    is_comparable: bool = True
    is_available: bool = True
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    source: str | None = None
    source_url: str | None = None
    last_verified_at: datetime | None = None
    inclusions: str | None = None
    conditions: str | None = None
    evidence_notes: str | None = None
    booking_url: str | None = None
    comparability_note: str | None = None
    comparison_group: str | None = None
    comparability_label: str | None = None


class PriceComparisonSummary(BaseModel):
    """Aggregate benchmark comparison across platforms and independent providers for a canonical service."""
    model_config = ConfigDict(from_attributes=True)

    canonical_service_slug: str | None = None
    canonical_service_name: str | None = None
    category_slug: str | None = None
    category_name: str | None = None
    currency: str = "INR"
    benchmark_unit: str | None = None
    price_range_display: str | None = None
    lowest_price: float | None = None
    highest_price: float | None = None
    verified_count: int = 0
    partially_verified_count: int = 0
    unverified_count: int = 0
    quote_required_count: int = 0
    unavailable_count: int = 0
    comparable_items: list[PriceComparisonItem] = Field(default_factory=list)
    quote_required_items: list[PriceComparisonItem] = Field(default_factory=list)
    unavailable_items: list[PriceComparisonItem] = Field(default_factory=list)
    notes: str | None = None

    @property
    def total_providers_compared(self) -> int:
        return len(self.comparable_items) + len(self.quote_required_items) + len(self.unavailable_items)


class UnifiedDiscoveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: DiscoveryQuery
    total_results: int = 0
    connectors_contacted: list[ConnectorStatus] = Field(default_factory=list)
    results: list[NormalizedProviderResult] = Field(default_factory=list)
    price_comparison: PriceComparisonSummary | None = None


class ServiceIntent(BaseModel):
    """Structured citizen intent extracted by the LLM from natural language query."""
    model_config = ConfigDict(extra="ignore")

    service: str | None = Field(
        default=None,
        description="Canonical service slug (e.g. water-tanker, solar-heater-repair, e-waste-pickup, locksmith-emergency, debris-bulk-waste) or service term.",
    )
    location: str | None = Field(
        default=None,
        description="Bengaluru area, neighborhood, or landmark extracted from query (e.g. Kengeri, Indiranagar, HSR Layout).",
    )
    radius_km: float | None = Field(
        default=None,
        ge=0.5,
        le=50.0,
        description="Search radius in kilometers if explicitly requested by citizen.",
    )
    capacity_litres: float | None = Field(
        default=None,
        description="Volume capacity in litres if specified (e.g. 6000 for 6000L tanker).",
    )
    urgent: bool = Field(
        default=False,
        description="True if citizen requested emergency, 24x7, or urgent immediate turnaround.",
    )
    requirements: list[str] = Field(
        default_factory=list,
        description="Specific requirements (e.g. ['potable water', 'same-day delivery', 'computerized key']).",
    )
    raw_notes: str | None = Field(
        default=None,
        description="Any free-text user specifications that cannot safely be normalized.",
    )


class ToolCallRecord(BaseModel):
    tool_name: str
    tool_arguments: dict[str, str | int | float | bool | None]


class AssistantChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str = Field(..., min_length=1, description="Natural language civic service query from citizen.")
    lat: float | None = Field(default=None, ge=-90, le=90, description="Optional current citizen latitude.")
    lng: float | None = Field(default=None, ge=-180, le=180, description="Optional current citizen longitude.")
    user_area: str | None = Field(default=None, description="Optional citizen selected area.")


class AssistantChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    intent: ServiceIntent
    tool_calls: list[ToolCallRecord] = []
    discovery_results: list[NormalizedProviderResult] = []
    price_comparison: PriceComparisonSummary | None = None
    reply: str
    fallback_used: bool = False
    error: str | None = None


class ReviewSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    review_url: str | None = Field(default=None, max_length=2000)
    review_text: str | None = Field(default=None, max_length=12000)

    @model_validator(mode="after")
    def require_review_input(self) -> "ReviewSummaryRequest":
        if not (self.review_url and self.review_url.strip()) and not (
            self.review_text and self.review_text.strip()
        ):
            raise ValueError("Provide a permitted review link or review text.")
        return self


class ReviewSummaryResponse(BaseModel):
    summary: str | None = None
    source: str
    source_url: str | None = None
    limitations: list[str] = Field(default_factory=list)
    used_user_text: bool = False
    generated_by: str = "deterministic"


# ---------------------------------------------------------
# Phase 1: Service Catalogue, Platform Listings & Pricing
# ---------------------------------------------------------


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str
    category_slug: str | None = None
    category_name: str | None = None
    slug: str
    name: str
    description: str | None = None
    unit: str | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class ServicePriceBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    price_type: PriceType
    amount: float | None = None
    price_min: float | None = None
    price_max: float | None = None
    currency: str = "INR"
    unit: str | None = None
    conditions: str | None = None
    inclusions: str | None = None
    exclusions: str | None = None
    source_url: str | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    research_record_id: str | None = None
    comparison_group: str | None = None
    comparability_label: str | None = None
    comparability_reason: str | None = None

    @model_validator(mode="after")
    def validate_pricing_consistency(self) -> "ServicePriceBase":
        if self.currency != "INR":
            raise ValueError(f"Unsupported currency: {self.currency}. Only INR is supported.")

        pt = self.price_type
        if pt == PriceType.FIXED:
            if self.amount is None or self.amount <= 0:
                raise ValueError("FIXED pricing requires a positive amount.")
        elif pt == PriceType.STARTING_AT:
            val = self.amount if self.amount is not None else self.price_min
            if val is None or val <= 0:
                raise ValueError("STARTING_AT pricing requires a positive amount or price_min.")
        elif pt == PriceType.RANGE:
            if self.price_min is None or self.price_max is None:
                raise ValueError("RANGE pricing requires both price_min and price_max.")
            if self.price_min <= 0 or self.price_max <= 0:
                raise ValueError("RANGE pricing requires positive bounds.")
            if self.price_min > self.price_max:
                raise ValueError(f"RANGE price_min ({self.price_min}) cannot exceed price_max ({self.price_max}).")
        elif pt == PriceType.CONSULTATION_FEE:
            if self.amount is None or self.amount < 0:
                raise ValueError("CONSULTATION_FEE pricing requires a non-negative amount.")
        elif pt == PriceType.PER_UNIT:
            val = self.amount if self.amount is not None else self.price_min
            if val is None or val <= 0:
                raise ValueError("PER_UNIT pricing requires a positive amount or price_min.")
            if not self.unit or not self.unit.strip():
                raise ValueError("PER_UNIT pricing requires a specified unit.")
        elif pt == PriceType.HOURLY:
            val = self.amount if self.amount is not None else self.price_min
            if val is None or val <= 0:
                raise ValueError("HOURLY pricing requires a positive amount or price_min.")
        elif pt == PriceType.QUOTE_REQUIRED:
            pass

        return self


class ServicePriceCreate(ServicePriceBase):
    service_id: str
    platform_listing_id: str | None = None
    provider_offering_id: str | None = None


class ServicePriceRead(ServicePriceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    service_id: str
    platform_listing_id: str | None = None
    provider_offering_id: str | None = None
    last_verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PlatformListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: PlatformType
    service_id: str
    service_slug: str | None = None
    service_name: str | None = None
    title: str
    description: str | None = None
    locality: str | None = None
    city: str = "Bengaluru"
    listing_url: str | None = None
    booking_url: str | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    source: str | None = None
    last_checked_at: datetime | None = None
    is_active: bool = True
    prices: list[ServicePriceRead] = []
    created_at: datetime
    updated_at: datetime


class ProviderOfferingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str
    provider_name: str | None = None
    service_id: str
    service_slug: str | None = None
    service_name: str | None = None
    custom_name: str | None = None
    description: str | None = None
    is_available: bool = True
    is_active: bool = True
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    source: str | None = None
    source_url: str | None = None
    last_verified_at: datetime | None = None
    prices: list[ServicePriceRead] = []
    created_at: datetime
    updated_at: datetime


class CitizenReviewCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider_id: str
    service_id: str | None = None
    citizen_user_id: str | None = None
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    review_title: str | None = Field(default=None, max_length=150)
    review_text: str = Field(..., min_length=5, max_length=2000)
    locality: str | None = Field(default=None, max_length=100)
    service_date: datetime | None = None


class CitizenReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str
    service_id: str | None = None
    citizen_user_id: str | None = None
    rating: float
    review_title: str | None = None
    review_text: str
    locality: str | None = None
    service_date: datetime | None = None
    is_verified_resident: bool = False
    is_published: bool = True
    created_at: datetime
    updated_at: datetime


class ThirdPartyReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str | None = None
    platform_listing_id: str | None = None
    source_platform: str
    external_rating: float | None = None
    external_reviews_count: int | None = None
    source_url: str | None = None
    last_synced_at: datetime | None = None
    created_at: datetime


class ServiceDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str
    category_slug: str | None = None
    category_name: str | None = None
    slug: str
    name: str
    description: str | None = None
    unit: str | None = None
    is_active: bool = True
    platform_listings: list[PlatformListingRead] = []
    provider_offerings: list[ProviderOfferingRead] = []
    prices: list[ServicePriceRead] = []
