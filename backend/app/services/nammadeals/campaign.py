from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from app.models.nammadeals import (
    Business,
    BusinessStatus,
    Campaign,
    CampaignApprovalStatus,
    CampaignStatus,
    CampaignType,
    CouponClaim,
    Offer,
    OfferType,
    TargetingMode,
    TargetingStrategy,
)
from app.schemas.nammadeals import (
    AdminCampaignCreateRequest,
    AdminCampaignUpdateRequest,
    CampaignCreate,
    CampaignRead,
    CampaignReviewRequest,
    CampaignUpdate,
    OfferCreate,
    OfferUpdate,
)
from app.services.nammadeals.maps import build_view_store_url

logger = logging.getLogger(__name__)


def build_campaign_read(db: Session, c: Campaign) -> CampaignRead:
    """Enriches a Campaign model into CampaignRead schema with computed metrics and store maps URL."""
    store_url = None
    biz_name = None
    biz_area = None
    if c.business:
        biz_name = c.business.name
        biz_area = c.business.area
        store_url = build_view_store_url(
            google_maps_url=c.business.google_maps_url,
            latitude=c.business.latitude,
            longitude=c.business.longitude,
            address=c.business.address,
            city=c.business.city,
        )

    # Offers and claims counts
    offers_count = len(c.offers) if c.offers else 0
    max_claims = sum(o.max_redemptions for o in c.offers) if c.offers else None

    # Count claims and redemptions
    current_claims = db.query(CouponClaim).filter(CouponClaim.campaign_id == c.id).count()
    redemptions = (
        db.query(CouponClaim)
        .filter(CouponClaim.campaign_id == c.id, CouponClaim.status == "REDEEMED")
        .count()
    )

    # Status mapping
    camp_status = CampaignStatus.ACTIVE
    if hasattr(c, "status") and c.status:
        try:
            camp_status = CampaignStatus(c.status)
        except ValueError:
            camp_status = CampaignStatus.ACTIVE if c.is_active else CampaignStatus.PAUSED

    t_mode = TargetingMode.BOTH
    if hasattr(c, "targeting_mode") and c.targeting_mode:
        try:
            t_mode = TargetingMode(c.targeting_mode)
        except ValueError:
            t_mode = TargetingMode.BOTH

    return CampaignRead(
        id=c.id,
        business_id=c.business_id,
        name=c.name,
        description=c.description,
        campaign_type=c.campaign_type,  # type: ignore[arg-type]
        start_date=c.start_date,
        end_date=c.end_date,
        approval_status=CampaignApprovalStatus(c.approval_status),
        status=camp_status,
        is_active=c.is_active,
        advertisement_image_url=getattr(c, "advertisement_image_url", None),
        targeting_mode=t_mode,
        targeting_strategy=TargetingStrategy(c.targeting_strategy),
        targeting_radius_km=c.targeting_radius_km,
        latitude=c.latitude,
        longitude=c.longitude,
        priority=c.priority,
        frequency_limit_per_user=c.frequency_limit_per_user,
        placement_config=c.placement_config,
        rejection_reason=c.rejection_reason,
        approved_by=c.approved_by,
        approved_at=c.approved_at,
        created_at=c.created_at,
        updated_at=c.updated_at,
        business_name=biz_name,
        business_area=biz_area,
        store_maps_url=store_url,
        offers_count=offers_count,
        max_claims=max_claims,
        current_claims=current_claims,
        redemptions_count=redemptions,
    )


def admin_create_campaign(
    db: Session,
    data: AdminCampaignCreateRequest,
    admin_id: str,
) -> Campaign:
    """Admin-only Campaign & Advertisement Creation.

    Creates an advertisement campaign directly for an approved business,
    including the offer, banner image, targeting mode, and schedule.
    """
    business = db.query(Business).filter(Business.id == data.business_id).first()
    if not business:
        raise ValueError(f"Business '{data.business_id}' not found.")
    if business.status != BusinessStatus.APPROVED.value:
        raise ValueError(f"Cannot create campaign for business with status '{business.status}'. Only APPROVED businesses can be advertised.")

    now = datetime.now(timezone.utc)
    is_active = data.status == CampaignStatus.ACTIVE
    approval_status = (
        CampaignApprovalStatus.APPROVED.value
        if data.status in (CampaignStatus.ACTIVE, CampaignStatus.PAUSED)
        else CampaignApprovalStatus.DRAFT.value
    )

    campaign = Campaign(
        business_id=business.id,
        name=data.name,
        description=data.description,
        campaign_type=data.campaign_type.value,
        advertisement_image_url=data.advertisement_image_url,
        targeting_mode=data.targeting_mode.value,
        targeting_strategy=TargetingStrategy.RADIUS.value,
        targeting_radius_km=data.targeting_radius_km,
        latitude=business.latitude,
        longitude=business.longitude,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status.value,
        is_active=is_active,
        approval_status=approval_status,
        approved_by=admin_id,
        approved_at=now,
        priority=10,
        frequency_limit_per_user=3,
    )
    db.add(campaign)
    db.flush()

    # Determine offer type
    offer_type = OfferType.SCRATCH_CARD.value if data.campaign_type == CampaignType.SCRATCH_CARD else OfferType.COUPON.value

    # Build predetermined scratch-card config if SCRATCH_CARD
    scratch_cfg = data.scratch_card_config
    if data.campaign_type == CampaignType.SCRATCH_CARD and not scratch_cfg:
        scratch_cfg = {
            "win_headline": data.offer_title,
            "description": data.offer_description or data.offer_title,
            "min_discount": data.discount_value,
            "max_discount": data.discount_value,
        }

    offer = Offer(
        campaign_id=campaign.id,
        title=data.offer_title,
        description=data.offer_description,
        promotional_image_url=data.advertisement_image_url,
        discount_type=data.discount_type.value,
        discount_value=data.discount_value,
        terms_and_conditions=data.terms_and_conditions,
        valid_from=data.start_date,
        valid_until=data.end_date,
        offer_type=offer_type,
        coupon_code=data.coupon_code.strip().upper(),
        scratch_card_config=scratch_cfg,
        max_redemptions=data.max_claims,
        redemption_count=0,
        is_active=True,
    )
    db.add(offer)

    db.commit()
    db.refresh(campaign)
    logger.info("Admin '%s' created campaign '%s' for business '%s' (status=%s)", admin_id, campaign.id, business.name, data.status.value)
    return campaign


def admin_update_campaign(
    db: Session,
    campaign_id: str,
    data: AdminCampaignUpdateRequest,
    admin_id: str,
) -> Campaign:
    """Admin updates campaign and associated offer configurations."""
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign '{campaign_id}' not found.")

    if data.name is not None:
        campaign.name = data.name
    if data.description is not None:
        campaign.description = data.description
    if data.advertisement_image_url is not None:
        campaign.advertisement_image_url = data.advertisement_image_url
    if data.targeting_mode is not None:
        campaign.targeting_mode = data.targeting_mode.value
    if data.targeting_radius_km is not None:
        campaign.targeting_radius_km = data.targeting_radius_km
    if data.start_date is not None:
        campaign.start_date = data.start_date
    if data.end_date is not None:
        campaign.end_date = data.end_date
    if data.status is not None:
        campaign.status = data.status.value
        campaign.is_active = (data.status == CampaignStatus.ACTIVE)

    # Update associated offer if present
    if campaign.offers:
        primary_offer = campaign.offers[0]
        if data.offer_title is not None:
            primary_offer.title = data.offer_title
        if data.offer_description is not None:
            primary_offer.description = data.offer_description
        if data.discount_type is not None:
            primary_offer.discount_type = data.discount_type.value
        if data.discount_value is not None:
            primary_offer.discount_value = data.discount_value
        if data.coupon_code is not None:
            primary_offer.coupon_code = data.coupon_code.strip().upper()
        if data.max_claims is not None:
            primary_offer.max_redemptions = data.max_claims
        if data.terms_and_conditions is not None:
            primary_offer.terms_and_conditions = data.terms_and_conditions
        if data.advertisement_image_url is not None:
            primary_offer.promotional_image_url = data.advertisement_image_url
        if data.end_date is not None:
            primary_offer.valid_until = data.end_date

    db.commit()
    db.refresh(campaign)
    logger.info("Admin '%s' updated campaign '%s'", admin_id, campaign.id)
    return campaign


def admin_set_campaign_status(
    db: Session,
    campaign_id: str,
    new_status: CampaignStatus,
    admin_id: str,
) -> Campaign:
    """Admin toggles campaign status (ACTIVE, PAUSED, DRAFT, DEACTIVATED).

    Pausing stops distribution immediately without invalidating already claimed coupons.
    Deactivating preserves all history and analytics.
    """
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign '{campaign_id}' not found.")

    campaign.status = new_status.value
    if new_status == CampaignStatus.ACTIVE:
        campaign.is_active = True
        campaign.approval_status = CampaignApprovalStatus.APPROVED.value
    elif new_status == CampaignStatus.PAUSED:
        campaign.is_active = False
    elif new_status == CampaignStatus.DEACTIVATED:
        campaign.is_active = False
        campaign.approval_status = CampaignApprovalStatus.SUSPENDED.value
    elif new_status == CampaignStatus.DRAFT:
        campaign.is_active = False
        campaign.approval_status = CampaignApprovalStatus.DRAFT.value

    db.commit()
    db.refresh(campaign)
    logger.info("Admin '%s' set campaign '%s' status to %s (is_active=%s)", admin_id, campaign.id, new_status.value, campaign.is_active)
    return campaign


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
