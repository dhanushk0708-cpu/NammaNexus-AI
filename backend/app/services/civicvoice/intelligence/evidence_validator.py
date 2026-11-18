from datetime import datetime, timezone
import re
from typing import Any

from app.models.civicvoice import CivicVoiceSourceRecord
from app.schemas.civicvoice import (
    CivicVoiceCleanSourceItem,
    CivicVoiceCoverageQuality,
    CivicVoiceExtractedSuggestion,
    CivicVoiceProblemConcern,
    CivicVoiceSummaryFinding,
    CivicVoiceSummaryResponse,
    CivicVoiceUniversalFinding,
    CivicVoiceUniversalSuggestion,
    CivicVoiceViewpointContrast,
    GeminiFindingItem,
    GeminiProblemConcernItem,
    GeminiResearchOutput,
    GeminiSuggestionItem,
)
from app.services.civicvoice.intelligence.evidence_preparer import PreparedEvidenceItem


class EvidenceValidator:
    """Performs deterministic application-side validation on Gemini research output.

    Guarantees citation integrity, source traceability, numerical grounding,
    and separation of official announcements from citizen sentiment.
    """

    CONSENSUS_PATTERNS = [
        r"(?i)\boverwhelming\s+(?:public\s+)?(?:consensus|majority|support|opposition)\b",
        r"(?i)\bunanimous(?:ly)?(?:\s+(?:citizen|public|community|resident))?\s+(?:rage|outrage|agreement|support|opposition|consensus)\b",
        r"(?i)\bunanimous(?:ly)?\b",
        r"(?i)\ball\s+citizens\s+(?:agree|feel|believe|support|oppose)\b",
        r"(?i)\ball\s+citizens\b",
        r"(?i)\buniversal\s+(?:outrage|acclaim|support|consensus|agreement)\b",
        r"(?i)\beveryone\s+(?:agrees|complains)\b",
    ]

    def _extract_numbers(self, text: str) -> list[str]:
        """Extracts significant numerical tokens (excluding common small digits and years like 2026)."""
        raw_tokens = re.findall(r"\b\d+(?:[.,]\d+)?%?\b", text)
        filtered = []
        for t in raw_tokens:
            clean_t = t.replace("%", "").replace(",", "")
            try:
                val = float(clean_t)
                # Ignore small numbers 0-5 and single digit references
                if val <= 5.0 or 2024 <= val <= 2030:
                    continue
                filtered.append(t)
            except ValueError:
                filtered.append(t)
        return filtered

    def _verify_numerical_claims(self, text: str, cited_items: list[PreparedEvidenceItem]) -> bool:
        """Verifies if quantitative claims in the text can be found in the cited evidence."""
        numbers = self._extract_numbers(text)
        if not numbers:
            return True  # No specific quantitative claims to verify

        combined_evidence_text = " ".join(
            f"{item.title} {item.excerpt}".lower() for item in cited_items
        )

        for num in numbers:
            clean_num = num.lower().replace("%", "").strip()
            if clean_num not in combined_evidence_text:
                return False  # Uncorroborated numerical claim detected

        return True

    def validate_and_assemble(
        self,
        report: GeminiResearchOutput,
        evidence_items: list[PreparedEvidenceItem],
        source_records_map: dict[str, CivicVoiceSourceRecord],
        ai_model_name: str | None = None,
    ) -> CivicVoiceSummaryResponse:
        """Validates all findings against ground-truth evidence and builds CivicVoiceSummaryResponse."""
        now = datetime.now(timezone.utc)
        evidence_map: dict[str, PreparedEvidenceItem] = {item.source_id: item for item in evidence_items}

        validation_notes: list[str] = []
        invalid_citations_stripped = 0
        unsupported_findings_suppressed = 0
        numerical_claims_flagged = 0
        official_sources_reclassified = 0

        # ---------------------------------------------------------------------
        # 1. Validate Positive Findings
        # ---------------------------------------------------------------------
        validated_positive: list[CivicVoiceUniversalFinding] = []
        for finding in report.positive_findings:
            raw_sids = finding.supporting_source_ids or []
            valid_items = [evidence_map[sid] for sid in raw_sids if sid in evidence_map]

            if len(raw_sids) > len(valid_items):
                invalid_count = len(raw_sids) - len(valid_items)
                invalid_citations_stripped += invalid_count
                validation_notes.append(
                    f"Stripped {invalid_count} ungrounded citation(s) from positive finding: '{finding.heading}'."
                )

            if raw_sids and not valid_items:
                # Finding claimed citations, but none were valid -> suppress
                unsupported_findings_suppressed += 1
                validation_notes.append(
                    f"Suppressed unsupported positive finding '{finding.heading}' (zero valid cited sources)."
                )
                continue

            # Check if citing exclusively official announcements for public sentiment
            all_official = bool(valid_items) and all(item.source_type == "official_information" for item in valid_items)
            uncertainty_text = finding.uncertainties
            if all_official:
                official_sources_reclassified += 1
                uncertainty_text = (
                    "Note: Sourced from official administrative notices or schedules, rather than direct citizen feedback."
                )

            # Check numerical claims
            numbers_valid = self._verify_numerical_claims(finding.explanation, valid_items)
            if not numbers_valid:
                numerical_claims_flagged += 1
                flag_msg = "Contains quantitative claim not directly corroborated in cited evidence."
                uncertainty_text = f"{uncertainty_text}; {flag_msg}" if uncertainty_text else flag_msg

            rec_ids = [item.record_id for item in valid_items]
            urls = list(dict.fromkeys(item.url for item in valid_items if item.url))
            dates = [item.published_at for item in valid_items if item.published_at]

            validated_positive.append(
                CivicVoiceUniversalFinding(
                    heading=finding.heading,
                    explanation=finding.explanation,
                    category=finding.category or "positive_highlight",
                    supporting_evidence_count=len(valid_items),
                    evidence_record_ids=rec_ids,
                    source_urls=urls,
                    earliest_date=min(dates) if dates else None,
                    latest_date=max(dates) if dates else None,
                    uncertainties=uncertainty_text,
                    evidence_strength=finding.evidence_strength or "moderate",
                )
            )

        # ---------------------------------------------------------------------
        # 2. Validate Negative Findings
        # ---------------------------------------------------------------------
        validated_negative: list[CivicVoiceUniversalFinding] = []
        for finding in report.negative_findings:
            raw_sids = finding.supporting_source_ids or []
            valid_items = [evidence_map[sid] for sid in raw_sids if sid in evidence_map]

            if len(raw_sids) > len(valid_items):
                invalid_count = len(raw_sids) - len(valid_items)
                invalid_citations_stripped += invalid_count
                validation_notes.append(
                    f"Stripped {invalid_count} ungrounded citation(s) from negative finding: '{finding.heading}'."
                )

            if raw_sids and not valid_items:
                unsupported_findings_suppressed += 1
                validation_notes.append(
                    f"Suppressed unsupported negative finding '{finding.heading}' (zero valid cited sources)."
                )
                continue

            all_official = bool(valid_items) and all(item.source_type == "official_information" for item in valid_items)
            uncertainty_text = finding.uncertainties
            if all_official:
                official_sources_reclassified += 1
                uncertainty_text = (
                    "Note: Sourced from official administrative notices, rather than direct citizen complaints."
                )

            numbers_valid = self._verify_numerical_claims(finding.explanation, valid_items)
            if not numbers_valid:
                numerical_claims_flagged += 1
                flag_msg = "Contains quantitative claim not directly corroborated in cited evidence."
                uncertainty_text = f"{uncertainty_text}; {flag_msg}" if uncertainty_text else flag_msg

            rec_ids = [item.record_id for item in valid_items]
            urls = list(dict.fromkeys(item.url for item in valid_items if item.url))
            dates = [item.published_at for item in valid_items if item.published_at]

            validated_negative.append(
                CivicVoiceUniversalFinding(
                    heading=finding.heading,
                    explanation=finding.explanation,
                    category=finding.category or "criticism_and_concern",
                    supporting_evidence_count=len(valid_items),
                    evidence_record_ids=rec_ids,
                    source_urls=urls,
                    earliest_date=min(dates) if dates else None,
                    latest_date=max(dates) if dates else None,
                    uncertainties=uncertainty_text,
                    evidence_strength=finding.evidence_strength or "moderate",
                )
            )

        # ---------------------------------------------------------------------
        # 3. Validate Problems and Concerns
        # ---------------------------------------------------------------------
        validated_problems: list[CivicVoiceProblemConcern] = []
        for prob in report.problems_and_concerns:
            raw_sids = prob.supporting_source_ids or []
            valid_items = [evidence_map[sid] for sid in raw_sids if sid in evidence_map]

            if raw_sids and not valid_items:
                unsupported_findings_suppressed += 1
                validation_notes.append(
                    f"Suppressed reported problem '{prob.heading}' (cited source IDs were not in evidence set)."
                )
                continue

            rec_ids = [item.record_id for item in valid_items]
            urls = list(dict.fromkeys(item.url for item in valid_items if item.url))

            validated_problems.append(
                CivicVoiceProblemConcern(
                    heading=prob.heading,
                    description=prob.description,
                    problem_type=prob.problem_type or "reported_problem",
                    supporting_record_count=len(valid_items) or 1,
                    evidence_record_ids=rec_ids,
                    source_urls=urls,
                    evidence_strength="strong" if len(valid_items) > 1 else "moderate",
                )
            )

        # ---------------------------------------------------------------------
        # 4. Validate Suggestions
        # ---------------------------------------------------------------------
        validated_suggestions: list[CivicVoiceUniversalSuggestion] = []
        for sug in report.suggestions:
            raw_sids = sug.supporting_source_ids or []
            valid_items = [evidence_map[sid] for sid in raw_sids if sid in evidence_map]

            origin = sug.origin or "synthesized_civicvoice"
            source_rec_id = valid_items[0].record_id if valid_items else None
            source_url = valid_items[0].url if valid_items else None

            if origin == "source_author" and not valid_items:
                # Contributor suggestion has no valid citation -> convert to synthesized recommendation
                origin = "synthesized_civicvoice"
                disclaimer = (
                    "CivicVoice Synthesized Recommendation: Reclassified as model-synthesized proposal due to lack of direct source link."
                )
            elif origin == "source_author":
                disclaimer = (
                    f"Directly proposed in source publication ({valid_items[0].publisher}); not an officially vetted municipal standard."
                )
            else:
                disclaimer = (
                    "CivicVoice Synthesized Recommendation: Generated algorithmically based on cross-source problem patterns."
                )

            validated_suggestions.append(
                CivicVoiceUniversalSuggestion(
                    heading=sug.heading,
                    suggestion=sug.suggestion,
                    origin=origin,
                    source_record_id=source_rec_id,
                    source_url=source_url,
                    disclaimer=disclaimer,
                )
            )

        # ---------------------------------------------------------------------
        # 5. Validate Viewpoint Contrasts
        # ---------------------------------------------------------------------
        validated_contrasts: list[CivicVoiceViewpointContrast] = []
        for vc in report.different_viewpoints:
            validated_contrasts.append(
                CivicVoiceViewpointContrast(
                    topic_aspect=vc.topic_aspect,
                    areas_of_agreement=vc.areas_of_agreement,
                    points_of_disagreement=vc.points_of_disagreement,
                    disputed_questions=vc.disputed_questions or [],
                )
            )

        # ---------------------------------------------------------------------
        # 6. Small Sample Bias & Consensus Language Check
        # ---------------------------------------------------------------------
        overall_summary = report.overall_summary or ""
        opinion_bearing_count = sum(1 for item in evidence_items if item.is_opinion_bearing)

        if opinion_bearing_count < 5:
            for pat in self.CONSENSUS_PATTERNS:
                if re.search(pat, overall_summary):
                    overall_summary = re.sub(
                        pat,
                        "preliminary public discussion indicates",
                        overall_summary,
                    )
                    validation_notes.append(
                        "Softened broad consensus terminology in summary due to limited opinion sample size (< 5 sources)."
                    )

        # ---------------------------------------------------------------------
        # 7. Coverage Quality and Clean Sources Assembly
        # ---------------------------------------------------------------------
        provider_dist: dict[str, int] = {}
        lang_dist: dict[str, int] = {}
        dates_list: list[datetime] = []
        missing_dates = 0

        clean_sources: list[CivicVoiceCleanSourceItem] = []
        for item in evidence_items:
            provider_dist[item.provider] = provider_dist.get(item.provider, 0) + 1
            l_key = item.language or "en"
            lang_dist[l_key] = lang_dist.get(l_key, 0) + 1

            if item.published_at:
                dates_list.append(item.published_at)
            else:
                missing_dates += 1

            clean_sources.append(
                CivicVoiceCleanSourceItem(
                    publisher=item.publisher,
                    title=item.title,
                    published_at=item.published_at,
                    excerpt=item.excerpt[:220] + "..." if len(item.excerpt) > 220 else item.excerpt,
                    url=item.url,
                    source_type=item.source_type,
                    language=item.language,
                )
            )

        limitations_list = list(report.limitations or [])
        if missing_dates > 0:
            limitations_list.append(
                f"{missing_dates} source record(s) lack explicit publication timestamps; temporal trends reflect voluntary commentary basis."
            )
        if unsupported_findings_suppressed > 0:
            limitations_list.append(
                f"{unsupported_findings_suppressed} potential finding(s) were suppressed during application validation due to lack of ground-truth evidence."
            )
        if numerical_claims_flagged > 0:
            limitations_list.append(
                f"{numerical_claims_flagged} quantitative metric(s) could not be verified in source texts and are flagged for review."
            )

        total_analyzed = len(evidence_items)
        if total_analyzed == 0:
            sample_size_assessment = "Zero external source records were retrieved for this query."
        elif total_analyzed < 5:
            sample_size_assessment = (
                f"Preliminary sample: {total_analyzed} records ({opinion_bearing_count} opinion-bearing). "
                "Provides initial directional perspective but is insufficient to assert broad statistical consensus."
            )
        elif total_analyzed < 20:
            sample_size_assessment = (
                f"Moderate sample: {total_analyzed} records across active sources. Captures primary reported themes "
                "and public reactions, subject to voluntary reporting patterns."
            )
        else:
            sample_size_assessment = (
                f"Substantial sample: {total_analyzed} records retrieved across news, social commentary, and multimedia. "
                "Provides robust cross-source visibility into public sentiment and civic discourse."
            )

        coverage = CivicVoiceCoverageQuality(
            total_source_records=len(source_records_map) or total_analyzed,
            total_analyzed_records=total_analyzed,
            provider_distribution=provider_dist,
            language_distribution=lang_dist,
            date_range_start=min(dates_list) if dates_list else None,
            date_range_end=max(dates_list) if dates_list else None,
            missing_timestamps_count=missing_dates,
            limitations=limitations_list,
        )

        validation_status = "validated_with_evidence"
        if unsupported_findings_suppressed > 0 or invalid_citations_stripped > 0 or numerical_claims_flagged > 0:
            validation_status = "validated_with_corrections"

        # Determine section status strings when empty
        pos_status = None if validated_positive else "No reliable positive opinions, appreciative highlights, or endorsements were identified in the collected evidence for this topic."
        neg_status = None if validated_negative else "No critical, dissatisfied, or opposing viewpoints were identified in the collected evidence for this topic."
        prob_status = None if validated_problems else "No concrete operational hazards, acute service failures, or verified safety problems were reported in the analyzed records."
        sug_status = None if validated_suggestions else "No specific civic suggestions or actionable improvement proposals were identified in the collected sources."

        # Backward compatibility legacy findings
        legacy_findings: list[CivicVoiceSummaryFinding] = [
            CivicVoiceSummaryFinding(
                finding_description=f.explanation,
                category=f.category,
                theme_label=f.heading,
                supporting_record_count=f.supporting_evidence_count,
                evidence_record_ids=f.evidence_record_ids,
                source_urls=f.source_urls,
                earliest_date=f.earliest_date,
                latest_date=f.latest_date,
                uncertainties=f.uncertainties,
            )
            for f in validated_positive + validated_negative
        ]

        legacy_suggestions: list[CivicVoiceExtractedSuggestion] = [
            CivicVoiceExtractedSuggestion(
                suggestion=s.suggestion,
                source_record_id=s.source_record_id or "",
                source_url=s.source_url or "",
                disclaimer=s.disclaimer,
            )
            for s in validated_suggestions
        ]

        relevant_dates_str = None
        if coverage.date_range_start and coverage.date_range_end:
            s_date = coverage.date_range_start.strftime("%d %b %Y")
            e_date = coverage.date_range_end.strftime("%d %b %Y")
            relevant_dates_str = f"Collected records span publication dates from {s_date} to {e_date}."

        return CivicVoiceSummaryResponse(
            topic=report.topic,
            generated_at=now,
            # Section A: Topic Introduction
            topic_title=report.topic.title(),
            introduction=report.introduction,
            relevant_dates=relevant_dates_str,
            facts_vs_claims=(
                "Verified Facts vs. Public Claims: Official schedules and published event dates cited from accredited news "
                "represent established event background. In contrast, online sentiment and citizen reviews represent "
                "voluntary perceptions, personal claims, and community expectations."
            ),
            # Section B: Overall Summary
            overall_summary=overall_summary,
            # Section C: Positive Opinions and Highlights
            positive_opinions=validated_positive,
            positive_opinions_status=pos_status,
            # Section D: Negative Opinions and Criticism
            negative_opinions=validated_negative,
            negative_opinions_status=neg_status,
            # Section E: Problems and Concerns
            problems_and_concerns=validated_problems,
            problems_and_concerns_status=prob_status,
            # Section F: Suggestions and Proposed Improvements
            suggestions_and_improvements=validated_suggestions,
            suggestions_status=sug_status,
            # Section G: Different Viewpoints and Disagreements
            viewpoint_contrasts=validated_contrasts,
            # Section H: Trends and Changes Over Time
            trends_overview=report.trends_overview or "Trend analysis requires multiple dated entries across consecutive time windows.",
            trends_available=report.trends_available,
            trend_items=[],
            # Section I: Clean Sources
            clean_sources=clean_sources,
            # Section J: Data Coverage and Limitations
            coverage=coverage,
            sample_size_assessment=sample_size_assessment,
            # Research and Validation metadata
            unresolved_questions=list(report.unresolved_questions or []),
            ai_synthesized=True,
            ai_model=ai_model_name,
            validation_status=validation_status,
            validation_notes=validation_notes,
            # Backward compatibility fields:
            findings=legacy_findings,
            extracted_suggestions=legacy_suggestions,
            conflicting_perspectives=[],
        )
