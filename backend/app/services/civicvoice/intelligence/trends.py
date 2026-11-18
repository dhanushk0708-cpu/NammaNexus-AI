from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.models.civicvoice import CivicVoiceAnalysisRecord, CivicVoiceSourceRecord
from app.schemas.civicvoice import CivicVoiceTrendItem, CivicVoiceTrendsResponse


class TrendAnalysisEngine:
    """Calculates time-window trends and emerging topics from actual collected records.

    Strictly compares equivalent time windows and reports limitations honestly.
    """

    def calculate_trends(
        self,
        analysis_records: list[CivicVoiceAnalysisRecord],
        source_records_map: dict[str, CivicVoiceSourceRecord],
        window_days: int = 7,
        as_of_time: datetime | None = None,
    ) -> CivicVoiceTrendsResponse:
        """Calculates volume differences across two equivalent successive time windows."""
        effective_window = max(1, min(window_days, 90))
        now = as_of_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        current_window_end = now
        current_window_start = current_window_end - timedelta(days=effective_window)
        previous_window_end = current_window_start
        previous_window_start = previous_window_end - timedelta(days=effective_window)

        current_theme_counts: dict[str, int] = defaultdict(int)
        previous_theme_counts: dict[str, int] = defaultdict(int)
        theme_labels: dict[str, str] = {}
        theme_evidence: dict[str, list[str]] = defaultdict(list)

        missing_pub_timestamps = 0

        for ar in analysis_records:
            theme_id = ar.theme_id or "general_civic"
            theme_labels[theme_id] = ar.theme_label or "General Civic"

            s_rec = source_records_map.get(ar.source_record_id)
            if not s_rec:
                continue

            rec_time = s_rec.published_at
            if not rec_time:
                missing_pub_timestamps += 1
                rec_time = s_rec.collected_at or ar.created_at

            if rec_time.tzinfo is None:
                rec_time = rec_time.replace(tzinfo=timezone.utc)

            # Classify into window
            if current_window_start <= rec_time <= current_window_end:
                current_theme_counts[theme_id] += 1
                theme_evidence[theme_id].append(ar.source_record_id)
            elif previous_window_start <= rec_time < previous_window_end:
                previous_theme_counts[theme_id] += 1
                if ar.source_record_id not in theme_evidence[theme_id]:
                    theme_evidence[theme_id].append(ar.source_record_id)

        all_theme_ids = set(current_theme_counts.keys()) | set(previous_theme_counts.keys())
        trends: list[CivicVoiceTrendItem] = []

        for tid in all_theme_ids:
            cur_count = current_theme_counts.get(tid, 0)
            prev_count = previous_theme_counts.get(tid, 0)
            diff = cur_count - prev_count

            if prev_count == 0 and cur_count >= 2:
                status = "new_observed_topic"
            elif prev_count == 0 and cur_count == 1:
                status = "single_observation"
            elif diff > 0:
                status = "increasing"
            elif diff < 0:
                status = "decreasing"
            elif cur_count > 0 and diff == 0:
                status = "stable"
            else:
                status = "insufficient_data"

            trends.append(
                CivicVoiceTrendItem(
                    theme_id=tid,
                    theme_label=theme_labels.get(tid, tid),
                    current_window_count=cur_count,
                    previous_window_count=prev_count,
                    change_count=diff,
                    status=status,
                    evidence_record_ids=theme_evidence.get(tid, []),
                )
            )

        # Sort trends: emerging/increasing first, then by current volume
        trends.sort(key=lambda t: (t.current_window_count, t.change_count), reverse=True)

        limitations = [
            f"Comparison evaluates two equal consecutive windows of {effective_window} days.",
            "Trends reflect the volume of public posts collected from monitored sources (Bluesky, YouTube, Tavily) and must not be interpreted as statistically representative of the general population.",
        ]
        if missing_pub_timestamps > 0:
            limitations.append(
                f"For {missing_pub_timestamps} records with missing publication dates, ingestion timestamp was used as a fallback."
            )
        if len(analysis_records) < 10:
            limitations.append(
                "Total sample size is small (<10 records); trends should be considered preliminary and indicative rather than definitive."
            )

        return CivicVoiceTrendsResponse(
            window_days=effective_window,
            current_window_start=current_window_start,
            current_window_end=current_window_end,
            previous_window_start=previous_window_start,
            previous_window_end=previous_window_end,
            timestamp_basis="published_at_preferred",
            missing_publication_timestamps_count=missing_pub_timestamps,
            trends=trends,
            data_limitations=limitations,
        )
