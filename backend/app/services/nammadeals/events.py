from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy.orm import Session

from app.models.nammadeals import (
    Campaign,
    Offer,
    PromotionEvent,
    PromotionEventType,
)
from app.schemas.nammadeals import PromotionEventCreate

logger = logging.getLogger(__name__)

DEBOUNCE_WINDOW_SECONDS = 5.0


def record_promotion_event(
    db: Session,
    data: PromotionEventCreate,
    citizen_user_id: str,
) -> PromotionEvent:
    """Record an impression or click event for a promotion.

    Enforces backend validation:
    - Campaign must exist.
    - Offer (if specified) must belong to the campaign.
    - Idempotency key deduplication.
    - Debounce rapid duplicate event firing.
    """
    if not citizen_user_id or not citizen_user_id.strip():
        raise ValueError("citizen_user_id must be provided to record promotion events.")

    campaign = db.query(Campaign).filter(Campaign.id == data.campaign_id).first()
    if not campaign:
        raise ValueError(f"Campaign '{data.campaign_id}' not found.")

    if data.offer_id:
        offer = db.query(Offer).filter(Offer.id == data.offer_id, Offer.campaign_id == campaign.id).first()
        if not offer:
            raise ValueError(f"Offer '{data.offer_id}' does not belong to campaign '{campaign.id}'.")

    now = datetime.now(timezone.utc)

    # 1. Idempotency key check
    if data.idempotency_key:
        existing = (
            db.query(PromotionEvent)
            .filter(PromotionEvent.idempotency_key == data.idempotency_key)
            .first()
        )
        if existing:
            logger.info("Idempotent promotion event returned for key '%s'", data.idempotency_key)
            return existing
    else:
        # 2. Debounce window check for non-idempotent duplicate rapid clicks/impressions
        recent_cutoff = now - timedelta(seconds=DEBOUNCE_WINDOW_SECONDS)
        recent_duplicate = (
            db.query(PromotionEvent)
            .filter(
                PromotionEvent.citizen_user_id == citizen_user_id,
                PromotionEvent.campaign_id == data.campaign_id,
                PromotionEvent.event_type == data.event_type.value,
                PromotionEvent.created_at >= recent_cutoff,
            )
            .first()
        )
        if recent_duplicate:
            logger.info(
                "Debounced duplicate %s event for citizen '%s' on campaign '%s'",
                data.event_type.value,
                citizen_user_id,
                data.campaign_id,
            )
            return recent_duplicate

    event = PromotionEvent(
        event_type=data.event_type.value,
        campaign_id=campaign.id,
        offer_id=data.offer_id,
        citizen_user_id=citizen_user_id,
        location_source=data.location_source,
        idempotency_key=data.idempotency_key,
        event_metadata=data.event_metadata,
        created_at=now,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(
        "Recorded %s event for campaign '%s' from citizen '%s' (id=%s)",
        event.event_type,
        event.campaign_id,
        citizen_user_id,
        event.id,
    )
    return event
