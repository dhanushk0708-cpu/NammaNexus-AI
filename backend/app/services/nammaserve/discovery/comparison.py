import logging
from app.models.nammaserve import VerificationStatus
from app.schemas.nammaserve import (
    DiscoveryQuery,
    NormalizedProviderResult,
    PriceComparisonItem,
    PriceComparisonSummary,
)

logger = logging.getLogger(__name__)


class PriceComparisonEngine:
    """Engine for aggregating, normalizing, and comparing service prices across platforms and providers."""

    @classmethod
    def build_summary(
        cls,
        query: DiscoveryQuery,
        results: list[NormalizedProviderResult],
    ) -> PriceComparisonSummary | None:
        """Construct a structured price comparison summary across discovered offerings."""
        target_service = query.resolved_service_slug or query.service
        if not target_service:
            return None

        comparable_items: list[PriceComparisonItem] = []
        quote_required_items: list[PriceComparisonItem] = []
        unavailable_items: list[PriceComparisonItem] = []

        seen_entities: set[str] = set()

        for res in results:
            # Only consider results that match the resolved service or category
            res_slug = (res.matched_service_slug or "").lower()
            q_slug = (query.resolved_service_slug or "").lower()
            q_cat = (query.resolved_category_slug or "").lower()

            if q_slug and res_slug and res_slug != q_slug:
                continue

            # Entity deduplication key to avoid repeating the exact same platform offering
            entity_key = f"{res.source_type}:{res.name.lower().strip()}"
            if entity_key in seen_entities:
                continue
            seen_entities.add(entity_key)

            p_type = (res.price_type or "").upper()
            is_platform = str(res.source_type).upper() not in {"LOCAL_DATABASE", "DIRECT_PROVIDER", "INDEPENDENT_PROVIDER"}

            # Check for quote-required or unavailable offerings
            if p_type == "QUOTE_REQUIRED":
                item = cls._to_comparison_item(
                    res,
                    is_platform=is_platform,
                    is_comparable=False,
                    is_available=True,
                    comparability_note="Custom quote required upon provider inspection.",
                )
                quote_required_items.append(item)
                continue

            if p_type == "UNAVAILABLE" or res.verification_status == VerificationStatus.UNAVAILABLE:
                item = cls._to_comparison_item(
                    res,
                    is_platform=is_platform,
                    is_comparable=False,
                    is_available=False,
                    comparability_note="Service currently unavailable from this provider.",
                )
                unavailable_items.append(item)
                continue

            # Check for missing prices
            has_price = res.amount is not None or res.price_min is not None or res.price_max is not None
            if not has_price:
                item = cls._to_comparison_item(
                    res,
                    is_platform=is_platform,
                    is_comparable=False,
                    is_available=True,
                    comparability_note="Price not publicly listed; contact provider for rates.",
                )
                unavailable_items.append(item)
                continue

            # Pricing type distinctions and scope comparability checks
            if p_type == "CONSULTATION_FEE":
                item = cls._to_comparison_item(
                    res,
                    is_platform=is_platform,
                    is_comparable=False,
                    is_available=True,
                    comparability_note="Inspection / visiting fee only; does not cover repair work or parts.",
                )
                comparable_items.append(item)
                continue

            if p_type == "HOURLY":
                item = cls._to_comparison_item(
                    res,
                    is_platform=is_platform,
                    is_comparable=False,
                    is_available=True,
                    comparability_note="Hourly labor rate; total cost depends on service duration.",
                )
                comparable_items.append(item)
                continue

            if p_type == "PER_UNIT":
                item = cls._to_comparison_item(
                    res,
                    is_platform=is_platform,
                    is_comparable=False,
                    is_available=True,
                    comparability_note=f"Per-unit rate ({res.price_unit or 'unit'}); total cost depends on measured quantity.",
                )
                comparable_items.append(item)
                continue

            # Standard job pricing: FIXED, STARTING_AT, RANGE
            comp_note = None
            if p_type == "FIXED":
                comp_note = "Confirmed fixed rate card for standard scope."
            elif p_type == "STARTING_AT":
                comp_note = "Base starting rate; final price depends on on-site scope inspection."
            elif p_type == "RANGE":
                comp_note = "Estimated price range depending on model or capacity."
            if p_type == "FIXED_DEFAULT_OPTION":
                comp_note = "Displayed price is for the platform's default option; other options may cost more."
            elif p_type == "FIXED_BY_VARIANT":
                comp_note = "Price varies by service variant; compare only after selecting the same variant."

            if res.comparability_label == "INSUFFICIENT_EVIDENCE" or res.comparability_label == "NOT_COMPARABLE":
                item = cls._to_comparison_item(
                    res,
                    is_platform=is_platform,
                    is_comparable=False,
                    is_available=True,
                    comparability_note=res.comparability_reason or "Insufficient evidence for a reliable comparison.",
                )
                unavailable_items.append(item)
                continue

            if res.comparability_label == "PARTIALLY_COMPARABLE":
                item = cls._to_comparison_item(
                    res,
                    is_platform=is_platform,
                    is_comparable=False,
                    is_available=True,
                    comparability_note=res.comparability_reason
                    or "Shown side by side for context, but excluded from the comparable benchmark.",
                )
                comparable_items.append(item)
                continue

            item = cls._to_comparison_item(
                res,
                is_platform=is_platform,
                is_comparable=True,
                is_available=True,
                comparability_note=comp_note,
            )
            comparable_items.append(item)

        if not comparable_items and not quote_required_items and not unavailable_items:
            return None

        # Sort comparable items: primary by effective price, secondary by verification status
        def sort_key(item: PriceComparisonItem) -> tuple[float, int]:
            eff_price = item.amount if item.amount is not None else (item.price_min if item.price_min is not None else item.price_max or 999999.0)
            v_rank = 0 if item.verification_status == VerificationStatus.VERIFIED else (1 if item.verification_status == VerificationStatus.PARTIALLY_VERIFIED else 2)
            return (eff_price, v_rank)

        comparable_items.sort(key=sort_key)

        # Compute price ranges ONLY from legitimately comparable whole-service items
        legit_comparables = [i for i in comparable_items if i.is_comparable]
        numeric_prices = [
            i.amount if i.amount is not None else i.price_min
            for i in legit_comparables
            if (i.amount is not None or i.price_min is not None)
        ]
        ceiling_prices = [
            i.price_max if i.price_max is not None else (i.amount if i.amount is not None else i.price_min)
            for i in legit_comparables
            if (i.price_max is not None or i.amount is not None or i.price_min is not None)
        ]

        lowest_price = min(numeric_prices) if numeric_prices else None
        highest_price = max(ceiling_prices) if ceiling_prices else None

        range_display = None
        if lowest_price is not None and highest_price is not None:
            if lowest_price == highest_price:
                range_display = f"₹{int(lowest_price) if float(lowest_price).is_integer() else lowest_price}"
            else:
                low_s = int(lowest_price) if float(lowest_price).is_integer() else lowest_price
                high_s = int(highest_price) if float(highest_price).is_integer() else highest_price
                range_display = f"₹{low_s} – ₹{high_s}"

        # Context-aware summary notes regarding pricing comparability
        has_starting = any(i.pricing_type == "STARTING_AT" for i in legit_comparables)
        has_fixed = any(i.pricing_type == "FIXED" for i in legit_comparables)
        if has_starting and has_fixed:
            summary_notes = "Verified Bengaluru price benchmark reflects both confirmed fixed rate cards and starting estimates. Final quote for starting rates is subject to scope assessment."
        elif has_fixed:
            summary_notes = "Verified Bengaluru price benchmark reflects confirmed platform fixed rate cards for standard scope."
        elif has_starting:
            summary_notes = "Verified Bengaluru price benchmark reflects verified starting rates. Final cost depends on on-site inspection."
        else:
            summary_notes = "Transparent price comparison across official platform rate cards and verified independent service providers in Bengaluru."

        # Count verification statuses
        all_items = comparable_items + quote_required_items + unavailable_items
        v_count = sum(1 for i in all_items if i.verification_status == VerificationStatus.VERIFIED)
        pv_count = sum(1 for i in all_items if i.verification_status == VerificationStatus.PARTIALLY_VERIFIED)
        uv_count = sum(1 for i in all_items if i.verification_status == VerificationStatus.UNVERIFIED)

        benchmark_unit = legit_comparables[0].price_unit if legit_comparables else (comparable_items[0].price_unit if comparable_items else None)

        return PriceComparisonSummary(
            canonical_service_slug=query.resolved_service_slug,
            canonical_service_name=query.resolved_service_name,
            category_slug=query.resolved_category_slug,
            category_name=query.resolved_category_name,
            currency="INR",
            benchmark_unit=benchmark_unit,
            price_range_display=range_display,
            lowest_price=lowest_price,
            highest_price=highest_price,
            verified_count=v_count,
            partially_verified_count=pv_count,
            unverified_count=uv_count,
            quote_required_count=len(quote_required_items),
            unavailable_count=len(unavailable_items),
            comparable_items=comparable_items,
            quote_required_items=quote_required_items,
            unavailable_items=unavailable_items,
            notes=summary_notes,
        )

    @classmethod
    def _to_comparison_item(
        cls,
        res: NormalizedProviderResult,
        is_platform: bool,
        is_comparable: bool,
        is_available: bool,
        comparability_note: str | None = None,
    ) -> PriceComparisonItem:
        return PriceComparisonItem(
            id=res.id,
            name=res.name,
            provider_type="PLATFORM" if is_platform else "INDEPENDENT_PROVIDER",
            pricing_type=res.price_type,
            amount=res.amount,
            price_min=res.price_min,
            price_max=res.price_max,
            price_unit=res.price_unit,
            currency=res.currency or "INR",
            formatted_price=res.formatted_price or "Contact for price",
            is_comparable=is_comparable,
            is_available=is_available,
            verification_status=res.verification_status,
            source=res.source,
            source_url=res.source_url,
            last_verified_at=res.last_verified_at,
            inclusions=res.inclusions,
            conditions=res.conditions,
            evidence_notes=res.evidence_notes,
            booking_url=res.source_url,
            comparability_note=comparability_note,
            comparison_group=res.comparison_group,
            comparability_label=res.comparability_label,
        )
