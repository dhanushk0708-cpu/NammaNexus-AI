from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.nammadeals import (
    Business,
    BusinessStatus,
    Campaign,
    CampaignApprovalStatus,
    Offer,
    PromotionEvent,
    PromotionEventType,
    TargetingStrategy,
)
from app.schemas.nammadeals import (
    LocationPolicy,
    PromotionItem,
    PromotionOfferItem,
    PromotionSelectionRequest,
    PromotionSelectionResponse,
)
from app.services.nammadeals.location import evaluate_location_match

logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def select_promotions(
    db: Session,
    request: PromotionSelectionRequest,
    citizen_user_id: str | None = None,
) -> PromotionSelectionResponse:
    """Intelligent promotion selection engine.

    Selects 2-3 highly relevant local business promotions based on citizen profile
    and/or SpotFix complaint locations, applying frequency caps, priority, and rotation.
    """
    effective_citizen_id = citizen_user_id or request.citizen_user_id or "anonymous_citizen"
    now = datetime.now(timezone.utc)

    # 1. Fetch candidate campaigns that are APPROVED, active, and within valid dates
    candidate_campaigns = (
        db.query(Campaign)
        .join(Business, Campaign.business_id == Business.id)
        .filter(
            Campaign.approval_status == CampaignApprovalStatus.APPROVED.value,
            Campaign.is_active.is_(True),
            Business.status == BusinessStatus.APPROVED.value,
        )
        .all()
    )

    # Filter out expired or not-yet-started campaigns (safe timezone check)
    valid_campaigns: list[Campaign] = []
    for c in candidate_campaigns:
        start_utc = _ensure_utc(c.start_date)
        end_utc = _ensure_utc(c.end_date)
        if start_utc <= now <= end_utc:
            valid_campaigns.append(c)

    if not valid_campaigns:
        return PromotionSelectionResponse(
            promotions=[],
            total_selected=0,
            location_sources_evaluated=[],
            policy_applied=request.location_policy,
        )

    # 2. Check per-citizen frequency caps (impressions in the last 24 hours)
    cutoff_24h = now - timedelta(hours=24)
    user_impressions = (
        db.query(PromotionEvent.campaign_id, func.count(PromotionEvent.id))
        .filter(
            PromotionEvent.citizen_user_id == effective_citizen_id,
            PromotionEvent.event_type == PromotionEventType.IMPRESSION.value,
            PromotionEvent.created_at >= cutoff_24h,
        )
        .group_by(PromotionEvent.campaign_id)
        .all()
    )
    impression_counts: dict[str, int] = {camp_id: count for camp_id, count in user_impressions}

    # Filter out campaigns that hit the citizen's frequency limit
    uncapped_campaigns: list[Campaign] = []
    for c in valid_campaigns:
        shown_count = impression_counts.get(c.id, 0)
        if shown_count < c.frequency_limit_per_user:
            uncapped_campaigns.append(c)

    # 3. Determine location sources and policy
    complaint_loc = request.complaint_location
    profile_loc = request.profile_location
    policy = request.location_policy

    has_complaint = (
        complaint_loc is not None
        and (complaint_loc.latitude is not None or complaint_loc.area is not None)
    )
    has_profile = (
        profile_loc is not None
        and (
            profile_loc.latitude is not None
            or profile_loc.area is not None
            or profile_loc.pincode is not None
        )
    )

    sources_evaluated: list[str] = []
    location_eval_sequence: list[tuple[str, dict]] = []

    if policy == LocationPolicy.COMPLAINT_ONLY:
        if has_complaint and complaint_loc:
            sources_evaluated.append("COMPLAINT")
            location_eval_sequence.append(
                (
                    "COMPLAINT",
                    {
                        "latitude": complaint_loc.latitude,
                        "longitude": complaint_loc.longitude,
                        "area": complaint_loc.area,
                        "city": "Bengaluru",
                    },
                )
            )
    elif policy == LocationPolicy.PROFILE_ONLY:
        if has_profile and profile_loc:
            sources_evaluated.append("PROFILE")
            location_eval_sequence.append(
                (
                    "PROFILE",
                    {
                        "latitude": profile_loc.latitude,
                        "longitude": profile_loc.longitude,
                        "area": profile_loc.area,
                        "pincode": profile_loc.pincode,
                        "city": profile_loc.city,
                    },
                )
            )
    elif policy == LocationPolicy.PREFER_COMPLAINT:
        if has_complaint and complaint_loc:
            sources_evaluated.append("COMPLAINT")
            location_eval_sequence.append(
                (
                    "COMPLAINT",
                    {
                        "latitude": complaint_loc.latitude,
                        "longitude": complaint_loc.longitude,
                        "area": complaint_loc.area,
                        "city": "Bengaluru",
                    },
                )
            )
        if has_profile and profile_loc:
            sources_evaluated.append("PROFILE")
            location_eval_sequence.append(
                (
                    "PROFILE",
                    {
                        "latitude": profile_loc.latitude,
                        "longitude": profile_loc.longitude,
                        "area": profile_loc.area,
                        "pincode": profile_loc.pincode,
                        "city": profile_loc.city,
                    },
                )
            )
    elif policy == LocationPolicy.PREFER_PROFILE:
        if has_profile and profile_loc:
            sources_evaluated.append("PROFILE")
            location_eval_sequence.append(
                (
                    "PROFILE",
                    {
                        "latitude": profile_loc.latitude,
                        "longitude": profile_loc.longitude,
                        "area": profile_loc.area,
                        "pincode": profile_loc.pincode,
                        "city": profile_loc.city,
                    },
                )
            )
        if has_complaint and complaint_loc:
            sources_evaluated.append("COMPLAINT")
            location_eval_sequence.append(
                (
                    "COMPLAINT",
                    {
                        "latitude": complaint_loc.latitude,
                        "longitude": complaint_loc.longitude,
                        "area": complaint_loc.area,
                        "city": "Bengaluru",
                    },
                )
            )
    else:  # COMBINED
        if has_complaint and complaint_loc:
            sources_evaluated.append("COMPLAINT")
            location_eval_sequence.append(
                (
                    "COMPLAINT",
                    {
                        "latitude": complaint_loc.latitude,
                        "longitude": complaint_loc.longitude,
                        "area": complaint_loc.area,
                        "city": "Bengaluru",
                    },
                )
            )
        if has_profile and profile_loc:
            sources_evaluated.append("PROFILE")
            location_eval_sequence.append(
                (
                    "PROFILE",
                    {
                        "latitude": profile_loc.latitude,
                        "longitude": profile_loc.longitude,
                        "area": profile_loc.area,
                        "pincode": profile_loc.pincode,
                        "city": profile_loc.city,
                    },
                )
            )

    selected_items: list[PromotionItem] = []
    seen_campaign_ids: set[str] = set()
    seen_business_ids: set[str] = set()

    def get_valid_offers(campaign: Campaign) -> list[PromotionOfferItem]:
        valid_offers: list[PromotionOfferItem] = []
        for o in campaign.offers:
            if o.is_active and o.redemption_count < o.max_redemptions:
                vf = _ensure_utc(o.valid_from)
                vu = _ensure_utc(o.valid_until)
                if vf <= now <= vu:
                    valid_offers.append(PromotionOfferItem.model_validate(o))
        return valid_offers

    # Helper to attempt candidate matching
    def try_match_candidates(
        source_label: str,
        loc_context: dict,
        allow_nearby: bool = False,
    ) -> list[tuple[float, Campaign, float | None, str]]:
        matches: list[tuple[float, Campaign, float | None, str]] = []
        for c in uncapped_campaigns:
            if c.id in seen_campaign_ids or c.business_id in seen_business_ids:
                continue

            offers = get_valid_offers(c)
            if not offers:
                continue

            is_match, dist, match_type = evaluate_location_match(
                c,
                latitude=loc_context.get("latitude"),
                longitude=loc_context.get("longitude"),
                area=loc_context.get("area"),
                pincode=loc_context.get("pincode"),
                city=loc_context.get("city"),
                allow_nearby_expansion=allow_nearby,
            )
            if is_match:
                # Scoring: priority * 100 - (impressions * 30 for rotation) + distance bonus
                score = c.priority * 100.0
                shown_count = impression_counts.get(c.id, 0)
                score -= shown_count * 30.0  # Rotation penalty
                if dist is not None:
                    score += max(0.0, 50.0 - dist * 3.0)  # Proximity bonus

                effective_source = source_label
                if match_type == "NEARBY":
                    effective_source = "NEARBY"
                elif match_type == "CITYWIDE":
                    effective_source = "CITYWIDE"
                elif match_type == "ONLINE":
                    effective_source = "ONLINE"

                matches.append((score, c, dist, effective_source))

        # Sort descending by score
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches

    target_limit = request.limit

    # Phase 1: Local matches against evaluation sequence (primary and fallback sources)
    for source_label, loc_ctx in location_eval_sequence:
        if len(selected_items) >= target_limit:
            break
        tier_matches = try_match_candidates(source_label, loc_ctx, allow_nearby=False)
        for _, camp, dist, match_source in tier_matches:
            if len(selected_items) >= target_limit:
                break
            if camp.id in seen_campaign_ids or camp.business_id in seen_business_ids:
                continue

            offers = get_valid_offers(camp)
            selected_items.append(
                PromotionItem(
                    campaign_id=camp.id,
                    campaign_name=camp.name,
                    campaign_type=camp.campaign_type,
                    business_name=camp.business.name,
                    business_category=camp.business.category,
                    business_area=camp.business.area,
                    matched_location_source=match_source,  # type: ignore[arg-type]
                    distance_km=dist,
                    offers=offers,
                )
            )
            seen_campaign_ids.add(camp.id)
            seen_business_ids.add(camp.business_id)

    # Phase 2: If insufficient, try nearby expanded radius
    if len(selected_items) < target_limit and location_eval_sequence:
        for source_label, loc_ctx in location_eval_sequence:
            if len(selected_items) >= target_limit:
                break
            nearby_matches = try_match_candidates(source_label, loc_ctx, allow_nearby=True)
            for _, camp, dist, match_source in nearby_matches:
                if len(selected_items) >= target_limit:
                    break
                if camp.id in seen_campaign_ids or camp.business_id in seen_business_ids:
                    continue

                offers = get_valid_offers(camp)
                selected_items.append(
                    PromotionItem(
                        campaign_id=camp.id,
                        campaign_name=camp.name,
                        campaign_type=camp.campaign_type,
                        business_name=camp.business.name,
                        business_category=camp.business.category,
                        business_area=camp.business.area,
                        matched_location_source=match_source,  # type: ignore[arg-type]
                        distance_km=dist,
                        offers=offers,
                    )
                )
                seen_campaign_ids.add(camp.id)
                seen_business_ids.add(camp.business_id)

    # Phase 3: City-wide campaigns fallback
    if len(selected_items) < target_limit:
        city_candidates = [
            c
            for c in uncapped_campaigns
            if c.targeting_strategy == TargetingStrategy.CITYWIDE.value
            and c.id not in seen_campaign_ids
            and c.business_id not in seen_business_ids
        ]
        city_candidates.sort(key=lambda c: c.priority - impression_counts.get(c.id, 0) * 0.3, reverse=True)
        for camp in city_candidates:
            if len(selected_items) >= target_limit:
                break
            offers = get_valid_offers(camp)
            if not offers:
                continue

            selected_items.append(
                PromotionItem(
                    campaign_id=camp.id,
                    campaign_name=camp.name,
                    campaign_type=camp.campaign_type,
                    business_name=camp.business.name,
                    business_category=camp.business.category,
                    business_area=camp.business.area,
                    matched_location_source="CITYWIDE",
                    distance_km=None,
                    offers=offers,
                )
            )
            seen_campaign_ids.add(camp.id)
            seen_business_ids.add(camp.business_id)

    # Phase 4: Online campaigns final fallback
    if len(selected_items) < target_limit:
        online_candidates = [
            c
            for c in uncapped_campaigns
            if c.targeting_strategy == TargetingStrategy.ONLINE.value
            and c.id not in seen_campaign_ids
            and c.business_id not in seen_business_ids
        ]
        online_candidates.sort(key=lambda c: c.priority - impression_counts.get(c.id, 0) * 0.3, reverse=True)
        for camp in online_candidates:
            if len(selected_items) >= target_limit:
                break
            offers = get_valid_offers(camp)
            if not offers:
                continue

            selected_items.append(
                PromotionItem(
                    campaign_id=camp.id,
                    campaign_name=camp.name,
                    campaign_type=camp.campaign_type,
                    business_name=camp.business.name,
                    business_category=camp.business.category,
                    business_area=camp.business.area,
                    matched_location_source="ONLINE",
                    distance_km=None,
                    offers=offers,
                )
            )
            seen_campaign_ids.add(camp.id)
            seen_business_ids.add(camp.business_id)

    logger.info(
        "Promotion engine selected %d promotions for citizen '%s' using policy %s (evaluated: %s)",
        len(selected_items),
        effective_citizen_id,
        policy.value,
        sources_evaluated,
    )

    return PromotionSelectionResponse(
        promotions=selected_items,
        total_selected=len(selected_items),
        location_sources_evaluated=sources_evaluated,
        policy_applied=policy,
    )
