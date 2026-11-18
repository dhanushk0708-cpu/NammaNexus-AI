from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.endpoints.nammadeals_deps import get_current_admin, get_current_user
from app.db.dependencies import get_db
from app.models.nammadeals import Business
from app.schemas.nammadeals import (
    AdvertiserPaymentCreate,
    AdvertiserPaymentRead,
    AdvertiserPaymentVerifyRequest,
    BusinessRead,
    BusinessRegistrationCreate,
    BusinessRegistrationRead,
    BusinessRegistrationReviewRequest,
    BusinessStatusUpdateRequest,
    BusinessUpdate,
    CampaignCreate,
    CampaignRead,
    CampaignReviewRequest,
    CampaignToggleActiveRequest,
    CampaignUpdate,
    OfferCreate,
    OfferRead,
    OfferUpdate,
)
from app.services.nammadeals import business as business_service
from app.services.nammadeals import campaign as campaign_service
from app.services.nammadeals import payment as payment_service

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
