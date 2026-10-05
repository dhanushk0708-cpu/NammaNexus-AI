from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.complaint import ComplaintStatus


class ComplaintDraftCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: str | None = None
    description: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    image_storage_key: str | None = None


class ComplaintUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subject: str | None = None
    complaint_text: str | None = None


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: ComplaintStatus
    category: str | None = None
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_storage_key: str | None = None
    confidence: float | None = None
    severity: str | None = None
    visual_explanation: str | None = None
    impact_score: int | None = None
    priority: str | None = None
    impact_reason: str | None = None
    authority: str | None = None
    department: str | None = None
    routing_reason: str | None = None
    subject: str | None = None
    complaint_text: str | None = None
    submitted_at: datetime | None = None
    recipient_email: str | None = None
    instagram_post_id: str | None = None
