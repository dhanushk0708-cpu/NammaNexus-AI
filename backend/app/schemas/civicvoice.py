from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CivicVoiceProvider(str, Enum):
    BLUESKY = "bluesky"
    YOUTUBE = "youtube"
    TAVILY = "tavily"


class ProviderConfigStatus(BaseModel):
    configured: bool
    details: str | None = None


class CivicVoiceConfigStatusResponse(BaseModel):
    status: str = "ok"
    bluesky_configured: bool
    bluesky_base_url: str
    youtube_configured: bool
    tavily_configured: bool
    total_source_records: int = 0
    total_analysis_records: int = 0
    total_citizen_submissions: int = 0


class CivicVoiceCollectRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Public topic or query to search across opinion providers (supports English and Kannada).",
    )
    topic: str | None = Field(
        None,
        max_length=200,
        description="Optional thematic topic or campaign tag (e.g. roads, waste, water).",
    )
    providers: list[CivicVoiceProvider] | None = Field(
        default=None,
        description="List of providers to query. Defaults to all configured providers.",
    )
    limit_per_provider: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of items to retrieve per provider (bounded between 1 and 50).",
    )


class NormalizedSourceRecord(BaseModel):
    """Provider-agnostic normalized representation of a public opinion record."""

    provider: str
    external_id: str | None = None
    dedup_key: str
    topic: str | None = None
    title: str | None = None
    content: str | None = None
    url: str
    author: str | None = None
    published_at: datetime | None = None
    collected_at: datetime
    language: str | None = None
    metadata_json: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class CivicVoiceRecordRead(BaseModel):
    """Database-backed representation of a stored public opinion record."""

    id: str
    provider: str
    external_id: str | None = None
    dedup_key: str
    topic: str | None = None
    title: str | None = None
    content: str | None = None
    url: str
    author: str | None = None
    published_at: datetime | None = None
    collected_at: datetime
    language: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProviderCollectionStatus(BaseModel):
    provider: str
    success: bool
    count: int = 0
    error_message: str | None = None


class CivicVoiceCollectionResponse(BaseModel):
    query: str
    topic: str | None = None
    total_collected: int
    total_persisted: int
    total_duplicates_skipped: int
    provider_statuses: list[ProviderCollectionStatus]
    records: list[CivicVoiceRecordRead]


class CivicVoiceRecordListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    records: list[CivicVoiceRecordRead]


# ============================================================================
# Opinion Intelligence Enums & Schemas
# ============================================================================


class OpinionCategory(str, Enum):
    POSITIVE_EXPERIENCE = "positive_experience"
    COMPLAINT_OR_CONCERN = "complaint_or_concern"
    SUGGESTION_OR_RECOMMENDATION = "suggestion_or_recommendation"
    QUESTION_OR_REQUEST = "question_or_request"
    NEUTRAL_OR_INFORMATIONAL = "neutral_or_informational"
    MIXED_OPINION = "mixed_opinion"
    UNCLEAR_OR_INSUFFICIENT = "unclear_or_insufficient_evidence"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"


class ContentIntent(str, Enum):
    FIRST_PERSON_EXPERIENCE = "first_person_experience"
    GENERAL_OPINION = "general_opinion"
    NEWS_OR_REPORTING = "news_or_reporting"
    PROMOTIONAL_MATERIAL = "promotional_material"
    INFORMATIONAL_CONTENT = "informational_content"
    UNCLEAR_INTENT = "unclear_intent"


class CivicVoiceAnalyzeRequest(BaseModel):
    record_ids: list[str] | None = Field(
        default=None,
        description="Explicit list of collected source record IDs to analyze.",
    )
    topic: str | None = Field(
        default=None,
        max_length=200,
        description="Optional topic filter to select unanalyzed records.",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of source records to analyze in this batch (bounded 1-100).",
    )
    force_reanalyze: bool = Field(
        default=False,
        description="If True, re-analyzes records that were already processed.",
    )


class CivicVoiceAnalysisRecordRead(BaseModel):
    id: str
    source_record_id: str
    category: OpinionCategory
    sentiment: SentimentLabel | None = None
    content_intent: ContentIntent | None = None
    confidence: str
    explanation: str | None = None
    detected_language: str | None = None
    has_complaint: bool = False
    extracted_complaint: str | None = None
    has_suggestion: bool = False
    extracted_suggestion: str | None = None
    theme_id: str | None = None
    theme_label: str | None = None
    analysis_method: str
    analysis_version: str
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CivicVoiceAnalyzeResponse(BaseModel):
    total_examined: int
    total_analyzed: int
    total_skipped: int
    analyses: list[CivicVoiceAnalysisRecordRead]


class CivicVoiceAnalysisListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    records: list[CivicVoiceAnalysisRecordRead]


class CivicVoiceTheme(BaseModel):
    theme_id: str
    theme_label: str
    description: str
    record_count: int
    evidence_record_ids: list[str]
    source_links: list[str]
    sentiment_breakdown: dict[str, int]
    earliest_date: datetime | None = None
    latest_date: datetime | None = None
    analysis_version: str = "v1.0"


class CivicVoiceThemesResponse(BaseModel):
    total_themes: int
    total_records_represented: int
    themes: list[CivicVoiceTheme]


class CivicVoiceTrendItem(BaseModel):
    theme_id: str
    theme_label: str
    current_window_count: int
    previous_window_count: int
    change_count: int
    status: str
    evidence_record_ids: list[str]


class CivicVoiceTrendsResponse(BaseModel):
    window_days: int
    current_window_start: datetime
    current_window_end: datetime
    previous_window_start: datetime
    previous_window_end: datetime
    timestamp_basis: str
    missing_publication_timestamps_count: int
    trends: list[CivicVoiceTrendItem]
    data_limitations: list[str]


class CivicVoiceSummaryFinding(BaseModel):
    finding_description: str
    category: str
    theme_label: str | None = None
    supporting_record_count: int
    evidence_record_ids: list[str]
    source_urls: list[str]
    earliest_date: datetime | None = None
    latest_date: datetime | None = None
    uncertainties: str | None = None


class CivicVoiceExtractedSuggestion(BaseModel):
    suggestion: str
    source_record_id: str
    source_url: str
    disclaimer: str = "Community-contributed suggestion. Not an officially approved or verified recommendation."


class CivicVoiceCoverageQuality(BaseModel):
    total_source_records: int
    total_analyzed_records: int
    provider_distribution: dict[str, int]
    language_distribution: dict[str, int]
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    missing_timestamps_count: int
    limitations: list[str]


class CivicVoiceUniversalFinding(BaseModel):
    heading: str
    explanation: str
    category: str
    supporting_evidence_count: int = 0
    evidence_record_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    earliest_date: datetime | None = None
    latest_date: datetime | None = None
    uncertainties: str | None = None
    evidence_strength: str = "moderate"  # "strong" | "moderate" | "anecdotal" | "unverified"


class CivicVoiceProblemConcern(BaseModel):
    heading: str
    description: str
    problem_type: str = "reported_problem"  # "reported_problem" | "verified_fact" | "unconfirmed_claim" | "unanswered_question"
    supporting_record_count: int = 1
    evidence_record_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    evidence_strength: str = "moderate"


class CivicVoiceUniversalSuggestion(BaseModel):
    heading: str
    suggestion: str
    origin: str = "source_author"  # "source_author" | "synthesized_civicvoice" | "synthesized_model"
    source_record_id: str | None = None
    source_url: str | None = None
    disclaimer: str = "Community-contributed suggestion. Not an officially approved or verified recommendation."


class CivicVoiceViewpointContrast(BaseModel):
    topic_aspect: str
    areas_of_agreement: str
    points_of_disagreement: str
    disputed_questions: list[str] = Field(default_factory=list)


class CivicVoiceCleanSourceItem(BaseModel):
    publisher: str
    title: str
    published_at: datetime | None = None
    excerpt: str
    url: str
    source_type: str  # "official_information" | "news_reporting" | "public_social_post" | "community_opinion"
    language: str | None = None


# ============================================================================
# Gemini Structured Research Schemas
# ============================================================================


class GeminiFindingItem(BaseModel):
    heading: str = Field(description="Concise, informative title for this finding")
    explanation: str = Field(description="Clear explanation grounded strictly in the cited evidence")
    category: str = Field(default="opinion_highlight", description="Category tag e.g. positive_highlight, criticism, logistical_friction")
    supporting_source_ids: list[str] = Field(default_factory=list, description="IDs of source records that directly support this finding (e.g. ['SRC-1'])")
    evidence_strength: str = Field(default="moderate", description="'strong' if multiple corroborate, 'moderate' if single reliable, 'anecdotal' if personal social post, 'unverified' if claim")
    uncertainties: str | None = Field(default=None, description="Known uncertainties, caveats, or missing information")


class GeminiProblemConcernItem(BaseModel):
    heading: str = Field(description="Summary of the reported problem or concern")
    description: str = Field(description="Specific description of the friction, obstacle, or failure")
    problem_type: str = Field(default="reported_problem", description="'reported_problem', 'verified_fact', 'unconfirmed_claim', or 'unanswered_question'")
    supporting_source_ids: list[str] = Field(default_factory=list, description="Source IDs directly reporting this problem")


class GeminiSuggestionItem(BaseModel):
    heading: str = Field(description="Short title for the recommendation or suggestion")
    suggestion: str = Field(description="The concrete proposal or proposed improvement")
    origin: str = Field(default="source_author", description="'source_author' if proposed by a contributor/source, 'synthesized_model' if generated by the AI model")
    supporting_source_ids: list[str] = Field(default_factory=list, description="Source IDs if originated from a source")
    disclaimer: str = Field(default="Community-contributed suggestion. Not an officially verified recommendation.")


class GeminiViewpointContrastItem(BaseModel):
    topic_aspect: str = Field(description="Specific aspect or sub-topic where perspectives diverge")
    areas_of_agreement: str = Field(description="Points on which sources broadly agree")
    points_of_disagreement: str = Field(description="Points of disagreement or conflicting perspectives")
    disputed_questions: list[str] = Field(default_factory=list, description="Concrete unresolved or disputed questions")


class GeminiResearchOutput(BaseModel):
    """Pydantic schema for Gemini structured output research synthesis."""

    topic: str = Field(description="The exact topic or query analyzed")
    introduction: str = Field(description="Concise, natural-language introduction establishing the topic context and scope")
    overall_summary: str = Field(description="Concise multi-paragraph summary synthesizing consensus, divergence, and dominant sentiment")
    positive_findings: list[GeminiFindingItem] = Field(default_factory=list, description="Supported positive opinions, highlights, or achievements (empty if none supported)")
    negative_findings: list[GeminiFindingItem] = Field(default_factory=list, description="Supported criticisms, complaints, or negative feedback (empty if none supported)")
    problems_and_concerns: list[GeminiProblemConcernItem] = Field(default_factory=list, description="Reported problems, hazards, or concerns (empty if none reported)")
    suggestions: list[GeminiSuggestionItem] = Field(default_factory=list, description="Actionable suggestions (clearly identifying source_author vs synthesized_model)")
    different_viewpoints: list[GeminiViewpointContrastItem] = Field(default_factory=list, description="Contrasting viewpoints, agreements, and disagreements")
    trends_overview: str = Field(default="", description="Observation on temporal changes or discussion velocity over time")
    trends_available: bool = Field(default=False, description="True if evidence spans multiple dates allowing meaningful trend observation")
    unresolved_questions: list[str] = Field(default_factory=list, description="Important evidence gaps and unanswered questions that could not be resolved from current evidence")
    limitations: list[str] = Field(default_factory=list, description="Specific methodological and data coverage limitations")
    follow_up_queries_suggested: list[str] = Field(default_factory=list, description="Targeted follow-up search queries to resolve identified evidence gaps")


class CivicVoiceSummaryResponse(BaseModel):
    topic: str | None = None
    generated_at: datetime

    # Section A: Topic Introduction
    topic_title: str = ""
    introduction: str = ""
    relevant_dates: str | None = None
    facts_vs_claims: str | None = None

    # Section B: Overall Summary
    overall_summary: str = ""

    # Section C: Positive Opinions and Highlights
    positive_opinions: list[CivicVoiceUniversalFinding] = Field(default_factory=list)
    positive_opinions_status: str | None = None

    # Section D: Negative Opinions and Criticism
    negative_opinions: list[CivicVoiceUniversalFinding] = Field(default_factory=list)
    negative_opinions_status: str | None = None

    # Section E: Problems and Concerns
    problems_and_concerns: list[CivicVoiceProblemConcern] = Field(default_factory=list)
    problems_and_concerns_status: str | None = None

    # Section F: Suggestions and Proposed Improvements
    suggestions_and_improvements: list[CivicVoiceUniversalSuggestion] = Field(default_factory=list)
    suggestions_status: str | None = None

    # Section G: Different Viewpoints and Disagreements
    viewpoint_contrasts: list[CivicVoiceViewpointContrast] = Field(default_factory=list)

    # Section H: Trends and Changes Over Time
    trends_overview: str = ""
    trends_available: bool = False
    trend_items: list[CivicVoiceTrendItem] = Field(default_factory=list)

    # Section I: Evidence and Sources
    clean_sources: list[CivicVoiceCleanSourceItem] = Field(default_factory=list)

    # Section J: Data Coverage and Limitations
    coverage: CivicVoiceCoverageQuality
    sample_size_assessment: str = ""

    # Research and Validation metadata
    unresolved_questions: list[str] = Field(default_factory=list)
    ai_synthesized: bool = False
    ai_model: str | None = None
    validation_status: str | None = None
    validation_notes: list[str] = Field(default_factory=list)

    # Backward compatibility fields:
    findings: list[CivicVoiceSummaryFinding] = Field(default_factory=list)
    extracted_suggestions: list[CivicVoiceExtractedSuggestion] = Field(default_factory=list)
    conflicting_perspectives: list[str] = Field(default_factory=list)


# ============================================================================
# Citizen Submission Schemas (Separate from External Public Data Collection)
# ============================================================================


class CivicVoiceCitizenSubmissionCreate(BaseModel):
    topic: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Civic topic or category (e.g. roads, waste_management, water_supply, traffic_and_transport).",
    )
    opinion_text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Citizen's opinion or suggestion in English or Kannada (10 - 2000 characters).",
    )
    locality: str | None = Field(
        default=None,
        max_length=100,
        description="Optional neighborhood or area in Bengaluru (e.g. Indiranagar, HSR Layout, Kengeri).",
    )
    language: str | None = Field(
        default="en",
        max_length=10,
        description="Language of the opinion ('en' or 'kn').",
    )
    consent_given: bool = Field(
        default=True,
        description="Confirmation of consent for anonymous community priority aggregation.",
    )


class CivicVoiceCitizenSubmissionRead(BaseModel):
    id: str
    topic: str
    opinion_text: str
    locality: str | None = None
    language: str | None = None
    consent_given: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CivicVoiceCitizenSubmissionResponse(BaseModel):
    id: str
    topic: str
    locality: str | None = None
    language: str | None = None
    created_at: datetime
    confirmation_message: str = (
        "Your civic opinion has been recorded for community intelligence. "
        "Please note: CivicVoice aggregates public priorities; this does not constitute "
        "an official administrative grievance ticket or guarantee authority dispatch."
    )


class CivicVoiceCitizenSubmissionListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    submissions: list[CivicVoiceCitizenSubmissionRead]


class CivicVoiceCitizenSubmissionsAggregatedResponse(BaseModel):
    """Anonymized, aggregate community insights from citizen submissions.

    Guarantees privacy by exposing only high-level volume distributions and never
    revealing raw opinion text, individual IDs, or timestamps.
    """

    total_submissions: int
    topic_distribution: dict[str, int]
    locality_distribution: dict[str, int]
    language_distribution: dict[str, int]
    privacy_notice: str = (
        "Citizen submissions are kept strictly confidential and aggregated into civic priority "
        "insights. Raw individual texts and personal identifiers are never exposed publicly."
    )


class ReportStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    SEND_FAILED = "send_failed"


class CivicVoiceReportGenerateRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Civic topic for the report (e.g. roads, solid_waste, water_drainage).",
    )
    title: str | None = Field(
        None,
        max_length=255,
        description="Optional custom title for the report.",
    )
    geographic_scope: str = Field(
        default="Bengaluru Urban (BBMP Wards)",
        max_length=150,
        description="Geographic scope of the civic intelligence analysis.",
    )
    reporting_period_days: int = Field(
        default=14,
        ge=1,
        le=90,
        description="Window in days over which source records and submissions are gathered.",
    )


class CivicVoiceReportUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    summary_content: str | None = None
    recommendations: str | None = None
    limitations: str | None = None
    recipient_email: str | None = Field(None, max_length=255)
    authority_name: str | None = Field(None, max_length=200)
    department_name: str | None = Field(None, max_length=200)
    official_portal_url: str | None = Field(None, max_length=500)


class CivicVoiceReportApproveRequest(BaseModel):
    notes: str | None = Field(None, max_length=500, description="Optional reviewer approval remarks.")


class CivicVoiceReportRejectRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1000, description="Specific justification for rejecting report.")


class CivicVoiceReportSendRequest(BaseModel):
    idempotency_key: str | None = Field(
        None,
        max_length=64,
        description="Client-supplied idempotency key to prevent accidental duplicate dispatches.",
    )
    confirm_send: bool = Field(
        default=True,
        description="Explicit human confirmation to authorize dispatch to official recipient.",
    )


class CivicVoiceReportAuditRead(BaseModel):
    id: str
    report_id: str
    action: str
    performed_by: str
    previous_status: str | None = None
    new_status: str | None = None
    details_json: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CivicVoiceReportRead(BaseModel):
    id: str
    title: str
    topic: str
    geographic_scope: str
    reporting_period_start: datetime | None = None
    reporting_period_end: datetime | None = None
    status: ReportStatus
    authority_name: str
    department_name: str
    recipient_email: str | None = None
    official_portal_url: str | None = None
    mapping_verified: bool
    mapping_source_url: str | None = None
    mapping_last_verified: datetime | None = None
    source_records_count: int
    citizen_submissions_count: int
    summary_content: str
    recommendations: str
    themes_summary: dict[str, Any] | None = None
    sentiment_summary: dict[str, Any] | None = None
    evidence_urls: list[str] | None = None
    limitations: str
    content_hash: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    sent_at: datetime | None = None
    idempotency_key: str | None = None
    delivery_details: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    audits: list[CivicVoiceReportAuditRead] = []

    model_config = ConfigDict(from_attributes=True)


class CivicVoiceReportListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    reports: list[CivicVoiceReportRead]


class CivicVoiceReportSendResponse(BaseModel):
    report_id: str
    status: ReportStatus
    recipient: str | None
    delivery_mode: str  # "resend_api" or "preview_export_only"
    message: str
    idempotency_key: str | None = None
    delivery_details: dict[str, Any] | None = None


class CivicVoiceReportExportResponse(BaseModel):
    report_id: str
    title: str
    format: str = "markdown"
    content: str
    generated_at: datetime


class CivicVoiceSearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Search query or public topic (e.g. 'Mysore Dasara 2026', 'Indiranagar garbage', 'metro phase 2').",
    )
    limit_per_provider: int = Field(
        default=5,
        ge=1,
        le=25,
        description="Number of records to retrieve per provider if collection is needed.",
    )
    force_refresh: bool = Field(
        default=False,
        description="Whether to force live collection even if cached records already exist.",
    )


class CivicVoiceSearchResponse(BaseModel):
    query: str
    topic: str
    total_records: int
    provider_statuses: list[ProviderCollectionStatus]
    records: list[CivicVoiceRecordRead]
    summary: CivicVoiceSummaryResponse
    themes: list[CivicVoiceTheme]
    trends: CivicVoiceTrendsResponse | None = None
    citizen_submissions_count: int = 0


class CivicVoiceTrendingTopicItem(BaseModel):
    topic: str
    record_count: int
    citizen_opinions_count: int = 0
    total_activity_count: int
    latest_activity: datetime | None = None
    sample_title: str | None = None


class CivicVoiceTrendingResponse(BaseModel):
    trending_topics: list[CivicVoiceTrendingTopicItem]





