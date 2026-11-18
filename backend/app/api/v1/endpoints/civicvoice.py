import logging
import secrets
import time
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.dependencies import get_db
from app.schemas.civicvoice import (
    CivicVoiceAnalysisListResponse,
    CivicVoiceAnalyzeRequest,
    CivicVoiceAnalyzeResponse,
    CivicVoiceCitizenSubmissionCreate,
    CivicVoiceCitizenSubmissionListResponse,
    CivicVoiceCitizenSubmissionResponse,
    CivicVoiceCitizenSubmissionsAggregatedResponse,
    CivicVoiceCollectionResponse,
    CivicVoiceCollectRequest,
    CivicVoiceConfigStatusResponse,
    CivicVoiceProvider,
    CivicVoiceRecordListResponse,
    CivicVoiceReportApproveRequest,
    CivicVoiceReportExportResponse,
    CivicVoiceReportGenerateRequest,
    CivicVoiceReportListResponse,
    CivicVoiceReportRead,
    CivicVoiceReportRejectRequest,
    CivicVoiceReportSendRequest,
    CivicVoiceReportSendResponse,
    CivicVoiceReportUpdate,
    CivicVoiceSearchRequest,
    CivicVoiceSearchResponse,
    CivicVoiceSummaryResponse,
    CivicVoiceThemesResponse,
    CivicVoiceTrendingResponse,
    CivicVoiceTrendsResponse,
    OpinionCategory,
    ReportStatus,
)
from app.services.civicvoice import CivicVoiceService
from app.services.civicvoice.report_delivery import ReportWorkflowError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/civicvoice",
    tags=["CivicVoice"],
)

civicvoice_service = CivicVoiceService()

# In-memory sliding-window rate limiter for citizen submissions
_submission_rate_limiter: dict[str, list[float]] = defaultdict(list)
SUBMISSION_RATE_LIMIT_WINDOW = 60.0  # seconds
SUBMISSION_MAX_PER_WINDOW = 15  # requests per window per IP


def check_submission_rate_limit(client_ip: str) -> bool:
    now = time.time()
    cutoff = now - SUBMISSION_RATE_LIMIT_WINDOW
    timestamps = [t for t in _submission_rate_limiter[client_ip] if t > cutoff]
    if len(timestamps) >= SUBMISSION_MAX_PER_WINDOW:
        _submission_rate_limiter[client_ip] = timestamps
        return False
    timestamps.append(now)
    _submission_rate_limiter[client_ip] = timestamps
    return True


# In-memory sliding-window rate limiter for public topic search
_search_rate_limiter: dict[str, list[float]] = defaultdict(list)
SEARCH_RATE_LIMIT_WINDOW = 60.0  # seconds
SEARCH_MAX_PER_WINDOW = 20  # requests per window per IP


def check_search_rate_limit(client_ip: str) -> bool:
    now = time.time()
    cutoff = now - SEARCH_RATE_LIMIT_WINDOW
    timestamps = [t for t in _search_rate_limiter[client_ip] if t > cutoff]
    if len(timestamps) >= SEARCH_MAX_PER_WINDOW:
        _search_rate_limiter[client_ip] = timestamps
        return False
    timestamps.append(now)
    _search_rate_limiter[client_ip] = timestamps
    return True




def verify_collection_authorization(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    """Verifies authorization for privileged CivicVoice data collection operations.

    Collection triggers external API requests that consume rate limits and quotas.
    In the absence of a platform-wide Supabase Auth session layer, this dependency
    enforces a strict, token-based authorization policy:
    1. An authorization token must be supplied via 'Authorization: Bearer <token>'
       or 'X-API-Key: <token>'.
    2. If no token is provided, returns HTTP 401 Unauthorized.
    3. If the server does not have an authorization token configured (CIVICVOICE_API_TOKEN),
       returns HTTP 403 Forbidden to prevent public exposure of privileged collection.
    4. If the provided token does not match the configured token using constant-time
       comparison, returns HTTP 403 Forbidden.
    """
    token: str | None = None
    if x_api_key and x_api_key.strip():
        token = x_api_key.strip()
    elif authorization and authorization.strip():
        parts = authorization.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip() or None
        elif len(parts) == 1 and parts[0].lower() != "bearer":
            token = parts[0].strip() or None

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required: missing Authorization or X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    configured_token = settings.civicvoice_api_token
    if not configured_token or not configured_token.strip():
        logger.warning(
            "CivicVoice collection requested but CIVICVOICE_API_TOKEN is not configured on the server."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CivicVoice collection is protected. Configure CIVICVOICE_API_TOKEN in backend environment to authorize collection operations.",
        )

    if not secrets.compare_digest(token, configured_token.strip()):
        logger.warning("CivicVoice collection rejected: invalid authorization token provided.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: invalid collection authorization credential.",
        )

    return token


@router.get(
    "/status",
    response_model=CivicVoiceConfigStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get CivicVoice provider configuration status",
)
def get_civicvoice_status(
    db: Session = Depends(get_db),
):
    """Returns non-sensitive provider configuration status.

    Never exposes API keys or credential secrets.
    """
    return civicvoice_service.get_config_status(db=db)


@router.post(
    "/search",
    response_model=CivicVoiceSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search public opinion intelligence across external sources (Public)",
)
async def search_civicvoice_topics(
    payload: CivicVoiceSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Executes a search-first public opinion intelligence retrieval.

    - Open, citizen-facing endpoint to search any civic topic, event, or discussion (e.g. 'Mysore Dasara 2026').
    - Rate-limited to prevent external provider quota exhaustion.
    - Collects evidence from Bluesky, YouTube, and Tavily without exposing provider keys or secrets.
    - Synthesizes findings, recurring themes, viewpoints, and coverage limitations.
    - Preserves citizen privacy by reporting only aggregate counts of community submissions.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not check_search_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Search rate limit reached. Please wait a moment before submitting another topic search.",
        )

    try:
        return await civicvoice_service.search_topic(
            db=db,
            query=payload.query,
            limit_per_provider=payload.limit_per_provider,
            force_refresh=payload.force_refresh,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.exception("Unexpected error during CivicVoice topic search")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while searching civic intelligence topics.",
        ) from exc


@router.get(
    "/trending",
    response_model=CivicVoiceTrendingResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve discovered trending civic topics from collected data (Public)",
)
def get_trending_topics(
    limit: int = Query(8, ge=1, le=50, description="Max trending topics to return"),
    db: Session = Depends(get_db),
):
    """Discovers trending civic topics from actual collected database records.

    Never fabricates topics or popularity counts.
    """
    return civicvoice_service.get_trending_topics(db=db, limit=limit)


@router.post(
    "/collect",
    response_model=CivicVoiceCollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Explicitly invoke public opinion collection across providers",
)
async def collect_civicvoice_records(
    payload: CivicVoiceCollectRequest,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Explicitly triggers public opinion data collection for a verified query across

    selected providers (Bluesky, YouTube, Tavily).

    Deduplicates results and persists newly discovered records into the database.
    """
    try:
        response = await civicvoice_service.collect_and_persist(
            db=db,
            query=payload.query,
            topic=payload.topic,
            providers=payload.providers,
            limit_per_provider=payload.limit_per_provider,
        )
        return response
    except Exception as exc:
        logger.exception("Unexpected error during CivicVoice collection")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CivicVoice collection encountered an internal processing error.",
        ) from exc


@router.get(
    "/records",
    response_model=CivicVoiceRecordListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve stored public opinion records with bounded pagination",
)
def get_civicvoice_records(
    provider: CivicVoiceProvider | None = Query(None, description="Filter by provider (bluesky, youtube, tavily)"),
    topic: str | None = Query(None, max_length=200, description="Filter by topic or category"),
    query: str | None = Query(None, max_length=200, description="Search keyword in title or content"),
    limit: int = Query(20, ge=1, le=100, description="Page limit (max 100)"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
):
    """Lists stored public opinion records with deterministic ordering, bounded pagination,

    and optional filtering by provider, topic, or keyword.
    """
    provider_str = provider.value if provider else None
    return civicvoice_service.list_records(
        db=db,
        provider=provider_str,
        topic=topic,
        query=query,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/analyze",
    response_model=CivicVoiceAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute opinion intelligence analysis on collected source records",
)
def analyze_civicvoice_records(
    payload: CivicVoiceAnalyzeRequest,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Executes opinion categorization, sentiment analysis, complaint and suggestion extraction

    on a bounded batch of stored source records. Requires valid collection authorization.
    """
    return civicvoice_service.analyze_source_records(
        db=db,
        record_ids=payload.record_ids,
        topic=payload.topic,
        limit=payload.limit,
        force_reanalyze=payload.force_reanalyze,
    )


@router.get(
    "/analysis",
    response_model=CivicVoiceAnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve stored opinion analysis records",
)
def get_civicvoice_analysis_records(
    category: OpinionCategory | None = Query(None, description="Filter by opinion category"),
    theme_id: str | None = Query(None, max_length=50, description="Filter by theme ID"),
    has_complaint: bool | None = Query(None, description="Filter by presence of extracted complaint"),
    has_suggestion: bool | None = Query(None, description="Filter by presence of extracted suggestion"),
    limit: int = Query(50, ge=1, le=100, description="Page limit (max 100)"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
):
    """Lists stored analysis records with bounded pagination and filters."""
    cat_str = category.value if category else None
    return civicvoice_service.list_analysis_records(
        db=db,
        category=cat_str,
        theme_id=theme_id,
        has_complaint=has_complaint,
        has_suggestion=has_suggestion,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/themes",
    response_model=CivicVoiceThemesResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve recurring civic opinion themes and traceable evidence",
)
def get_civicvoice_themes(
    topic: str | None = Query(None, max_length=200, description="Filter themes by topic or campaign"),
    db: Session = Depends(get_db),
):
    """Clusters analyzed records into recurring civic themes with evidence IDs, counts, and URLs."""
    return civicvoice_service.get_themes(
        db=db,
        topic=topic,
    )


@router.get(
    "/trends",
    response_model=CivicVoiceTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve emerging topics and volume trends across equivalent time windows",
)
def get_civicvoice_trends(
    topic: str | None = Query(None, max_length=200, description="Filter by topic or campaign"),
    window_days: int = Query(7, ge=1, le=90, description="Time window in days for comparison (1-90)"),
    db: Session = Depends(get_db),
):
    """Calculates trend comparisons across two equivalent successive time windows."""
    return civicvoice_service.get_trends(
        db=db,
        topic=topic,
        window_days=window_days,
    )


@router.get(
    "/summary",
    response_model=CivicVoiceSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve evidence-backed intelligence summary and source coverage quality",
)
def get_civicvoice_summary(
    topic: str | None = Query(None, max_length=200, description="Generate summary for specific topic"),
    db: Session = Depends(get_db),
):
    """Generates an evidence-grounded summary linking findings directly to supporting records."""
    return civicvoice_service.get_summary(
        db=db,
        topic=topic,
    )


@router.post(
    "/submissions",
    response_model=CivicVoiceCitizenSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit citizen civic opinion or community feedback",
)
def submit_citizen_opinion(
    payload: CivicVoiceCitizenSubmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Submits a citizen civic opinion or community suggestion.

    This is an open, citizen-facing endpoint designed for local community feedback.
    - Requires consent acknowledgment.
    - Does not collect or store personal contact details or social profiles.
    - Rate-limited to prevent automated spam.
    - Persisted separately from external web-scraped public records.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not check_submission_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Submission rate limit exceeded. Please wait a moment before submitting another opinion.",
        )

    if not payload.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent confirmation is required to submit a civic opinion.",
        )

    try:
        return civicvoice_service.create_citizen_submission(db=db, payload=payload)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.exception("Error saving citizen submission")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving your opinion. Please try again.",
        ) from exc


@router.get(
    "/submissions",
    response_model=CivicVoiceCitizenSubmissionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve stored citizen community submissions (Protected Administrative Access)",
)
def get_citizen_submissions(
    topic: str | None = Query(None, max_length=100, description="Filter citizen opinions by topic"),
    locality: str | None = Query(None, max_length=100, description="Filter by Bengaluru locality"),
    limit: int = Query(20, ge=1, le=100, description="Page limit (max 100)"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Lists raw community citizen submissions with bounded pagination.

    Protected: Raw citizen submissions are confidential to protect resident privacy.
    Requires valid authorization token.
    """
    return civicvoice_service.list_citizen_submissions(
        db=db,
        topic=topic,
        locality=locality,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/submissions/aggregated",
    response_model=CivicVoiceCitizenSubmissionsAggregatedResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve anonymized, aggregate insights from citizen submissions (Public)",
)
def get_citizen_submissions_aggregated(
    topic: str | None = Query(None, max_length=100, description="Filter citizen opinions by topic"),
    suppress_small_groups: bool = Query(False, description="Apply k-anonymity threshold (< 3) suppression to small groups"),
    db: Session = Depends(get_db),
):
    """Public aggregated insights over citizen community submissions.

    Does not expose raw opinion text, individual IDs, or timestamps.
    """
    return civicvoice_service.get_citizen_submissions_aggregated(
        db=db,
        topic=topic,
        suppress_small_groups_flag=suppress_small_groups,
    )


# ============================================================================
# Verified Official Civic Reports & Human Approval Workflow Endpoints
# ============================================================================


@router.post(
    "/reports/generate",
    response_model=CivicVoiceReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate evidence-backed civic priority report from persisted intelligence",
)
def generate_civic_report(
    payload: CivicVoiceReportGenerateRequest,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Generates an evidence-backed civic priority report mapping public analysis and

    privacy-safe citizen submissions to a verified government authority.
    Protected: Requires valid authorization token.
    """
    try:
        return civicvoice_service.generate_report(
            db=db,
            topic=payload.topic,
            title=payload.title,
            geographic_scope=payload.geographic_scope,
            reporting_period_days=payload.reporting_period_days,
            created_by="authorized_analyst",
        )
    except Exception as exc:
        logger.exception("Error generating civic report")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate civic report: {exc}",
        ) from exc


@router.get(
    "/reports",
    response_model=CivicVoiceReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve list of generated civic reports with status filters",
)
def list_civic_reports(
    topic: str | None = Query(None, max_length=100, description="Filter reports by topic"),
    report_status: ReportStatus | None = Query(None, alias="status", description="Filter by workflow status"),
    limit: int = Query(20, ge=1, le=100, description="Page limit (max 100)"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Lists persisted civic reports with bounded pagination and workflow filters."""
    status_val = report_status.value if report_status else None
    return civicvoice_service.list_reports(
        db=db,
        topic=topic,
        status=status_val,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/reports/{report_id}",
    response_model=CivicVoiceReportRead,
    status_code=status.HTTP_200_OK,
    summary="Retrieve complete civic report details and audit trail",
)
def get_civic_report(
    report_id: str,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Retrieves single report details, findings, evidence URLs, and review audit trail."""
    try:
        return civicvoice_service.get_report(db=db, report_id=report_id)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        ) from val_err


@router.patch(
    "/reports/{report_id}",
    response_model=CivicVoiceReportRead,
    status_code=status.HTTP_200_OK,
    summary="Edit civic report content or recipient (invalidates prior approval)",
)
def update_civic_report(
    report_id: str,
    payload: CivicVoiceReportUpdate,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Applies human review edits to report title, content, recommendations, or recipient.

    CRITICAL RULE: If a report was already approved, any edit invalidates its approval,
    reverting status to 'pending_review' and requiring a new review sign-off.
    """
    try:
        return civicvoice_service.update_report(
            db=db,
            report_id=report_id,
            update_data=payload,
            performed_by="authorized_reviewer",
        )
    except ReportWorkflowError as wf_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(wf_err),
        ) from wf_err


@router.post(
    "/reports/{report_id}/approve",
    response_model=CivicVoiceReportRead,
    status_code=status.HTTP_200_OK,
    summary="Approve civic report and bind cryptographic content hash",
)
def approve_civic_report(
    report_id: str,
    payload: CivicVoiceReportApproveRequest | None = None,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Approves report content and binds a SHA-256 cryptographic digest to guarantee integrity."""
    try:
        notes = payload.notes if payload else None
        return civicvoice_service.approve_report(
            db=db,
            report_id=report_id,
            reviewer_id="authorized_reviewer",
            notes=notes,
        )
    except ReportWorkflowError as wf_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(wf_err),
        ) from wf_err


@router.post(
    "/reports/{report_id}/reject",
    response_model=CivicVoiceReportRead,
    status_code=status.HTTP_200_OK,
    summary="Reject civic report with documented justification",
)
def reject_civic_report(
    report_id: str,
    payload: CivicVoiceReportRejectRequest,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Rejects report with reviewer-documented reason in audit log."""
    try:
        return civicvoice_service.reject_report(
            db=db,
            report_id=report_id,
            reviewer_id="authorized_reviewer",
            reason=payload.reason,
        )
    except ReportWorkflowError as wf_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(wf_err),
        ) from wf_err


@router.post(
    "/reports/{report_id}/send",
    response_model=CivicVoiceReportSendResponse,
    status_code=status.HTTP_200_OK,
    summary="Dispatch approved report to verified government authority or preview export",
)
def send_civic_report(
    report_id: str,
    payload: CivicVoiceReportSendRequest | None = None,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Authorizes dispatch to verified official government channels.

    Guarantees:
    - Pre-approval check: only approved reports can be dispatched.
    - Destination check: recipient must be verified against official government directory.
    - Hash integrity: detects post-approval modification.
    - Idempotency: prevents accidental duplicate transmissions.
    - Safe fallback: honest preview/export response if email service is unconfigured.
    """
    idempotency_key = payload.idempotency_key if payload else None
    confirm_send = payload.confirm_send if payload else True

    try:
        return civicvoice_service.send_report(
            db=db,
            report_id=report_id,
            sender_id="authorized_reviewer",
            idempotency_key=idempotency_key,
            confirm_send=confirm_send,
        )
    except ReportWorkflowError as wf_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(wf_err),
        ) from wf_err


@router.get(
    "/reports/{report_id}/export",
    response_model=CivicVoiceReportExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export verified report in clean markdown format for manual review or dispatch",
)
def export_civic_report(
    report_id: str,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_collection_authorization),
):
    """Generates a complete, verified markdown export document including official metadata and audit trail."""
    try:
        return civicvoice_service.export_report(db=db, report_id=report_id)
    except ReportWorkflowError as wf_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(wf_err),
        ) from wf_err



