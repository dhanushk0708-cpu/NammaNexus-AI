from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from app.models.nammadeals import (
    Business,
    BusinessStatus,
    Campaign,
    CampaignApprovalStatus,
    Offer,
)
from app.schemas.nammadeals import (
    CampaignCreate,
    CampaignReviewRequest,
    CampaignUpdate,
    OfferCreate,
    OfferUpdate,
)

logger = logging.getLogger(__name__)


def create_campaign(
    db: Session,
    business_id: str,
    owner_user_id: str,
    data: CampaignCreate,
) -> Campaign:
    """Create a new advertising campaign for an approved business.

    Enforces invariants:
    - Business must exist and be owned by the requesting user.
    - Business must have status APPROVED.
    - Initial campaign status is DRAFT and is_active is False.
    """
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise ValueError(f"Business '{business_id}' not found.")
    if business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to create campaigns for this business.")
    if business.status != BusinessStatus.APPROVED.value:
        raise ValueError(
            f"Cannot create campaign for business with status '{business.status}'. Only APPROVED businesses can create campaigns."
        )

    # Use business coordinates as fallback if campaign coordinates not provided
    latitude = data.latitude if data.latitude is not None else business.latitude
    longitude = data.longitude if data.longitude is not None else business.longitude

    campaign = Campaign(
        business_id=business.id,
        name=data.name,
        description=data.description,
        campaign_type=data.campaign_type.value,
        start_date=data.start_date,
        end_date=data.end_date,
        approval_status=CampaignApprovalStatus.DRAFT.value,
        is_active=False,
        targeting_strategy=data.targeting_strategy.value,
        targeting_radius_km=data.targeting_radius_km,
        latitude=latitude,
        longitude=longitude,
        priority=data.priority,
        frequency_limit_per_user=data.frequency_limit_per_user,
        placement_config=data.placement_config,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    logger.info("Campaign '%s' (DRAFT) created for business '%s'.", campaign.id, business.id)
    return campaign


def get_campaign_by_id(db: Session, campaign_id: str) -> Campaign | None:
    """Fetch campaign by ID."""
    return db.query(Campaign).filter(Campaign.id == campaign_id).first()


def list_campaigns_for_business(
    db: Session,
    business_id: str,
    owner_user_id: str,
) -> list[Campaign]:
    """List campaigns for a business, verifying owner permissions."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise ValueError(f"Business '{business_id}' not found.")
    if business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to view campaigns for this business.")

    return (
        db.query(Campaign)
        .filter(Campaign.business_id == business_id)
        .order_by(Campaign.created_at.desc())
        .all()
    )


def update_campaign(
    db: Session,
    campaign_id: str,
    owner_user_id: str,
    data: CampaignUpdate,
) -> Campaign:
    """Update a campaign draft.

    Only campaigns in DRAFT or REJECTED status can be edited by the owner.
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign '{campaign_id}' not found.")
    if campaign.business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to modify this campaign.")
    if campaign.approval_status not in (CampaignApprovalStatus.DRAFT.value, CampaignApprovalStatus.REJECTED.value):
        raise ValueError(
            f"Cannot edit campaign with status '{campaign.approval_status}'. Only DRAFT or REJECTED campaigns can be edited."
        )

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        if val is not None:
            if hasattr(val, "value"):
                setattr(campaign, field, val.value)
            else:
                setattr(campaign, field, val)

    db.commit()
    db.refresh(campaign)
    return campaign


def submit_campaign_for_approval(
    db: Session,
    campaign_id: str,
    owner_user_id: str,
) -> Campaign:
    """Submit a DRAFT or REJECTED campaign to administrators for review."""
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign '{campaign_id}' not found.")
    if campaign.business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to submit this campaign.")
    if campaign.business.status != BusinessStatus.APPROVED.value:
        raise ValueError("Cannot submit campaign: parent business is not in APPROVED status.")

    if campaign.approval_status not in (CampaignApprovalStatus.DRAFT.value, CampaignApprovalStatus.REJECTED.value):
        raise ValueError(
            f"Cannot submit campaign with status '{campaign.approval_status}'. Only DRAFT or REJECTED campaigns can be submitted."
        )

    # Ensure campaign has at least one offer before submission
    offer_count = db.query(Offer).filter(Offer.campaign_id == campaign.id).count()
    if offer_count == 0:
        raise ValueError("Cannot submit campaign for approval without at least one promotional offer.")

    campaign.approval_status = CampaignApprovalStatus.PENDING_APPROVAL.value
    campaign.rejection_reason = None
    db.commit()
    db.refresh(campaign)
    logger.info("Campaign '%s' submitted for admin approval.", campaign.id)
    return campaign


def admin_list_campaigns(
    db: Session,
    approval_status: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Campaign]:
    """Admin endpoint to list campaigns, optionally filtered by approval status."""
    query = db.query(Campaign)
    if approval_status:
        query = query.filter(Campaign.approval_status == approval_status)
    return query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()


def admin_review_campaign(
    db: Session,
    campaign_id: str,
    review_data: CampaignReviewRequest,
    admin_id: str,
) -> Campaign:
    """Admin approves, rejects, or suspends a campaign."""
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign '{campaign_id}' not found.")

    now = datetime.now(timezone.utc)

    if review_data.action == "APPROVE":
        if campaign.business.status != BusinessStatus.APPROVED.value:
            raise ValueError("Cannot approve campaign for a non-approved business.")
        campaign.approval_status = CampaignApprovalStatus.APPROVED.value
        campaign.approved_by = admin_id
        campaign.approved_at = now
        campaign.rejection_reason = None
    elif review_data.action == "REJECT":
        campaign.approval_status = CampaignApprovalStatus.REJECTED.value
        campaign.rejection_reason = review_data.rejection_reason
        campaign.is_active = False
    elif review_data.action == "SUSPEND":
        campaign.approval_status = CampaignApprovalStatus.SUSPENDED.value
        campaign.is_active = False

    db.commit()
    db.refresh(campaign)
    logger.info("Campaign '%s' reviewed by admin '%s'. Action: %s", campaign.id, admin_id, review_data.action)
    return campaign


def toggle_campaign_active(
    db: Session,
    campaign_id: str,
    owner_user_id: str,
    is_active: bool,
) -> Campaign:
    """Business owner activates or pauses an approved campaign.

    Enforces invariants:
    - Campaign must have approval_status == APPROVED.
    - Business must be in APPROVED status.
    - Campaign must not be expired.
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign '{campaign_id}' not found.")
    if campaign.business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to manage this campaign.")

    if is_active:
        if campaign.approval_status != CampaignApprovalStatus.APPROVED.value:
            raise ValueError(
                f"Cannot activate campaign with approval status '{campaign.approval_status}'. Only APPROVED campaigns can be activated."
            )
        if campaign.business.status != BusinessStatus.APPROVED.value:
            raise ValueError("Cannot activate campaign because the parent business is not APPROVED.")
        end_date = campaign.end_date
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        if end_date < datetime.now(timezone.utc):
            raise ValueError("Cannot activate an expired campaign.")

    campaign.is_active = is_active
    db.commit()
    db.refresh(campaign)
    logger.info("Campaign '%s' is_active set to %s by owner '%s'.", campaign.id, is_active, owner_user_id)
    return campaign


# --- Offer Management ---

def create_offer(
    db: Session,
    campaign_id: str,
    owner_user_id: str,
    data: OfferCreate,
) -> Offer:
    """Create an offer within a campaign."""
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign '{campaign_id}' not found.")
    if campaign.business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to add offers to this campaign.")

    offer = Offer(
        campaign_id=campaign.id,
        title=data.title,
        description=data.description,
        promotional_image_url=data.promotional_image_url,
        discount_type=data.discount_type.value,
        discount_value=data.discount_value,
        terms_and_conditions=data.terms_and_conditions,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        offer_type=data.offer_type.value,
        coupon_code=data.coupon_code,
        scratch_card_config=data.scratch_card_config,
        max_redemptions=data.max_redemptions,
        redemption_count=0,
        is_active=True,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    logger.info("Offer '%s' created for campaign '%s'.", offer.id, campaign.id)
    return offer


def get_offer_by_id(db: Session, offer_id: str) -> Offer | None:
    """Fetch offer by ID."""
    return db.query(Offer).filter(Offer.id == offer_id).first()


def list_offers_for_campaign(
    db: Session,
    campaign_id: str,
    owner_user_id: str,
) -> list[Offer]:
    """List offers for a campaign, checking ownership."""
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign '{campaign_id}' not found.")
    if campaign.business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to view offers for this campaign.")

    return db.query(Offer).filter(Offer.campaign_id == campaign_id).order_by(Offer.created_at.asc()).all()


def update_offer(
    db: Session,
    offer_id: str,
    owner_user_id: str,
    data: OfferUpdate,
) -> Offer:
    """Update an offer."""
    offer = get_offer_by_id(db, offer_id)
    if not offer:
        raise ValueError(f"Offer '{offer_id}' not found.")
    if offer.campaign.business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to modify this offer.")

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        if val is not None:
            if hasattr(val, "value"):
                setattr(offer, field, val.value)
            else:
                setattr(offer, field, val)

    db.commit()
    db.refresh(offer)
    return offer
