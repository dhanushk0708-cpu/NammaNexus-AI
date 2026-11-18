import logging
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload

from app.models.nammadeals import (
    Business,
    BusinessStatus,
    Campaign,
    CampaignApprovalStatus,
    CouponClaim,
    CouponClaimStatus,
    DiscountType,
    Offer,
    OfferType,
    PromotionEvent,
    PromotionEventType,
)
from app.schemas.nammadeals import (
    CouponClaimRead,
    CouponRedemptionRead,
    ScratchCardRevealRead,
)

logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def generate_unique_coupon_code(offer_code: str | None = None) -> str:
    """Generate a clean, unambiguous uppercase alphanumeric coupon code."""
    token = secrets.token_hex(4).upper()  # 8 hex chars
    if offer_code and offer_code.strip():
        prefix = "".join(c for c in offer_code.strip().upper() if c.isalnum())[:10]
        return f"{prefix}-{token}"
    return f"NEXUS-{token}"


def build_claim_read(claim: CouponClaim) -> CouponClaimRead:
    """Enrich a CouponClaim ORM entity into a clean response schema.

    Tenant privacy is strictly preserved: no citizen PII is leaked to businesses.
    """
    offer = claim.offer
    campaign = claim.campaign
    business = campaign.business if campaign else None

    # Parse predetermined discount summary if available
    disc_type = None
    disc_val = None
    if offer:
        disc_type = DiscountType(offer.discount_type) if offer.discount_type else None
        disc_val = offer.discount_value

    return CouponClaimRead(
        id=claim.id,
        citizen_user_id=claim.citizen_user_id,
        campaign_id=claim.campaign_id,
        offer_id=claim.offer_id,
        unique_coupon_code=claim.unique_coupon_code,
        status=CouponClaimStatus(claim.status),
        claimed_at=claim.claimed_at,
        redeemed_at=claim.redeemed_at,
        redeemed_by_business_id=claim.redeemed_by_business_id,
        redemption_notes=claim.redemption_notes,
        scratch_reward_revealed=claim.scratch_reward_revealed,
        claim_metadata=claim.claim_metadata,
        business_id=business.id if business else None,
        business_name=business.name if business else None,
        business_area=business.area if business else None,
        campaign_name=campaign.name if campaign else None,
        offer_title=offer.title if offer else None,
        offer_description=offer.description if offer else None,
        offer_type=OfferType(offer.offer_type) if offer else None,
        discount_type=disc_type,
        discount_value=disc_val,
        terms_and_conditions=offer.terms_and_conditions if offer else None,
        valid_until=offer.valid_until if offer else None,
    )


def claim_coupon(
    db: Session,
    offer_id: str,
    citizen_user_id: str,
    client_notes: str | None = None,
) -> CouponClaimRead:
    """Backend-authoritative coupon claiming.

    Validates offer validity, campaign approval, limits, and idempotently/strictly
    prevents duplicate claims by the same citizen for the same offer.
    """
    if not citizen_user_id or not citizen_user_id.strip():
        raise ValueError("Authenticated citizen identity is required to claim a coupon.")

    now = datetime.now(timezone.utc)

    # 1. Fetch offer and related campaign
    offer = (
        db.query(Offer)
        .options(joinedload(Offer.campaign).joinedload(Campaign.business))
        .filter(Offer.id == offer_id)
        .first()
    )
    if not offer:
        raise ValueError("Offer not found.")

    if not offer.is_active:
        raise ValueError("This offer is currently inactive.")

    if _ensure_utc(offer.valid_until) < now:
        raise ValueError("This offer has expired.")

    if offer.redemption_count >= offer.max_redemptions:
        raise ValueError("Maximum redemptions for this offer have already been reached.")

    campaign = offer.campaign
    if not campaign or not campaign.is_active or campaign.approval_status != CampaignApprovalStatus.APPROVED.value:
        raise ValueError("The promotional campaign for this offer is not currently active.")

    if not (_ensure_utc(campaign.start_date) <= now <= _ensure_utc(campaign.end_date)):
        raise ValueError("The promotional campaign is outside its scheduled activity dates.")

    if not campaign.business or campaign.business.status != BusinessStatus.APPROVED.value:
        raise ValueError("The business offering this promotion is not verified.")

    # 2. Check duplicate claim
    existing_claim = (
        db.query(CouponClaim)
        .options(joinedload(CouponClaim.offer), joinedload(CouponClaim.campaign).joinedload(Campaign.business))
        .filter(
            CouponClaim.citizen_user_id == citizen_user_id,
            CouponClaim.offer_id == offer_id,
        )
        .first()
    )
    if existing_claim:
        # Return existing claim idempotently if already claimed
        return build_claim_read(existing_claim)

    # 3. Generate unique personalized coupon code
    code = generate_unique_coupon_code(offer.coupon_code)
    # Collision safety loop
    for _ in range(5):
        collision = db.query(CouponClaim).filter(CouponClaim.unique_coupon_code == code).first()
        if not collision:
            break
        code = generate_unique_coupon_code(offer.coupon_code)

    # 4. Prepare predetermined reward data if scratch-card
    metadata: dict[str, Any] = {"notes": client_notes} if client_notes else {}
    if offer.offer_type == OfferType.SCRATCH_CARD.value:
        config = offer.scratch_card_config or {}
        reward_headline = config.get("win_headline") or offer.title
        reward_description = (
            config.get("description")
            or offer.description
            or "Exclusive in-store reward configured by business."
        )
        min_disc = config.get("min_discount")
        max_disc = config.get("max_discount")
        # Predetermined exact value, never randomized at reveal time
        reward_discount = min_disc if min_disc is not None else offer.discount_value

        metadata["predetermined_reward"] = {
            "headline": reward_headline,
            "description": reward_description,
            "discount_percentage": reward_discount,
            "max_discount": max_disc,
            "configured_at": now.isoformat(),
        }

    # 5. Persist CouponClaim
    claim = CouponClaim(
        id=str(uuid4()),
        citizen_user_id=citizen_user_id,
        campaign_id=campaign.id,
        offer_id=offer.id,
        unique_coupon_code=code,
        status=CouponClaimStatus.CLAIMED.value,
        claimed_at=now,
        scratch_reward_revealed=False,
        claim_metadata=metadata,
    )
    db.add(claim)

    # 6. Record CLAIM event in analytics table
    claim_event = PromotionEvent(
        id=str(uuid4()),
        event_type=PromotionEventType.CLAIM.value,
        campaign_id=campaign.id,
        offer_id=offer.id,
        citizen_user_id=citizen_user_id,
        location_source="CITIZEN_CLAIM",
        idempotency_key=f"claim_{citizen_user_id}_{offer.id}",
        event_metadata={"coupon_code": code},
        created_at=now,
    )
    db.add(claim_event)

    db.commit()
    db.refresh(claim)

    logger.info("Coupon %s successfully claimed by citizen %s for offer %s", code, citizen_user_id, offer.id)
    return build_claim_read(claim)


def reveal_scratch_card(
    db: Session,
    offer_id: str,
    citizen_user_id: str,
) -> ScratchCardRevealRead:
    """Backend-authorized predetermined scratch-card reveal.

    CRITICAL RULE: Rewards must be predetermined and configured by the business,
    approved by admin. Never implement random lottery rewards or client-side reward generation.
    Subsequent calls return the exact same saved reward.
    """
    if not citizen_user_id or not citizen_user_id.strip():
        raise ValueError("Authenticated citizen identity is required to scratch a card.")

    now = datetime.now(timezone.utc)

    # Find existing claim or create it
    claim = (
        db.query(CouponClaim)
        .options(joinedload(CouponClaim.offer), joinedload(CouponClaim.campaign).joinedload(Campaign.business))
        .filter(
            CouponClaim.citizen_user_id == citizen_user_id,
            CouponClaim.offer_id == offer_id,
        )
        .first()
    )

    if not claim:
        # Automatically claim the offer if not yet claimed
        claim_read = claim_coupon(db, offer_id, citizen_user_id)
        claim = (
            db.query(CouponClaim)
            .options(joinedload(CouponClaim.offer), joinedload(CouponClaim.campaign).joinedload(Campaign.business))
            .filter(CouponClaim.id == claim_read.id)
            .first()
        )

    if not claim or not claim.offer:
        raise ValueError("Failed to retrieve scratch-card offer.")

    if claim.offer.offer_type != OfferType.SCRATCH_CARD.value:
        raise ValueError("This offer is a standard coupon, not a scratch card.")

    metadata = dict(claim.claim_metadata or {})

    # If already revealed, return the exact same persisted reward
    if claim.scratch_reward_revealed:
        saved_reward = metadata.get("predetermined_reward", {})
        return ScratchCardRevealRead(
            success=True,
            message="Scratch card reward already revealed.",
            claim=build_claim_read(claim),
            reward_headline=saved_reward.get("headline", claim.offer.title),
            reward_description=saved_reward.get("description", claim.offer.description or "Exclusive offer"),
            discount_percentage=saved_reward.get("discount_percentage", claim.offer.discount_value),
            revealed_at=_ensure_utc(claim.updated_at if hasattr(claim, "updated_at") else claim.claimed_at),
            is_already_revealed=True,
        )

    # First time reveal: Retrieve predetermined configuration
    config = claim.offer.scratch_card_config or {}
    predetermined = metadata.get("predetermined_reward") or {
        "headline": config.get("win_headline") or claim.offer.title,
        "description": config.get("description") or claim.offer.description or "Exclusive in-store reward",
        "discount_percentage": config.get("min_discount") or claim.offer.discount_value,
    }

    metadata["predetermined_reward"] = predetermined
    metadata["revealed_at"] = now.isoformat()

    claim.scratch_reward_revealed = True
    claim.claim_metadata = metadata

    db.commit()
    db.refresh(claim)

    logger.info("Scratch-card %s revealed by citizen %s", claim.unique_coupon_code, citizen_user_id)
    return ScratchCardRevealRead(
        success=True,
        message="Congratulations! Your scratch card reward has been revealed.",
        claim=build_claim_read(claim),
        reward_headline=predetermined.get("headline", claim.offer.title),
        reward_description=predetermined.get("description", claim.offer.description or ""),
        discount_percentage=predetermined.get("discount_percentage", claim.offer.discount_value),
        revealed_at=now,
        is_already_revealed=False,
    )


def list_my_claimed_coupons(
    db: Session,
    citizen_user_id: str,
    status_filter: CouponClaimStatus | None = None,
) -> list[CouponClaimRead]:
    """Retrieve all claimed coupons for the authenticated citizen."""
    if not citizen_user_id or not citizen_user_id.strip():
        raise ValueError("Citizen user ID is required.")

    query = (
        db.query(CouponClaim)
        .options(
            joinedload(CouponClaim.offer),
            joinedload(CouponClaim.campaign).joinedload(Campaign.business),
        )
        .filter(CouponClaim.citizen_user_id == citizen_user_id)
    )

    if status_filter:
        query = query.filter(CouponClaim.status == status_filter.value)

    claims = query.order_by(CouponClaim.claimed_at.desc()).all()
    return [build_claim_read(c) for c in claims]


def redeem_coupon(
    db: Session,
    business_id: str,
    owner_user_id: str,
    coupon_code: str,
    notes: str | None = None,
) -> CouponRedemptionRead:
    """Merchant-side coupon verification and redemption.

    Enforces:
    - Business ownership authentication.
    - Row-level locking to prevent concurrency race conditions and double redemptions.
    - Business authorization (coupon must belong to this business's campaign).
    - Status and expiration verification.
    - Real-time increment of offer redemption count.
    - Logging of REDEMPTION analytics event.
    """
    clean_code = coupon_code.strip().upper()
    now = datetime.now(timezone.utc)

    # 1. Verify business ownership
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise ValueError("Business not found.")

    if business.owner_user_id != owner_user_id and owner_user_id != "admin":
        raise PermissionError("You do not have permission to redeem coupons for this business.")

    # 2. Query claim with row-level lock where supported
    claim_query = (
        db.query(CouponClaim)
        .options(
            joinedload(CouponClaim.offer),
            joinedload(CouponClaim.campaign).joinedload(Campaign.business),
        )
        .filter(CouponClaim.unique_coupon_code == clean_code)
    )

    # If backend supports FOR UPDATE (e.g. Postgres), use it
    try:
        claim = claim_query.with_for_update().first()
    except Exception:
        # Fallback for SQLite in unit tests
        claim = claim_query.first()

    if not claim:
        raise ValueError(f"Invalid coupon code: '{coupon_code}'. Code does not exist.")

    # 3. Verify business match
    if claim.campaign.business_id != business_id:
        raise PermissionError(
            f"This coupon was issued for '{claim.campaign.business.name}', not for your business."
        )

    # 4. Check already redeemed or expired
    if claim.status == CouponClaimStatus.REDEEMED.value:
        redeemed_time_str = claim.redeemed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if claim.redeemed_at else "previously"
        raise ValueError(f"Coupon '{coupon_code}' has already been redeemed on {redeemed_time_str}.")

    if claim.status == CouponClaimStatus.CANCELLED.value:
        raise ValueError(f"Coupon '{coupon_code}' has been cancelled.")

    if _ensure_utc(claim.offer.valid_until) < now:
        claim.status = CouponClaimStatus.EXPIRED.value
        db.commit()
        raise ValueError("This coupon has expired and is no longer valid for redemption.")

    # 5. Check offer max redemption limits
    offer = claim.offer
    if offer.redemption_count >= offer.max_redemptions:
        raise ValueError("Maximum redemptions for this offer have already been reached.")

    # 6. Apply redemption
    claim.status = CouponClaimStatus.REDEEMED.value
    claim.redeemed_at = now
    claim.redeemed_by_business_id = business_id
    claim.redemption_notes = notes

    offer.redemption_count += 1

    # 7. Record REDEMPTION event
    redemption_event = PromotionEvent(
        id=str(uuid4()),
        event_type=PromotionEventType.REDEMPTION.value,
        campaign_id=claim.campaign_id,
        offer_id=claim.offer_id,
        citizen_user_id=claim.citizen_user_id,
        location_source="IN_STORE_REDEMPTION",
        idempotency_key=f"redeem_{claim.unique_coupon_code}",
        event_metadata={"business_id": business_id, "notes": notes},
        created_at=now,
    )
    db.add(redemption_event)

    db.commit()
    db.refresh(claim)

    # Prepare readable discount summary
    if offer.discount_type == DiscountType.PERCENTAGE.value:
        discount_summary = f"{offer.discount_value:.0f}% OFF"
    elif offer.discount_type == DiscountType.FLAT.value:
        discount_summary = f"₹{offer.discount_value:.0f} OFF"
    else:
        discount_summary = f"Special Offer ({offer.offer_type})"

    logger.info("Coupon %s redeemed successfully by business %s", clean_code, business.name)

    return CouponRedemptionRead(
        success=True,
        message=f"Coupon successfully verified and redeemed! Applied discount: {discount_summary}",
        unique_coupon_code=claim.unique_coupon_code,
        redeemed_at=now,
        business_id=business.id,
        business_name=business.name,
        campaign_id=claim.campaign.id,
        campaign_name=claim.campaign.name,
        offer_id=offer.id,
        offer_title=offer.title,
        discount_summary=discount_summary,
        redemption_notes=notes,
        claim=build_claim_read(claim),
    )
