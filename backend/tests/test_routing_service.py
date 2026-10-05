import pytest
from pydantic import ValidationError

from app.schemas.ai import RoutingResult
from app.services.routing import route_complaint


@pytest.mark.parametrize(
    ("category", "authority", "department"),
    [
        ("POTHOLE", "BBMP", "Road Infrastructure"),
        ("GARBAGE", "BBMP", "Solid Waste Management"),
        ("WATER_LEAKAGE", "BWSSB", "Water Supply Maintenance"),
        ("WATERLOGGING", "BBMP", "Storm Water Drains"),
        ("STREET_LIGHT", "BESCOM", "Street Lighting"),
        ("FALLEN_TREE", "BBMP", "Tree Management"),
    ],
)
def test_route_complaint_supported_categories(category, authority, department):
    result = route_complaint(
        category=category,
        severity="HIGH",
        priority="HIGH",
        impact_score=72,
    )

    assert isinstance(result, RoutingResult)
    assert result.authority == authority
    assert result.department == department
    assert result.routing_reason


def test_route_complaint_rejects_unsupported_category():
    with pytest.raises(ValidationError, match="Unsupported complaint category."):
        route_complaint(category="SEWAGE_OVERFLOW")


def test_route_complaint_rejects_invalid_category():
    with pytest.raises(ValidationError):
        route_complaint(category=None)  # type: ignore[arg-type]


def test_route_complaint_rejects_invalid_severity():
    with pytest.raises(ValidationError, match="Unsupported severity level."):
        route_complaint(category="POTHOLE", severity="URGENT")


def test_route_complaint_returns_schema_valid_output():
    result = route_complaint(
        category="GARBAGE",
        severity="MEDIUM",
        priority="MEDIUM",
        impact_score=50,
    )

    validated = RoutingResult.model_validate(result.model_dump())

    assert validated == result


def test_route_complaint_includes_valid_location_context():
    result = route_complaint(
        category="WATER_LEAKAGE",
        priority="HIGH",
        impact_score=65,
        latitude=12.9716,
        longitude=77.5946,
    )

    assert "map-confirmed coordinates" in result.routing_reason


def test_route_complaint_allows_missing_location():
    result = route_complaint(
        category="STREET_LIGHT",
        priority="MEDIUM",
        impact_score=45,
    )

    assert "map-confirmed coordinates" not in result.routing_reason


def test_route_complaint_is_deterministic():
    first = route_complaint(
        category="FALLEN_TREE",
        severity="CRITICAL",
        priority="CRITICAL",
        impact_score=90,
        latitude=12.95,
        longitude=77.62,
    )
    second = route_complaint(
        category="FALLEN_TREE",
        severity="CRITICAL",
        priority="CRITICAL",
        impact_score=90,
        latitude=12.95,
        longitude=77.62,
    )

    assert first == second
