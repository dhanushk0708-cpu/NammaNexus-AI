from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.endpoints.nammadeals_deps import get_current_admin, get_current_user
from app.db.dependencies import get_db
from app.models.nammadeals import Business
from app.schemas.nammadeals import (
    AdminPlatformAnalyticsRead,
    AdvertiserPaymentCreate,
    AdvertiserPaymentRead,
    AdvertiserPaymentVerifyRequest,
    BusinessAnalyticsRead,
    BusinessRead,
    BusinessRegistrationCreate,
    BusinessRegistrationRead,
    BusinessRegistrationReviewRequest,
    BusinessStatusUpdateRequest,
    BusinessUpdate,
    CampaignAnalyticsRead,
    CampaignCreate,
    CampaignRead,
    CampaignReviewRequest,
    CampaignToggleActiveRequest,
    CampaignUpdate,
    CouponClaimCreate,
    CouponClaimRead,
    CouponClaimStatus,
    CouponRedemptionRead,
    CouponRedemptionRequest,
    OfferCreate,
    OfferRead,
    OfferUpdate,
    PromotionEventCreate,
    PromotionEventRead,
    PromotionItem,
    PromotionOfferItem,
    PromotionSelectionRequest,
    PromotionSelectionResponse,
    ScratchCardRevealRead,
    ScratchCardRevealRequest,
)
from app.services.nammadeals import analytics as analytics_service
from app.services.nammadeals import business as business_service
from app.services.nammadeals import campaign as campaign_service
from app.services.nammadeals import claims as claims_service
from app.services.nammadeals import events as events_service
from app.services.nammadeals import payment as payment_service
from app.services.nammadeals import selection as selection_service

router = APIRouter(
    prefix="/nammadeals",
    tags=["NammaDeals"],
)


# ============================================================================
# 1. Business Registration
# ============================================================================

@router.post(
    "/registrations",
    response_model=BusinessRegistrationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new business registration",
)
def submit_business_registration(
    data: BusinessRegistrationCreate,
    db: Session = Depends(get_db),
):
    """Prospective business owners submit their business details for verification."""
    try:
        registration = business_service.submit_registration(db, data)
        return registration
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/admin/registrations",
    response_model=list[BusinessRegistrationRead],
    summary="Admin: List business registration requests",
)
def admin_list_registrations(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Admin reviews pending or historical business registrations."""
    return business_service.list_registrations(db, status=status_filter, skip=skip, limit=limit)


@router.get(
    "/admin/registrations/{reg_id}",
    response_model=BusinessRegistrationRead,
    summary="Admin: Get registration details",
)
def admin_get_registration(
    reg_id: str,
    _admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    reg = business_service.get_registration(db, reg_id)
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found.")
    return reg


@router.post(
    "/admin/registrations/{reg_id}/review",
    summary="Admin: Approve or reject a business registration",
)
def admin_review_registration(
    reg_id: str,
    review_data: BusinessRegistrationReviewRequest,
    admin_id: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Admin approves or rejects a prospective business registration."""
    try:
        registration, business = business_service.review_registration(db, reg_id, review_data, admin_id)
        return {
            "registration": BusinessRegistrationRead.model_validate(registration),
            "business": BusinessRead.model_validate(business) if business else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# 2. Businesses
# ============================================================================

@router.get(
    "/businesses/me",
    response_model=list[BusinessRead],
    summary="List businesses owned by current authenticated user",
)
def get_my_businesses(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return business_service.get_businesses_by_owner(db, user_id)


@router.get(
    "/businesses/{business_id}",
    response_model=BusinessRead,
    summary="Get business profile by ID",
)
def get_business(
    business_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = business_service.get_business_by_id(db, business_id)
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")
    if business.owner_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this business.",
        )
    return business


@router.patch(
    "/businesses/{business_id}",
    response_model=BusinessRead,
    summary="Update business profile",
)
def update_business(
    business_id: str,
    data: BusinessUpdate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return business_service.update_business(db, business_id, user_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch(
    "/admin/businesses/{business_id}/status",
    response_model=BusinessRead,
    summary="Admin: Update business status (e.g. SUSPENDED)",
)
def admin_update_business_status(
    business_id: str,
    status_data: BusinessStatusUpdateRequest,
    admin_id: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        return business_service.update_business_status(db, business_id, status_data, admin_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# 3. Campaigns
# ============================================================================

@router.post(
    "/businesses/{business_id}/campaigns",
    response_model=CampaignRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new campaign for a business",
)
def create_campaign(
    business_id: str,
    data: CampaignCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return campaign_service.create_campaign(db, business_id, user_id, data)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/businesses/{business_id}/campaigns",
    response_model=list[CampaignRead],
    summary="List all campaigns for a business",
)
def list_business_campaigns(
    business_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return campaign_service.list_campaigns_for_business(db, business_id, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/campaigns/{campaign_id}",
    response_model=CampaignRead,
    summary="Get campaign details",
)
def get_campaign(
    campaign_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = campaign_service.get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    if campaign.business.owner_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this campaign.",
        )
    return campaign


@router.patch(
    "/campaigns/{campaign_id}",
    response_model=CampaignRead,
    summary="Update a campaign draft",
)
def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return campaign_service.update_campaign(db, campaign_id, user_id, data)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/campaigns/{campaign_id}/submit-approval",
    response_model=CampaignRead,
    summary="Submit a campaign for admin approval",
)
def submit_campaign_for_approval(
    campaign_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return campaign_service.submit_campaign_for_approval(db, campaign_id, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/campaigns/{campaign_id}/toggle-active",
    response_model=CampaignRead,
    summary="Activate or pause an approved campaign",
)
def toggle_campaign_active(
    campaign_id: str,
    data: CampaignToggleActiveRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return campaign_service.toggle_campaign_active(db, campaign_id, user_id, data.is_active)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/admin/campaigns",
    response_model=list[CampaignRead],
    summary="Admin: List campaigns for review",
)
def admin_list_campaigns(
    approval_status: Annotated[str | None, Query(alias="approval_status")] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return campaign_service.admin_list_campaigns(db, approval_status=approval_status, skip=skip, limit=limit)


@router.post(
    "/admin/campaigns/{campaign_id}/review",
    response_model=CampaignRead,
    summary="Admin: Approve, reject, or suspend campaign",
)
def admin_review_campaign(
    campaign_id: str,
    review_data: CampaignReviewRequest,
    admin_id: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        return campaign_service.admin_review_campaign(db, campaign_id, review_data, admin_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# 4. Offers
# ============================================================================

@router.post(
    "/campaigns/{campaign_id}/offers",
    response_model=OfferRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an offer for a campaign",
)
def create_offer(
    campaign_id: str,
    data: OfferCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return campaign_service.create_offer(db, campaign_id, user_id, data)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/campaigns/{campaign_id}/offers",
    response_model=list[OfferRead],
    summary="List offers for a campaign",
)
def list_offers(
    campaign_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return campaign_service.list_offers_for_campaign(db, campaign_id, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/offers/{offer_id}",
    response_model=OfferRead,
    summary="Update an offer",
)
def update_offer(
    offer_id: str,
    data: OfferUpdate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return campaign_service.update_offer(db, offer_id, user_id, data)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# 5. Advertiser Payments
# ============================================================================

@router.post(
    "/businesses/{business_id}/payments",
    response_model=AdvertiserPaymentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record an advertiser payment",
)
def record_payment(
    business_id: str,
    data: AdvertiserPaymentCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return payment_service.record_payment(db, business_id, user_id, data)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/businesses/{business_id}/payments",
    response_model=list[AdvertiserPaymentRead],
    summary="List payments for a business",
)
def list_business_payments(
    business_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return payment_service.list_payments_for_business(db, business_id, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/admin/payments",
    response_model=list[AdvertiserPaymentRead],
    summary="Admin: List advertiser payments",
)
def admin_list_payments(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return payment_service.admin_list_payments(db, verification_status=status_filter, skip=skip, limit=limit)


@router.post(
    "/admin/payments/{payment_id}/verify",
    response_model=AdvertiserPaymentRead,
    summary="Admin: Verify or fail an advertiser payment",
)
def admin_verify_payment(
    payment_id: str,
    data: AdvertiserPaymentVerifyRequest,
    admin_id: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        return payment_service.admin_verify_payment(db, payment_id, data, admin_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# 6. Promotion Engine & Event Tracking
# ============================================================================

@router.post(
    "/promotions/select",
    response_model=PromotionSelectionResponse,
    summary="Select relevant local business promotions for a citizen",
)
def select_promotions(
    request: PromotionSelectionRequest,
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
    db: Session = Depends(get_db),
):
    """Dynamically select 2-3 local promotions based on citizen profile and/or SpotFix complaint locations."""
    citizen_id = x_user_id or request.citizen_user_id or "anonymous_citizen"
    try:
        return selection_service.select_promotions(db, request, citizen_id)
    except Exception as e:
        # Promotion engine must fail gracefully without bringing down caller
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Promotion selection failed: {e}")


@router.get(
    "/promotions/{campaign_id}",
    response_model=PromotionItem,
    summary="Get promotion details for a campaign",
)
def get_promotion_details(
    campaign_id: str,
    db: Session = Depends(get_db),
):
    campaign = campaign_service.get_campaign_by_id(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion campaign not found.")

    valid_offers = [
        PromotionOfferItem.model_validate(o)
        for o in campaign.offers
        if o.is_active and o.redemption_count < o.max_redemptions
    ]

    return PromotionItem(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        campaign_type=campaign.campaign_type,
        business_name=campaign.business.name,
        business_category=campaign.business.category,
        business_area=campaign.business.area,
        matched_location_source="CITYWIDE",
        distance_km=None,
        offers=valid_offers,
    )


@router.post(
    "/promotions/events",
    response_model=PromotionEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record promotion impression or click",
)
def record_promotion_event(
    data: PromotionEventCreate,
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
    db: Session = Depends(get_db),
):
    """Reliably records impression or click events reported by citizen client."""
    citizen_id = x_user_id or "anonymous_citizen"
    try:
        return events_service.record_promotion_event(db, data, citizen_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# 7. Citizen Coupon Claiming & Scratch-Cards
# ============================================================================

@router.post(
    "/coupons/claim",
    response_model=CouponClaimRead,
    status_code=status.HTTP_201_CREATED,
    summary="Citizen: Claim an offer coupon",
)
def claim_coupon(
    data: CouponClaimCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Claims an offer for the authenticated citizen, generating a unique personalized coupon code."""
    try:
        return claims_service.claim_coupon(db, data.offer_id, user_id, data.client_notes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/coupons/my",
    response_model=list[CouponClaimRead],
    summary="Citizen: List my claimed coupons and scratch-card rewards",
)
def list_my_coupons(
    status_filter: Annotated[CouponClaimStatus | None, Query(alias="status")] = None,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all coupons claimed by the authenticated citizen."""
    try:
        return claims_service.list_my_claimed_coupons(db, user_id, status_filter)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/scratch-cards/{offer_id}/reveal",
    response_model=ScratchCardRevealRead,
    summary="Citizen: Reveal a predetermined scratch-card reward",
)
def reveal_scratch_card(
    offer_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authorizes and reveals a predetermined scratch-card reward configured by the business.

    Subsequent calls return the exact same persisted reward.
    """
    try:
        return claims_service.reveal_scratch_card(db, offer_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# 8. In-Store Coupon Redemption
# ============================================================================

@router.post(
    "/businesses/{business_id}/redeem",
    response_model=CouponRedemptionRead,
    summary="Merchant: Verify and redeem a citizen's coupon code in-store",
)
def redeem_coupon(
    business_id: str,
    data: CouponRedemptionRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verifies a citizen's unique coupon code in-store, locks row to prevent double-redemptions,

    updates redemption counts and logs a verified redemption event.
    """
    try:
        return claims_service.redeem_coupon(db, business_id, user_id, data.coupon_code, data.notes)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# 9. Performance & Platform Analytics
# ============================================================================

@router.get(
    "/campaigns/{campaign_id}/analytics",
    response_model=CampaignAnalyticsRead,
    summary="Business Owner: Get conversion analytics for a campaign",
)
def get_campaign_analytics(
    campaign_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns impressions, clicks, claims, redemptions, CTR, and conversion rates."""
    try:
        return analytics_service.get_campaign_analytics(db, campaign_id, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/businesses/{business_id}/analytics",
    response_model=BusinessAnalyticsRead,
    summary="Business Owner: Get aggregate analytics for a business",
)
def get_business_analytics(
    business_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns business-wide campaign performance and monetization metrics."""
    try:
        return analytics_service.get_business_analytics(db, business_id, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/admin/analytics",
    response_model=AdminPlatformAnalyticsRead,
    summary="Admin: Get platform-wide operational and revenue intelligence",
)
def get_admin_analytics(
    _admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Returns system-wide counts, campaign metrics, platform CTR, and revenue totals."""
    return analytics_service.get_admin_analytics(db)


