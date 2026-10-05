from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.ai import (
    ComplaintWriterResult,
    PriorityLevel,
    SeverityLevel,
    SpotFixCategory,
)


CATEGORY_LABELS: dict[SpotFixCategory, str] = {
    SpotFixCategory.POTHOLE: "pothole",
    SpotFixCategory.GARBAGE: "garbage/waste",
    SpotFixCategory.WATER_LEAKAGE: "water leakage",
    SpotFixCategory.WATERLOGGING: "waterlogging",
    SpotFixCategory.STREET_LIGHT: "street light",
    SpotFixCategory.FALLEN_TREE: "fallen tree",
}


class ComplaintWriterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: SpotFixCategory
    description: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    severity: SeverityLevel | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    visual_explanation: str | None = None
    impact_score: int | None = Field(default=None, ge=0, le=100)
    priority: PriorityLevel | None = None
    impact_reason: str | None = None
    authority: str
    department: str
    routing_reason: str | None = None

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

    @field_validator(
        "description",
        "visual_explanation",
        "impact_reason",
        "authority",
        "department",
        "routing_reason",
    )
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        stripped_value = value.strip()
        return stripped_value or None


def _format_category(category: SpotFixCategory) -> str:
    return CATEGORY_LABELS[category]


def write_complaint_draft(
    *,
    category: SpotFixCategory | str,
    description: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    severity: SeverityLevel | str | None = None,
    confidence: float | None = None,
    visual_explanation: str | None = None,
    impact_score: int | None = None,
    priority: PriorityLevel | str | None = None,
    impact_reason: str | None = None,
    authority: str,
    department: str,
    routing_reason: str | None = None,
) -> ComplaintWriterResult:
    writer_input = ComplaintWriterInput(
        category=category,
        description=description,
        latitude=latitude,
        longitude=longitude,
        severity=severity,
        confidence=confidence,
        visual_explanation=visual_explanation,
        impact_score=impact_score,
        priority=priority,
        impact_reason=impact_reason,
        authority=authority,
        department=department,
        routing_reason=routing_reason,
    )

    category_label = _format_category(writer_input.category)
    subject = f"Complaint regarding {category_label} issue"

    location_line = "Location: Not provided."
    if writer_input.latitude is not None and writer_input.longitude is not None:
        location_line = (
            f"Location coordinates: {writer_input.latitude}, {writer_input.longitude}."
        )

    evidence_lines = []
    if writer_input.description:
        evidence_lines.append(f"Citizen description: {writer_input.description}")
    if writer_input.visual_explanation:
        evidence_lines.append(f"Image analysis: {writer_input.visual_explanation}")
    if writer_input.severity:
        evidence_lines.append(f"Severity: {writer_input.severity.value}.")
    if writer_input.confidence is not None:
        evidence_lines.append(
            f"Image analysis confidence: {int(writer_input.confidence * 100)}%."
        )
    if writer_input.impact_score is not None and writer_input.priority is not None:
        evidence_lines.append(
            f"Impact assessment: {writer_input.priority.value} priority with score {writer_input.impact_score}/100."
        )
    elif writer_input.priority is not None:
        evidence_lines.append(
            f"Impact assessment: {writer_input.priority.value} priority."
        )
    if writer_input.impact_reason:
        evidence_lines.append(f"Impact reason: {writer_input.impact_reason}")
    if writer_input.routing_reason:
        evidence_lines.append(f"Routing reason: {writer_input.routing_reason}")

    if not evidence_lines:
        evidence_lines.append(
            f"A {category_label} issue has been reported for official review."
        )

    complaint_text = "\n".join(
        [
            f"To: {writer_input.authority} - {writer_input.department}",
            "",
            f"Subject: {subject}",
            "",
            (
                "This complaint draft is prepared for citizen review regarding "
                f"a reported {category_label} issue."
            ),
            location_line,
            "",
            "Verified details:",
            *evidence_lines,
            "",
            (
                "Requested action: Please inspect the reported issue and take "
                "appropriate civic maintenance action based on the verified details above."
            ),
        ]
    )

    return ComplaintWriterResult(
        subject=subject,
        complaint_text=complaint_text,
    )
