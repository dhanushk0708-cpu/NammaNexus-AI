import logging
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.nammadeals import (
    AdvertiserPayment,
    Business,
    BusinessRegistration,
    BusinessRegistrationStatus,
    BusinessStatus,
    Campaign,
    CampaignApprovalStatus,
    Offer,
    PaymentVerificationStatus,
    PromotionEvent,
    PromotionEventType,
)
from app.schemas.nammadeals import (
    AdminPlatformAnalyticsRead,
    BusinessAnalyticsRead,
    CampaignAnalyticsRead,
)

logger = logging.getLogger(__name__)


def get_campaign_analytics(
    db: Session,
    campaign_id: str,
    owner_user_id: str,
) -> CampaignAnalyticsRead:
    """Retrieve full-lifecycle conversion analytics for a single advertising campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise ValueError("Campaign not found.")

    if campaign.business.owner_user_id != owner_user_id and owner_user_id != "admin":
        raise PermissionError("You do not have access to this campaign's analytics.")

    # Aggregate counts by event type
    events = (
        db.query(PromotionEvent.event_type, func.count(PromotionEvent.id))
        .filter(PromotionEvent.campaign_id == campaign_id)
        .group_by(PromotionEvent.event_type)
        .all()
    )
    counts = {etype: count for etype, count in events}

    impressions = counts.get(PromotionEventType.IMPRESSION.value, 0)
    clicks = counts.get(PromotionEventType.CLICK.value, 0)
    claims = counts.get(PromotionEventType.CLAIM.value, 0)
    redemptions = counts.get(PromotionEventType.REDEMPTION.value, 0)

    ctr = round((clicks / impressions * 100.0), 2) if impressions > 0 else 0.0
    claim_rate = round((claims / impressions * 100.0), 2) if impressions > 0 else 0.0
    redemption_rate = round((redemptions / claims * 100.0), 2) if claims > 0 else 0.0

    return CampaignAnalyticsRead(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        status=campaign.approval_status,
        impressions=impressions,
        clicks=clicks,
        claims=claims,
        redemptions=redemptions,
        ctr_percentage=ctr,
        claim_rate_percentage=claim_rate,
        redemption_rate_percentage=redemption_rate,
        budget_allocated=None,
    )


def get_business_analytics(
    db: Session,
    business_id: str,
    owner_user_id: str,
) -> BusinessAnalyticsRead:
    """Retrieve aggregate performance and revenue metrics for a verified business."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise ValueError("Business not found.")

    if business.owner_user_id != owner_user_id and owner_user_id != "admin":
        raise PermissionError("You do not have access to this business's analytics.")

    campaign_ids = [c.id for c in business.campaigns]
    total_campaigns = len(campaign_ids)
    active_campaigns = sum(
        1 for c in business.campaigns
        if c.is_active and c.approval_status == CampaignApprovalStatus.APPROVED.value
    )
    total_offers = sum(len(c.offers) for c in business.campaigns)

    impressions = 0
    clicks = 0
    claims = 0
    redemptions = 0

    if campaign_ids:
        events = (
            db.query(PromotionEvent.event_type, func.count(PromotionEvent.id))
            .filter(PromotionEvent.campaign_id.in_(campaign_ids))
            .group_by(PromotionEvent.event_type)
            .all()
        )
        counts = {etype: count for etype, count in events}
        impressions = counts.get(PromotionEventType.IMPRESSION.value, 0)
        clicks = counts.get(PromotionEventType.CLICK.value, 0)
        claims = counts.get(PromotionEventType.CLAIM.value, 0)
        redemptions = counts.get(PromotionEventType.REDEMPTION.value, 0)

    ctr = round((clicks / impressions * 100.0), 2) if impressions > 0 else 0.0
    redemption_rate = round((redemptions / claims * 100.0), 2) if claims > 0 else 0.0

    # Total verified payments
    verified_sum = (
        db.query(func.coalesce(func.sum(AdvertiserPayment.amount), 0.0))
        .filter(
            AdvertiserPayment.business_id == business_id,
            AdvertiserPayment.verification_status == PaymentVerificationStatus.VERIFIED.value,
        )
        .scalar()
    )

    return BusinessAnalyticsRead(
        business_id=business.id,
        business_name=business.name,
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        total_offers=total_offers,
        impressions=impressions,
        clicks=clicks,
        claims=claims,
        redemptions=redemptions,
        overall_ctr_percentage=ctr,
        overall_redemption_rate_percentage=redemption_rate,
        verified_payments_total=float(verified_sum or 0.0),
    )


def get_admin_analytics(db: Session) -> AdminPlatformAnalyticsRead:
    """Retrieve platform-wide operational, conversion, and monetization intelligence for administrators."""
    total_registrations = db.query(func.count(BusinessRegistration.id)).scalar() or 0
    pending_registrations = (
        db.query(func.count(BusinessRegistration.id))
        .filter(BusinessRegistration.status == BusinessRegistrationStatus.PENDING.value)
        .scalar()
        or 0
    )

    total_businesses = db.query(func.count(Business.id)).scalar() or 0
    verified_businesses = (
        db.query(func.count(Business.id))
        .filter(Business.status == BusinessStatus.APPROVED.value)
        .scalar()
        or 0
    )

    total_campaigns = db.query(func.count(Campaign.id)).scalar() or 0
    active_campaigns = (
        db.query(func.count(Campaign.id))
        .filter(
            Campaign.is_active == True,
            Campaign.approval_status == CampaignApprovalStatus.APPROVED.value,
        )
        .scalar()
        or 0
    )
    pending_campaign_approvals = (
        db.query(func.count(Campaign.id))
        .filter(Campaign.approval_status == CampaignApprovalStatus.PENDING_APPROVAL.value)
        .scalar()
        or 0
    )

    # Event aggregates
    events = (
        db.query(PromotionEvent.event_type, func.count(PromotionEvent.id))
        .group_by(PromotionEvent.event_type)
        .all()
    )
    counts = {etype: count for etype, count in events}

    impressions = counts.get(PromotionEventType.IMPRESSION.value, 0)
    clicks = counts.get(PromotionEventType.CLICK.value, 0)
    claims = counts.get(PromotionEventType.CLAIM.value, 0)
    redemptions = counts.get(PromotionEventType.REDEMPTION.value, 0)

    overall_ctr = round((clicks / impressions * 100.0), 2) if impressions > 0 else 0.0

    # Revenue
    verified_rev = (
        db.query(func.coalesce(func.sum(AdvertiserPayment.amount), 0.0))
        .filter(AdvertiserPayment.verification_status == PaymentVerificationStatus.VERIFIED.value)
        .scalar()
        or 0.0
    )
    pending_rev = (
        db.query(func.coalesce(func.sum(AdvertiserPayment.amount), 0.0))
        .filter(AdvertiserPayment.verification_status == PaymentVerificationStatus.PENDING.value)
        .scalar()
        or 0.0
    )

    return AdminPlatformAnalyticsRead(
        total_registrations=total_registrations,
        pending_registrations=pending_registrations,
        total_businesses=total_businesses,
        verified_businesses=verified_businesses,
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        pending_campaign_approvals=pending_campaign_approvals,
        total_impressions=impressions,
        total_clicks=clicks,
        total_claims=claims,
        total_redemptions=redemptions,
        overall_ctr_percentage=overall_ctr,
        total_revenue_inr=float(verified_rev),
        pending_revenue_inr=float(pending_rev),
    )
