import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.schemas.spotfix import (
    ComplaintDraftCreate,
    ComplaintResponse,
    ComplaintUpdate,
)
from app.services.email import EmailDeliveryError, EmailService
from app.services.instagram import InstagramPublishError, InstagramService
from app.services.gemini_vision import (
    GeminiResponseValidationError,
    GeminiVisionService,
    GeminiVisionServiceError,
)
from app.services.image_validation import (
    ImageTooLargeError,
    InvalidImageFileError,
    UnsupportedImageTypeError,
    validate_image_upload,
)
from app.services.complaint_writer import write_complaint_draft
from app.services.predictive_impact import calculate_predictive_impact
from app.services.routing import route_complaint
from app.services.storage.local import (
    LocalStorageService,
    StorageKeyNotFoundError,
    StorageKeyValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/spotfix",
    tags=["SpotFix"],
)


storage_service = LocalStorageService(Path("storage/spotfix"))
gemini_service = GeminiVisionService()
email_service = EmailService()
instagram_service = InstagramService()


@router.post("/uploads")
async def upload_image(image: UploadFile = File(...)):
    image_bytes = await image.read()

    try:
        extension = validate_image_upload(image_bytes, image.content_type)
    except UnsupportedImageTypeError as exc:
        raise HTTPException(
            status_code=415,
            detail=str(exc),
        ) from exc
    except ImageTooLargeError as exc:
        raise HTTPException(
            status_code=413,
            detail=str(exc),
        ) from exc
    except InvalidImageFileError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    stored_filename = await storage_service.save(
        image_bytes,
        extension,
    )

    return {
        "success": True,
        "original_filename": image.filename,
        "stored_filename": stored_filename,
        "content_type": image.content_type,
        "size_bytes": len(image_bytes),
        "message": "Image uploaded and stored successfully.",
    }


@router.post(
    "/complaints",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_complaint_draft(
    complaint_in: ComplaintDraftCreate,
    db: Session = Depends(get_db),
):
    try:
        validated_key = storage_service.validate_image_reference(
            complaint_in.image_storage_key
        )
    except StorageKeyNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except StorageKeyValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    ai_result = None
    category = complaint_in.category

    if validated_key is not None:
        try:
            image_bytes = storage_service.read_image(validated_key)
            ai_result = gemini_service.analyze_image(
                image_bytes,
                mime_type="image/jpeg",
            )
        except StorageKeyNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            ) from exc
        except StorageKeyValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        except GeminiResponseValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        except GeminiVisionServiceError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        category = ai_result.category

    impact_result = calculate_predictive_impact(
        severity=ai_result.severity if ai_result else None,
        confidence=ai_result.confidence if ai_result else None,
        category=category,
        latitude=complaint_in.latitude,
        longitude=complaint_in.longitude,
    )

    routing_result = route_complaint(
        category=category,
        severity=ai_result.severity if ai_result else None,
        priority=impact_result.priority,
        impact_score=impact_result.impact_score,
        latitude=complaint_in.latitude,
        longitude=complaint_in.longitude,
    )

    draft_result = write_complaint_draft(
        category=category,
        description=complaint_in.description,
        latitude=complaint_in.latitude,
        longitude=complaint_in.longitude,
        severity=ai_result.severity if ai_result else None,
        confidence=ai_result.confidence if ai_result else None,
        visual_explanation=ai_result.visual_explanation if ai_result else None,
        impact_score=impact_result.impact_score,
        priority=impact_result.priority,
        impact_reason=impact_result.impact_reason,
        authority=routing_result.authority,
        department=routing_result.department,
        routing_reason=routing_result.routing_reason,
    )

    complaint = Complaint(
        status=ComplaintStatus.DRAFT.value,
        category=category,
        description=complaint_in.description,
        latitude=complaint_in.latitude,
        longitude=complaint_in.longitude,
        image_storage_key=validated_key,
        confidence=ai_result.confidence if ai_result else None,
        severity=ai_result.severity if ai_result else None,
        visual_explanation=ai_result.visual_explanation if ai_result else None,
        impact_score=impact_result.impact_score,
        priority=impact_result.priority,
        impact_reason=impact_result.impact_reason,
        authority=routing_result.authority,
        department=routing_result.department,
        routing_reason=routing_result.routing_reason,
        subject=draft_result.subject,
        complaint_text=draft_result.complaint_text,
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return complaint


@router.get(
    "/complaints/{complaint_id}",
    response_model=ComplaintResponse,
)
async def get_complaint(
    complaint_id: str,
    db: Session = Depends(get_db),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )
    return complaint


@router.patch(
    "/complaints/{complaint_id}",
    response_model=ComplaintResponse,
)
async def update_complaint_draft(
    complaint_id: str,
    complaint_in: ComplaintUpdate,
    db: Session = Depends(get_db),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )
    if complaint.status == ComplaintStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted complaints cannot be edited.",
        )

    if complaint_in.subject is not None:
        complaint.subject = complaint_in.subject
    if complaint_in.complaint_text is not None:
        complaint.complaint_text = complaint_in.complaint_text

    db.commit()
    db.refresh(complaint)
    return complaint


@router.post(
    "/complaints/{complaint_id}/approve",
    response_model=ComplaintResponse,
)
async def approve_complaint(
    complaint_id: str,
    db: Session = Depends(get_db),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )
    if complaint.status == ComplaintStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted complaints cannot be approved again.",
        )

    complaint.status = ComplaintStatus.APPROVED.value
    db.commit()
    db.refresh(complaint)
    return complaint


@router.post(
    "/complaints/{complaint_id}/submit",
    response_model=ComplaintResponse,
)
async def submit_complaint(
    complaint_id: str,
    db: Session = Depends(get_db),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )
    if complaint.status == ComplaintStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint has already been submitted.",
        )
    if complaint.status != ComplaintStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint must be approved before submission.",
        )

    recipient_email = email_service.get_recipient_email(
        complaint.authority,
        complaint.department,
    )

    try:
        email_service.send_official_email(
            complaint_id=complaint.id,
            subject=complaint.subject or "Civic Issue Complaint",
            complaint_text=complaint.complaint_text or "",
            authority=complaint.authority,
            department=complaint.department,
            recipient_email=recipient_email,
        )
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    complaint.status = ComplaintStatus.SUBMITTED.value
    complaint.submitted_at = datetime.utcnow()
    complaint.recipient_email = recipient_email

    # Attempt Instagram publishing after successful submission
    try:
        post_id = instagram_service.publish_complaint(complaint)
        if post_id:
            complaint.instagram_post_id = post_id
    except InstagramPublishError as exc:
        logger.warning("Instagram publishing failed for complaint %s: %s", complaint.id, exc)

    db.commit()
    db.refresh(complaint)
    return complaint


@router.get(
    "/images/{image_key}",
    response_class=Response,
)
async def get_public_image(image_key: str):
    try:
        image_bytes = storage_service.read_image(image_key)
    except (StorageKeyNotFoundError, StorageKeyValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        ) from exc

    ext = Path(image_key).suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(ext)

    if not media_type:
        if image_bytes.startswith(b"\xff\xd8\xff"):
            media_type = "image/jpeg"
        elif image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            media_type = "image/png"
        elif image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
            media_type = "image/webp"
        else:
            media_type = "image/jpeg"

    return Response(
        content=image_bytes,
        media_type=media_type,
        headers={"Content-Length": str(len(image_bytes))},
    )
