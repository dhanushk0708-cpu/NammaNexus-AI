import pytest
from app.schemas.ai import PredictiveImpactResult
from app.services.predictive_impact import calculate_predictive_impact


def test_predictive_impact_low_severity():
    result = calculate_predictive_impact(severity="LOW", confidence=0.9, category="GARBAGE")
    assert isinstance(result, PredictiveImpactResult)
    assert result.priority == "LOW"
    assert 0 <= result.impact_score <= 100
    assert "severity LOW" in result.impact_reason


def test_predictive_impact_medium_severity():
    result = calculate_predictive_impact(severity="MEDIUM", confidence=0.8, category="STREET_LIGHT")
    assert isinstance(result, PredictiveImpactResult)
    assert result.priority == "MEDIUM"
    assert 0 <= result.impact_score <= 100
    assert "severity MEDIUM" in result.impact_reason


def test_predictive_impact_high_severity():
    result = calculate_predictive_impact(severity="HIGH", confidence=0.9, category="POTHOLE")
    assert isinstance(result, PredictiveImpactResult)
    assert result.priority in ["HIGH", "CRITICAL"]
    assert 0 <= result.impact_score <= 100
    assert "severity HIGH" in result.impact_reason


def test_predictive_impact_critical_severity():
    result = calculate_predictive_impact(
        severity="CRITICAL", confidence=0.95, category="FALLEN_TREE", has_location=True
    )
    assert isinstance(result, PredictiveImpactResult)
    assert result.priority == "CRITICAL"
    assert result.impact_score >= 80
    assert 0 <= result.impact_score <= 100
    assert "CRITICAL" in result.priority


def test_predictive_impact_low_confidence():
    high_conf = calculate_predictive_impact(severity="HIGH", confidence=0.95, category="POTHOLE")
    low_conf = calculate_predictive_impact(severity="HIGH", confidence=0.1, category="POTHOLE")
    assert low_conf.impact_score < high_conf.impact_score
    assert 0 <= low_conf.impact_score <= 100


def test_predictive_impact_high_confidence():
    result = calculate_predictive_impact(severity="CRITICAL", confidence=1.0, category="WATERLOGGING")
    assert result.impact_score >= 80
    assert result.priority == "CRITICAL"


@pytest.mark.parametrize(
    "category",
    [
        "POTHOLE",
        "GARBAGE",
        "WATER_LEAKAGE",
        "WATERLOGGING",
        "STREET_LIGHT",
        "FALLEN_TREE",
    ],
)
def test_predictive_impact_all_supported_categories(category):
    result = calculate_predictive_impact(severity="MEDIUM", confidence=0.8, category=category)
    assert isinstance(result, PredictiveImpactResult)
    assert category in result.impact_reason
    assert 0 <= result.impact_score <= 100


def test_predictive_impact_missing_or_invalid_inputs():
    result_none = calculate_predictive_impact(severity=None, confidence=None, category=None)
    assert isinstance(result_none, PredictiveImpactResult)
    assert result_none.priority in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert 0 <= result_none.impact_score <= 100

    result_invalid_conf = calculate_predictive_impact(severity="HIGH", confidence="invalid") # type: ignore
    assert isinstance(result_invalid_conf, PredictiveImpactResult)
    assert 0 <= result_invalid_conf.impact_score <= 100


def test_predictive_impact_score_boundaries():
    # Force max boundary condition
    max_res = calculate_predictive_impact(
        severity="CRITICAL", confidence=1.0, category="FALLEN_TREE", latitude=12.9, longitude=77.5
    )
    assert 0 <= max_res.impact_score <= 100

    # Force min boundary condition
    min_res = calculate_predictive_impact(
        severity="LOW", confidence=0.0, category="GARBAGE", has_location=False
    )
    assert 0 <= min_res.impact_score <= 100


def test_predictive_impact_valid_priority_enum():
    allowed_priorities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    for sev in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        res = calculate_predictive_impact(severity=sev, confidence=0.7)
        assert res.priority in allowed_priorities
