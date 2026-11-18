import asyncio
from datetime import datetime, timezone
import logging
import time
from uuid import uuid4

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.civicvoice import (
    CivicVoiceAnalysisRecord,
    CivicVoiceCitizenSubmission,
    CivicVoiceReport,
    CivicVoiceReportAudit,
    CivicVoiceSourceRecord,
)
from app.schemas.civicvoice import (
    CivicVoiceAnalysisListResponse,
    CivicVoiceAnalysisRecordRead,
    CivicVoiceAnalyzeResponse,
    CivicVoiceCitizenSubmissionCreate,
    CivicVoiceCitizenSubmissionListResponse,
    CivicVoiceCitizenSubmissionRead,
    CivicVoiceCitizenSubmissionResponse,
    CivicVoiceCitizenSubmissionsAggregatedResponse,
    CivicVoiceCollectionResponse,
    CivicVoiceConfigStatusResponse,
    CivicVoiceProvider,
    CivicVoiceRecordListResponse,
    CivicVoiceRecordRead,
    CivicVoiceReportExportResponse,
    CivicVoiceReportListResponse,
    CivicVoiceReportRead,
    CivicVoiceReportSendResponse,
    CivicVoiceReportUpdate,
    CivicVoiceSearchResponse,
    CivicVoiceSummaryResponse,
    CivicVoiceTheme,
    CivicVoiceThemesResponse,
    CivicVoiceTrendingResponse,
    CivicVoiceTrendingTopicItem,
    CivicVoiceTrendsResponse,
    NormalizedSourceRecord,
    ProviderCollectionStatus,
    ReportStatus,
)
from app.services.civicvoice.collectors.base import (
    BaseCollector,
    CollectorAuthError,
    CollectorError,
    CollectorNetworkError,
    CollectorQuotaError,
)
from app.services.civicvoice.collectors.bluesky import BlueskyCollector
from app.services.civicvoice.collectors.tavily import TavilyCollector
from app.services.civicvoice.collectors.youtube import YouTubeCollector
from app.services.civicvoice.intelligence import (
    BaseOpinionAnalyzer,
    CivicVoiceGeminiResearcher,
    EvidencePreparer,
    EvidenceValidator,
    PreparedEvidenceItem,
    RuleBasedMultilingualAnalyzer,
    SummarySynthesizer,
    ThemeClusterEngine,
    TrendAnalysisEngine,
    classify_theme_for_text,
)
from app.services.civicvoice.privacy import suppress_small_groups
from app.services.civicvoice.report_delivery import CivicVoiceReportDeliveryService
from app.services.civicvoice.report_generator import CivicVoiceReportGenerator

logger = logging.getLogger(__name__)


class CivicVoiceService:
    """Core domain service for CivicVoice data collection, intelligence analysis, and synthesis."""

    def __init__(
        self,
        bluesky_collector: BaseCollector | None = None,
        youtube_collector: BaseCollector | None = None,
        tavily_collector: BaseCollector | None = None,
        opinion_analyzer: BaseOpinionAnalyzer | None = None,
        theme_engine: ThemeClusterEngine | None = None,
        trend_engine: TrendAnalysisEngine | None = None,
        summary_synthesizer: SummarySynthesizer | None = None,
        report_generator: CivicVoiceReportGenerator | None = None,
        report_delivery: CivicVoiceReportDeliveryService | None = None,
        gemini_researcher: CivicVoiceGeminiResearcher | None = None,
        evidence_preparer: EvidencePreparer | None = None,
        evidence_validator: EvidenceValidator | None = None,
    ) -> None:
        self.bluesky = bluesky_collector or BlueskyCollector()
        self.youtube = youtube_collector or YouTubeCollector()
        self.tavily = tavily_collector or TavilyCollector()
        self.analyzer = opinion_analyzer or RuleBasedMultilingualAnalyzer()
        self.theme_engine = theme_engine or ThemeClusterEngine()
        self.trend_engine = trend_engine or TrendAnalysisEngine()
        self.summary_synthesizer = summary_synthesizer or SummarySynthesizer()
        self.report_generator = report_generator or CivicVoiceReportGenerator()
        self.report_delivery = report_delivery or CivicVoiceReportDeliveryService()
        self.gemini_researcher = gemini_researcher or CivicVoiceGeminiResearcher()
        self.evidence_preparer = evidence_preparer or EvidencePreparer()
        self.evidence_validator = evidence_validator or EvidenceValidator()
        self._search_cache: dict[str, tuple[float, CivicVoiceSearchResponse]] = {}

    def get_config_status(self, db: Session | None = None) -> CivicVoiceConfigStatusResponse:
        """Returns non-sensitive provider configuration status.

        Never exposes keys or secrets.
        """
        total_source = 0
        total_analysis = 0
        total_citizen = 0
        if db is not None:
            try:
                total_source = db.query(CivicVoiceSourceRecord).count()
                total_analysis = db.query(CivicVoiceAnalysisRecord).count()
                total_citizen = db.query(CivicVoiceCitizenSubmission).count()
            except Exception as exc:
                logger.warning("Could not query record counts for status: %s", exc)

        return CivicVoiceConfigStatusResponse(
            status="ok",
            bluesky_configured=self.bluesky.is_configured(),
            bluesky_base_url=settings.bluesky_api_base_url,
            youtube_configured=self.youtube.is_configured(),
            tavily_configured=self.tavily.is_configured(),
            total_source_records=total_source,
            total_analysis_records=total_analysis,
            total_citizen_submissions=total_citizen,
        )

    async def collect_and_persist(
        self,
        db: Session,
        query: str,
        topic: str | None = None,
        providers: list[CivicVoiceProvider] | None = None,
        limit_per_provider: int = 10,
    ) -> CivicVoiceCollectionResponse:
        """Collects public opinion records across requested providers, deduplicates them,

        persists new entries to the database, and returns the collection summary.
        """
        selected_providers = providers or [
            CivicVoiceProvider.BLUESKY,
            CivicVoiceProvider.YOUTUBE,
            CivicVoiceProvider.TAVILY,
        ]

        tasks = []
        task_providers = []

        for p in selected_providers:
            provider_val = p.value if isinstance(p, CivicVoiceProvider) else str(p)
            if provider_val == CivicVoiceProvider.BLUESKY.value:
                tasks.append(self.bluesky.collect(query=query, limit=limit_per_provider, topic=topic))
                task_providers.append(CivicVoiceProvider.BLUESKY.value)
            elif provider_val == CivicVoiceProvider.YOUTUBE.value:
                if self.youtube.is_configured():
                    tasks.append(self.youtube.collect(query=query, limit=limit_per_provider, topic=topic))
                    task_providers.append(CivicVoiceProvider.YOUTUBE.value)
                else:
                    logger.info("Skipping YouTube collection: API key is not configured.")
            elif provider_val == CivicVoiceProvider.TAVILY.value:
                if self.tavily.is_configured():
                    tasks.append(self.tavily.collect(query=query, limit=limit_per_provider, topic=topic))
                    task_providers.append(CivicVoiceProvider.TAVILY.value)
                else:
                    logger.info("Skipping Tavily collection: API key is not configured.")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_collected_records: list[NormalizedSourceRecord] = []
        provider_statuses: list[ProviderCollectionStatus] = []

        for prov_name, outcome in zip(task_providers, results):
            if isinstance(outcome, Exception):
                logger.warning("Provider %s collection failed: %s", prov_name, outcome)
                error_msg = str(outcome)
                if isinstance(outcome, (CollectorAuthError, CollectorQuotaError, CollectorNetworkError)):
                    error_msg = outcome.message
                provider_statuses.append(
                    ProviderCollectionStatus(
                        provider=prov_name,
                        success=False,
                        count=0,
                        error_message=error_msg,
                    )
                )
            elif isinstance(outcome, list):
                all_collected_records.extend(outcome)
                provider_statuses.append(
                    ProviderCollectionStatus(
                        provider=prov_name,
                        success=True,
                        count=len(outcome),
                    )
                )

        # Persistence with deduplication
        persisted_records, dups_skipped = self.persist_records(db, all_collected_records)

        return CivicVoiceCollectionResponse(
            query=query,
            topic=topic,
            total_collected=len(all_collected_records),
            total_persisted=len(persisted_records),
            total_duplicates_skipped=dups_skipped,
            provider_statuses=provider_statuses,
            records=[CivicVoiceRecordRead.model_validate(r) for r in persisted_records],
        )

    def persist_records(
        self,
        db: Session,
        records: list[NormalizedSourceRecord],
    ) -> tuple[list[CivicVoiceSourceRecord], int]:
        """Atomically persists normalized records, applying deduplication and non-destructive updates.

        Returns (persisted_records_list, duplicates_count).
        """
        if not records:
            return [], 0

        # In-memory deduplication pass for the incoming batch
        unique_incoming: dict[str, NormalizedSourceRecord] = {}
        for rec in records:
            if rec.dedup_key not in unique_incoming:
                unique_incoming[rec.dedup_key] = rec

        keys = list(unique_incoming.keys())
        existing_records = {
            r.dedup_key: r
            for r in db.query(CivicVoiceSourceRecord)
            .filter(CivicVoiceSourceRecord.dedup_key.in_(keys))
            .all()
        }

        persisted: list[CivicVoiceSourceRecord] = []
        duplicates_count = 0
        now = datetime.now(timezone.utc)

        for dedup_key, incoming in unique_incoming.items():
            if dedup_key in existing_records:
                duplicates_count += 1
                existing = existing_records[dedup_key]
                # Non-destructive update: never overwrite existing useful values with None/empty
                changed = False
                if not existing.title and incoming.title:
                    existing.title = incoming.title
                    changed = True
                if not existing.content and incoming.content:
                    existing.content = incoming.content
                    changed = True
                if not existing.author and incoming.author:
                    existing.author = incoming.author
                    changed = True
                if not existing.published_at and incoming.published_at:
                    existing.published_at = incoming.published_at
                    changed = True
                if not existing.language and incoming.language:
                    existing.language = incoming.language
                    changed = True
                if not existing.topic and incoming.topic:
                    existing.topic = incoming.topic
                    changed = True
                if changed:
                    existing.updated_at = now
                persisted.append(existing)
            else:
                new_row = CivicVoiceSourceRecord(
                    id=str(uuid4()),
                    provider=incoming.provider,
                    external_id=incoming.external_id,
                    dedup_key=incoming.dedup_key,
                    topic=incoming.topic,
                    title=incoming.title,
                    content=incoming.content,
                    url=incoming.url,
                    author=incoming.author,
                    published_at=incoming.published_at,
                    collected_at=incoming.collected_at or now,
                    language=incoming.language,
                    metadata_json=incoming.metadata_json,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_row)
                persisted.append(new_row)

        db.commit()
        for r in persisted:
            db.refresh(r)

        return persisted, duplicates_count

    def list_records(
        self,
        db: Session,
        provider: str | None = None,
        topic: str | None = None,
        query: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> CivicVoiceRecordListResponse:
        """Retrieves collected public opinion records with bounded pagination and filters."""
        bounded_limit = max(1, min(limit, 100))
        bounded_offset = max(0, offset)

        q = db.query(CivicVoiceSourceRecord)

        if provider:
            q = q.filter(CivicVoiceSourceRecord.provider == provider.strip().lower())
        if topic:
            q = q.filter(CivicVoiceSourceRecord.topic.ilike(f"%{topic.strip()}%"))
        if query:
            clean_q = query.strip()
            q = q.filter(
                or_(
                    CivicVoiceSourceRecord.title.ilike(f"%{clean_q}%"),
                    CivicVoiceSourceRecord.content.ilike(f"%{clean_q}%"),
                )
            )

        total = q.count()
        rows = (
            q.order_by(desc(CivicVoiceSourceRecord.collected_at))
            .offset(bounded_offset)
            .limit(bounded_limit)
            .all()
        )

        return CivicVoiceRecordListResponse(
            total=total,
            limit=bounded_limit,
            offset=bounded_offset,
            records=[CivicVoiceRecordRead.model_validate(r) for r in rows],
        )

    def analyze_source_records(
        self,
        db: Session,
        record_ids: list[str] | None = None,
        topic: str | None = None,
        limit: int = 50,
        force_reanalyze: bool = False,
    ) -> CivicVoiceAnalyzeResponse:
        """Executes opinion intelligence analysis over a bounded set of stored source records."""
        bounded_limit = max(1, min(limit, 100))

        q = db.query(CivicVoiceSourceRecord)
        if record_ids:
            q = q.filter(CivicVoiceSourceRecord.id.in_(record_ids))
        if topic:
            q = q.filter(CivicVoiceSourceRecord.topic.ilike(f"%{topic.strip()}%"))

        source_records = q.limit(bounded_limit).all()

        now = datetime.now(timezone.utc)
        persisted_analyses: list[CivicVoiceAnalysisRecord] = []
        skipped_count = 0

        # Check existing analyses
        existing_map: dict[str, CivicVoiceAnalysisRecord] = {}
        if source_records:
            s_ids = [s.id for s in source_records]
            existing = (
                db.query(CivicVoiceAnalysisRecord)
                .filter(CivicVoiceAnalysisRecord.source_record_id.in_(s_ids))
                .all()
            )
            existing_map = {ar.source_record_id: ar for ar in existing}

        for s_rec in source_records:
            if s_rec.id in existing_map and not force_reanalyze:
                persisted_analyses.append(existing_map[s_rec.id])
                skipped_count += 1
                continue

            # Analyze record
            res = self.analyzer.analyze_record(s_rec)

            # Assign theme
            theme_text = ((s_rec.title or "") + " " + (s_rec.content or "") + " " + (s_rec.topic or "")).strip()
            theme_id, theme_label = classify_theme_for_text(theme_text, category=res.category.value)

            if s_rec.id in existing_map and force_reanalyze:
                # Update existing analysis in-place without creating duplicate records
                target = existing_map[s_rec.id]
                target.category = res.category.value
                target.sentiment = res.sentiment.value
                target.content_intent = res.content_intent.value
                target.confidence = res.confidence
                target.explanation = res.explanation
                target.detected_language = res.detected_language
                target.has_complaint = res.has_complaint
                target.extracted_complaint = res.extracted_complaint
                target.has_suggestion = res.has_suggestion
                target.extracted_suggestion = res.extracted_suggestion
                target.theme_id = theme_id
                target.theme_label = theme_label
                target.analysis_method = res.analysis_method
                target.analysis_version = res.analysis_version
                target.metadata_json = res.metadata
                target.updated_at = now
                persisted_analyses.append(target)
            else:
                new_analysis = CivicVoiceAnalysisRecord(
                    id=str(uuid4()),
                    source_record_id=s_rec.id,
                    category=res.category.value,
                    sentiment=res.sentiment.value,
                    content_intent=res.content_intent.value,
                    confidence=res.confidence,
                    explanation=res.explanation,
                    detected_language=res.detected_language,
                    has_complaint=res.has_complaint,
                    extracted_complaint=res.extracted_complaint,
                    has_suggestion=res.has_suggestion,
                    extracted_suggestion=res.extracted_suggestion,
                    theme_id=theme_id,
                    theme_label=theme_label,
                    analysis_method=res.analysis_method,
                    analysis_version=res.analysis_version,
                    metadata_json=res.metadata,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_analysis)
                persisted_analyses.append(new_analysis)

        db.commit()
        for ar in persisted_analyses:
            db.refresh(ar)

        return CivicVoiceAnalyzeResponse(
            total_examined=len(source_records),
            total_analyzed=len(persisted_analyses) - skipped_count,
            total_skipped=skipped_count,
            analyses=[CivicVoiceAnalysisRecordRead.model_validate(ar) for ar in persisted_analyses],
        )

    def list_analysis_records(
        self,
        db: Session,
        category: str | None = None,
        theme_id: str | None = None,
        has_complaint: bool | None = None,
        has_suggestion: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> CivicVoiceAnalysisListResponse:
        """Retrieves stored analysis records with bounded pagination and filters."""
        bounded_limit = max(1, min(limit, 100))
        bounded_offset = max(0, offset)

        q = db.query(CivicVoiceAnalysisRecord)

        if category:
            q = q.filter(CivicVoiceAnalysisRecord.category == category.strip().lower())
        if theme_id:
            q = q.filter(CivicVoiceAnalysisRecord.theme_id == theme_id.strip())
        if has_complaint is not None:
            q = q.filter(CivicVoiceAnalysisRecord.has_complaint == has_complaint)
        if has_suggestion is not None:
            q = q.filter(CivicVoiceAnalysisRecord.has_suggestion == has_suggestion)

        total = q.count()
        rows = (
            q.order_by(desc(CivicVoiceAnalysisRecord.created_at))
            .offset(bounded_offset)
            .limit(bounded_limit)
            .all()
        )

        return CivicVoiceAnalysisListResponse(
            total=total,
            limit=bounded_limit,
            offset=bounded_offset,
            records=[CivicVoiceAnalysisRecordRead.model_validate(ar) for ar in rows],
        )

    def get_themes(
        self,
        db: Session,
        topic: str | None = None,
    ) -> CivicVoiceThemesResponse:
        """Clusters analyzed records into recurring themes with evidence IDs and canonical URLs."""
        q = db.query(CivicVoiceAnalysisRecord)
        analysis_records = q.all()

        s_ids = [ar.source_record_id for ar in analysis_records]
        source_records = db.query(CivicVoiceSourceRecord).filter(CivicVoiceSourceRecord.id.in_(s_ids)).all() if s_ids else []
        source_map = {s.id: s for s in source_records}

        if topic:
            filtered_analyses = []
            for ar in analysis_records:
                s_rec = source_map.get(ar.source_record_id)
                if s_rec and s_rec.topic and topic.lower() in s_rec.topic.lower():
                    filtered_analyses.append(ar)
            analysis_records = filtered_analyses

        themes = self.theme_engine.cluster_records(analysis_records, source_map)

        return CivicVoiceThemesResponse(
            total_themes=len(themes),
            total_records_represented=len(analysis_records),
            themes=themes,
        )

    def get_trends(
        self,
        db: Session,
        topic: str | None = None,
        window_days: int = 7,
    ) -> CivicVoiceTrendsResponse:
        """Calculates trend comparisons across equivalent time windows."""
        q = db.query(CivicVoiceAnalysisRecord)
        analysis_records = q.all()

        s_ids = [ar.source_record_id for ar in analysis_records]
        source_records = db.query(CivicVoiceSourceRecord).filter(CivicVoiceSourceRecord.id.in_(s_ids)).all() if s_ids else []
        source_map = {s.id: s for s in source_records}

        if topic:
            filtered_analyses = []
            for ar in analysis_records:
                s_rec = source_map.get(ar.source_record_id)
                if s_rec and s_rec.topic and topic.lower() in s_rec.topic.lower():
                    filtered_analyses.append(ar)
            analysis_records = filtered_analyses

        return self.trend_engine.calculate_trends(
            analysis_records=analysis_records,
            source_records_map=source_map,
            window_days=window_days,
        )

    def get_summary(
        self,
        db: Session,
        topic: str | None = None,
    ) -> CivicVoiceSummaryResponse:
        """Synthesizes an evidence-backed intelligence summary report grounded in actual records."""
        q = db.query(CivicVoiceAnalysisRecord)
        analysis_records = q.all()

        s_ids = [ar.source_record_id for ar in analysis_records]
        source_records = db.query(CivicVoiceSourceRecord).filter(CivicVoiceSourceRecord.id.in_(s_ids)).all() if s_ids else []
        source_map = {s.id: s for s in source_records}

        if topic:
            filtered_analyses = []
            for ar in analysis_records:
                s_rec = source_map.get(ar.source_record_id)
                if s_rec and s_rec.topic and topic.lower() in s_rec.topic.lower():
                    filtered_analyses.append(ar)
            analysis_records = filtered_analyses

        trends = self.trend_engine.calculate_trends(
            analysis_records=analysis_records,
            source_records_map=source_map,
            window_days=7,
        )
        return self.summary_synthesizer.generate_summary(
            analysis_records=analysis_records,
            source_records_map=source_map,
            topic=topic,
            trends_result=trends,
        )

    def create_citizen_submission(
        self,
        db: Session,
        payload: CivicVoiceCitizenSubmissionCreate,
    ) -> CivicVoiceCitizenSubmissionResponse:
        """Validates and persists a direct citizen opinion submission.

        Separated from external public-source scraping to preserve data provenance
        and maintain citizen privacy without requiring unnecessary personal metadata.
        """
        if not payload.consent_given:
            raise ValueError("Consent is required to submit a community civic opinion.")

        clean_topic = payload.topic.strip()
        clean_text = payload.opinion_text.strip()
        clean_locality = payload.locality.strip() if payload.locality else None
        clean_lang = payload.language.strip().lower() if payload.language else "en"

        now = datetime.now(timezone.utc)
        submission = CivicVoiceCitizenSubmission(
            id=str(uuid4()),
            topic=clean_topic,
            opinion_text=clean_text,
            locality=clean_locality,
            language=clean_lang,
            consent_given=True,
            created_at=now,
            updated_at=now,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

        return CivicVoiceCitizenSubmissionResponse(
            id=submission.id,
            topic=submission.topic,
            locality=submission.locality,
            language=submission.language,
            created_at=submission.created_at,
        )

    def list_citizen_submissions(
        self,
        db: Session,
        topic: str | None = None,
        locality: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> CivicVoiceCitizenSubmissionListResponse:
        """Retrieves stored citizen opinions with bounded pagination and optional filtering."""
        bounded_limit = max(1, min(limit, 100))
        bounded_offset = max(0, offset)

        q = db.query(CivicVoiceCitizenSubmission)
        if topic:
            q = q.filter(CivicVoiceCitizenSubmission.topic.ilike(f"%{topic.strip()}%"))
        if locality:
            q = q.filter(CivicVoiceCitizenSubmission.locality.ilike(f"%{locality.strip()}%"))

        total = q.count()
        rows = (
            q.order_by(desc(CivicVoiceCitizenSubmission.created_at))
            .offset(bounded_offset)
            .limit(bounded_limit)
            .all()
        )

        return CivicVoiceCitizenSubmissionListResponse(
            total=total,
            limit=bounded_limit,
            offset=bounded_offset,
            submissions=[CivicVoiceCitizenSubmissionRead.model_validate(r) for r in rows],
        )

    def get_citizen_submissions_aggregated(
        self,
        db: Session,
        topic: str | None = None,
        suppress_small_groups_flag: bool = False,
    ) -> CivicVoiceCitizenSubmissionsAggregatedResponse:
        """Computes anonymized aggregate metrics over citizen submissions.

        Guarantees privacy: does NOT return raw text, IDs, or timestamps.
        If suppress_small_groups_flag is True, applies k-anonymity suppression (< 3).
        """
        q = db.query(CivicVoiceCitizenSubmission)
        if topic:
            q = q.filter(CivicVoiceCitizenSubmission.topic.ilike(f"%{topic.strip()}%"))

        submissions = q.all()
        topic_dist: dict[str, int] = {}
        locality_dist: dict[str, int] = {}
        lang_dist: dict[str, int] = {}

        for s in submissions:
            t = s.topic or "other"
            topic_dist[t] = topic_dist.get(t, 0) + 1
            if s.locality:
                locality_dist[s.locality] = locality_dist.get(s.locality, 0) + 1
            lang = s.language or "en"
            lang_dist[lang] = lang_dist.get(lang, 0) + 1

        if suppress_small_groups_flag:
            topic_dist = suppress_small_groups(topic_dist)
            locality_dist = suppress_small_groups(locality_dist)
            lang_dist = suppress_small_groups(lang_dist)

        return CivicVoiceCitizenSubmissionsAggregatedResponse(
            total_submissions=len(submissions),
            topic_distribution=topic_dist,
            locality_distribution=locality_dist,
            language_distribution=lang_dist,
        )

    def generate_report(
        self,
        db: Session,
        topic: str,
        title: str | None = None,
        geographic_scope: str = "Bengaluru Urban (BBMP Wards)",
        reporting_period_days: int = 14,
        created_by: str = "authorized_analyst",
    ) -> CivicVoiceReportRead:
        """Generates and persists an evidence-backed civic priority report."""
        report = self.report_generator.generate_report(
            db=db,
            topic=topic,
            title=title,
            geographic_scope=geographic_scope,
            reporting_period_days=reporting_period_days,
            created_by=created_by,
        )
        return CivicVoiceReportRead.model_validate(report)

    def list_reports(
        self,
        db: Session,
        topic: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> CivicVoiceReportListResponse:
        """Lists persisted civic reports with bounded pagination and filtering."""
        bounded_limit = max(1, min(limit, 100))
        bounded_offset = max(0, offset)

        q = db.query(CivicVoiceReport)
        if topic:
            q = q.filter(CivicVoiceReport.topic.ilike(f"%{topic.strip()}%"))
        if status:
            q = q.filter(CivicVoiceReport.status == status.strip())

        total = q.count()
        reports = (
            q.order_by(desc(CivicVoiceReport.created_at))
            .offset(bounded_offset)
            .limit(bounded_limit)
            .all()
        )

        return CivicVoiceReportListResponse(
            total=total,
            limit=bounded_limit,
            offset=bounded_offset,
            reports=[CivicVoiceReportRead.model_validate(r) for r in reports],
        )

    def get_report(self, db: Session, report_id: str) -> CivicVoiceReportRead:
        """Retrieves a single report by ID along with its audit trail."""
        report = db.get(CivicVoiceReport, report_id)
        if not report:
            raise ValueError(f"CivicVoice Report '{report_id}' not found.")
        return CivicVoiceReportRead.model_validate(report)

    def update_report(
        self,
        db: Session,
        report_id: str,
        update_data: CivicVoiceReportUpdate,
        performed_by: str = "authorized_reviewer",
    ) -> CivicVoiceReportRead:
        """Updates report content or recipient. Automatically invalidates approval if modified."""
        report = self.report_delivery.update_report(
            db=db,
            report_id=report_id,
            update_data=update_data,
            performed_by=performed_by,
        )
        return CivicVoiceReportRead.model_validate(report)

    def approve_report(
        self,
        db: Session,
        report_id: str,
        reviewer_id: str = "authorized_reviewer",
        notes: str | None = None,
    ) -> CivicVoiceReportRead:
        """Approves a report and binds its cryptographic content hash."""
        report = self.report_delivery.approve_report(
            db=db,
            report_id=report_id,
            reviewer_id=reviewer_id,
            notes=notes,
        )
        return CivicVoiceReportRead.model_validate(report)

    def reject_report(
        self,
        db: Session,
        report_id: str,
        reviewer_id: str = "authorized_reviewer",
        reason: str = "Report rejected by human reviewer.",
    ) -> CivicVoiceReportRead:
        """Rejects a report with specified justification."""
        report = self.report_delivery.reject_report(
            db=db,
            report_id=report_id,
            reviewer_id=reviewer_id,
            reason=reason,
        )
        return CivicVoiceReportRead.model_validate(report)

    def send_report(
        self,
        db: Session,
        report_id: str,
        sender_id: str = "authorized_reviewer",
        idempotency_key: str | None = None,
        confirm_send: bool = True,
    ) -> CivicVoiceReportSendResponse:
        """Dispatches an approved report to official recipient or provides verified export."""
        return self.report_delivery.send_report(
            db=db,
            report_id=report_id,
            sender_id=sender_id,
            idempotency_key=idempotency_key,
            confirm_send=confirm_send,
        )

    def export_report(self, db: Session, report_id: str) -> CivicVoiceReportExportResponse:
        """Exports report in markdown format for download or offline dispatch."""
        return self.report_delivery.export_report(db=db, report_id=report_id)

    def get_trending_topics(self, db: Session, limit: int = 8) -> CivicVoiceTrendingResponse:
        """Discovers trending civic topics from actual collected database records.

        Never fabricates topics or popularity counts.
        """
        source_topic_rows = (
            db.query(
                CivicVoiceSourceRecord.topic,
                func.count(CivicVoiceSourceRecord.id).label("count"),
                func.max(CivicVoiceSourceRecord.collected_at).label("latest"),
                func.max(CivicVoiceSourceRecord.title).label("sample_title"),
            )
            .filter(
                CivicVoiceSourceRecord.topic.isnot(None),
                CivicVoiceSourceRecord.topic != "",
            )
            .group_by(CivicVoiceSourceRecord.topic)
            .all()
        )

        citizen_topic_rows = (
            db.query(
                CivicVoiceCitizenSubmission.topic,
                func.count(CivicVoiceCitizenSubmission.id).label("count"),
                func.max(CivicVoiceCitizenSubmission.created_at).label("latest"),
            )
            .filter(
                CivicVoiceCitizenSubmission.topic.isnot(None),
                CivicVoiceCitizenSubmission.topic != "",
            )
            .group_by(CivicVoiceCitizenSubmission.topic)
            .all()
        )

        theme_rows = (
            db.query(
                CivicVoiceAnalysisRecord.theme_label,
                func.count(CivicVoiceAnalysisRecord.id).label("count"),
                func.max(CivicVoiceAnalysisRecord.created_at).label("latest"),
            )
            .filter(
                CivicVoiceAnalysisRecord.theme_label.isnot(None),
                CivicVoiceAnalysisRecord.theme_label != "",
            )
            .group_by(CivicVoiceAnalysisRecord.theme_label)
            .all()
        )

        aggregated: dict[str, dict[str, Any]] = {}

        for topic, cnt, latest, sample_title in source_topic_rows:
            if not topic:
                continue
            key = topic.strip().title()
            if key not in aggregated:
                aggregated[key] = {
                    "topic": key,
                    "record_count": 0,
                    "citizen_opinions_count": 0,
                    "latest_activity": latest,
                    "sample_title": sample_title,
                }
            aggregated[key]["record_count"] += cnt
            if latest and (not aggregated[key]["latest_activity"] or latest > aggregated[key]["latest_activity"]):
                aggregated[key]["latest_activity"] = latest
            if sample_title and not aggregated[key]["sample_title"]:
                aggregated[key]["sample_title"] = sample_title

        for topic, cnt, latest in citizen_topic_rows:
            if not topic:
                continue
            key = topic.strip().title()
            if key not in aggregated:
                aggregated[key] = {
                    "topic": key,
                    "record_count": 0,
                    "citizen_opinions_count": 0,
                    "latest_activity": latest,
                    "sample_title": None,
                }
            aggregated[key]["citizen_opinions_count"] += cnt
            if latest and (not aggregated[key]["latest_activity"] or latest > aggregated[key]["latest_activity"]):
                aggregated[key]["latest_activity"] = latest

        if len(aggregated) < 4:
            for theme_label, cnt, latest in theme_rows:
                if not theme_label:
                    continue
                key = theme_label.strip()
                if key not in aggregated:
                    aggregated[key] = {
                        "topic": key,
                        "record_count": cnt,
                        "citizen_opinions_count": 0,
                        "latest_activity": latest,
                        "sample_title": None,
                    }

        items = []
        for info in aggregated.values():
            total = info["record_count"] + info["citizen_opinions_count"]
            items.append(
                CivicVoiceTrendingTopicItem(
                    topic=info["topic"],
                    record_count=info["record_count"],
                    citizen_opinions_count=info["citizen_opinions_count"],
                    total_activity_count=total,
                    latest_activity=info["latest_activity"],
                    sample_title=info["sample_title"],
                )
            )

        items.sort(
            key=lambda x: (
                x.total_activity_count,
                x.latest_activity.timestamp() if x.latest_activity else 0,
            ),
            reverse=True,
        )

        return CivicVoiceTrendingResponse(trending_topics=items[:limit])

    async def search_topic(
        self,
        db: Session,
        query: str,
        limit_per_provider: int = 5,
        force_refresh: bool = False,
    ) -> CivicVoiceSearchResponse:
        """Executes a search-first intelligence flow for arbitrary queries.

        Architecture:
        User query -> source collection -> relevance filtering -> evidence extraction
        -> Gemini research and synthesis -> evidence validation -> structured report.
        """
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Search query cannot be empty.")

        # ---------------------------------------------------------------------
        # 1. In-Memory Research Query Cache (1-Hour TTL)
        # ---------------------------------------------------------------------
        cache_key = clean_query.lower()
        now_ts = time.time()
        if not force_refresh and cache_key in self._search_cache:
            cached_time, cached_resp = self._search_cache[cache_key]
            if now_ts - cached_time < 3600.0:
                logger.info("Serving cached CivicVoice research for topic: '%s'", clean_query)
                live_citizen_count = (
                    db.query(CivicVoiceCitizenSubmission)
                    .filter(CivicVoiceCitizenSubmission.topic.ilike(f"%{clean_query}%"))
                    .count()
                )
                return cached_resp.model_copy(update={"citizen_submissions_count": live_citizen_count})

        # ---------------------------------------------------------------------
        # 2. Source Collection Across Providers
        # ---------------------------------------------------------------------
        matching_query_filter = or_(
            CivicVoiceSourceRecord.topic.ilike(f"%{clean_query}%"),
            CivicVoiceSourceRecord.title.ilike(f"%{clean_query}%"),
            CivicVoiceSourceRecord.content.ilike(f"%{clean_query}%"),
        )
        existing_matching = (
            db.query(CivicVoiceSourceRecord)
            .filter(matching_query_filter)
            .order_by(desc(CivicVoiceSourceRecord.collected_at))
            .limit(50)
            .all()
        )

        provider_statuses: list[ProviderCollectionStatus] = []

        if force_refresh or len(existing_matching) < 2:
            try:
                collection_res = await self.collect_and_persist(
                    db=db,
                    query=clean_query,
                    topic=clean_query,
                    limit_per_provider=limit_per_provider,
                )
                provider_statuses = collection_res.provider_statuses
            except Exception as coll_err:
                logger.warning("Error during live collection for query '%s': %s", clean_query, coll_err)
                provider_statuses = [
                    ProviderCollectionStatus(
                        provider="external_search",
                        success=False,
                        count=0,
                        error_message=f"Collection notice: {str(coll_err)}",
                    )
                ]

            existing_matching = (
                db.query(CivicVoiceSourceRecord)
                .filter(matching_query_filter)
                .order_by(desc(CivicVoiceSourceRecord.collected_at))
                .limit(50)
                .all()
            )
        else:
            prov_counts: dict[str, int] = {}
            for r in existing_matching:
                prov_counts[r.provider] = prov_counts.get(r.provider, 0) + 1
            for p, cnt in prov_counts.items():
                provider_statuses.append(
                    ProviderCollectionStatus(
                        provider=p,
                        success=True,
                        count=cnt,
                    )
                )

        # ---------------------------------------------------------------------
        # 3. Analyze Unprocessed Records for Local DB Intelligence
        # ---------------------------------------------------------------------
        if existing_matching:
            try:
                self.analyze_source_records(
                    db=db,
                    record_ids=[r.id for r in existing_matching],
                    topic=clean_query,
                    limit=len(existing_matching),
                    force_reanalyze=False,
                )
            except Exception as an_err:
                logger.warning("Analysis step encountered an error: %s", an_err)

        matching_ids = [r.id for r in existing_matching]
        analyses = (
            db.query(CivicVoiceAnalysisRecord)
            .filter(CivicVoiceAnalysisRecord.source_record_id.in_(matching_ids))
            .all()
            if matching_ids
            else []
        )
        source_map = {r.id: r for r in existing_matching}

        themes = self.theme_engine.cluster_records(analyses, source_map)
        trends = self.trend_engine.calculate_trends(
            analysis_records=analyses,
            source_records_map=source_map,
            window_days=7,
        )

        # ---------------------------------------------------------------------
        # 4. Evidence Preparation & Relevance Filtering
        # ---------------------------------------------------------------------
        relevant_evidence, _ = self.evidence_preparer.prepare_evidence(
            query=clean_query,
            records=existing_matching,
        )

        # ---------------------------------------------------------------------
        # 5. Gemini Research and Synthesis (with Gap Detection & Follow-up)
        # ---------------------------------------------------------------------
        summary: CivicVoiceSummaryResponse

        if self.gemini_researcher.is_configured():
            async def followup_collector_fn(sub_q: str, limit: int) -> list[PreparedEvidenceItem]:
                """Follow-up retrieval callback bounded to active providers."""
                try:
                    coll_res = await self.collect_and_persist(
                        db=db,
                        query=sub_q,
                        topic=clean_query,
                        limit_per_provider=limit,
                    )
                    for r in coll_res.records:
                        source_map[r.id] = r
                    prep_new, _ = self.evidence_preparer.prepare_evidence(query=clean_query, records=coll_res.records)
                    return prep_new
                except Exception as sub_err:
                    logger.debug("Follow-up collection notice: %s", sub_err)
                    return []

            try:
                gemini_output, final_evidence = await self.gemini_researcher.execute_research(
                    query=clean_query,
                    initial_evidence=relevant_evidence,
                    followup_collector=followup_collector_fn,
                    max_followup_rounds=1,
                )
                summary = self.evidence_validator.validate_and_assemble(
                    report=gemini_output,
                    evidence_items=final_evidence,
                    source_records_map=source_map,
                    ai_model_name=self.gemini_researcher.model,
                )
            except Exception as gemini_err:
                logger.warning(
                    "Gemini AI research synthesis failed for '%s': %s. Reverting to rule-based fallback.",
                    clean_query,
                    gemini_err,
                )
                summary = self.summary_synthesizer.generate_summary(
                    analysis_records=analyses,
                    source_records_map=source_map,
                    topic=clean_query,
                    trends_result=trends,
                )
                summary.ai_synthesized = False
                summary.ai_model = None
                summary.validation_status = "rule_based_fallback"
                summary.validation_notes = [
                    f"Gemini AI synthesis could not be completed ({str(gemini_err)}). Displaying transparent deterministic rule-based analysis."
                ]
        else:
            summary = self.summary_synthesizer.generate_summary(
                analysis_records=analyses,
                source_records_map=source_map,
                topic=clean_query,
                trends_result=trends,
            )
            summary.ai_synthesized = False
            summary.ai_model = None
            summary.validation_status = "rule_based_fallback"
            summary.validation_notes = [
                "Gemini API key is not configured on the backend. Displaying transparent deterministic rule-based analysis."
            ]

        # ---------------------------------------------------------------------
        # 6. Citizen Submission Privacy (Aggregated Volume Only)
        # ---------------------------------------------------------------------
        citizen_count = (
            db.query(CivicVoiceCitizenSubmission)
            .filter(CivicVoiceCitizenSubmission.topic.ilike(f"%{clean_query}%"))
            .count()
        )

        response = CivicVoiceSearchResponse(
            query=clean_query,
            topic=clean_query,
            total_records=len(existing_matching),
            provider_statuses=provider_statuses,
            records=[CivicVoiceRecordRead.model_validate(r) for r in existing_matching],
            summary=summary,
            themes=themes,
            trends=trends,
            citizen_submissions_count=citizen_count,
        )

        # Cache response
        self._search_cache[cache_key] = (now_ts, response)
        return response

    def clear_cache(self) -> None:
        """Clears the in-memory research search cache."""
        self._search_cache.clear()




