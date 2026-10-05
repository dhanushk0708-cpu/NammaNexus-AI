from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import settings
from app.schemas.ai import SpotFixImageAnalysisResult


class GeminiVisionServiceError(RuntimeError):
    """Raised when Gemini analysis cannot be completed safely."""


class GeminiConfigurationError(GeminiVisionServiceError):
    """Raised when Gemini is not configured for app use."""


class GeminiResponseValidationError(GeminiVisionServiceError):
    """Raised when Gemini returns malformed or untrusted data."""


class GeminiVisionService:
    def __init__(self, client: Any | None = None):
        self.client = client

    @property
    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key)

    def _require_client(self) -> Any:
        if self.client is not None:
            return self.client

        if not self.is_configured:
            raise GeminiConfigurationError("Gemini API key is not configured.")

        try:
            from google import genai
        except ImportError as exc:
            raise GeminiConfigurationError(
                "Gemini SDK is not installed for this environment."
            ) from exc

        return genai.Client(api_key=settings.gemini_api_key)

    def _normalize_result(self, payload: Any) -> SpotFixImageAnalysisResult:
        if not isinstance(payload, dict):
            raise GeminiResponseValidationError(
                "AI response must be a structured object."
            )

        required_fields = {
            "category",
            "confidence",
            "severity",
            "visual_explanation",
        }

        if not required_fields.issubset(payload.keys()):
            raise GeminiResponseValidationError(
                "AI response is missing required fields."
            )

        normalized_payload = {
            "category": payload.get("category"),
            "confidence": payload.get("confidence"),
            "severity": payload.get("severity"),
            "visual_explanation": payload.get("visual_explanation"),
        }

        if any(value is None for value in normalized_payload.values()):
            raise GeminiResponseValidationError(
                "AI response contains null required fields."
            )

        if isinstance(normalized_payload["category"], str):
            normalized_payload["category"] = normalized_payload["category"].strip()

        if isinstance(normalized_payload["severity"], str):
            normalized_payload["severity"] = normalized_payload["severity"].strip()

        if isinstance(normalized_payload["visual_explanation"], str):
            normalized_payload["visual_explanation"] = normalized_payload[
                "visual_explanation"
            ].strip()

        try:
            return SpotFixImageAnalysisResult.model_validate(normalized_payload)
        except Exception as exc:
            raise GeminiResponseValidationError(
                "AI response failed schema validation."
            ) from exc

    def _extract_payload(self, response: Any) -> Any:
        if response is None:
            raise GeminiResponseValidationError("AI response was empty.")

        def parse_json_text(raw_text: Any) -> Any:
            if isinstance(raw_text, (dict, list)):
                return raw_text

            if not isinstance(raw_text, str) or not raw_text.strip():
                raise GeminiResponseValidationError("AI response was empty.")

            cleaned = raw_text.strip()

            cleaned = re.sub(
                r"^```(?:json)?\s*",
                "",
                cleaned,
                flags=re.I,
            )

            cleaned = re.sub(
                r"\s*```\s*$",
                "",
                cleaned,
                flags=re.I,
            )

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as exc:
                raise GeminiResponseValidationError(
                    "AI response was not valid JSON."
                ) from exc

        if hasattr(response, "text"):
            try:
                return parse_json_text(response.text)
            except GeminiResponseValidationError:
                pass

        if hasattr(response, "candidates"):
            candidates = response.candidates

            if isinstance(candidates, list) and candidates:
                first_candidate = candidates[0]
                candidate_content = getattr(
                    first_candidate,
                    "content",
                    None,
                )

                if candidate_content is not None:
                    parts = getattr(
                        candidate_content,
                        "parts",
                        None,
                    )

                    if isinstance(parts, list):
                        for part in parts:
                            json_value = None

                            if hasattr(part, "text"):
                                json_value = getattr(part, "text")

                            elif hasattr(part, "to_json_dict"):
                                json_value = part.to_json_dict().get("text")

                            if json_value is not None:
                                try:
                                    return parse_json_text(json_value)
                                except GeminiResponseValidationError:
                                    continue

        if isinstance(response, str):
            return parse_json_text(response)

        if isinstance(response, dict):
            return response

        raise GeminiResponseValidationError("AI response format is unsupported.")

    def analyze_image(
        self,
        image_bytes: bytes,
        *,
        mime_type: str | None = None,
    ) -> SpotFixImageAnalysisResult:
        if not self.is_configured and self.client is None:
            raise GeminiConfigurationError("Gemini API key is not configured.")

        client = self._require_client()

        prompt = (
            "Analyze the civic issue shown in this image. "
            "Use only one of these categories: "
            "POTHOLE, GARBAGE, WATER_LEAKAGE, WATERLOGGING, "
            "STREET_LIGHT, FALLEN_TREE. "
            "Return the category, confidence, severity, and a concise "
            "visual explanation based only on visible evidence. "
            "If the image does not clearly match a supported category, "
            "do not invent evidence."
        )

        try:
            if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                from google.genai import types

                user_content = types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=mime_type or "image/jpeg",
                        ),
                    ],
                )

                response_schema = types.Schema(
                    type="OBJECT",
                    properties={
                        "category": types.Schema(
                            type="STRING",
                            enum=[
                                "POTHOLE",
                                "GARBAGE",
                                "WATER_LEAKAGE",
                                "WATERLOGGING",
                                "STREET_LIGHT",
                                "FALLEN_TREE",
                            ],
                        ),
                        "confidence": types.Schema(
                            type="NUMBER",
                            minimum=0,
                            maximum=1,
                        ),
                        "severity": types.Schema(
                            type="STRING",
                            enum=[
                                "LOW",
                                "MEDIUM",
                                "HIGH",
                                "CRITICAL",
                            ],
                        ),
                        "visual_explanation": types.Schema(
                            type="STRING",
                        ),
                    },
                    required=[
                        "category",
                        "confidence",
                        "severity",
                        "visual_explanation",
                    ],
                )

                response = client.models.generate_content(
                    model=settings.gemini_model,
                    contents=[user_content],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                    ),
                )

            elif hasattr(client, "generate_content"):
                response = client.generate_content(
                    [
                        prompt,
                        {
                            "mime_type": mime_type or "image/jpeg",
                            "data": image_bytes,
                        },
                    ]
                )

            else:
                raise GeminiConfigurationError(
                    "Gemini client does not support image analysis."
                )

        except GeminiVisionServiceError:
            raise

        except TimeoutError as exc:
            raise GeminiVisionServiceError("Gemini request timed out.") from exc

        except Exception as exc:
            raise GeminiVisionServiceError("Gemini image analysis failed.") from exc

        payload = self._extract_payload(response)

        return self._normalize_result(payload)
