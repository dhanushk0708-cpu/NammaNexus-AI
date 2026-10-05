from app.schemas.ai import PredictiveImpactResult, PriorityLevel


def calculate_predictive_impact(
    severity: str | None = None,
    confidence: float | None = None,
    category: str | None = None,
    has_location: bool = False,
    latitude: float | None = None,
    longitude: float | None = None,
) -> PredictiveImpactResult:
    """
    Predictive Impact Service:
    Calculates impact_score (0-100), priority (LOW|MEDIUM|HIGH|CRITICAL), and impact_reason.
    Uses transparent, explainable rule-based scoring without inventing non-existent metadata.
    """
    if latitude is not None and longitude is not None:
        has_location = True

    # 1. Base Score by Severity
    severity_clean = severity.upper().strip() if severity else "LOW"
    severity_scores = {
        "CRITICAL": 85,
        "HIGH": 65,
        "MEDIUM": 45,
        "LOW": 25,
    }
    base_score = severity_scores.get(severity_clean, 25)

    # 2. Category modifier
    category_clean = category.upper().strip() if category else None
    category_modifiers = {
        "FALLEN_TREE": 10,
        "WATERLOGGING": 10,
        "POTHOLE": 5,
        "WATER_LEAKAGE": 5,
        "GARBAGE": 0,
        "STREET_LIGHT": 0,
    }
    cat_modifier = category_modifiers.get(category_clean, 0) if category_clean else 0

    # 3. Confidence weighting factor
    try:
        conf_value = float(confidence) if confidence is not None else 0.8
    except (ValueError, TypeError):
        conf_value = 0.8
    
    conf_value = max(0.0, min(1.0, conf_value))

    # Weight base + category by confidence
    raw_score = (base_score + cat_modifier) * (0.5 + 0.5 * conf_value)

    # 4. Location bonus (+5 if map confirmed coordinates are present)
    loc_bonus = 5 if has_location else 0
    final_score = int(round(raw_score + loc_bonus))

    # Clamp final score to strict [0, 100]
    final_score = max(0, min(100, final_score))

    # 5. Priority Mapping
    if final_score >= 80:
        priority = PriorityLevel.CRITICAL.value
    elif final_score >= 60:
        priority = PriorityLevel.HIGH.value
    elif final_score >= 40:
        priority = PriorityLevel.MEDIUM.value
    else:
        priority = PriorityLevel.LOW.value

    # Build concise explainable reason
    reasons = [f"severity {severity_clean}"]
    if category_clean:
        reasons.append(f"category {category_clean}")
    if confidence is not None:
        reasons.append(f"AI confidence {int(conf_value * 100)}%")
    if has_location:
        reasons.append("map-confirmed location")

    impact_reason = (
        f"Calculated {priority} priority (score {final_score}/100) based on "
        + ", ".join(reasons)
        + "."
    )

    return PredictiveImpactResult(
        impact_score=final_score,
        priority=priority,
        impact_reason=impact_reason,
    )
