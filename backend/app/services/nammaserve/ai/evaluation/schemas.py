from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.nammaserve import ServiceIntent


class ExpectedIntent(BaseModel):
    """Ground-truth expected intent fields for an evaluation case."""
    model_config = ConfigDict(extra="ignore")

    service: str = Field(..., description="Expected canonical service slug (e.g. 'water-tanker')")
    location: Optional[str] = Field(default=None, description="Expected Bengaluru locality")
    capacity_litres: Optional[float] = Field(default=None, description="Expected capacity in litres")
    urgent: bool = Field(default=False, description="Expected urgency boolean")


class EvaluationCase(BaseModel):
    """A single evaluation query case."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique case identifier")
    query: str = Field(..., description="Natural language citizen query text")
    expected: ExpectedIntent = Field(..., description="Ground-truth expected intent")


class EvaluationDataset(BaseModel):
    """Versioned collection of golden evaluation cases."""
    model_config = ConfigDict(extra="ignore")

    version: str = Field(..., description="Dataset version (e.g. 'intent_eval_v1')")
    description: Optional[str] = Field(default=None)
    cases: list[EvaluationCase] = Field(default_factory=list)


@dataclass
class CaseEvaluationResult:
    """Evaluation scoring outcome for a single case."""

    case_id: str
    query: str
    expected: ExpectedIntent
    actual: ServiceIntent
    passed: bool
    failed_fields: list[str]
    field_results: dict[str, bool]
    provider: Optional[str] = None
    model: Optional[str] = None
    latency_ms: Optional[float] = None


@dataclass
class EvaluationReport:
    """Comprehensive, deterministic evaluation report across a dataset."""

    dataset_version: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    provider: Optional[str] = None
    model: Optional[str] = None
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    case_pass_rate: float = 0.0
    service_accuracy: float = 0.0
    location_accuracy: float = 0.0
    capacity_accuracy: float = 0.0
    urgency_accuracy: float = 0.0
    total_field_accuracy: float = 0.0
    results: list[CaseEvaluationResult] = field(default_factory=list)

    def summary_text(self) -> str:
        """Format a human-readable console report."""
        lines = [
            "==================================================",
            "NammaServe AI Intent Extraction Evaluation",
            "==================================================",
            f"Dataset:            {self.dataset_version}",
            f"Provider/Model:     {self.provider or 'N/A'} ({self.model or 'N/A'})",
            f"Timestamp:          {self.timestamp}",
            f"Total Cases:        {self.total_cases}",
            f"Passed Cases:       {self.passed_cases}",
            f"Failed Cases:       {self.failed_cases}",
            "--------------------------------------------------",
            f"Case Pass Rate:     {self.case_pass_rate:.1f}%",
            f"Service Accuracy:   {self.service_accuracy:.1f}%",
            f"Location Accuracy:  {self.location_accuracy:.1f}%",
            f"Capacity Accuracy:  {self.capacity_accuracy:.1f}%",
            f"Urgency Accuracy:   {self.urgency_accuracy:.1f}%",
            f"Total Field Acc:    {self.total_field_accuracy:.1f}%",
            "==================================================",
        ]

        if self.failed_cases > 0:
            lines.append("Failed Cases Details:")
            for r in self.results:
                if not r.passed:
                    lines.append(f"\n[Case: {r.case_id}]")
                    lines.append(f"  Query:    \"{r.query}\"")
                    lines.append(
                        f"  Expected: service={r.expected.service}, location={r.expected.location}, "
                        f"capacity={r.expected.capacity_litres}, urgent={r.expected.urgent}"
                    )
                    lines.append(
                        f"  Actual:   service={r.actual.service}, location={r.actual.location}, "
                        f"capacity={r.actual.capacity_litres}, urgent={r.actual.urgent}"
                    )
                    lines.append(f"  Failed:   {', '.join(r.failed_fields)}")
            lines.append("==================================================")

        return "\n".join(lines)
