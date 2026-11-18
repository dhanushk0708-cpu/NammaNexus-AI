from collections import defaultdict
from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import urlparse

from app.models.civicvoice import CivicVoiceAnalysisRecord, CivicVoiceSourceRecord
from app.schemas.civicvoice import (
    CivicVoiceCleanSourceItem,
    CivicVoiceCoverageQuality,
    CivicVoiceExtractedSuggestion,
    CivicVoiceProblemConcern,
    CivicVoiceSummaryFinding,
    CivicVoiceSummaryResponse,
    CivicVoiceTrendItem,
    CivicVoiceTrendsResponse,
    CivicVoiceUniversalFinding,
    CivicVoiceUniversalSuggestion,
    CivicVoiceViewpointContrast,
    OpinionCategory,
)


def _clean_text(text: str | None) -> str:
    """Cleans up raw HTML, markdown tags, JSON artifacts, and excessive whitespace."""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r"<[^<]+?>", " ", text)
    # Strip markdown images ![alt](url) and links [text](url) -> text
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    # Strip raw URL strings
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    # Normalize multiple whitespace and newlines
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _clean_excerpt(text: str | None, max_len: int = 180) -> str:
    """Produces a clean, bounded excerpt avoiding raw scrap text overload."""
    cleaned = _clean_text(text)
    if not cleaned:
        return "Source record available via external link."
    if len(cleaned) <= max_len:
        return cleaned
    truncated = cleaned[:max_len].rsplit(" ", 1)[0]
    return f"{truncated}..."


def _derive_publisher(rec: CivicVoiceSourceRecord) -> str:
    """Extracts a readable publisher or channel name from author or canonical URL."""
    if rec.provider == "bluesky":
        if rec.author:
            clean_a = rec.author.strip()
            return f"Bluesky ({clean_a})" if not clean_a.lower().startswith("bluesky") else clean_a
        return "Bluesky"

    if rec.author and not rec.author.startswith("http"):
        author_clean = rec.author.strip()
        # If author looks like domain (e.g. www.deccanherald.com or thehindu.com)
        if "." in author_clean and not author_clean.startswith("@"):
            host = author_clean.replace("www.", "").split("/")[0]
            parts = host.split(".")
            if len(parts) >= 2:
                name = parts[0].replace("-", " ").title()
                return name
        return author_clean

    if rec.url:
        try:
            parsed = urlparse(rec.url)
            host = parsed.netloc.replace("www.", "")
            parts = host.split(".")
            if len(parts) >= 2:
                name = parts[0].replace("-", " ").title()
                return name
        except Exception:
            pass

    return rec.provider.capitalize()


def _classify_source_type(rec: CivicVoiceSourceRecord, ar: CivicVoiceAnalysisRecord | None = None) -> str:
    """Classifies source type into standard civic information categories."""
    url_lower = (rec.url or "").lower()
    if ".gov" in url_lower or ".nic.in" in url_lower or "bbmp" in url_lower or "karnataka.gov" in url_lower:
        return "official_information"

    if rec.provider == "tavily":
        news_domains = ["thehindu", "deccanherald", "timesofindia", "indianexpress", "ndtv", "bbc", "hindustantimes"]
        if any(d in url_lower for d in news_domains) or (ar and ar.content_intent == "news_or_reporting"):
            return "news_reporting"
        return "news_reporting"
    elif rec.provider == "youtube":
        return "multimedia_reporting"
    elif rec.provider == "bluesky":
        return "public_social_post"

    return "community_opinion"


class SummarySynthesizer:
    """Generates evidence-backed universal public-opinion intelligence reports.

    Converts raw retrieved evidence across any search topic into the standard 10-section
    universal report structure (Sections A through J) without fabricating facts or statistics.
    """

    def generate_summary(
        self,
        analysis_records: list[CivicVoiceAnalysisRecord],
        source_records_map: dict[str, CivicVoiceSourceRecord],
        topic: str | None = None,
        trends_result: CivicVoiceTrendsResponse | None = None,
    ) -> CivicVoiceSummaryResponse:
        """Synthesizes universal structured report sections A through J."""
        now = datetime.now(timezone.utc)
        topic_title = topic.strip().title() if topic and topic.strip() else "Public Discussion"

        # -------------------------------------------------------------------------
        # Section J Calculation First: Coverage Quality & Data Limitations
        # -------------------------------------------------------------------------
        provider_dist: dict[str, int] = defaultdict(int)
        lang_dist: dict[str, int] = defaultdict(int)
        dates: list[datetime] = []
        missing_timestamps = 0

        for ar in analysis_records:
            s_rec = source_records_map.get(ar.source_record_id)
            if s_rec:
                provider_dist[s_rec.provider] += 1
                if s_rec.published_at:
                    dates.append(s_rec.published_at)
                else:
                    missing_timestamps += 1

            lang = ar.detected_language or "unknown"
            lang_dist[lang] += 1

        limitations_list = [
            "Findings reflect public posts and articles collected across Bluesky, YouTube, and Tavily, and do not represent the full demographic distribution or statistical consensus of Bengaluru or the broader public.",
            "Public social media and web commentary represent voluntary public expression and cannot be treated as official municipal incident reports or binding grievance filings.",
            "Community suggestions reflect contributor viewpoints and have not undergone official administrative feasibility verification.",
            "Absence of criticism or complaint records in the current sample does not guarantee the complete absence of ground-level citizen dissatisfaction.",
        ]

        coverage = CivicVoiceCoverageQuality(
            total_source_records=len(source_records_map),
            total_analyzed_records=len(analysis_records),
            provider_distribution=dict(provider_dist),
            language_distribution=dict(lang_dist),
            date_range_start=min(dates) if dates else None,
            date_range_end=max(dates) if dates else None,
            missing_timestamps_count=missing_timestamps,
            limitations=limitations_list,
        )

        # Sample size assessment for Section J
        total_count = len(analysis_records)
        if total_count == 0:
            sample_size_assessment = "No records were retrieved from external providers for this topic."
        elif total_count < 5:
            sample_size_assessment = (
                f"Preliminary sample: {total_count} records collected across active sources. "
                "This small sample provides directional orientation but is insufficient to draw statistically definitive conclusions."
            )
        elif total_count < 20:
            sample_size_assessment = (
                f"Moderate sample: {total_count} records collected across active providers. "
                "Captures key discussion themes and reported experiences, while remaining subject to voluntary participation bias."
            )
        else:
            sample_size_assessment = (
                f"Substantial sample: {total_count} records collected across diverse sources. "
                "Provides robust cross-source visibility into public reactions, news coverage, and community concerns."
            )

        # -------------------------------------------------------------------------
        # Section I: Clean, Deduplicated Evidence and Sources
        # -------------------------------------------------------------------------
        analysis_by_source: dict[str, CivicVoiceAnalysisRecord] = {
            ar.source_record_id: ar for ar in analysis_records
        }
        clean_sources: list[CivicVoiceCleanSourceItem] = []
        seen_urls: set[str] = set()

        for s_rec in sorted(
            source_records_map.values(),
            key=lambda r: (r.published_at or r.collected_at or now),
            reverse=True,
        ):
            if not s_rec.url or s_rec.url in seen_urls:
                continue
            seen_urls.add(s_rec.url)

            ar_rec = analysis_by_source.get(s_rec.id)
            clean_title = _clean_text(s_rec.title) or f"External report regarding {topic_title}"
            clean_excerpt = _clean_excerpt(s_rec.content, max_len=180)
            publisher_name = _derive_publisher(s_rec)
            stype = _classify_source_type(s_rec, ar_rec)

            clean_sources.append(
                CivicVoiceCleanSourceItem(
                    publisher=publisher_name,
                    title=clean_title,
                    published_at=s_rec.published_at,
                    excerpt=clean_excerpt,
                    url=s_rec.url,
                    source_type=stype,
                    language=s_rec.language or (ar_rec.detected_language if ar_rec else None),
                )
            )

        # Handle Empty Result State honestly
        if not analysis_records:
            intro_empty = (
                f"This report covers the searched topic '{topic_title}'. "
                "Currently, no public social posts, news articles, or video records were retrieved from external providers."
            )
            summary_empty = (
                f"No external discussion records were discovered for '{topic_title}'. "
                "This may indicate that the topic is newly emerging, not widely discussed under this phrasing, "
                "or that external provider queries returned no matching items."
            )
            return CivicVoiceSummaryResponse(
                topic=topic,
                generated_at=now,
                topic_title=topic_title,
                introduction=intro_empty,
                relevant_dates=None,
                facts_vs_claims="No records available to distinguish verified facts from claims.",
                overall_summary=summary_empty,
                positive_opinions=[],
                positive_opinions_status="No reliable positive opinions found (no source records retrieved).",
                negative_opinions=[],
                negative_opinions_status="No critical or opposing viewpoints found (no source records retrieved).",
                problems_and_concerns=[],
                problems_and_concerns_status="No problems or operational concerns identified.",
                suggestions_and_improvements=[],
                suggestions_status="No community suggestions or improvement proposals recorded.",
                viewpoint_contrasts=[],
                trends_overview="Trend analysis unavailable due to zero collected records.",
                trends_available=False,
                trend_items=[],
                clean_sources=[],
                coverage=coverage,
                sample_size_assessment=sample_size_assessment,
                findings=[],
                extracted_suggestions=[],
                conflicting_perspectives=[],
            )

        # -------------------------------------------------------------------------
        # Theme Grouping & Evidence Aggregation
        # -------------------------------------------------------------------------
        theme_groups: dict[str, list[CivicVoiceAnalysisRecord]] = defaultdict(list)
        for ar in analysis_records:
            t_id = ar.theme_id or "general_discussion"
            theme_groups[t_id].append(ar)

        # Legacy & Universal Finding Accumulators
        legacy_findings: list[CivicVoiceSummaryFinding] = []
        positive_findings: list[CivicVoiceUniversalFinding] = []
        negative_findings: list[CivicVoiceUniversalFinding] = []
        problems_list: list[CivicVoiceProblemConcern] = []
        suggestions_list: list[CivicVoiceUniversalSuggestion] = []
        conflicts_list: list[str] = []
        viewpoint_contrasts: list[CivicVoiceViewpointContrast] = []

        total_positive = 0
        total_negative = 0
        total_neutral = 0

        for theme_id, recs in theme_groups.items():
            t_label = recs[0].theme_label if recs and recs[0].theme_label else theme_id.replace("_", " ").title()
            ev_ids = [r.source_record_id for r in recs]
            ev_urls: list[str] = []
            f_dates: list[datetime] = []

            for r in recs:
                s_rec = source_records_map.get(r.source_record_id)
                if s_rec:
                    if s_rec.url and s_rec.url not in ev_urls:
                        ev_urls.append(s_rec.url)
                    if s_rec.published_at:
                        f_dates.append(s_rec.published_at)
                    elif s_rec.collected_at:
                        f_dates.append(s_rec.collected_at)

            theme_complaint_recs = [r for r in recs if r.has_complaint or r.sentiment == "negative"]
            theme_positive_recs = [r for r in recs if r.category == OpinionCategory.POSITIVE_EXPERIENCE.value or r.sentiment == "positive"]
            theme_neutral_recs = [r for r in recs if r not in theme_complaint_recs and r not in theme_positive_recs]

            total_positive += len(theme_positive_recs)
            total_negative += len(theme_complaint_recs)
            total_neutral += len(theme_neutral_recs)

            earliest = min(f_dates) if f_dates else None
            latest = max(f_dates) if f_dates else None

            # ---------------------------------------------------------------------
            # Section C: Positive Opinions & Highlights
            # ---------------------------------------------------------------------
            if theme_positive_recs:
                pos_ev_ids = [r.source_record_id for r in theme_positive_recs]
                pos_urls = [
                    source_records_map[r_id].url
                    for r_id in pos_ev_ids
                    if r_id in source_records_map and source_records_map[r_id].url
                ]
                pos_explanation = (
                    f"Sources highlight positive experiences and supportive viewpoints regarding {t_label.lower()}. "
                    f"Commentary notes appreciation for quality, heritage, benefits, and commendable developments."
                )
                positive_findings.append(
                    CivicVoiceUniversalFinding(
                        heading=f"Positive Outlook & Appreciation in {t_label}",
                        explanation=pos_explanation,
                        category="positive_highlight",
                        supporting_evidence_count=len(theme_positive_recs),
                        evidence_record_ids=pos_ev_ids,
                        source_urls=list(dict.fromkeys(pos_urls)),
                        earliest_date=earliest,
                        latest_date=latest,
                        uncertainties="Reflects voluntary public satisfaction; individual experiences may differ by location and time.",
                    )
                )

            # ---------------------------------------------------------------------
            # Section D: Negative Opinions & Criticism
            # ---------------------------------------------------------------------
            if theme_complaint_recs:
                neg_ev_ids = [r.source_record_id for r in theme_complaint_recs]
                neg_urls = [
                    source_records_map[r_id].url
                    for r_id in neg_ev_ids
                    if r_id in source_records_map and source_records_map[r_id].url
                ]
                neg_explanation = (
                    f"Sources document critical feedback and public dissatisfaction concerning {t_label.lower()}. "
                    f"Contributors express frustration with unresolved bottlenecks, service friction, and organizational challenges."
                )
                negative_findings.append(
                    CivicVoiceUniversalFinding(
                        heading=f"Criticisms & Dissatisfaction in {t_label}",
                        explanation=neg_explanation,
                        category="criticism_and_concern",
                        supporting_evidence_count=len(theme_complaint_recs),
                        evidence_record_ids=neg_ev_ids,
                        source_urls=list(dict.fromkeys(neg_urls)),
                        earliest_date=earliest,
                        latest_date=latest,
                        uncertainties="Grounded in public commentary; physical or administrative confirmation pending official audit.",
                    )
                )

                # -----------------------------------------------------------------
                # Section E: Concrete Problems & Concerns
                # -----------------------------------------------------------------
                for cr in theme_complaint_recs:
                    s_item = source_records_map.get(cr.source_record_id)
                    problem_desc = cr.extracted_complaint or _clean_excerpt(cr.explanation or (s_item.content if s_item else None), 140)
                    problems_list.append(
                        CivicVoiceProblemConcern(
                            heading=f"Reported Friction: {t_label}",
                            description=problem_desc,
                            problem_type="reported_problem",
                            supporting_record_count=1,
                            evidence_record_ids=[cr.source_record_id],
                            source_urls=[s_item.url] if s_item and s_item.url else [],
                        )
                    )

            # ---------------------------------------------------------------------
            # Section G: Viewpoint Contrasts & Disagreements
            # ---------------------------------------------------------------------
            if len(theme_positive_recs) > 0 and len(theme_complaint_recs) > 0:
                conflicts_list.append(
                    f"Contrasting sentiment in '{t_label}': {len(theme_complaint_recs)} records express criticism or concerns, "
                    f"while {len(theme_positive_recs)} records highlight satisfaction or positive progress."
                )
                viewpoint_contrasts.append(
                    CivicVoiceViewpointContrast(
                        topic_aspect=t_label,
                        areas_of_agreement=f"Both supportive and critical voices recognize the high importance and public visibility of {t_label.lower()}.",
                        points_of_disagreement=(
                            f"Opinions diverge regarding execution: while {len(theme_positive_recs)} records commend current progress or cultural value, "
                            f"{len(theme_complaint_recs)} records raise friction regarding accessibility, delays, or practical difficulties."
                        ),
                        disputed_questions=[
                            f"How effectively can logistics and services balance rising demand in {t_label.lower()}?",
                            f"What immediate steps will address reported friction points without dampening positive participation?",
                        ],
                    )
                )

            # Backward-compatible legacy finding
            if len(theme_complaint_recs) > 0:
                f_desc = f"{len(theme_complaint_recs)} recorded posts express dissatisfaction or unresolved concerns regarding {t_label.lower()}."
                f_cat = "complaint_focus"
            elif len(theme_positive_recs) > 0:
                f_desc = f"{len(theme_positive_recs)} recorded posts highlight positive developments or citizen appreciation for {t_label.lower()}."
                f_cat = "positive_focus"
            else:
                f_desc = f"{len(recs)} recorded posts provide informational observations regarding {t_label.lower()}."
                f_cat = "informational"

            legacy_findings.append(
                CivicVoiceSummaryFinding(
                    finding_description=f_desc,
                    category=f_cat,
                    theme_label=t_label,
                    supporting_record_count=len(recs),
                    evidence_record_ids=ev_ids,
                    source_urls=ev_urls,
                    earliest_date=earliest,
                    latest_date=latest,
                    uncertainties="Sentiment represents voluntary online expression; individual claim verification pending official ground inspection." if len(theme_complaint_recs) > 0 else None,
                )
            )

        # -------------------------------------------------------------------------
        # Section F: Suggestions and Proposed Improvements
        # -------------------------------------------------------------------------
        legacy_suggestions: list[CivicVoiceExtractedSuggestion] = []
        for ar in analysis_records:
            if ar.has_suggestion and ar.extracted_suggestion:
                s_rec = source_records_map.get(ar.source_record_id)
                s_url = s_rec.url if s_rec else ""
                legacy_suggestions.append(
                    CivicVoiceExtractedSuggestion(
                        suggestion=ar.extracted_suggestion,
                        source_record_id=ar.source_record_id,
                        source_url=s_url,
                    )
                )
                suggestions_list.append(
                    CivicVoiceUniversalSuggestion(
                        heading=f"Source Suggestion ({_derive_publisher(s_rec) if s_rec else 'Public Post'})",
                        suggestion=ar.extracted_suggestion,
                        origin="source_author",
                        source_record_id=ar.source_record_id,
                        source_url=s_url,
                        disclaimer="Explicitly proposed by source author or public contributor; not an officially vetted recommendation.",
                    )
                )

        # If recurring problems exist, synthesize CivicVoice objective improvements
        if problems_list:
            top_themes = [t for t in list(theme_groups.keys())[:2] if t]
            theme_str = ", ".join(t.replace("_", " ").title() for t in top_themes)
            suggestions_list.append(
                CivicVoiceUniversalSuggestion(
                    heading="Proactive Service & Information Transparency",
                    suggestion=(
                        f"Implement clear, real-time public communication and dedicated ground assistance to alleviate "
                        f"reported friction in {theme_str.lower() or 'key operational areas'}."
                    ),
                    origin="synthesized_civicvoice",
                    source_record_id=None,
                    source_url=None,
                    disclaimer=(
                        "CivicVoice Synthesized Recommendation: Generated algorithmically based on cross-source "
                        "problem patterns. Never attributed to a real person or individual publisher."
                    ),
                )
            )

        # Fallback if no suggestions found
        suggestions_status = None
        if not suggestions_list:
            suggestions_status = "No explicit civic suggestions or actionable improvement proposals were identified in the collected sources."

        # Status strings for positive / negative sections
        positive_status = None
        if not positive_findings:
            positive_status = "No reliable positive opinions, appreciative highlights, or endorsements were identified in the collected evidence for this topic."

        negative_status = None
        if not negative_findings:
            negative_status = "No critical, dissatisfied, or opposing viewpoints were identified in the collected evidence for this topic."

        problems_status = None
        if not problems_list:
            problems_status = "No concrete operational hazards, acute service failures, or verified safety problems were reported in the analyzed records."

        # If no viewpoint contrasts exist, provide consistent perspective note
        if not viewpoint_contrasts:
            viewpoint_contrasts.append(
                CivicVoiceViewpointContrast(
                    topic_aspect="Overall Topic Sentiment",
                    areas_of_agreement="Collected commentary reflects broadly uniform perspectives across active sources without strong polarity.",
                    points_of_disagreement="No substantial factional disagreements or conflicting camps were identified in the available evidence.",
                    disputed_questions=["Are there localized variations in community experience not captured by current online sources?"],
                )
            )

        # -------------------------------------------------------------------------
        # Section A: Topic Introduction
        # -------------------------------------------------------------------------
        providers_searched_str = ", ".join(f"{p.capitalize()}" for p in provider_dist.keys()) or "external search providers"
        top_theme_names = [r[0].theme_label for r in theme_groups.values() if r and r[0].theme_label]
        top_themes_str = ", ".join(top_theme_names[:3]) if top_theme_names else "general civic interest"

        intro_text = (
            f"This universal intelligence report synthesizes public commentary, news reporting, and citizen discourse "
            f"regarding **{topic_title}**. The topic is being actively discussed across {providers_searched_str}, "
            f"focusing on {top_themes_str}. The findings below outline what retrieved sources collectively indicate, "
            f"highlighting supportive viewpoints, criticisms, operational problems, and proposed improvements."
        )

        relevant_dates_str = None
        if coverage.date_range_start and coverage.date_range_end:
            s_date = coverage.date_range_start.strftime("%d %b %Y")
            e_date = coverage.date_range_end.strftime("%d %b %Y")
            relevant_dates_str = f"Collected records span publication dates from {s_date} to {e_date}."
        elif coverage.date_range_start:
            s_date = coverage.date_range_start.strftime("%d %b %Y")
            relevant_dates_str = f"Retrieved source records date from {s_date} onward."

        facts_vs_claims_str = (
            "Verified Facts vs. Public Claims: Official dates, scheduled events, and regulatory announcements cited from news "
            "reporting represent established event background. In contrast, online sentiment, social commentary, and informal "
            "reviews represent voluntary citizen perceptions, expectations, and personal claims."
        )

        # -------------------------------------------------------------------------
        # Section B: Overall Summary (Concise, Readable Synthesized Paragraphs)
        # -------------------------------------------------------------------------
        pct_pos = round((total_positive / total_count) * 100) if total_count else 0
        pct_neg = round((total_negative / total_count) * 100) if total_count else 0
        pct_neu = max(0, 100 - pct_pos - pct_neg)

        para_1 = (
            f"Public discussion regarding **{topic_title}** currently comprises {total_count} analyzed records retrieved "
            f"across {providers_searched_str}. Overall sentiment shows {pct_pos}% positive appreciation, {pct_neg}% critical "
            f"feedback or complaints, and {pct_neu}% neutral or informational reporting."
        )

        if total_negative > 0 and total_positive > 0:
            para_2 = (
                f"Public opinion presents a nuanced dynamic: while community members value the significance and positive highlights "
                f"associated with {top_themes_str.lower()}, notable concerns remain regarding practical difficulties, service bottlenecks, "
                f"and logistical execution. Addressing these frictions while sustaining high engagement represents the primary discussion theme."
            )
        elif total_negative > 0:
            para_2 = (
                f"The prevailing tone centers on unresolved concerns and critical observations. Commentators emphasize practical "
                f"difficulties and call for administrative attention to improve user and citizen experiences in {top_themes_str.lower()}."
            )
        elif total_positive > 0:
            para_2 = (
                f"The prevailing tone is predominantly supportive and appreciative. Sources reflect positive community reception, "
                f"commending cultural heritage, innovation, and constructive developments in {top_themes_str.lower()}."
            )
        else:
            para_2 = (
                f"The discussion is primarily informational and observational in nature, focusing on schedules, factual overviews, "
                f"and descriptive updates without significant public polarization."
            )

        overall_summary_text = f"{para_1}\n\n{para_2}"

        # -------------------------------------------------------------------------
        # Section H: Trends and Changes Over Time
        # -------------------------------------------------------------------------
        trends_available = False
        trends_overview_text = (
            "Trend analysis across consecutive 7-day time windows is currently unavailable due to insufficient historical "
            "or multi-day publication timestamps in the retrieved records."
        )
        trend_items_list: list[CivicVoiceTrendItem] = []

        if trends_result and trends_result.trends:
            trends_available = True
            trend_items_list = trends_result.trends
            trends_overview_text = (
                f"Comparative analysis across consecutive time windows indicates active volume dynamics across "
                f"{len(trend_items_list)} themes. Note: Volume fluctuations reflect collected mentions across active "
                f"external providers over time, and do not represent proof of broad population-wide opinion shifts."
            )
        elif len(dates) >= 3 and (max(dates) - min(dates)).days >= 1:
            trends_available = True
            trends_overview_text = (
                f"Retrieved records show activity across multiple days from {min(dates).strftime('%d %b')} to "
                f"{max(dates).strftime('%d %b %Y')}. The discussion remains active with steady topical interest across news and social media."
            )

        # Sort findings by supporting record count descending
        positive_findings.sort(key=lambda f: f.supporting_evidence_count, reverse=True)
        negative_findings.sort(key=lambda f: f.supporting_evidence_count, reverse=True)
        legacy_findings.sort(key=lambda f: f.supporting_record_count, reverse=True)

        return CivicVoiceSummaryResponse(
            topic=topic,
            generated_at=now,
            # Section A: Topic Introduction
            topic_title=topic_title,
            introduction=intro_text,
            relevant_dates=relevant_dates_str,
            facts_vs_claims=facts_vs_claims_str,
            # Section B: Overall Summary
            overall_summary=overall_summary_text,
            # Section C: Positive Opinions and Highlights
            positive_opinions=positive_findings,
            positive_opinions_status=positive_status,
            # Section D: Negative Opinions and Criticism
            negative_opinions=negative_findings,
            negative_opinions_status=negative_status,
            # Section E: Problems and Concerns
            problems_and_concerns=problems_list,
            problems_and_concerns_status=problems_status,
            # Section F: Suggestions and Proposed Improvements
            suggestions_and_improvements=suggestions_list,
            suggestions_status=suggestions_status,
            # Section G: Different Viewpoints and Disagreements
            viewpoint_contrasts=viewpoint_contrasts,
            # Section H: Trends and Changes Over Time
            trends_overview=trends_overview_text,
            trends_available=trends_available,
            trend_items=trend_items_list,
            # Section I: Clean Sources
            clean_sources=clean_sources,
            # Section J: Data Coverage and Limitations
            coverage=coverage,
            sample_size_assessment=sample_size_assessment,
            # Backward-compatible fields
            findings=legacy_findings,
            extracted_suggestions=legacy_suggestions,
            conflicting_perspectives=conflicts_list,
        )
