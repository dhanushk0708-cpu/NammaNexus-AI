import re
from typing import Optional

from app.schemas.nammaserve import ServiceIntent
from app.services.nammaserve.ai.evaluation.schemas import (
    CaseEvaluationResult,
    EvaluationCase,
    EvaluationReport,
)

# Canonical service aliases for deterministic comparison
SERVICE_ALIASES = {
    "water-tanker": {"water-tanker", "water tanker", "watertanker", "potable-water-tanker"},
    "solar-heater-repair": {
        "solar-heater-repair",
        "solar heater repair",
        "solar-water-heater-repair",
        "solar water heater repair",
        "solar-water-heater",
    },
    "e-waste-pickup": {
        "e-waste-pickup",
        "e waste pickup",
        "ewaste-pickup",
        "ewaste pickup",
        "e-waste",
        "ewaste",
    },
    "locksmith-emergency": {
        "locksmith-emergency",
        "locksmith emergency",
        "locksmith",
        "keymaker",
    },
    "debris-bulk-waste": {
        "debris-bulk-waste",
        "debris bulk waste",
        "debris-waste",
        "debris pickup",
        "construction-debris",
    },
}


def normalize_text(val: Optional[str]) -> Optional[str]:
    """Trim, collapse multiple whitespace runs, and lowercase a string field."""
    if val is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(val).strip().lower())
    return cleaned if cleaned else None


def compare_service(actual: Optional[str], expected: str) -> bool:
    """Deterministically compare actual extracted service against expected service."""
    norm_actual = normalize_text(actual)
    norm_expected = normalize_text(expected)

    if norm_actual is None:
        return False

    # Exact normalized match
    if norm_actual == norm_expected:
        return True

    # Check hyphenated equivalence
    if norm_actual.replace("-", " ") == norm_expected.replace("-", " "):
        return True

    # Canonical alias set lookup
    for canonical_slug, aliases in SERVICE_ALIASES.items():
        if norm_expected in aliases or norm_expected == canonical_slug:
            if norm_actual in aliases or norm_actual.replace(" ", "-") in aliases:
                return True

    return False


def compare_location(actual: Optional[str], expected: Optional[str]) -> bool:
    """Deterministically compare actual extracted location against expected location."""
    norm_actual = normalize_text(actual)
    norm_expected = normalize_text(expected)

    if norm_expected is None and norm_actual is None:
        return True
    if norm_expected is None or norm_actual is None:
        return False

    return norm_actual == norm_expected


def compare_capacity(actual: Optional[float], expected: Optional[float]) -> bool:
    """Deterministically compare numeric capacity values (handling None)."""
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False

    try:
        return abs(float(actual) - float(expected)) < 1e-3
    except (ValueError, TypeError):
        return False


def compare_urgency(actual: Optional[bool], expected: Optional[bool]) -> bool:
    """Deterministically compare boolean urgency."""
    act_bool = bool(actual) if actual is not None else False
    exp_bool = bool(expected) if expected is not None else False
    return act_bool == exp_bool


# Alias for generic boolean comparisons
compare_boolean = compare_urgency


def evaluate_case(
    case: EvaluationCase,
    actual_intent: ServiceIntent,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    latency_ms: Optional[float] = None,
) -> CaseEvaluationResult:
    """Evaluate an actual ServiceIntent against an EvaluationCase ground truth."""
    service_match = compare_service(actual_intent.service, case.expected.service)
    location_match = compare_location(actual_intent.location, case.expected.location)
    capacity_match = compare_capacity(
        actual_intent.capacity_litres, case.expected.capacity_litres
    )
    urgency_match = compare_urgency(actual_intent.urgent, case.expected.urgent)

    field_results = {
        "service": service_match,
        "location": location_match,
        "capacity_litres": capacity_match,
        "urgent": urgency_match,
    }

    failed_fields = [k for k, matched in field_results.items() if not matched]
    passed = len(failed_fields) == 0

    return CaseEvaluationResult(
        case_id=case.id,
        query=case.query,
        expected=case.expected,
        actual=actual_intent,
        passed=passed,
        failed_fields=failed_fields,
        field_results=field_results,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
    )


def compute_report(
    dataset_version: str,
    results: list[CaseEvaluationResult],
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> EvaluationReport:
    """Compute aggregate accuracy metrics across all evaluated cases."""
    total_cases = len(results)
    if total_cases == 0:
        return EvaluationReport(
            dataset_version=dataset_version,
            provider=provider,
            model=model,
            total_cases=0,
        )

    passed_cases = sum(1 for r in results if r.passed)
    failed_cases = total_cases - passed_cases

    case_pass_rate = (passed_cases / total_cases) * 100.0
    service_accuracy = (
        sum(1 for r in results if r.field_results["service"]) / total_cases
    ) * 100.0
    location_accuracy = (
        sum(1 for r in results if r.field_results["location"]) / total_cases
    ) * 100.0
    capacity_accuracy = (
        sum(1 for r in results if r.field_results["capacity_litres"]) / total_cases
    ) * 100.0
    urgency_accuracy = (
        sum(1 for r in results if r.field_results["urgent"]) / total_cases
    ) * 100.0

    total_fields = total_cases * 4
    total_correct_fields = sum(
        sum(1 for m in r.field_results.values() if m) for r in results
    )
    total_field_accuracy = (total_correct_fields / total_fields) * 100.0

    return EvaluationReport(
        dataset_version=dataset_version,
        provider=provider,
        model=model,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        case_pass_rate=round(case_pass_rate, 2),
        service_accuracy=round(service_accuracy, 2),
        location_accuracy=round(location_accuracy, 2),
        capacity_accuracy=round(capacity_accuracy, 2),
        urgency_accuracy=round(urgency_accuracy, 2),
        total_field_accuracy=round(total_field_accuracy, 2),
        results=results,
    )
