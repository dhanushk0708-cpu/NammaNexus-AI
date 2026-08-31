from io import BytesIO
from pathlib import Path
from app.core.config import settings
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.services.storage.local import LocalStorageService


router = APIRouter(
    prefix="/spotfix",
    tags=["SpotFix"],
)


ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


storage_service = LocalStorageService(
    Path("storage/spotfix")
)


@router.post("/uploads")
async def upload_image(image: UploadFile = File(...)):
    extension = ALLOWED_CONTENT_TYPES.get(image.content_type)

    if extension is None:
        raise HTTPException(
            status_code=415,
            detail="Only JPEG, PNG, and WebP images are allowed.",
        )

    image_bytes = await image.read()

    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image size must not exceed 10 MB.",
        )

    try:
        with Image.open(BytesIO(image_bytes)) as verified_image:
            verified_image.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid image.",
        )

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