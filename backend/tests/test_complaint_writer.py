import pytest
from pydantic import ValidationError

from app.schemas.ai import ComplaintWriterResult
from app.services.complaint_writer import write_complaint_draft


@pytest.mark.parametrize(
    ("category", "expected_phrase"),
    [
        ("POTHOLE", "pothole issue"),
        ("GARBAGE", "garbage/waste issue"),
        ("WATER_LEAKAGE", "water leakage issue"),
        ("WATERLOGGING", "waterlogging issue"),
        ("STREET_LIGHT", "street light issue"),
        ("FALLEN_TREE", "fallen tree issue"),
    ],
)
def test_write_complaint_draft_supports_all_categories(
    category,
    expected_phrase,
):
    result = write_complaint_draft(
        category=category,
        description="Issue reported by citizen.",
        authority="BBMP",
        department="Road Infrastructure",
    )

    assert isinstance(result, ComplaintWriterResult)
    assert expected_phrase in result.subject
    assert expected_phrase in result.complaint_text


def test_write_complaint_draft_includes_severity_and_priority():
    result = write_complaint_draft(
        category="POTHOLE",
        severity="HIGH",
        impact_score=73,
        priority="HIGH",
        authority="BBMP",
        department="Road Infrastructure",
    )

    assert "Severity: HIGH." in result.complaint_text
    assert "HIGH priority with score 73/100" in result.complaint_text


def test_write_complaint_draft_includes_authority_and_department():
    result = write_complaint_draft(
        category="WATER_LEAKAGE",
        authority="BWSSB",
        department="Water Supply Maintenance",
    )

    assert result.complaint_text.startswith("To: BWSSB - Water Supply Maintenance")


def test_write_complaint_draft_includes_coordinates_when_available():
    result = write_complaint_draft(
        category="GARBAGE",
        latitude=12.9716,
        longitude=77.5946,
        authority="BBMP",
        department="Solid Waste Management",
    )

    assert "Location coordinates: 12.9716, 77.5946." in result.complaint_text


def test_write_complaint_draft_handles_missing_optional_data():
    result = write_complaint_draft(
        category="STREET_LIGHT",
        authority="BESCOM",
        department="Street Lighting",
    )

    assert "Location: Not provided." in result.complaint_text
    assert "Citizen description:" not in result.complaint_text
    assert "Image analysis:" not in result.complaint_text
    assert "reported street light issue" in result.complaint_text


def test_complaint_writer_result_validation_rejects_empty_text():
    with pytest.raises(ValidationError, match="Complaint draft fields cannot be empty."):
        ComplaintWriterResult(subject=" ", complaint_text="Valid text")


def test_write_complaint_draft_rejects_invalid_category():
    with pytest.raises(ValidationError, match="Unsupported complaint category."):
        write_complaint_draft(
            category="UNSUPPORTED",
            authority="BBMP",
            department="Road Infrastructure",
        )


def test_write_complaint_draft_rejects_invalid_severity():
    with pytest.raises(ValidationError, match="Unsupported severity level."):
        write_complaint_draft(
            category="POTHOLE",
            severity="URGENT",
            authority="BBMP",
            department="Road Infrastructure",
        )


def test_write_complaint_draft_is_deterministic():
    payload = {
        "category": "FALLEN_TREE",
        "description": "Tree is blocking part of the road.",
        "latitude": 12.95,
        "longitude": 77.62,
        "severity": "CRITICAL",
        "confidence": 0.91,
        "visual_explanation": "A fallen tree is visible on the road.",
        "impact_score": 90,
        "priority": "CRITICAL",
        "impact_reason": "Calculated CRITICAL priority from verified inputs.",
        "authority": "BBMP",
        "department": "Tree Management",
        "routing_reason": "Fallen tree incidents are routed to BBMP tree management.",
    }

    first = write_complaint_draft(**payload)
    second = write_complaint_draft(**payload)

    assert first == second
