"""CivicVoice Civic Priority Report Generator.

Transforms persisted public opinion intelligence and privacy-safe citizen submissions
into structured, verifiable, evidence-grounded civic reports for official department review.

Guiding Principles:
- Never invents statistics, quotations, sources, or findings.
- Strictly distinguishes observed public-source opinions from citizen-submitted feedback.
- Clearly states that online data is not representative of all Bengaluru residents.
- Enforces cryptographic hash binding (SHA-256) to ensure approval integrity.
- Applies k-anonymity privacy suppression to citizen feedback.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import logging
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.civicvoice import (
    CivicVoiceAnalysisRecord,
    CivicVoiceCitizenSubmission,
    CivicVoiceReport,
    CivicVoiceReportAudit,
    CivicVoiceSourceRecord,
)
from app.schemas.civicvoice import ReportStatus
from app.services.civicvoice.department_mapper import resolve_department_mapping
from app.services.civicvoice.privacy import build_safe_citizen_report_metrics

logger = logging.getLogger(__name__)


def compute_report_content_hash(
    title: str,
    topic: str,
    recipient_email: str | None,
    summary_content: str,
    recommendations: str,
    limitations: str,
) -> str:
    """Computes a SHA-256 cryptographic digest binding the exact approved report content and recipient."""
    canonical = (
        f"{title.strip()}|"
        f"{topic.strip().lower()}|"
        f"{(recipient_email or '').strip().lower()}|"
        f"{summary_content.strip()}|"
        f"{recommendations.strip()}|"
        f"{limitations.strip()}"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CivicVoiceReportGenerator:
    """Generates traceable, evidence-grounded civic reports from real database records."""

    def generate_report(
        self,
        db: Session,
        topic: str,
        title: str | None = None,
        geographic_scope: str = "Bengaluru Urban (BBMP Wards)",
        reporting_period_days: int = 14,
        created_by: str = "system_analyst",
    ) -> CivicVoiceReport:
        """Synthesizes analysis and citizen submissions into a persisted, review-ready draft report."""
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=reporting_period_days)

        # 1. Resolve official government department mapping
        dept_mapping = resolve_department_mapping(topic)
        matching_topics = set(dept_mapping.topics_handled or [])
        matching_topics.add(topic.lower())
        matching_topics.add(topic.lower().replace("_", " "))

        # 2. Query collected source records & analysis records within period
        source_stmt = select(CivicVoiceSourceRecord).where(
            CivicVoiceSourceRecord.collected_at >= period_start
        )
        if topic and topic.lower() not in ("all", "general", "bengaluru"):
            source_conds = []
            for t in matching_topics:
                source_conds.append(func.lower(CivicVoiceSourceRecord.topic).contains(t))
                source_conds.append(func.lower(CivicVoiceSourceRecord.topic) == t)
            source_stmt = source_stmt.where(or_(*source_conds))

        sources = list(db.scalars(source_stmt.order_by(desc(CivicVoiceSourceRecord.collected_at))).all())
        source_ids = [s.id for s in sources]

        analyses: list[CivicVoiceAnalysisRecord] = []
        if source_ids:
            analyses_stmt = select(CivicVoiceAnalysisRecord).where(
                CivicVoiceAnalysisRecord.source_record_id.in_(source_ids)
            )
            analyses = list(db.scalars(analyses_stmt).all())

        # 3. Query citizen submissions within period
        sub_stmt = select(CivicVoiceCitizenSubmission).where(
            CivicVoiceCitizenSubmission.created_at >= period_start
        )
        if topic and topic.lower() not in ("all", "general", "bengaluru"):
            sub_conds = []
            for t in matching_topics:
                sub_conds.append(func.lower(CivicVoiceCitizenSubmission.topic).contains(t))
                sub_conds.append(func.lower(CivicVoiceCitizenSubmission.topic) == t)
            sub_stmt = sub_stmt.where(or_(*sub_conds))

        submissions = list(db.scalars(sub_stmt.order_by(desc(CivicVoiceCitizenSubmission.created_at))).all())

        # 4. Compute privacy-safe citizen metrics (k-anonymity threshold = 3)
        sub_locality_counter = Counter(s.locality for s in submissions if s.locality)
        sub_topic_counter = Counter(s.topic for s in submissions if s.topic)
        safe_citizen_metrics = build_safe_citizen_report_metrics(
            total_submissions=len(submissions),
            topic_distribution=dict(sub_topic_counter),
            locality_distribution=dict(sub_locality_counter),
            threshold=3,
        )

        # 5. Aggregate findings from analyzed public source records
        sentiment_counter = Counter(a.sentiment for a in analyses if a.sentiment)
        theme_counter = Counter(a.theme_label for a in analyses if a.theme_label)

        complaints_list: list[dict[str, str]] = []
        suggestions_list: list[dict[str, str]] = []
        evidence_urls: list[str] = []

        # Map source records for fast lookup
        source_lookup = {s.id: s for s in sources}
        for a in analyses:
            src = source_lookup.get(a.source_record_id)
            if src and src.url and src.url not in evidence_urls:
                evidence_urls.append(src.url)

            if a.has_complaint and a.extracted_complaint:
                complaints_list.append({
                    "complaint": a.extracted_complaint,
                    "theme": a.theme_label or "General",
                    "source_url": src.url if src else None,
                })
            if a.has_suggestion and a.extracted_suggestion:
                suggestions_list.append({
                    "suggestion": a.extracted_suggestion,
                    "theme": a.theme_label or "General",
                    "source_url": src.url if src else None,
                })

        # 6. Trend calculation across equivalent past period
        past_start = period_start - timedelta(days=reporting_period_days)
        past_sources_count = db.scalar(
            select(func.count(CivicVoiceSourceRecord.id)).where(
                CivicVoiceSourceRecord.collected_at >= past_start,
                CivicVoiceSourceRecord.collected_at < period_start,
            )
        ) or 0
        trend_direction = "stable"
        if len(sources) > past_sources_count * 1.25:
            trend_direction = "increasing"
        elif len(sources) < past_sources_count * 0.75:
            trend_direction = "decreasing"

        # 7. Formulate structured content blocks
        report_title = title or f"Civic Priority Brief: {topic.replace('_', ' ').title()} ({dept_mapping.authority_name})"

        summary_content = self._build_summary_content(
            topic=topic,
            dept_mapping=dept_mapping,
            sources_count=len(sources),
            analyses_count=len(analyses),
            safe_citizen_metrics=safe_citizen_metrics,
            sentiment_counter=sentiment_counter,
            theme_counter=theme_counter,
            complaints_list=complaints_list[:5],
            suggestions_list=suggestions_list[:5],
            trend_direction=trend_direction,
            past_sources_count=past_sources_count,
            period_days=reporting_period_days,
        )

        recommendations = self._build_recommendations(
            topic=topic,
            dept_mapping=dept_mapping,
            theme_counter=theme_counter,
            suggestions_list=suggestions_list[:5],
            complaints_count=len(complaints_list),
        )

        limitations = self._build_limitations(
            sources_count=len(sources),
            citizen_count=len(submissions),
            dept_mapping=dept_mapping,
        )

        # 8. Cryptographic hash binding
        content_hash = compute_report_content_hash(
            title=report_title,
            topic=topic,
            recipient_email=dept_mapping.recipient_email,
            summary_content=summary_content,
            recommendations=recommendations,
            limitations=limitations,
        )

        report = CivicVoiceReport(
            title=report_title,
            topic=topic,
            geographic_scope=geographic_scope,
            reporting_period_start=period_start,
            reporting_period_end=now,
            status=ReportStatus.DRAFT.value,
            authority_name=dept_mapping.authority_name,
            department_name=dept_mapping.department_name,
            recipient_email=dept_mapping.recipient_email,
            official_portal_url=dept_mapping.official_portal_url,
            mapping_verified=dept_mapping.is_verified,
            mapping_source_url=dept_mapping.verification_source_url,
            mapping_last_verified=datetime.strptime(dept_mapping.last_verified_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) if dept_mapping.last_verified_date else None,
            source_records_count=len(sources),
            citizen_submissions_count=len(submissions),
            summary_content=summary_content,
            recommendations=recommendations,
            themes_summary={
                "theme_counts": dict(theme_counter),
                "total_themes": len(theme_counter),
            },
            sentiment_summary={
                "sentiment_breakdown": dict(sentiment_counter),
                "total_sentiments_analyzed": len(analyses),
            },
            evidence_urls=evidence_urls[:25],
            limitations=limitations,
            content_hash=content_hash,
            delivery_details={
                "citizen_metrics": safe_citizen_metrics,
                "trend": {
                    "direction": trend_direction,
                    "current_window_count": len(sources),
                    "previous_window_count": past_sources_count,
                    "window_days": reporting_period_days,
                },
            },
        )

        db.add(report)
        db.flush()

        # Audit initial report creation
        audit = CivicVoiceReportAudit(
            report_id=report.id,
            action="created",
            performed_by=created_by,
            previous_status=None,
            new_status=ReportStatus.DRAFT.value,
            details_json={
                "topic": topic,
                "authority": dept_mapping.authority_name,
                "mapping_verified": dept_mapping.is_verified,
                "source_records_count": len(sources),
                "citizen_submissions_count": len(submissions),
                "content_hash": content_hash,
            },
        )
        db.add(audit)
        db.commit()
        db.refresh(report)
        return report

    def _build_summary_content(
        self,
        topic: str,
        dept_mapping: Any,
        sources_count: int,
        analyses_count: int,
        safe_citizen_metrics: dict[str, Any],
        sentiment_counter: Counter,
        theme_counter: Counter,
        complaints_list: list[dict[str, str]],
        suggestions_list: list[dict[str, str]],
        trend_direction: str,
        past_sources_count: int,
        period_days: int,
    ) -> str:
        """Constructs an evidence-grounded markdown summary body."""
        lines: list[str] = [
            f"### Executive Summary — {topic.replace('_', ' ').title()}",
            "",
            f"**Responsible Authority**: {dept_mapping.authority_name} ({dept_mapping.department_name})",
            f"**Jurisdiction**: {dept_mapping.jurisdiction}",
            f"**Official Verification**: {'Verified (Official Government Portal)' if dept_mapping.is_verified else 'UNVERIFIED — Requires Human Verification'}",
            "",
            "#### 1. Evidence Base & Data Provenance",
            f"- **Public Web & Social Sources Analyzed**: {sources_count} records ({analyses_count} categorized findings from Bluesky, YouTube, and Tavily).",
            f"- **Direct Citizen Community Submissions**: {safe_citizen_metrics['total_represented']} verified resident submissions represented.",
            "",
        ]

        # Citizen feedback distribution with k-anonymity
        if safe_citizen_metrics.get("sample_warning"):
            lines.append(f"> [!NOTE]\n> {safe_citizen_metrics['sample_warning']}\n")
        else:
            locs = safe_citizen_metrics.get("locality_distribution", {})
            if locs:
                lines.append("**Top Reporting Localities (Citizen Feedback)**:")
                for loc, count in locs.items():
                    lines.append(f"- {loc}: {count} submissions")
                lines.append("")

        # Sentiments
        lines.append("#### 2. Observed Public Sentiment Breakdown")
        if sentiment_counter:
            for s_label, count in sentiment_counter.items():
                pct = round((count / max(analyses_count, 1)) * 100, 1)
                lines.append(f"- **{s_label.title()}**: {count} ({pct}%)")
        else:
            lines.append("- *No sentiment distribution observed for the selected period.*")
        lines.append("")

        # Themes
        lines.append("#### 3. Recurring Civic Themes")
        if theme_counter:
            for t_label, count in theme_counter.items():
                lines.append(f"- **{t_label}**: {count} records")
        else:
            lines.append("- *No distinct themes detected in current dataset.*")
        lines.append("")

        # Trend explanation
        lines.append("#### 4. Activity Volume & Observed Trajectory")
        lines.append(
            f"- Observed volume trajectory is **{trend_direction}** over the last {period_days} days "
            f"(current: {sources_count} records vs {past_sources_count} in previous comparable window)."
        )
        lines.append(
            "> [!IMPORTANT]\n"
            "> An observed change in data volume reflects shifts in recorded public and citizen commentary "
            "within our collection scope, and does NOT constitute proof of ground-level causal changes or definitive city-wide trends."
        )
        lines.append("")

        # Top complaints
        if complaints_list:
            lines.append("#### 5. Sample Grounded Citizen Complaints")
            for c in complaints_list:
                src_link = f" ([Source Link]({c['source_url']}))" if c.get("source_url") else ""
                lines.append(f"- *\"{c['complaint']}\"*{src_link} — Category: {c['theme']}")
            lines.append("")

        # Top suggestions
        if suggestions_list:
            lines.append("#### 6. Actionable Community Suggestions")
            for s in suggestions_list:
                src_link = f" ([Source Link]({s['source_url']}))" if s.get("source_url") else ""
                lines.append(f"- *\"{s['suggestion']}\"*{src_link} — Category: {s['theme']}")
            lines.append("")

        return "\n".join(lines)

    def _build_recommendations(
        self,
        topic: str,
        dept_mapping: Any,
        theme_counter: Counter,
        suggestions_list: list[dict[str, str]],
        complaints_count: int,
    ) -> str:
        """Generates pragmatic administrative recommendations grounded in recorded evidence."""
        lines: list[str] = [
            f"Administrative action plan recommended for {dept_mapping.department_name}:",
            "",
            f"1. **Inspection and Ground Verification**: Dispatch field engineering / sanitary inspection teams to inspect reported locations under {dept_mapping.authority_name}.",
        ]

        if theme_counter:
            top_theme = theme_counter.most_common(1)[0][0]
            lines.append(
                f"2. **Targeted Remediation for High-Frequency Theme**: Prioritize resources toward '{top_theme}', which represents the largest share of public concerns in this reporting cycle."
            )
        else:
            lines.append(
                "2. **Thematic Resource Allocation**: Align grievance redressal teams to focus on core recurring issues identified in citizen feedback."
            )

        if suggestions_list:
            top_sugg = suggestions_list[0]["suggestion"]
            lines.append(
                f"3. **Community Proposal Feasibility Review**: Evaluate citizen-suggested intervention: \"{top_sugg}\" for incorporation into the upcoming ward maintenance schedule."
            )
        else:
            lines.append(
                "3. **Public Grievance Channel Communication**: Issue an advisory via official portal channels outlining current maintenance schedules and remediation timelines."
            )

        lines.append(
            f"4. **Inter-Agency Coordination**: Maintain cross-department sync between {dept_mapping.authority_name} and adjacent utilities (e.g., BESCOM, BWSSB) to prevent utility cut and road repair conflicts."
        )

        return "\n".join(lines)

    def _build_limitations(
        self,
        sources_count: int,
        citizen_count: int,
        dept_mapping: Any,
    ) -> str:
        """States explicit methodology limitations, sample size warnings, and privacy safeguards."""
        warnings: list[str] = []

        if sources_count < 5:
            warnings.append(
                f"Low public-source sample size warning: Only {sources_count} public records were available for this period. Findings represent indicative feedback rather than statistically conclusive public opinion."
            )
        if citizen_count < 3:
            warnings.append(
                f"Privacy and small sample suppression: Only {citizen_count} direct citizen submissions recorded. Detailed locality breakdowns have been suppressed to protect contributor anonymity."
            )
        if not dept_mapping.is_verified:
            warnings.append(
                "Department mapping verification warning: The responsible department could not be verified against an official government directory. Automated dispatch is disabled; an authorized reviewer must manually assign and verify the recipient."
            )

        warnings.append(
            "Demographic and digital coverage limits: Analyzed records originate from public internet sources (Bluesky, YouTube, indexed web sources) and opt-in citizen submissions. Findings do not represent non-digital residents or communities without internet access."
        )
        warnings.append(
            "Analytical uncertainty: Natural language categorization and sentiment extraction are performed by automated intelligence and may contain interpretive uncertainty. All findings require human official review prior to policy or administrative action."
        )

        return "\n\n".join(f"- {w}" for w in warnings)
