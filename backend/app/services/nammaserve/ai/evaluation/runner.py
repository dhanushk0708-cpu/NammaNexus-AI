import asyncio
import json
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from app.services.nammaserve.ai.assistant import ServiceAssistant
from app.services.nammaserve.ai.cache import IntentCache
from app.services.nammaserve.ai.evaluation.evaluator import compute_report, evaluate_case
from app.services.nammaserve.ai.evaluation.schemas import (
    CaseEvaluationResult,
    EvaluationDataset,
    EvaluationReport,
)
from app.services.nammaserve.ai.telemetry import InMemoryTelemetryHandler

DEFAULT_DATASET_PATH = (
    Path(__file__).parent / "datasets" / "intent_eval_v1.json"
)


def load_dataset(file_path: Optional[str | Path] = None) -> EvaluationDataset:
    """Load and validate an EvaluationDataset from JSON file."""
    path = Path(file_path) if file_path else DEFAULT_DATASET_PATH
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return EvaluationDataset.model_validate(data)


class EvaluationRunner:
    """Orchestrates deterministic intent evaluation against the golden dataset.

    Key guarantees:
    - Intent caching is explicitly disabled during evaluation to ensure true LLM extraction.
    - Captures provider, model, and latency per case via telemetry.
    - Strictly non-invasive: does not modify production state.
    """

    def __init__(
        self,
        assistant: Optional[ServiceAssistant] = None,
        dataset_path: Optional[str | Path] = None,
    ):
        self.dataset_path = dataset_path or DEFAULT_DATASET_PATH
        self.telemetry = InMemoryTelemetryHandler()

        if assistant is not None:
            self.assistant = assistant
            # Ensure evaluation cache is disabled
            self.assistant.intent_cache = IntentCache(enabled=False)
            if self.assistant.provider_manager is not None:
                self.assistant.provider_manager.telemetry_handler = self.telemetry
        else:
            # Create a standalone assistant instance with disabled cache
            self.assistant = ServiceAssistant(
                db=None,  # Intent extraction does not query database
                intent_cache=IntentCache(enabled=False),
            )
            if self.assistant.provider_manager is not None:
                self.assistant.provider_manager.telemetry_handler = self.telemetry

    async def run(
        self,
        dataset: Optional[EvaluationDataset] = None,
    ) -> EvaluationReport:
        """Execute evaluation across all cases in the dataset."""
        ds = dataset or load_dataset(self.dataset_path)
        results: list[CaseEvaluationResult] = []

        overall_provider: Optional[str] = None
        overall_model: Optional[str] = None

        for case in ds.cases:
            case_req_id = f"eval-{case.id}-{uuid4().hex[:6]}"
            actual_intent, _ = await self.assistant.parse_intent(
                message=case.query,
                request_id=case_req_id,
            )

            # Match telemetry event to extract provider/model/latency
            matched_events = [
                e for e in self.telemetry.events if e.request_id == case_req_id
            ]
            last_event = matched_events[-1] if matched_events else None

            provider_name = last_event.provider if last_event else None
            model_name = last_event.model if last_event else None
            latency_ms = last_event.latency_ms if last_event else None

            if provider_name and not overall_provider:
                overall_provider = provider_name
            if model_name and not overall_model:
                overall_model = model_name

            case_result = evaluate_case(
                case=case,
                actual_intent=actual_intent,
                provider=provider_name,
                model=model_name,
                latency_ms=latency_ms,
            )
            results.append(case_result)

        return compute_report(
            dataset_version=ds.version,
            results=results,
            provider=overall_provider,
            model=overall_model,
        )

    def run_sync(
        self,
        dataset: Optional[EvaluationDataset] = None,
    ) -> EvaluationReport:
        """Synchronous helper for CLI and script execution."""
        return asyncio.run(self.run(dataset))
