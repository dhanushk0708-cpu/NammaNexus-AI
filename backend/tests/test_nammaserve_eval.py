import asyncio
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
import pytest

from app.schemas.nammaserve import ServiceIntent
from app.services.nammaserve.ai.assistant import ServiceAssistant
from app.services.nammaserve.ai.cache import IntentCache
from app.services.nammaserve.ai.evaluation.evaluator import (
    compare_capacity,
    compare_location,
    compare_service,
    compare_urgency,
    compute_report,
    evaluate_case,
    normalize_text,
)
from app.services.nammaserve.ai.evaluation.runner import EvaluationRunner, load_dataset
from app.services.nammaserve.ai.evaluation.schemas import (
    CaseEvaluationResult,
    EvaluationCase,
    EvaluationDataset,
    ExpectedIntent,
)


# --------------------------------------------------------------------
# 1. Dataset Loading & Schema Validation
# --------------------------------------------------------------------
def test_load_golden_dataset_validation():
    dataset = load_dataset()
    assert dataset.version == "intent_eval_v1"
    assert len(dataset.cases) == 20

    # Ensure all case IDs are unique
    ids = [c.id for c in dataset.cases]
    assert len(ids) == len(set(ids))

    # Validate individual fields
    for case in dataset.cases:
        assert isinstance(case.id, str) and len(case.id) > 0
        assert isinstance(case.query, str) and len(case.query) > 0
        assert isinstance(case.expected.service, str) and len(case.expected.service) > 0
        assert isinstance(case.expected.urgent, bool)


def test_load_nonexistent_dataset_raises():
    with pytest.raises(FileNotFoundError):
        load_dataset(Path("nonexistent_path/dataset.json"))


# --------------------------------------------------------------------
# 2. Normalization & Comparison Helpers Tests
# --------------------------------------------------------------------
def test_normalize_text():
    assert normalize_text(None) is None
    assert normalize_text("  ") is None
    assert normalize_text("  Indiranagar  ") == "indiranagar"
    assert normalize_text("HSR   Layout  ") == "hsr layout"


def test_compare_service():
    # Exact and hyphenated matches
    assert compare_service("water-tanker", "water-tanker") is True
    assert compare_service("water tanker", "water-tanker") is True
    assert compare_service("Water-Tanker", "water tanker") is True

    # Canonical aliases
    assert compare_service("solar water heater repair", "solar-heater-repair") is True
    assert compare_service("locksmith", "locksmith-emergency") is True
    assert compare_service("e-waste", "e-waste-pickup") is True
    assert compare_service("construction-debris", "debris-bulk-waste") is True

    # Mismatches
    assert compare_service("water-tanker", "locksmith-emergency") is False
    assert compare_service(None, "water-tanker") is False


def test_compare_location():
    assert compare_location("Kengeri", "kengeri") is True
    assert compare_location("  HSR Layout ", "hsr   layout") is True
    assert compare_location(None, None) is True
    assert compare_location("Whitefield", None) is False
    assert compare_location(None, "Whitefield") is False
    assert compare_location("Indiranagar", "Koramangala") is False


def test_compare_capacity():
    assert compare_capacity(6000.0, 6000) is True
    assert compare_capacity(4000.0, 4000.0) is True
    assert compare_capacity(None, None) is True
    assert compare_capacity(6000.0, None) is False
    assert compare_capacity(None, 6000.0) is False
    assert compare_capacity(6000.0, 4000.0) is False


def test_compare_urgency():
    assert compare_urgency(True, True) is True
    assert compare_urgency(False, False) is True
    assert compare_urgency(None, False) is True  # None treated as False
    assert compare_urgency(True, False) is False
    assert compare_urgency(False, True) is False


# --------------------------------------------------------------------
# 3. Case Evaluation Scoring Tests
# --------------------------------------------------------------------
def test_evaluate_case_perfect_match():
    case = EvaluationCase(
        id="case_001",
        query="Need 6000L water in Kengeri urgently",
        expected=ExpectedIntent(
            service="water-tanker",
            location="Kengeri",
            capacity_litres=6000.0,
            urgent=True,
        ),
    )
    actual = ServiceIntent(
        service="water-tanker",
        location="Kengeri",
        capacity_litres=6000.0,
        urgent=True,
    )

    result = evaluate_case(case, actual, provider="groq", model="llama-3.3-70b-versatile", latency_ms=120.0)
    assert result.passed is True
    assert result.failed_fields == []
    assert result.field_results == {
        "service": True,
        "location": True,
        "capacity_litres": True,
        "urgent": True,
    }
    assert result.provider == "groq"
    assert result.latency_ms == 120.0


def test_evaluate_case_single_field_failure():
    case = EvaluationCase(
        id="case_002",
        query="Need 6000L water in Kengeri urgently",
        expected=ExpectedIntent(
            service="water-tanker",
            location="Kengeri",
            capacity_litres=6000.0,
            urgent=True,
        ),
    )
    actual = ServiceIntent(
        service="water-tanker",
        location="Bengaluru",  # Wrong location
        capacity_litres=6000.0,
        urgent=True,
    )

    result = evaluate_case(case, actual)
    assert result.passed is False
    assert result.failed_fields == ["location"]
    assert result.field_results["location"] is False
    assert result.field_results["service"] is True


def test_evaluate_case_multiple_field_failures():
    case = EvaluationCase(
        id="case_003",
        query="Locked out in Koramangala",
        expected=ExpectedIntent(
            service="locksmith-emergency",
            location="Koramangala",
            capacity_litres=None,
            urgent=True,
        ),
    )
    actual = ServiceIntent(
        service="water-tanker",  # Wrong service
        location="Koramangala",
        capacity_litres=5000.0,  # Wrong capacity
        urgent=False,  # Wrong urgency
    )

    result = evaluate_case(case, actual)
    assert result.passed is False
    assert sorted(result.failed_fields) == sorted(["service", "capacity_litres", "urgent"])


# --------------------------------------------------------------------
# 4. Aggregate Report Computation Tests
# --------------------------------------------------------------------
def test_compute_report_metrics():
    c1 = EvaluationCase(
        id="c1",
        query="q1",
        expected=ExpectedIntent(service="water-tanker", location="Kengeri", capacity_litres=6000.0, urgent=True),
    )
    c2 = EvaluationCase(
        id="c2",
        query="q2",
        expected=ExpectedIntent(service="locksmith-emergency", location="HSR", capacity_litres=None, urgent=False),
    )

    # c1: all 4 fields pass
    res1 = evaluate_case(c1, ServiceIntent(service="water-tanker", location="Kengeri", capacity_litres=6000.0, urgent=True))
    # c2: location fails, other 3 pass
    res2 = evaluate_case(c2, ServiceIntent(service="locksmith-emergency", location="WrongLoc", capacity_litres=None, urgent=False))

    report = compute_report("intent_eval_v1", [res1, res2], provider="groq", model="llama-3.3-70b-versatile")

    assert report.total_cases == 2
    assert report.passed_cases == 1
    assert report.failed_cases == 1
    assert report.case_pass_rate == 50.0
    assert report.service_accuracy == 100.0
    assert report.location_accuracy == 50.0
    assert report.capacity_accuracy == 100.0
    assert report.urgency_accuracy == 100.0
    # 7 out of 8 total fields correct -> 87.5%
    assert report.total_field_accuracy == 87.5

    summary = report.summary_text()
    assert "Case Pass Rate:     50.0%" in summary
    assert "Failed Cases Details:" in summary
    assert "[Case: c2]" in summary


def test_compute_report_empty_results():
    report = compute_report("intent_eval_v1", [])
    assert report.total_cases == 0
    assert report.passed_cases == 0
    assert report.case_pass_rate == 0.0


# --------------------------------------------------------------------
# 5. EvaluationRunner End-to-End with Mock LLM & Cache Isolation
# --------------------------------------------------------------------
def test_evaluation_runner_executes_isolated_without_production_cache():
    async def _test():
        # Mock LLM
        mock_llm = MagicMock()
        mock_structured = MagicMock()

        async def mock_ainvoke(messages):
            prompt_text = messages[1].content.lower()
            if "water" in prompt_text:
                return ServiceIntent(service="water-tanker", location="Kengeri", capacity_litres=6000.0, urgent=True)
            return ServiceIntent(service="locksmith-emergency", location="Koramangala", urgent=True)

        mock_structured.ainvoke = AsyncMock(side_effect=mock_ainvoke)
        mock_llm.with_structured_output.return_value = mock_structured

        # Test dataset with 2 cases
        custom_ds = EvaluationDataset(
            version="custom_test_v1",
            cases=[
                EvaluationCase(
                    id="t1",
                    query="Water tanker 6000L in Kengeri",
                    expected=ExpectedIntent(service="water-tanker", location="Kengeri", capacity_litres=6000.0, urgent=True),
                ),
                EvaluationCase(
                    id="t2",
                    query="Locked out in Koramangala",
                    expected=ExpectedIntent(service="locksmith-emergency", location="Koramangala", capacity_litres=None, urgent=True),
                ),
            ],
        )

        assistant = ServiceAssistant(db=None, llm=mock_llm)
        runner = EvaluationRunner(assistant=assistant)

        # Ensure cache is disabled inside runner
        assert runner.assistant.intent_cache.enabled is False

        report = await runner.run(dataset=custom_ds)

        assert report.total_cases == 2
        assert report.passed_cases == 2
        assert report.case_pass_rate == 100.0
        assert report.service_accuracy == 100.0

    asyncio.run(_test())
