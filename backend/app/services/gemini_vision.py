from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import settings
from app.schemas.ai import SpotFixImageAnalysisResult, ValidationStatus

logger = logging.getLogger(__name__)


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

        data = dict(payload)

        # Backward compatibility if mock or response has category but missing validation_status
        if not data.get("validation_status") and data.get("category"):
            data["validation_status"] = "ACCEPTED"
            data.setdefault("is_civic_issue", True)

        required_fields = {
            "validation_status",
            "visual_explanation",
            "confidence",
        }

        if not required_fields.issubset(data.keys()):
            raise GeminiResponseValidationError(
                "AI response is missing required fields."
            )

        status_str = str(data.get("validation_status") or "").strip().upper()
        if status_str not in {"ACCEPTED", "UNCLEAR", "REJECTED"}:
            raise GeminiResponseValidationError(
                f"Unsupported validation status: {data.get('validation_status')}."
            )

        data["validation_status"] = status_str

        if status_str == "ACCEPTED":
            data["is_civic_issue"] = True
            if not data.get("category"):
                raise GeminiResponseValidationError(
                    "AI response for ACCEPTED status must include a category."
                )
            if not data.get("severity"):
                raise GeminiResponseValidationError(
                    "AI response for ACCEPTED status must include severity."
                )
        else:
            data["is_civic_issue"] = False
            data["category"] = None
            data["severity"] = None
            if not data.get("rejection_reason"):
                data["rejection_reason"] = (
                    str(data.get("visual_explanation") or "").strip()
                    or (
                        "Image quality is insufficient."
                        if status_str == "UNCLEAR"
                        else "No supported civic issue detected."
                    )
                )

        try:
            return SpotFixImageAnalysisResult.model_validate(data)
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
            "You are a civic intelligence visual inspector for Bengaluru SpotFix. "
            "Analyze the image to determine whether a supported civic issue is visibly identifiable. "
            "Supported categories ONLY: "
            "1. POTHOLE: Visible depression, road crater, broken asphalt hole on roadway. "
            "2. GARBAGE: Visible dumped waste, uncollected trash heap, overflowing public dumpster. "
            "3. WATER_LEAKAGE: Visible potable water pipe burst, municipal line leakage spraying or gushing. "
            "4. WATERLOGGING: Visible standing flood water, submerged road/street section due to poor drainage. "
            "5. STREET_LIGHT: Visible damaged, hanging, broken street light pole or unlit civic fixture. "
            "6. FALLEN_TREE: Visible fallen tree, uprooted trunk, or large branch blocking civic road/pathway. "
            "Determine validation_status: "
            "- ACCEPTED: A supported civic issue is visibly identifiable. "
            "- UNCLEAR: Image quality, blur, lighting, angle, or visual evidence is insufficient to verify a civic issue. "
            "- REJECTED: No civic issue is visible (e.g. normal road, selfie, animal, random object) OR the issue shown is an unsupported category (e.g. illegal parking, graffiti, building construction, traffic violation, encroachment). "
            "Rules: "
            "1. If ACCEPTED: is_civic_issue must be true, category must be one of the 6 supported categories, severity must be LOW, MEDIUM, HIGH, or CRITICAL. "
            "A genuine low-severity issue (e.g. minor pothole or small trash pile) must remain ACCEPTED with severity LOW. "
            "2. If UNCLEAR or REJECTED: is_civic_issue must be false, category must be null, severity must be null, and rejection_reason must clearly explain why. "
            "3. Do not invent or assume evidence not visible in the image. Ground visual_explanation strictly in visible details."
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
                        "validation_status": types.Schema(
                            type="STRING",
                            enum=["ACCEPTED", "UNCLEAR", "REJECTED"],
                        ),
                        "is_civic_issue": types.Schema(
                            type="BOOLEAN",
                        ),
                        "category": types.Schema(
                            type="STRING",
                            nullable=True,
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
                            nullable=True,
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
                        "rejection_reason": types.Schema(
                            type="STRING",
                            nullable=True,
                        ),
                    },
                    required=[
                        "validation_status",
                        "is_civic_issue",
                        "confidence",
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
