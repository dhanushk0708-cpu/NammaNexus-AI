from __future__ import annotations

import httpx

from app.core.config import settings


class EmailDeliveryError(Exception):
    """Raised when sending an official email fails."""

    pass


class EmailService:
    def get_recipient_email(
        self,
        authority: str | None,
        department: str | None,
    ) -> str:
        if authority and department:
            key = f"{authority}:{department}"
            if key in settings.official_email_mapping:
                return settings.official_email_mapping[key]

        if authority:
            authority_key = f"{authority}:DEFAULT"
            if authority_key in settings.official_email_mapping:
                return settings.official_email_mapping[authority_key]

        return settings.default_official_email

    def send_official_email(
        self,
        *,
        complaint_id: str,
        subject: str,
        complaint_text: str,
        authority: str | None,
        department: str | None,
        recipient_email: str | None = None,
    ) -> dict:
        target_email = recipient_email or self.get_recipient_email(
            authority, department
        )
        email_subject = f"[Complaint Ref: {complaint_id}] {subject}"
        email_body = (
            f"OFFICIAL CIVIC COMPLAINT SUBMISSION\n"
            f"Reference ID: {complaint_id}\n"
            f"Authority: {authority or 'N/A'}\n"
            f"Department: {department or 'N/A'}\n\n"
            f"Subject: {subject}\n\n"
            f"Details:\n{complaint_text}\n"
        )

        if not settings.resend_api_key:
            raise EmailDeliveryError(
                "Email delivery failed: Resend API key is not configured."
            )

        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.resend_from_email,
                    "to": [target_email],
                    "subject": email_subject,
                    "text": email_body,
                },
                timeout=10.0,
            )
            if response.status_code not in (200, 201):
                raise EmailDeliveryError(
                    f"Email provider returned status {response.status_code}: {response.text}"
                )
            return response.json()
        except httpx.RequestError as exc:
            raise EmailDeliveryError(
                f"Failed to communicate with email provider: {exc}"
            ) from exc
