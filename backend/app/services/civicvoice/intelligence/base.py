from abc import ABC, abstractmethod
import re
from typing import Any

from app.models.civicvoice import CivicVoiceSourceRecord
from app.schemas.civicvoice import (
    ContentIntent,
    OpinionCategory,
    SentimentLabel,
)


def detect_text_language(text: str | None) -> str:
    """Detects whether text is primarily Kannada, English, Mixed, or Unknown.

    Uses Unicode character ranges:
    - Kannada Unicode block: U+0C80 to U+0CFF
    - Latin/English block: [a-zA-Z]
    Does not mutate or corrupt the original text.
    """
    if not text or not text.strip():
        return "unknown"

    kannada_chars = len(re.findall(r"[\u0C80-\u0CFF]", text))
    latin_chars = len(re.findall(r"[a-zA-Z]", text))

    if kannada_chars > 0 and latin_chars > 0:
        # If both are present in meaningful amounts, mark as mixed
        if kannada_chars >= 5 and latin_chars >= 5:
            return "mixed"
        elif kannada_chars > latin_chars:
            return "kn"
        else:
            return "en"
    elif kannada_chars > 0:
        return "kn"
    elif latin_chars > 0:
        return "en"

    return "unknown"


class AnalyzedOpinionResult:
    """Structured in-memory result of analyzing a single source record."""

    def __init__(
        self,
        category: OpinionCategory,
        sentiment: SentimentLabel,
        content_intent: ContentIntent,
        confidence: str,
        explanation: str,
        detected_language: str,
        has_complaint: bool = False,
        extracted_complaint: str | None = None,
        has_suggestion: bool = False,
        extracted_suggestion: str | None = None,
        theme_id: str | None = None,
        theme_label: str | None = None,
        analysis_method: str = "rule_based_multilingual",
        analysis_version: str = "v1.0",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.category = category
        self.sentiment = sentiment
        self.content_intent = content_intent
        self.confidence = confidence
        self.explanation = explanation
        self.detected_language = detected_language
        self.has_complaint = has_complaint
        self.extracted_complaint = extracted_complaint
        self.has_suggestion = has_suggestion
        self.extracted_suggestion = extracted_suggestion
        self.theme_id = theme_id
        self.theme_label = theme_label
        self.analysis_method = analysis_method
        self.analysis_version = analysis_version
        self.metadata = metadata or {}


class BaseOpinionAnalyzer(ABC):
    """Abstract interface for opinion intelligence analyzers."""

    @abstractmethod
    def analyze_record(self, record: CivicVoiceSourceRecord) -> AnalyzedOpinionResult:
        """Analyzes a single source record and returns a structured opinion result."""
        pass
