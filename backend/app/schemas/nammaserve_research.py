"""Pydantic schemas for NammaServe Provider Research and Booking Requests."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ResearchCandidateBase(BaseModel):
    batch_id: str
    provider_id: str
    provider_name: str
    service_category: str
    raw_service_category: str
    specific_services: str | None = None
    requested_area: str
    area_name: str
    business_address: str | None = None
    public_phone: str | None = None
    public_email: str | None = None
    website_url: str | None = None
    contact_or_booking_url: str | None = None
    advertised_service_areas: str | None = None
    area_coverage_evidence_url: str | None = None
    price_type: str | None = None
    price_amount: float | None = None
    price_currency: str = "INR"
    price_unit: str | None = None
    price_scope: str | None = None
    price_source_url: str | None = None
    rating: float | None = None
    review_count: int | None = None
    rating_platform: str | None = None
    rating_source_url: str | None = None
    booking_method: str | None = None
    availability_status: str = "UNKNOWN"
    verification_status: str = "DISCOVERED"
    primary_source_url: str | None = None
    secondary_source_url: str | None = None
    research_date: str | None = None
    confidence: str = "HIGH"
    evidence_summary: str | None = None
    missing_information: str | None = None
    duplicate_group_id: str | None = None
    provider_rank: int = 1
    notes: str | None = None
    review_summary: str | None = None
    review_positive_themes: str | None = None
    review_negative_themes: str | None = None
    review_date_range: str | None = None
    review_summary_source_url: str | None = None
    review_summary_limitations: str | None = None


class ResearchCandidateRead(ResearchCandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    raw_record: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ResearchCandidateListResponse(BaseModel):
    total: int
    page: int
    limit: int
    pages: int
    items: list[ResearchCandidateRead]


class ResearchCoverageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    batch_id: str
    area: str
    clean_area: str
    service_category: str
    research_status: str
    provider_1_id: str | None = None
    provider_1_name: str | None = None
    provider_1_source_url: str | None = None
    provider_2_id: str | None = None
    provider_2_name: str | None = None
    provider_2_source_url: str | None = None
    providers_found: int
    sources_checked: str | None = None
    evidence_summary: str | None = None
    limitations: str | None = None
    research_date: str | None = None
    created_at: datetime


class ResearchCoverageResponse(BaseModel):
    total_cells: int
    completed_cells: int
    cells: list[ResearchCoverageRead]


class ResearchOverviewMetrics(BaseModel):
    total_candidates: int
    distinct_businesses: int
    total_areas: int
    total_categories: int
    total_coverage_cells: int
    completed_coverage_cells: int
    published_prices_count: int
    ratings_count: int
    verification_breakdown: dict[str, int]
    price_type_breakdown: dict[str, int]
    areas_list: list[str]
    categories_list: list[str]
    disclaimer: str = (
        "Research data — information may not be independently verified. "
        "Prices, availability, service coverage, and provider details should be confirmed before booking."
    )


class BookingRequestCreate(BaseModel):
    candidate_id: str | None = None
    provider_name: str = Field(..., min_length=2, max_length=200)
    service_category: str = Field(..., min_length=2, max_length=100)
    area: str = Field(..., min_length=2, max_length=100)
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_phone: str = Field(..., min_length=10, max_length=20)
    customer_email: str | None = None
    customer_address: str | None = None
    preferred_date: str | None = None
    preferred_time_slot: str | None = None
    issue_description: str = Field(..., min_length=5, max_length=2000)


class BookingRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_id: str | None = None
    provider_name: str
    service_category: str
    area: str
    customer_name: str
    customer_phone: str
    customer_email: str | None = None
    customer_address: str | None = None
    preferred_date: str | None = None
    preferred_time_slot: str | None = None
    issue_description: str
    status: str
    is_research_candidate: bool
    confirmation_message: str = (
        "Booking request recorded. Provider confirmation is required before service is scheduled."
    )
    created_at: datetime
