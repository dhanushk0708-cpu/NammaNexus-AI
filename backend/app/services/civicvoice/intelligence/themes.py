from collections import defaultdict
from datetime import datetime
from typing import Any

from app.models.civicvoice import CivicVoiceAnalysisRecord, CivicVoiceSourceRecord
from app.schemas.civicvoice import CivicVoiceTheme, OpinionCategory

THEME_DEFINITIONS: dict[str, dict[str, Any]] = {
    "road_infrastructure": {
        "label": "Road Infrastructure & Potholes",
        "description": "Citizen reports, observations, and concerns regarding damaged roads, potholes, and cratered surfaces.",
        "keywords": {
            "pothole", "potholes", "road", "roads", "crater", "asphalt", "tar", "paving",
            "ಗುಂಡಿ", "ರಸ್ತೆ", "ರಸ್ತೆಗಳು", "ಹಾಳಾದ ರಸ್ತೆ", "ರಸ್ತೆಯಲ್ಲಿ ಗುಂಡಿ",
        },
    },
    "traffic_congestion": {
        "label": "Traffic & Congestion Management",
        "description": "Reports regarding bottleneck junctions, traffic snarls, slow transit, and signal timing.",
        "keywords": {
            "traffic", "jam", "congestion", "signal", "junction", "gridlock", "commute", "peak hour",
            "ಟ್ರಾಫಿಕ್", "ಜಾಮ್", "ದಟ್ಟಣೆ", "ಸಿಗ್ನಲ್", "ಟ್ರಾಫಿಕ್ ಜಾಮ್",
        },
    },
    "waste_management": {
        "label": "Cleanliness & Solid Waste Management",
        "description": "Citizen observations regarding unattended garbage piles, black spots, irregular clearing, and odors.",
        "keywords": {
            "garbage", "trash", "waste", "dump", "dumping", "bin", "stench", "litter",
            "ಕಸ", "ತ್ಯಾಜ್ಯ", "ಕಸದ ತೊಟ್ಟಿ", "ವಾಸನೆ", "ದುರ್ವಾಸನೆ", "ಕಸ ವಿಲೇವಾರಿ",
        },
    },
    "water_drainage": {
        "label": "Water Supply & Stormwater Drainage",
        "description": "Reports on drinking water scarcity, pipeline bursts, clogged drains, and monsoon waterlogging.",
        "keywords": {
            "water", "leak", "pipeline", "drain", "drainage", "waterlogging", "flood", "sewage",
            "ನೀರು", "ನೀರಿನ ಕೊರತೆ", "ಚರಂಡಿ", "ರಾಜಕಾಲುವೆ", "ಮಳೆ ನೀರು", "ನೀರು ಸೋರಿಕೆ",
        },
    },
    "public_transport": {
        "label": "Public Transport & Connectivity",
        "description": "Feedback and suggestions regarding BMTC bus frequency, Metro accessibility, and transit stops.",
        "keywords": {
            "bus", "buses", "bmtc", "metro", "station", "feeder", "transit",
            "ಬಸ್", "ಬಸ್ಸು", "ಮೆಟ್ರೋ", "ಸಾರಿಗೆ", "ನಿಲ್ದಾಣ",
        },
    },
    "public_safety_lighting": {
        "label": "Street Lighting & Public Safety",
        "description": "Issues concerning non-functioning streetlights, unlit stretches, and pedestrian safety.",
        "keywords": {
            "street light", "streetlight", "dark", "safety", "unlit", "crime", "lamp post",
            "ಬೀದಿ ದೀಪ", "ಕತ್ತಲೆ", "ಸುರಕ್ಷತೆ", "ದೀಪ ಹಾಳಾಗಿದೆ",
        },
    },
    "positive_initiatives": {
        "label": "Appreciation & Civic Improvement",
        "description": "Public commendation for civic repairs, community cleanups, or improved services.",
        "keywords": {
            "thank", "great job", "appreciate", "clean", "fixed", "kudos", "well done",
            "ಧನ್ಯವಾದ", "ಉತ್ತಮ ಕೆಲಸ", "ಮೆಚ್ಚುಗೆ", "ಸರಿಮಾಡಲಾಗಿದೆ",
        },
    },
}


def classify_theme_for_text(text: str, category: str | None = None) -> tuple[str, str]:
    """Matches text against theme keyword dictionaries in English and Kannada.

    Returns (theme_id, theme_label).
    """
    lower_text = text.lower() if text else ""

    # Check positive experience override if explicitly categorized
    if category == OpinionCategory.POSITIVE_EXPERIENCE.value:
        # If it doesn't match a specific civic pillar, label as positive initiatives
        for theme_id, meta in THEME_DEFINITIONS.items():
            if theme_id != "positive_initiatives" and any(kw in lower_text for kw in meta["keywords"]):
                return theme_id, meta["label"]
        return "positive_initiatives", THEME_DEFINITIONS["positive_initiatives"]["label"]

    best_theme = "general_civic"
    best_label = "General Civic Observations"
    max_matches = 0

    for theme_id, meta in THEME_DEFINITIONS.items():
        if theme_id == "positive_initiatives":
            continue
        matches = sum(1 for kw in meta["keywords"] if kw in lower_text)
        if matches > max_matches:
            max_matches = matches
            best_theme = theme_id
            best_label = meta["label"]

    return best_theme, best_label


class ThemeClusterEngine:
    """Aggregates analyzed opinion records into recurring themes with traceable evidence."""

    def cluster_records(
        self,
        analysis_records: list[CivicVoiceAnalysisRecord],
        source_records_map: dict[str, CivicVoiceSourceRecord],
    ) -> list[CivicVoiceTheme]:
        """Groups analysis records by theme and calculates genuine counts, links, and dates."""
        grouped: dict[str, list[CivicVoiceAnalysisRecord]] = defaultdict(list)

        for ar in analysis_records:
            theme_key = ar.theme_id or "general_civic"
            grouped[theme_key].append(ar)

        theme_results: list[CivicVoiceTheme] = []

        for theme_id, records in grouped.items():
            definition = THEME_DEFINITIONS.get(theme_id, {
                "label": records[0].theme_label if records and records[0].theme_label else "General Civic Observations",
                "description": "Citizen discussions and feedback on general civic matters.",
            })

            evidence_ids = []
            source_links = []
            sentiment_counts: dict[str, int] = defaultdict(int)
            dates: list[datetime] = []

            for r in records:
                evidence_ids.append(r.source_record_id)
                s_rec = source_records_map.get(r.source_record_id)
                if s_rec:
                    if s_rec.url and s_rec.url not in source_links:
                        source_links.append(s_rec.url)
                    if s_rec.published_at:
                        dates.append(s_rec.published_at)
                    elif s_rec.collected_at:
                        dates.append(s_rec.collected_at)

                if r.sentiment:
                    sentiment_counts[r.sentiment] += 1
                else:
                    sentiment_counts["neutral"] += 1

            earliest = min(dates) if dates else None
            latest = max(dates) if dates else None

            theme_results.append(
                CivicVoiceTheme(
                    theme_id=theme_id,
                    theme_label=definition["label"],
                    description=definition["description"],
                    record_count=len(records),
                    evidence_record_ids=evidence_ids,
                    source_links=source_links,
                    sentiment_breakdown=dict(sentiment_counts),
                    earliest_date=earliest,
                    latest_date=latest,
                    analysis_version="v1.0",
                )
            )

        # Sort themes by record count descending
        theme_results.sort(key=lambda t: t.record_count, reverse=True)
        return theme_results
