from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.nammaserve import SourceType, VerificationStatus


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
    phone: str
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


class NormalizedProviderResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str
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
    price_min: float | None = None
    price_max: float | None = None
    price_unit: str | None = None
    minimum_order: str | None = None
    capacity: str | None = None
    water_type: str | None = None
    availability: str | None = None
    payment_methods: str | None = None
    operating_hours: str | None = None
    is_emergency_service: bool = False
    notes: str | None = None

    # Evidence & Verification
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    source: str | None = None
    source_type: SourceType = SourceType.LOCAL_DATABASE
    source_url: str | None = None
    last_verified_at: datetime | None = None

    # Ranking & Explainability
    match_score: float = Field(default=0.0, description="Deterministic match score between 0 and 100")
    ranking_reasons: list[str] = Field(default_factory=list, description="Explainable reasons why this provider was ranked")


class ConnectorStatus(BaseModel):
    connector_name: str
    source_type: SourceType
    is_available: bool
    status_message: str
    results_count: int = 0


class UnifiedDiscoveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: DiscoveryQuery
    total_results: int
    connectors_contacted: list[ConnectorStatus]
    results: list[NormalizedProviderResult]


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
    reply: str
    fallback_used: bool = False
    error: str | None = None

