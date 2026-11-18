from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from app.models.nammadeals import (
    Business,
    BusinessRegistration,
    BusinessRegistrationStatus,
    BusinessStatus,
    Campaign,
)
from app.schemas.nammadeals import (
    BusinessRegistrationCreate,
    BusinessRegistrationReviewRequest,
    BusinessStatusUpdateRequest,
    BusinessUpdate,
)

logger = logging.getLogger(__name__)


def submit_registration(db: Session, data: BusinessRegistrationCreate) -> BusinessRegistration:
    """Submit a prospective business registration request.

    New registrations enter PENDING status and must be verified by an administrator.
    """
    registration = BusinessRegistration(
        business_name=data.business_name,
        description=data.description,
        category=data.category,
        contact_name=data.contact_name,
        email=data.email,
        phone=data.phone,
        address=data.address,
        city=data.city,
        area=data.area,
        pincode=data.pincode,
        latitude=data.latitude,
        longitude=data.longitude,
        status=BusinessRegistrationStatus.PENDING.value,
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    logger.info("New business registration submitted: id=%s name=%s", registration.id, registration.business_name)
    return registration


def list_registrations(
    db: Session,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[BusinessRegistration]:
    """List business registration requests with optional status filtering."""
    query = db.query(BusinessRegistration)
    if status:
        query = query.filter(BusinessRegistration.status == status)
    return query.order_by(BusinessRegistration.created_at.desc()).offset(skip).limit(limit).all()


def get_registration(db: Session, reg_id: str) -> BusinessRegistration | None:
    """Fetch a single registration by UUID."""
    return db.query(BusinessRegistration).filter(BusinessRegistration.id == reg_id).first()


def review_registration(
    db: Session,
    reg_id: str,
    review_data: BusinessRegistrationReviewRequest,
    admin_id: str,
) -> tuple[BusinessRegistration, Business | None]:
    """Admin reviews a business registration request.

    If APPROVED:
      - Registration transitions to APPROVED.
      - A new Business profile is created with status APPROVED and linked to the owner user ID.
    If REJECTED:
      - Registration transitions to REJECTED with rejection reason.
      - No Business record is created.
    """
    registration = get_registration(db, reg_id)
    if not registration:
        raise ValueError(f"Business registration '{reg_id}' not found.")

    if registration.status != BusinessRegistrationStatus.PENDING.value:
        raise ValueError(
            f"Cannot review registration with status '{registration.status}'. Only PENDING registrations can be reviewed."
        )

    now = datetime.now(timezone.utc)
    business: Business | None = None

    if review_data.action == "APPROVE":
        registration.status = BusinessRegistrationStatus.APPROVED.value
        registration.reviewed_by = admin_id
        registration.reviewed_at = now
        registration.rejection_reason = None

        business = Business(
            owner_user_id=review_data.owner_user_id,  # type: ignore[arg-type]
            registration_id=registration.id,
            name=registration.business_name,
            description=registration.description,
            category=registration.category,
            email=registration.email,
            phone=registration.phone,
            address=registration.address,
            city=registration.city,
            area=registration.area,
            pincode=registration.pincode,
            latitude=registration.latitude,
            longitude=registration.longitude,
            status=BusinessStatus.APPROVED.value,
            verified_at=now,
            verified_by=admin_id,
        )
        db.add(business)
        db.commit()
        db.refresh(registration)
        db.refresh(business)
        logger.info(
            "Approved business registration '%s'. Created Business '%s' for owner '%s'.",
            registration.id,
            business.id,
            business.owner_user_id,
        )
    else:  # REJECT
        registration.status = BusinessRegistrationStatus.REJECTED.value
        registration.rejection_reason = review_data.rejection_reason
        registration.reviewed_by = admin_id
        registration.reviewed_at = now
        db.commit()
        db.refresh(registration)
        logger.info("Rejected business registration '%s'. Reason: %s", registration.id, registration.rejection_reason)

    return registration, business


def get_business_by_id(db: Session, business_id: str) -> Business | None:
    """Fetch a business by ID."""
    return db.query(Business).filter(Business.id == business_id).first()


def get_businesses_by_owner(db: Session, owner_user_id: str) -> list[Business]:
    """Fetch all businesses owned by a specific user."""
    return (
        db.query(Business)
        .filter(Business.owner_user_id == owner_user_id)
        .order_by(Business.created_at.desc())
        .all()
    )


def update_business(
    db: Session,
    business_id: str,
    owner_user_id: str,
    data: BusinessUpdate,
) -> Business:
    """Owner updates non-administrative business profile fields."""
    business = get_business_by_id(db, business_id)
    if not business:
        raise ValueError(f"Business '{business_id}' not found.")
    if business.owner_user_id != owner_user_id:
        raise PermissionError("You do not have permission to modify this business.")

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(business, field, val)

    db.commit()
    db.refresh(business)
    return business


def update_business_status(
    db: Session,
    business_id: str,
    status_data: BusinessStatusUpdateRequest,
    admin_id: str,
) -> Business:
    """Admin updates business status (e.g., SUSPENDED, APPROVED, REJECTED).

    If SUSPENDED:
      - Immediately deactivates all active advertising campaigns for this business.
    """
    business = get_business_by_id(db, business_id)
    if not business:
        raise ValueError(f"Business '{business_id}' not found.")

    old_status = business.status
    business.status = status_data.status.value
    if status_data.reason:
        business.rejection_reason = status_data.reason

    if status_data.status == BusinessStatus.APPROVED:
        business.verified_at = datetime.now(timezone.utc)
        business.verified_by = admin_id

    # Enforce invariant: Suspended businesses cannot run campaigns
    if status_data.status == BusinessStatus.SUSPENDED:
        deactivated_count = (
            db.query(Campaign)
            .filter(Campaign.business_id == business.id, Campaign.is_active.is_(True))
            .update({"is_active": False}, synchronize_session=False)
        )
        logger.warning(
            "Business '%s' suspended by admin '%s'. Deactivated %d active campaigns.",
            business.id,
            admin_id,
            deactivated_count,
        )

    db.commit()
    db.refresh(business)
    logger.info("Updated business '%s' status: %s -> %s", business.id, old_status, business.status)
    return business
