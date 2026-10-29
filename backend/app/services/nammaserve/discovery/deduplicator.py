import re
from typing import Any

from app.models.nammaserve import VerificationStatus
from app.schemas.nammaserve import NormalizedProviderResult, ServiceMatchLevel
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
    return digits if len(digits) == 10 else ""


def normalize_name(name: str) -> str:
    """Normalize business name for matching."""
    return re.sub(r"[^a-zA-Z0-9]", "", name.lower())


class ResultDeduplicator:
    """Deduplicates results across multiple source connectors with provenance preservation."""

    @classmethod
    def deduplicate(
        cls, results: list[NormalizedProviderResult]
    ) -> list[NormalizedProviderResult]:
        unique_results: list[NormalizedProviderResult] = []

        for candidate in results:
            cand_phone = normalize_phone(candidate.phone)
            cand_name = normalize_name(candidate.name)
            cand_ext_ids = candidate.external_ids or {}

            matched_idx = -1
            for idx, existing in enumerate(unique_results):
                ext_phone = normalize_phone(existing.phone)
                ext_name = normalize_name(existing.name)
                ext_ids = existing.external_ids or {}

                # 1. Primary Match: Stable External ID
                # If both share any non-empty stable external ID key-value pair, they are the same entity
                common_keys = set(cand_ext_ids.keys()) & set(ext_ids.keys())
                has_ext_id_match = False
                for k in common_keys:
                    if cand_ext_ids[k] and ext_ids[k] and cand_ext_ids[k] == ext_ids[k]:
                        has_ext_id_match = True
                        break

                if has_ext_id_match:
                    matched_idx = idx
                    break

                # 2. Secondary Match: Valid 10-digit phone
                if cand_phone and ext_phone and cand_phone == ext_phone:
                    matched_idx = idx
                    break

                # 3. Conservative Match: Identical normalized name + tight spatial proximity (<= 100 meters)
                if cand_name and ext_name and cand_name == ext_name:
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
                        # Conservative 100m radius to avoid false merging in dense Bengaluru commercial areas
                        if dist_diff <= 0.10:
                            matched_idx = idx
                            break
                    elif (
                        len(cand_name) >= 6
                        and candidate.area
                        and existing.area
                        and candidate.area.strip().lower() == existing.area.strip().lower()
                    ):
                        # Only match non-coordinate entries if the name is specific (>= 6 chars) and locality matches exactly
                        matched_idx = idx
                        break

            if matched_idx >= 0:
                cls._merge_records(unique_results, matched_idx, candidate)
            else:
                # Ensure candidate sources list contains at least its primary source
                if not candidate.sources:
                    candidate.sources = [candidate.source]
                unique_results.append(candidate)

        return unique_results

    @classmethod
    def _merge_records(
        cls,
        unique_results: list[NormalizedProviderResult],
        target_idx: int,
        incoming: NormalizedProviderResult,
    ) -> None:
        """Merge incoming record into existing record with verification protection and provenance."""
        existing = unique_results[target_idx]

        # Determine which record should be the base
        # Never overwrite a VERIFIED record with an UNVERIFIED discovery record
        if (
            incoming.verification_status == VerificationStatus.VERIFIED
            and existing.verification_status != VerificationStatus.VERIFIED
        ):
            base = incoming
            donor = existing
        else:
            base = existing
            donor = incoming

        # Combine source provenance
        donor_sources = donor.sources or ([donor.source] if donor.source else [])
        base_sources = base.sources or ([base.source] if base.source else [])
        combined_sources = list(dict.fromkeys(base_sources + donor_sources))
        base.sources = combined_sources

        # Combine external IDs
        combined_ext_ids = dict(donor.external_ids or {})
        combined_ext_ids.update(base.external_ids or {})
        base.external_ids = combined_ext_ids

        # Preserve higher service match level: CONFIRMED > PROBABLE > UNCONFIRMED
        match_order = {
            ServiceMatchLevel.CONFIRMED: 3,
            ServiceMatchLevel.PROBABLE: 2,
            ServiceMatchLevel.UNCONFIRMED: 1,
            None: 0,
        }
        base_lvl = match_order.get(base.service_match_level, 0)
        donor_lvl = match_order.get(donor.service_match_level, 0)
        if donor_lvl > base_lvl:
            base.service_match_level = donor.service_match_level
            base.service_match_confidence = donor.service_match_confidence
            base.service_match_reason = donor.service_match_reason

        # Fill in missing metadata fields on base without overwriting verified details
        if not base.phone and donor.phone:
            base.phone = donor.phone
        if not base.alternate_phone and donor.alternate_phone:
            base.alternate_phone = donor.alternate_phone
        if not base.address and donor.address:
            base.address = donor.address
        if not base.website and donor.website:
            base.website = donor.website
        if not base.operating_hours and donor.operating_hours:
            base.operating_hours = donor.operating_hours
        if not base.source_url and donor.source_url:
            base.source_url = donor.source_url
        if base.latitude is None and donor.latitude is not None:
            base.latitude = donor.latitude
            base.longitude = donor.longitude
            base.distance_km = donor.distance_km
        if not base.rating and donor.rating:
            base.rating = donor.rating
            base.review_count = donor.review_count
        if base.price_min is None and donor.price_min is not None:
            base.price_min = donor.price_min
            base.price_max = donor.price_max
            base.price_unit = donor.price_unit
            base.price_type = donor.price_type
            base.inclusions = donor.inclusions
            base.exclusions = donor.exclusions
            base.conditions = donor.conditions
        if not base.last_checked_at and donor.last_checked_at:
            base.last_checked_at = donor.last_checked_at
        if not base.discovered_at and donor.discovered_at:
            base.discovered_at = donor.discovered_at

        unique_results[target_idx] = base
