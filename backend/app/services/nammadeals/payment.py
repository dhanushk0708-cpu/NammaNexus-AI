import logging
from sqlalchemy.orm import Session

from app.models.nammadeals import (
    AdvertiserPayment,
    Business,
    Campaign,
    PaymentVerificationStatus,
)
from app.schemas.nammadeals import (
    AdvertiserPaymentCreate,
    AdvertiserPaymentVerifyRequest,
)

logger = logging.getLogger(__name__)


def record_payment(
    db: Session,
    business_id: str,
    owner_user_id: str,
    data: AdvertiserPaymentCreate,
) -> AdvertiserPayment:
    """Record an advertiser payment for business verification or campaign promotion."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise ValueError(f"Business '{business_id}' not found.")
    if business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to record payments for this business.")

    if data.campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == data.campaign_id).first()
        if not campaign or campaign.business_id != business.id:
            raise ValueError(f"Campaign '{data.campaign_id}' does not belong to business '{business_id}'.")

    # Check for existing transaction_id
    existing = db.query(AdvertiserPayment).filter(AdvertiserPayment.transaction_id == data.transaction_id).first()
    if existing:
        raise ValueError(f"Transaction ID '{data.transaction_id}' has already been recorded.")

    payment = AdvertiserPayment(
        business_id=business.id,
        campaign_id=data.campaign_id,
        amount=data.amount,
        currency=data.currency,
        transaction_id=data.transaction_id,
        payment_method=data.payment_method.value,
        payment_date=data.payment_date,
        verification_status=PaymentVerificationStatus.PENDING.value,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info("Payment '%s' recorded for business '%s' (tx: %s)", payment.id, business.id, payment.transaction_id)
    return payment


def list_payments_for_business(
    db: Session,
    business_id: str,
    owner_user_id: str,
) -> list[AdvertiserPayment]:
    """List payment records for a business, checking owner permissions."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise ValueError(f"Business '{business_id}' not found.")
    if business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to view payments for this business.")

    return (
        db.query(AdvertiserPayment)
        .filter(AdvertiserPayment.business_id == business_id)
        .order_by(AdvertiserPayment.created_at.desc())
        .all()
    )


def admin_list_payments(
    db: Session,
    verification_status: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[AdvertiserPayment]:
    """Admin endpoint to list advertiser payments."""
    query = db.query(AdvertiserPayment)
    if verification_status:
        query = query.filter(AdvertiserPayment.verification_status == verification_status)
    return query.order_by(AdvertiserPayment.created_at.desc()).offset(skip).limit(limit).all()


def admin_verify_payment(
    db: Session,
    payment_id: str,
    verify_data: AdvertiserPaymentVerifyRequest,
    admin_id: str,
) -> AdvertiserPayment:
    """Admin verifies or rejects a payment."""
    payment = db.query(AdvertiserPayment).filter(AdvertiserPayment.id == payment_id).first()
    if not payment:
        raise ValueError(f"Payment record '{payment_id}' not found.")

    status_map = {
        "VERIFY": PaymentVerificationStatus.VERIFIED.value,
        "FAIL": PaymentVerificationStatus.FAILED.value,
        "REFUND": PaymentVerificationStatus.REFUNDED.value,
    }
    payment.verification_status = status_map[verify_data.action]
    if verify_data.admin_notes:
        payment.admin_notes = verify_data.admin_notes

    db.commit()
    db.refresh(payment)
    logger.info("Payment '%s' updated to status '%s' by admin '%s'", payment.id, payment.verification_status, admin_id)
    return payment
