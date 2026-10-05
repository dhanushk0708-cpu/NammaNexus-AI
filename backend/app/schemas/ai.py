from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SpotFixCategory(str, Enum):
    POTHOLE = "POTHOLE"
    GARBAGE = "GARBAGE"
    WATER_LEAKAGE = "WATER_LEAKAGE"
    WATERLOGGING = "WATERLOGGING"
    STREET_LIGHT = "STREET_LIGHT"
    FALLEN_TREE = "FALLEN_TREE"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SpotFixImageAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: SpotFixCategory
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: SeverityLevel
    visual_explanation: str = Field(..., min_length=1)

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, value: SpotFixCategory | str) -> SpotFixCategory:
        if isinstance(value, SpotFixCategory):
            return value

        if not isinstance(value, str):
            raise ValueError("Unsupported complaint category.")

        normalized_value = value.strip().upper()

        try:
            return SpotFixCategory(normalized_value)
        except ValueError as exc:
            raise ValueError("Unsupported complaint category.") from exc

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, value: SeverityLevel | str) -> SeverityLevel:
        if isinstance(value, SeverityLevel):
            return value

        if not isinstance(value, str):
            raise ValueError("Unsupported severity level.")

        normalized_value = value.strip().upper()

        try:
            return SeverityLevel(normalized_value)
        except ValueError as exc:
            raise ValueError("Unsupported severity level.") from exc

    @field_validator("visual_explanation")
    @classmethod
    def validate_visual_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Visual explanation cannot be empty.")
        return value.strip()


class PriorityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PredictiveImpactResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    impact_score: int = Field(..., ge=0, le=100)
    priority: PriorityLevel
    impact_reason: str = Field(..., min_length=1)

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, value: PriorityLevel | str) -> PriorityLevel:
        if isinstance(value, PriorityLevel):
            return value

        if not isinstance(value, str):
            raise ValueError("Unsupported priority level.")

        normalized_value = value.strip().upper()

        try:
            return PriorityLevel(normalized_value)
        except ValueError as exc:
            raise ValueError("Unsupported priority level.") from exc

    @field_validator("impact_reason")
    @classmethod
    def validate_impact_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Impact reason cannot be empty.")
        return value.strip()


class RoutingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authority: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    routing_reason: str = Field(..., min_length=1)

    @field_validator("authority", "department", "routing_reason")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Routing fields cannot be empty.")
        return value.strip()


class ComplaintWriterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(..., min_length=1)
    complaint_text: str = Field(..., min_length=1)

    @field_validator("subject", "complaint_text")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Complaint draft fields cannot be empty.")
        return value.strip()
