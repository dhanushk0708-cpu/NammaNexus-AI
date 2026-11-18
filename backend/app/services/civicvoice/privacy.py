"""CivicVoice Privacy & Small-Group Suppression Utilities.

Protects resident privacy by applying k-anonymity / minimum group-size thresholds
to citizen-contributed statistics before inclusion in dashboards, reports, exports, or logs.
"""
from typing import TypeVar

K_ANONYMITY_THRESHOLD = 3
SUPPRESSED_LABEL = "Other / Suppressed (< 3)"

T = TypeVar("T")


def suppress_small_groups(
    distribution: dict[str, int],
    threshold: int = K_ANONYMITY_THRESHOLD,
    suppression_label: str = SUPPRESSED_LABEL,
) -> dict[str, int]:
    """Applies small-group suppression to a frequency distribution dictionary.

    Any group with a count less than the threshold is suppressed and aggregated
    into a generalized category to prevent singling out individual contributors
    or inferring small groups by subtraction.
    """
    if not distribution:
        return {}

    safe_distribution: dict[str, int] = {}
    suppressed_count = 0

    for key, count in distribution.items():
        if count >= threshold:
            safe_distribution[key] = count
        else:
            suppressed_count += count

    if suppressed_count > 0:
        safe_distribution[suppression_label] = suppressed_count

    return safe_distribution


def build_safe_citizen_report_metrics(
    total_submissions: int,
    topic_distribution: dict[str, int],
    locality_distribution: dict[str, int],
    threshold: int = K_ANONYMITY_THRESHOLD,
) -> dict:
    """Builds privacy-safe aggregate citizen metrics for official civic reports.

    Applies k-anonymity suppression to prevent re-identification of individual
    contributors. If total submissions is below threshold, suppresses granular
    breakdowns entirely.
    """
    if total_submissions < threshold:
        return {
            "total_represented": total_submissions,
            "sample_warning": f"Citizen submissions count ({total_submissions}) is below privacy threshold ({threshold}). Granular locality and topic distributions are withheld to protect contributor anonymity.",
            "topic_distribution": {},
            "locality_distribution": {},
        }

    return {
        "total_represented": total_submissions,
        "sample_warning": None,
        "topic_distribution": suppress_small_groups(topic_distribution, threshold=threshold),
        "locality_distribution": suppress_small_groups(locality_distribution, threshold=threshold),
    }

