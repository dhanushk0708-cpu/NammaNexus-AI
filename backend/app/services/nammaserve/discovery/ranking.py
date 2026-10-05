from app.models.nammaserve import VerificationStatus
from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult


class DeterministicRankingEngine:
    """Deterministic, explainable ranking engine for civic service providers."""

    @classmethod
    def rank_results(
        cls,
        results: list[NormalizedProviderResult],
        query: DiscoveryQuery,
    ) -> list[NormalizedProviderResult]:
        ranked_results: list[NormalizedProviderResult] = []

        for item in results:
            score = 0.0
            reasons: list[str] = []

            # 1. Service match score
            if query.service:
                svc_term = query.service.strip().lower()
                matched_slug = (item.matched_service_slug or "").lower()
                matched_name = (item.matched_service_name or "").lower()

                if svc_term == matched_slug or svc_term.replace("-", " ") == matched_name:
                    score += 40.0
                    reasons.append(f"Direct match for '{item.matched_service_name or query.service}'")
                elif svc_term in matched_slug or svc_term in matched_name:
                    score += 30.0
                    reasons.append(f"Relevant match for '{item.matched_service_name or query.service}'")
                else:
                    score += 15.0
            else:
                score += 20.0

            # 2. Verification status score
            if item.verification_status == VerificationStatus.VERIFIED:
                score += 30.0
                reasons.append("Verified by NammaNexus team")
            elif item.verification_status == VerificationStatus.UNVERIFIED:
                score += 5.0
                reasons.append("Community listing (unverified)")
            elif item.verification_status == VerificationStatus.OUTDATED:
                score += 0.0
                reasons.append("Verification pending update")
            elif item.verification_status == VerificationStatus.FLAGGED:
                score -= 50.0
                reasons.append("Flagged for review")

            # 3. Proximity score
            if item.distance_km is not None:
                if item.distance_km <= 2.0:
                    score += 20.0
                    reasons.append(f"Ultra-close proximity ({item.distance_km:.1f} km away)")
                elif item.distance_km <= 5.0:
                    score += 15.0
                    reasons.append(f"Nearby ({item.distance_km:.1f} km away)")
                elif item.distance_km <= 10.0:
                    score += 10.0
                    reasons.append(f"Within radius ({item.distance_km:.1f} km away)")
                else:
                    score += 5.0
                    reasons.append(f"{item.distance_km:.1f} km away")
            elif query.area and item.area and query.area.lower() in item.area.lower():
                score += 15.0
                reasons.append(f"Located in '{item.area}'")

            # 4. Metadata Completeness
            if item.price_min is not None or item.price_max is not None:
                score += 5.0
                if item.price_min and item.price_max:
                    reasons.append(f"Transparent pricing (₹{int(item.price_min)} - ₹{int(item.price_max)} {item.price_unit or ''})")
                elif item.price_min:
                    reasons.append(f"Starting price: ₹{int(item.price_min)} {item.price_unit or ''}")

            if item.is_emergency_service or query.emergency_only:
                score += 5.0
                reasons.append("24x7 Emergency service")

            # Clamp score between 0.0 and 100.0
            final_score = max(0.0, min(100.0, score))
            item.match_score = round(final_score, 1)
            item.ranking_reasons = reasons
            ranked_results.append(item)

        # Sort primarily by match_score descending, secondarily by distance_km ascending
        ranked_results.sort(
            key=lambda x: (
                -x.match_score,
                x.distance_km if x.distance_km is not None else 999.0,
            )
        )

        return ranked_results
