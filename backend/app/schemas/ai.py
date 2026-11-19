from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class ValidationStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    UNCLEAR = "UNCLEAR"
    REJECTED = "REJECTED"


class SpotFixImageAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    validation_status: ValidationStatus = ValidationStatus.ACCEPTED
    is_civic_issue: bool = True
    category: SpotFixCategory | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: SeverityLevel | None = None
    visual_explanation: str = Field(..., min_length=1)
    rejection_reason: str | None = None

    @field_validator("validation_status", mode="before")
    @classmethod
    def validate_validation_status(
        cls, value: ValidationStatus | str
    ) -> ValidationStatus:
        if isinstance(value, ValidationStatus):
            return value
        if not isinstance(value, str):
            raise ValueError("Unsupported validation status.")
        normalized = value.strip().upper()
        try:
            return ValidationStatus(normalized)
        except ValueError as exc:
            raise ValueError(f"Unsupported validation status: {value}") from exc

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(
        cls, value: SpotFixCategory | str | None
    ) -> SpotFixCategory | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
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
    def validate_severity(
        cls, value: SeverityLevel | str | None
    ) -> SeverityLevel | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
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
        if not value or not value.strip():
            raise ValueError("Visual explanation cannot be empty.")
        return value.strip()

    @field_validator("rejection_reason", mode="before")
    @classmethod
    def validate_rejection_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return str(value)

    @model_validator(mode="after")
    def validate_status_rules(self) -> "SpotFixImageAnalysisResult":
        if self.validation_status == ValidationStatus.ACCEPTED:
            if not self.is_civic_issue:
                raise ValueError("An ACCEPTED image must have is_civic_issue=True.")
            if self.category is None:
                raise ValueError("An ACCEPTED image must have a supported category.")
            if self.severity is None:
                raise ValueError("An ACCEPTED image must have a severity level.")
        elif self.validation_status == ValidationStatus.UNCLEAR:
            self.category = None
            self.severity = None
            self.is_civic_issue = False
            if not self.rejection_reason:
                self.rejection_reason = "Image quality or visual evidence is insufficient to verify a civic issue."
        elif self.validation_status == ValidationStatus.REJECTED:
            self.category = None
            self.severity = None
            self.is_civic_issue = False
            if not self.rejection_reason:
                self.rejection_reason = "No supported civic issue is visible in the image."
        return self


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
