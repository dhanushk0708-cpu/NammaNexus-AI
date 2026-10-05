import json

from app.core.config import settings
from app.schemas.ai import SpotFixImageAnalysisResult
from app.services.gemini_vision import (
    GeminiConfigurationError,
    GeminiResponseValidationError,
    GeminiVisionService,
)


class FakeGeminiClient:
    def __init__(self, payload):
        self.payload = payload
        self.models = self

    def generate_content(self, contents, **kwargs):
        class FakeResponse:
            def __init__(self, payload):
                self.text = json.dumps(payload)

        return FakeResponse(self.payload)


def test_valid_structured_ai_result():
    payload = {
        "category": "POTHOLE",
        "confidence": 0.94,
        "severity": "HIGH",
        "visual_explanation": "Large pothole across the road lane.",
    }

    original_key = settings.gemini_api_key
    settings.gemini_api_key = "test-key"
    try:
        service = GeminiVisionService(client=FakeGeminiClient(payload))
        result = service.analyze_image(b"fake-bytes", mime_type="image/jpeg")

        assert isinstance(result, SpotFixImageAnalysisResult)
        assert result.category == "POTHOLE"
        assert result.confidence == 0.94
        assert result.severity == "HIGH"
        assert result.visual_explanation == "Large pothole across the road lane."
    finally:
        settings.gemini_api_key = original_key


def test_malformed_ai_output():
    original_key = settings.gemini_api_key
    settings.gemini_api_key = "test-key"

    try:
        service = GeminiVisionService(
            client=FakeGeminiClient({"category": "POTHOLE"})
        )

        try:
            service.analyze_image(b"fake-bytes")
            assert False, "Expected validation error"
        except GeminiResponseValidationError:
            pass
    finally:
        settings.gemini_api_key = original_key


def test_invalid_category():
    payload = {
        "category": "INVALID_CATEGORY",
        "confidence": 0.5,
        "severity": "LOW",
        "visual_explanation": "This is not supported.",
    }

    original_key = settings.gemini_api_key
    settings.gemini_api_key = "test-key"

    try:
        service = GeminiVisionService(client=FakeGeminiClient(payload))

        try:
            service.analyze_image(b"fake-bytes")
            assert False, "Expected validation error"
        except GeminiResponseValidationError:
            pass
    finally:
        settings.gemini_api_key = original_key


def test_invalid_severity():
    payload = {
        "category": "GARBAGE",
        "confidence": 0.8,
        "severity": "URGENT",
        "visual_explanation": "Overflowing bins near the corner.",
    }

    original_key = settings.gemini_api_key
    settings.gemini_api_key = "test-key"

    try:
        service = GeminiVisionService(client=FakeGeminiClient(payload))

        try:
            service.analyze_image(b"fake-bytes")
            assert False, "Expected validation error"
        except GeminiResponseValidationError:
            pass
    finally:
        settings.gemini_api_key = original_key


def test_current_official_sdk_client_shape():
    payload = {
        "category": "STREET_LIGHT",
        "confidence": 0.87,
        "severity": "MEDIUM",
        "visual_explanation": "A broken street light with exposed wiring.",
    }

    class FakeOfficialGeminiClient:
        class models:
            @staticmethod
            def generate_content(*, model, contents, **kwargs):
                class FakeResponse:
                    text = json.dumps(payload)

                return FakeResponse()

    original_key = settings.gemini_api_key
    settings.gemini_api_key = "test-key"

    try:
        service = GeminiVisionService(client=FakeOfficialGeminiClient())

        result = service.analyze_image(
            b"fake-bytes",
            mime_type="image/jpeg",
        )

        assert result.category == "STREET_LIGHT"
        assert result.confidence == 0.87
        assert result.severity == "MEDIUM"
        assert (
            result.visual_explanation
            == "A broken street light with exposed wiring."
        )
    finally:
        settings.gemini_api_key = original_key


def test_google_genai_structured_response_payload():
    payload = {
        "category": "GARBAGE",
        "confidence": 0.79,
        "severity": "HIGH",
        "visual_explanation": "Overflowing waste bins on the roadside.",
    }

    class FakeTextPart:
        text = json.dumps(payload)

    class FakeContent:
        def __init__(self, parts):
            self.parts = parts

    class FakeCandidate:
        def __init__(self, content):
            self.content = content

    class FakeGoogleGenAIResponse:
        def __init__(self):
            self.candidates = [
                FakeCandidate(
                    FakeContent([FakeTextPart()])
                )
            ]

    original_key = settings.gemini_api_key
    settings.gemini_api_key = "test-key"

    try:
        service = GeminiVisionService(
            client=FakeGeminiClient(payload)
        )

        extracted = service._extract_payload(
            FakeGoogleGenAIResponse()
        )

        assert extracted == payload

        result = service._normalize_result(extracted)

        assert result.category == "GARBAGE"
        assert result.severity == "HIGH"
    finally:
        settings.gemini_api_key = original_key


def test_missing_api_key_behavior():
    original_key = settings.gemini_api_key
    settings.gemini_api_key = None

    try:
        service = GeminiVisionService()

        try:
            service.analyze_image(b"fake-bytes")
            assert False, "Expected configuration error"
        except GeminiConfigurationError:
            pass
    finally:
        settings.gemini_api_key = original_key