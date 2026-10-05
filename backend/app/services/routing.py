from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.ai import PriorityLevel, RoutingResult, SeverityLevel, SpotFixCategory


class RoutingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: SpotFixCategory
    severity: SeverityLevel | None = None
    priority: PriorityLevel | None = None
    impact_score: int | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, value: SpotFixCategory | str) -> SpotFixCategory:
        if isinstance(value, SpotFixCategory):
            return value

        if not isinstance(value, str):
            raise ValueError("Unsupported complaint category.")

        try:
            return SpotFixCategory(value.strip().upper())
        except ValueError as exc:
            raise ValueError("Unsupported complaint category.") from exc

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(
        cls, value: SeverityLevel | str | None
    ) -> SeverityLevel | None:
        if value is None or isinstance(value, SeverityLevel):
            return value

        if not isinstance(value, str):
            raise ValueError("Unsupported severity level.")

        try:
            return SeverityLevel(value.strip().upper())
        except ValueError as exc:
            raise ValueError("Unsupported severity level.") from exc

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(
        cls, value: PriorityLevel | str | None
    ) -> PriorityLevel | None:
        if value is None or isinstance(value, PriorityLevel):
            return value

        if not isinstance(value, str):
            raise ValueError("Unsupported priority level.")

        try:
            return PriorityLevel(value.strip().upper())
        except ValueError as exc:
            raise ValueError("Unsupported priority level.") from exc


class RoutingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authority: str
    department: str
    base_reason: str


ROUTING_RULES: dict[SpotFixCategory, RoutingRule] = {
    SpotFixCategory.POTHOLE: RoutingRule(
        authority="BBMP",
        department="Road Infrastructure",
        base_reason=(
            "Pothole-related road issues fall under BBMP road infrastructure responsibility."
        ),
    ),
    SpotFixCategory.GARBAGE: RoutingRule(
        authority="BBMP",
        department="Solid Waste Management",
        base_reason=(
            "Garbage and public waste complaints fall under BBMP solid waste management."
        ),
    ),
    SpotFixCategory.WATER_LEAKAGE: RoutingRule(
        authority="BWSSB",
        department="Water Supply Maintenance",
        base_reason=(
            "Water leakage issues are routed to BWSSB for water supply network maintenance."
        ),
    ),
    SpotFixCategory.WATERLOGGING: RoutingRule(
        authority="BBMP",
        department="Storm Water Drains",
        base_reason=(
            "Waterlogging complaints are routed to BBMP storm water drain operations."
        ),
    ),
    SpotFixCategory.STREET_LIGHT: RoutingRule(
        authority="BESCOM",
        department="Street Lighting",
        base_reason=(
            "Street light faults are routed to BESCOM street lighting operations."
        ),
    ),
    SpotFixCategory.FALLEN_TREE: RoutingRule(
        authority="BBMP",
        department="Tree Management",
        base_reason=(
            "Fallen tree incidents are routed to BBMP tree management for clearance."
        ),
    ),
}


def route_complaint(
    *,
    category: SpotFixCategory | str,
    severity: SeverityLevel | str | None = None,
    priority: PriorityLevel | str | None = None,
    impact_score: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> RoutingResult:
    request = RoutingRequest(
        category=category,
        severity=severity,
        priority=priority,
        impact_score=impact_score,
        latitude=latitude,
        longitude=longitude,
    )

    rule = ROUTING_RULES[request.category]

    reason_parts = [rule.base_reason]

    if request.priority is not None and request.impact_score is not None:
        reason_parts.append(
            f"Current impact assessment is {request.priority.value} priority with score {request.impact_score}/100."
        )
    elif request.priority is not None:
        reason_parts.append(
            f"Current impact assessment is {request.priority.value} priority."
        )
    elif request.severity is not None:
        reason_parts.append(
            f"Visible severity was assessed as {request.severity.value}."
        )

    if request.latitude is not None and request.longitude is not None:
        reason_parts.append("Complaint includes map-confirmed coordinates.")

    return RoutingResult(
        authority=rule.authority,
        department=rule.department,
        routing_reason=" ".join(reason_parts),
    )
