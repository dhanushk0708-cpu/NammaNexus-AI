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
    BusinessRead,
    BusinessRegistrationCreate,
    BusinessRegistrationRead,
    BusinessRegistrationReviewRequest,
    BusinessStatusUpdateRequest,
    BusinessUpdate,
)
from app.services.nammadeals.maps import (
    build_view_store_url,
    extract_coordinates_from_maps_url,
    is_valid_google_maps_url,
)

logger = logging.getLogger(__name__)


def build_registration_read(r: BusinessRegistration) -> BusinessRegistrationRead:
    store_url = build_view_store_url(
        google_maps_url=r.google_maps_url,
        latitude=r.latitude,
        longitude=r.longitude,
        address=r.address,
        city=r.city,
    )
    return BusinessRegistrationRead(
        id=r.id,
        business_name=r.business_name,
        description=r.description,
        category=r.category,
        contact_name=r.contact_name,
        email=r.email,
        phone=r.phone,
        address=r.address,
        city=r.city,
        area=r.area,
        pincode=r.pincode,
        google_maps_url=r.google_maps_url,
        logo_url=r.logo_url,
        google_maps_store_url=store_url,
        latitude=r.latitude,
        longitude=r.longitude,
        status=BusinessRegistrationStatus(r.status),
        rejection_reason=r.rejection_reason,
        reviewed_by=r.reviewed_by,
        reviewed_at=r.reviewed_at,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def build_business_read(b: Business) -> BusinessRead:
    store_url = build_view_store_url(
        google_maps_url=b.google_maps_url,
        latitude=b.latitude,
        longitude=b.longitude,
        address=b.address,
        city=b.city,
    )
    return BusinessRead(
        id=b.id,
        owner_user_id=b.owner_user_id,
        registration_id=b.registration_id,
        name=b.name,
        description=b.description,
        category=b.category,
        email=b.email,
        phone=b.phone,
        address=b.address,
        city=b.city,
        area=b.area,
        pincode=b.pincode,
        google_maps_url=b.google_maps_url,
        logo_url=b.logo_url,
        google_maps_store_url=store_url,
        latitude=b.latitude,
        longitude=b.longitude,
        status=BusinessStatus(b.status),
        verified_at=b.verified_at,
        verified_by=b.verified_by,
        rejection_reason=b.rejection_reason,
        created_at=b.created_at,
        updated_at=b.updated_at,
    )


def submit_registration(db: Session, data: BusinessRegistrationCreate) -> BusinessRegistration:
    """Submit a prospective business registration request.

    New registrations enter PENDING status and must be verified by an administrator.
    Validates Google Maps link if supplied and extracts coordinates when reliably possible.
    """
    maps_url = data.google_maps_url.strip() if data.google_maps_url and data.google_maps_url.strip() else None
    if maps_url and not is_valid_google_maps_url(maps_url):
        raise ValueError("Invalid Google Maps link. Please provide a valid maps.google.com or maps.app.goo.gl link.")

    lat = data.latitude
    lng = data.longitude
    if maps_url and (lat is None or lng is None):
        extracted_lat, extracted_lng = extract_coordinates_from_maps_url(maps_url)
        if extracted_lat is not None and extracted_lng is not None:
            lat = extracted_lat
            lng = extracted_lng

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
        google_maps_url=maps_url,
        logo_url=data.logo_url,
        latitude=lat,
        longitude=lng,
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
            google_maps_url=registration.google_maps_url,
            logo_url=registration.logo_url,
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
    if business.owner_user_id != owner_user_id and owner_user_id != "admin":
        raise PermissionError("You do not have permission to modify this business.")

    update_dict = data.model_dump(exclude_unset=True)
    if "google_maps_url" in update_dict and update_dict["google_maps_url"]:
        maps_url = update_dict["google_maps_url"].strip()
        if not is_valid_google_maps_url(maps_url):
            raise ValueError("Invalid Google Maps link.")
        update_dict["google_maps_url"] = maps_url
        if "latitude" not in update_dict or update_dict["latitude"] is None:
            extracted_lat, extracted_lng = extract_coordinates_from_maps_url(maps_url)
            if extracted_lat is not None and extracted_lng is not None:
                update_dict["latitude"] = extracted_lat
                update_dict["longitude"] = extracted_lng

    for field, val in update_dict.items():
        setattr(business, field, val)

    db.commit()
    db.refresh(business)
    return business


def admin_update_business(
    db: Session,
    business_id: str,
    data: BusinessUpdate,
    admin_id: str,
) -> Business:
    """Admin edits or verifies business location and profile details."""
    return update_business(db, business_id, owner_user_id="admin", data=data)


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
