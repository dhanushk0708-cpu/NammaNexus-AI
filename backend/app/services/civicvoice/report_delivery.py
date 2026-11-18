"""CivicVoice Report Delivery & Human Approval Workflow Manager.

Manages review transitions (draft -> pending_review -> approved -> sent),
enforces cryptographic content-hash approval binding, guarantees idempotency,
and integrates with official delivery channels while safeguarding privacy.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.civicvoice import (
    CivicVoiceReport,
    CivicVoiceReportAudit,
)
from app.schemas.civicvoice import (
    CivicVoiceReportExportResponse,
    CivicVoiceReportSendResponse,
    CivicVoiceReportUpdate,
    ReportStatus,
)
from app.services.civicvoice.department_mapper import resolve_department_mapping
from app.services.civicvoice.report_generator import compute_report_content_hash

logger = logging.getLogger(__name__)


class ReportWorkflowError(Exception):
    """Raised when an invalid report workflow transition or permission violation occurs."""

    pass


class CivicVoiceReportDeliveryService:
    """Handles report editing, review approval/rejection, export, and official email delivery."""

    def update_report(
        self,
        db: Session,
        report_id: str,
        update_data: CivicVoiceReportUpdate,
        performed_by: str,
    ) -> CivicVoiceReport:
        """Applies edits to an existing report.

        CRITICAL INTEGRITY RULE: If an approved report is modified, its approval
        is automatically invalidated, setting status back to 'pending_review' and
        requiring new authorized human sign-off.
        """
        report = db.get(CivicVoiceReport, report_id)
        if not report:
            raise ReportWorkflowError(f"CivicVoice Report '{report_id}' not found.")

        if report.status == ReportStatus.SENT.value:
            raise ReportWorkflowError("Cannot modify a report that has already been dispatched to an official authority.")

        was_approved = report.status == ReportStatus.APPROVED.value
        old_hash = report.content_hash
        previous_status = report.status

        # Apply field updates
        if update_data.title is not None:
            report.title = update_data.title.strip()
        if update_data.summary_content is not None:
            report.summary_content = update_data.summary_content
        if update_data.recommendations is not None:
            report.recommendations = update_data.recommendations
        if update_data.limitations is not None:
            report.limitations = update_data.limitations
        if update_data.authority_name is not None:
            report.authority_name = update_data.authority_name.strip()
        if update_data.department_name is not None:
            report.department_name = update_data.department_name.strip()
        if update_data.official_portal_url is not None:
            report.official_portal_url = update_data.official_portal_url.strip()

        # Handle recipient email changes & re-verification
        if update_data.recipient_email is not None:
            new_email = update_data.recipient_email.strip()
            report.recipient_email = new_email or None
            # If recipient changed, re-evaluate mapping verification
            canonical_mapping = resolve_department_mapping(report.topic)
            if canonical_mapping.is_verified and canonical_mapping.recipient_email == report.recipient_email:
                report.mapping_verified = True
            else:
                # Custom or modified recipient requires manual verification
                report.mapping_verified = False

        # Compute new content hash
        new_hash = compute_report_content_hash(
            title=report.title,
            topic=report.topic,
            recipient_email=report.recipient_email,
            summary_content=report.summary_content,
            recommendations=report.recommendations,
            limitations=report.limitations,
        )
        report.content_hash = new_hash

        # Check for approval invalidation
        if was_approved and new_hash != old_hash:
            report.status = ReportStatus.PENDING_REVIEW.value
            report.approved_by = None
            report.approved_at = None

            audit = CivicVoiceReportAudit(
                report_id=report.id,
                action="approval_invalidated",
                performed_by=performed_by,
                previous_status=ReportStatus.APPROVED.value,
                new_status=ReportStatus.PENDING_REVIEW.value,
                details_json={
                    "reason": "Report content or recipient was modified after approval. New review required.",
                    "old_content_hash": old_hash,
                    "new_content_hash": new_hash,
                },
            )
            db.add(audit)
        else:
            audit = CivicVoiceReportAudit(
                report_id=report.id,
                action="edited",
                performed_by=performed_by,
                previous_status=previous_status,
                new_status=report.status,
                details_json={
                    "content_hash": new_hash,
                    "fields_updated": [k for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None],
                },
            )
            db.add(audit)

        db.commit()
        db.refresh(report)
        return report

    def approve_report(
        self,
        db: Session,
        report_id: str,
        reviewer_id: str,
        notes: str | None = None,
    ) -> CivicVoiceReport:
        """Explicitly approves a civic report for official delivery.

        Binds the exact report content with a fresh SHA-256 hash.
        """
        report = db.get(CivicVoiceReport, report_id)
        if not report:
            raise ReportWorkflowError(f"CivicVoice Report '{report_id}' not found.")

        if report.status == ReportStatus.SENT.value:
            raise ReportWorkflowError("Report has already been delivered.")

        # Re-compute and bind hash
        current_hash = compute_report_content_hash(
            title=report.title,
            topic=report.topic,
            recipient_email=report.recipient_email,
            summary_content=report.summary_content,
            recommendations=report.recommendations,
            limitations=report.limitations,
        )
        report.content_hash = current_hash

        previous_status = report.status
        report.status = ReportStatus.APPROVED.value
        report.approved_by = reviewer_id
        report.approved_at = datetime.now(timezone.utc)
        report.rejection_reason = None

        audit = CivicVoiceReportAudit(
            report_id=report.id,
            action="approved",
            performed_by=reviewer_id,
            previous_status=previous_status,
            new_status=ReportStatus.APPROVED.value,
            details_json={
                "notes": notes,
                "bound_content_hash": current_hash,
                "recipient_email": report.recipient_email,
                "mapping_verified": report.mapping_verified,
            },
        )
        db.add(audit)
        db.commit()
        db.refresh(report)
        return report

    def reject_report(
        self,
        db: Session,
        report_id: str,
        reviewer_id: str,
        reason: str,
    ) -> CivicVoiceReport:
        """Rejects a civic report with recorded justification."""
        report = db.get(CivicVoiceReport, report_id)
        if not report:
            raise ReportWorkflowError(f"CivicVoice Report '{report_id}' not found.")

        if report.status == ReportStatus.SENT.value:
            raise ReportWorkflowError("Cannot reject a report that has already been dispatched.")

        previous_status = report.status
        report.status = ReportStatus.REJECTED.value
        report.rejection_reason = reason
        report.approved_by = None
        report.approved_at = None

        audit = CivicVoiceReportAudit(
            report_id=report.id,
            action="rejected",
            performed_by=reviewer_id,
            previous_status=previous_status,
            new_status=ReportStatus.REJECTED.value,
            details_json={"rejection_reason": reason},
        )
        db.add(audit)
        db.commit()
        db.refresh(report)
        return report

    def send_report(
        self,
        db: Session,
        report_id: str,
        sender_id: str,
        idempotency_key: str | None = None,
        confirm_send: bool = True,
    ) -> CivicVoiceReportSendResponse:
        """Authorizes and delivers an approved civic report to official government channels.

        Enforces:
        1. Explicit human approval prerequisite (`status == approved`).
        2. Recipient verification prerequisite (`mapping_verified == True`).
        3. Cryptographic content hash match (prevents unapproved content tampering).
        4. Idempotency protection to prevent duplicate sends.
        5. Honest fallback to preview/export when Resend API is not configured.
        """
        report = db.get(CivicVoiceReport, report_id)
        if not report:
            raise ReportWorkflowError(f"CivicVoice Report '{report_id}' not found.")

        if not confirm_send:
            raise ReportWorkflowError("Send confirmation is required before dispatching an official report.")

        # 1. Idempotency Check: if report already delivered, return existing delivery status safely
        effective_key = idempotency_key or report.idempotency_key or f"cv-send-{report.id}"
        if report.status == ReportStatus.SENT.value and report.sent_at:
            logger.info("Report '%s' has already been sent (idempotent duplicate avoided).", report.id)
            return CivicVoiceReportSendResponse(
                report_id=report.id,
                status=ReportStatus.SENT,
                recipient=report.recipient_email,
                delivery_mode="resend_api" if settings.resend_api_key else "preview_export_only",
                message="Report has already been delivered to the official authority (idempotent request).",
                idempotency_key=report.idempotency_key,
                delivery_details=report.delivery_details,
            )

        # 2. Human Approval Check
        if report.status != ReportStatus.APPROVED.value:
            raise ReportWorkflowError(
                f"Cannot send report: Status is '{report.status}'. "
                f"Reports must be explicitly approved by an authorized reviewer before delivery."
            )

        # 3. Recipient Verification Check
        if not report.mapping_verified or not report.recipient_email:
            raise ReportWorkflowError(
                f"Cannot send report to unverified recipient: Authority '{report.authority_name}' "
                f"or recipient channel is unverified. Dispatch is restricted to verified official channels."
            )

        # 4. Content Integrity Hash Check
        current_hash = compute_report_content_hash(
            title=report.title,
            topic=report.topic,
            recipient_email=report.recipient_email,
            summary_content=report.summary_content,
            recommendations=report.recommendations,
            limitations=report.limitations,
        )
        if current_hash != report.content_hash:
            raise ReportWorkflowError(
                "Report content integrity check failed: Content or recipient differs from the approved version. "
                "The approval has been invalidated; please submit for re-review."
            )

        # 5. Delivery Execution via Provider (Resend) or Preview/Export
        if not settings.resend_api_key or not settings.resend_api_key.strip():
            logger.warning(
                "Resend API key is not configured. Falling back to local verified preview and export mode."
            )
            audit = CivicVoiceReportAudit(
                report_id=report.id,
                action="delivery_preview_ready",
                performed_by=sender_id,
                previous_status=report.status,
                new_status=report.status,
                details_json={
                    "reason": "Resend API key not configured in environment. Report verified and ready for manual export.",
                    "recipient": report.recipient_email,
                },
            )
            db.add(audit)
            db.commit()

            return CivicVoiceReportSendResponse(
                report_id=report.id,
                status=ReportStatus.APPROVED,
                recipient=report.recipient_email,
                delivery_mode="preview_export_only",
                message=(
                    "Email provider (Resend) is not configured in this environment. "
                    "The report is verified, approved, and ready. Please use the export endpoint to "
                    "download the formatted report for official submission."
                ),
                idempotency_key=effective_key,
                delivery_details={"export_available": True},
            )

        # Dispatch via Resend API
        email_subject = f"[CIVICVOICE OFFICIAL REPORT] {report.title}"
        email_body = self._format_plain_text_dispatch(report)

        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key.strip()}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.resend_from_email,
                    "to": [report.recipient_email],
                    "subject": email_subject,
                    "text": email_body,
                },
                timeout=12.0,
            )

            if response.status_code not in (200, 201):
                err_text = response.text[:200]
                logger.error("Resend API error: %s (status %s)", err_text, response.status_code)
                report.status = ReportStatus.SEND_FAILED.value
                report.delivery_details = {
                    "provider": "resend",
                    "status_code": response.status_code,
                    "error": "Email delivery provider rejected the message.",
                }
                audit = CivicVoiceReportAudit(
                    report_id=report.id,
                    action="send_failed",
                    performed_by=sender_id,
                    previous_status=ReportStatus.APPROVED.value,
                    new_status=ReportStatus.SEND_FAILED.value,
                    details_json={"provider_status": response.status_code},
                )
                db.add(audit)
                db.commit()
                raise ReportWorkflowError(f"Email delivery provider error ({response.status_code}).")

            res_json = response.json()
            provider_id = res_json.get("id")

            report.status = ReportStatus.SENT.value
            report.sent_at = datetime.now(timezone.utc)
            report.idempotency_key = effective_key
            report.delivery_details = {
                "provider": "resend",
                "message_id": provider_id,
                "sent_to": report.recipient_email,
                "sent_at": report.sent_at.isoformat(),
            }

            audit = CivicVoiceReportAudit(
                report_id=report.id,
                action="sent",
                performed_by=sender_id,
                previous_status=ReportStatus.APPROVED.value,
                new_status=ReportStatus.SENT.value,
                details_json={
                    "provider": "resend",
                    "message_id": provider_id,
                    "recipient": report.recipient_email,
                    "idempotency_key": effective_key,
                },
            )
            db.add(audit)
            db.commit()
            db.refresh(report)

            return CivicVoiceReportSendResponse(
                report_id=report.id,
                status=ReportStatus.SENT,
                recipient=report.recipient_email,
                delivery_mode="resend_api",
                message=f"Report successfully delivered to {report.authority_name} ({report.recipient_email}).",
                idempotency_key=effective_key,
                delivery_details=report.delivery_details,
            )

        except httpx.RequestError as exc:
            logger.exception("Network failure communicating with Resend API")
            report.status = ReportStatus.SEND_FAILED.value
            report.delivery_details = {
                "provider": "resend",
                "error": "Network timeout or connection error during official delivery.",
            }
            audit = CivicVoiceReportAudit(
                report_id=report.id,
                action="send_failed",
                performed_by=sender_id,
                previous_status=ReportStatus.APPROVED.value,
                new_status=ReportStatus.SEND_FAILED.value,
                details_json={"network_error": str(exc)[:200]},
            )
            db.add(audit)
            db.commit()
            raise ReportWorkflowError("Network connection failure during official email delivery.") from exc

    def export_report(self, db: Session, report_id: str) -> CivicVoiceReportExportResponse:
        """Formats and exports a complete official markdown document for human review or offline dispatch."""
        report = db.get(CivicVoiceReport, report_id)
        if not report:
            raise ReportWorkflowError(f"CivicVoice Report '{report_id}' not found.")

        now = datetime.now(timezone.utc)
        markdown_body = [
            f"# {report.title}",
            "",
            "## Official Verification & Routing Metadata",
            f"- **Report Reference ID**: `{report.id}`",
            f"- **Target Civic Authority**: {report.authority_name}",
            f"- **Responsible Department**: {report.department_name}",
            f"- **Jurisdiction**: {report.geographic_scope}",
            f"- **Official Portal**: {report.official_portal_url or 'N/A'}",
            f"- **Official Submission Recipient**: {report.recipient_email or 'Unassigned'}",
            f"- **Channel Verification Status**: {'Verified (Official Government Portal)' if report.mapping_verified else 'UNVERIFIED'}",
            f"- **Verification Source**: {report.mapping_source_url or 'N/A'}",
            "",
            "## Approval & Integrity",
            f"- **Workflow Status**: `{report.status.upper()}`",
            f"- **Content Hash (SHA-256)**: `{report.content_hash}`",
            f"- **Approved By**: {report.approved_by or 'Pending Review'}",
            f"- **Approved At**: {report.approved_at.isoformat() if report.approved_at else 'N/A'}",
            f"- **Dispatched At**: {report.sent_at.isoformat() if report.sent_at else 'Not Dispatched'}",
            "",
            "---",
            "",
            report.summary_content,
            "",
            "---",
            "",
            "### Recommended Administrative Actions",
            report.recommendations,
            "",
            "---",
            "",
            "### Methodology, Sample Size & Privacy Limitations",
            report.limitations,
            "",
            "---",
            f"*Generated by NammaNexus AI — CivicVoice Intelligence Platform on {now.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        ]

        return CivicVoiceReportExportResponse(
            report_id=report.id,
            title=report.title,
            format="markdown",
            content="\n".join(markdown_body),
            generated_at=now,
        )

    def _format_plain_text_dispatch(self, report: CivicVoiceReport) -> str:
        """Formats the official plain-text email message for government dispatch."""
        return (
            f"OFFICIAL CIVIC INTELLIGENCE REPORT\n"
            f"===================================\n"
            f"Report ID: {report.id}\n"
            f"Title: {report.title}\n"
            f"Authority: {report.authority_name}\n"
            f"Department: {report.department_name}\n"
            f"Geographic Scope: {report.geographic_scope}\n"
            f"Approved By: {report.approved_by} on {report.approved_at}\n"
            f"Cryptographic Hash: {report.content_hash}\n\n"
            f"SUMMARY & CITIZEN EVIDENCE:\n"
            f"---------------------------\n"
            f"{report.summary_content}\n\n"
            f"RECOMMENDED ADMINISTRATIVE ACTIONS:\n"
            f"-----------------------------------\n"
            f"{report.recommendations}\n\n"
            f"LIMITATIONS & PRIVACY STATEMENT:\n"
            f"--------------------------------\n"
            f"{report.limitations}\n\n"
            f"DATA PRIVACY NOTE: Raw individual resident feedback is strictly confidential. "
            f"Only aggregated metrics and public online citations are included."
        )
