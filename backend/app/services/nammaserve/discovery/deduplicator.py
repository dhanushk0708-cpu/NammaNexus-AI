import re

from app.models.nammaserve import VerificationStatus
from app.schemas.nammaserve import NormalizedProviderResult
from app.services.nammaserve.discovery.distance import haversine_distance_km


def normalize_phone(phone: str | None) -> str:
    """Normalize phone number to 10-digit standard for deduplication."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("91") and len(digits) == 12:
        return digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        return digits[1:]
    return digits


def normalize_name(name: str) -> str:
    """Normalize business name for matching."""
    return re.sub(r"[^a-zA-Z0-9]", "", name.lower())


class ResultDeduplicator:
    """Deduplicates results across multiple source connectors."""

    @classmethod
    def deduplicate(
        cls, results: list[NormalizedProviderResult]
    ) -> list[NormalizedProviderResult]:
        unique_results: list[NormalizedProviderResult] = []

        for candidate in results:
            cand_phone = normalize_phone(candidate.phone)
            cand_name = normalize_name(candidate.name)

            matched_idx = -1
            for idx, existing in enumerate(unique_results):
                ext_phone = normalize_phone(existing.phone)
                ext_name = normalize_name(existing.name)

                # Match by valid 10-digit phone
                if cand_phone and ext_phone and cand_phone == ext_phone:
                    matched_idx = idx
                    break

                # Match by name and spatial proximity (< 500m)
                if cand_name == ext_name:
                    if (
                        candidate.latitude is not None
                        and candidate.longitude is not None
                        and existing.latitude is not None
                        and existing.longitude is not None
                    ):
                        dist_diff = haversine_distance_km(
                            candidate.latitude,
                            candidate.longitude,
                            existing.latitude,
                            existing.longitude,
                        )
                        if dist_diff <= 0.5:
                            matched_idx = idx
                            break
                    elif candidate.area and existing.area and candidate.area.lower() == existing.area.lower():
                        matched_idx = idx
                        break

            if matched_idx >= 0:
                # Merge: prefer verified / local record
                existing = unique_results[matched_idx]
                if (
                    candidate.verification_status == VerificationStatus.VERIFIED
                    and existing.verification_status != VerificationStatus.VERIFIED
                ):
                    # Candidate is verified, replace existing
                    unique_results[matched_idx] = candidate
                else:
                    # Keep existing, but fill missing info
                    if not existing.address and candidate.address:
                        existing.address = candidate.address
                    if not existing.source_url and candidate.source_url:
                        existing.source_url = candidate.source_url
                    if not existing.operating_hours and candidate.operating_hours:
                        existing.operating_hours = candidate.operating_hours
            else:
                unique_results.append(candidate)

        return unique_results
