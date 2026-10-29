"""Validate and idempotently import the Phase B research artifact.

This importer is intentionally fail-closed for database targets. It can be
used with a confirmed local SQLite/PostgreSQL session. A development Supabase
target requires an explicit function opt-in and process confirmation flag.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.seeds.pricing_seed import is_safe_local_environment
from app.models.nammaserve import (
    PlatformListing,
    PriceType,
    Service,
    ServicePrice,
    VerificationStatus,
)

PHASE_B_JSON = Path(__file__).resolve().parents[4] / "docs" / "nammaserve" / "research" / "nammaserve_phase_b_research.json"

SERVICE_NAME_TO_SLUG = {
    "AC foam-jet service": "split-ac-deep-clean",
    "AC power-jet service": "split-ac-deep-clean",
    "AC power-jet service (split)": "split-ac-deep-clean",
    "AC power-jet service (window)": "window-ac-service",
    "AC anti-rust deep clean": "split-ac-deep-clean",
    "AC gas refill & check-up": "ac-gas-refill",
    "AC repair inspection / check-up": "ac-repair",
    "AC water-leakage repair": "ac-repair",
    "AC installation": "ac-installation-uninstallation",
    "AC uninstallation": "ac-installation-uninstallation",
    # Category-only directory records are intentionally left for review because
    # attaching them to a specific service would invent a service match.
    "Bathroom deep cleaning": "bathroom-deep-cleaning",
    "Full apartment deep cleaning (unfurnished)": "full-home-deep-cleaning-1bhk",
    "Full apartment deep cleaning (furnished)": "full-home-deep-cleaning-1bhk",
    "Full apartment deep cleaning (unfurnished, premium tier)": "full-home-deep-cleaning-1bhk",
    "Full apartment deep cleaning (furnished, premium tier)": "full-home-deep-cleaning-1bhk",
    "Bungalow/villa deep cleaning (unfurnished)": "full-home-deep-cleaning-3bhk",
    "Bungalow/villa deep cleaning (furnished)": "full-home-deep-cleaning-3bhk",
    "Villa deep cleaning (unfurnished)": "full-home-deep-cleaning-3bhk",
    "Villa deep cleaning (furnished)": "full-home-deep-cleaning-3bhk",
    "Kitchen deep cleaning": "kitchen-deep-cleaning",
    "Kitchen deep cleaning (empty kitchen)": "kitchen-deep-cleaning",
    "Kitchen deep cleaning (occupied kitchen)": "kitchen-deep-cleaning",
    "Kitchen + bathroom + balcony cleaning combo": "kitchen-deep-cleaning",
    "Partial / custom home cleaning": "full-home-deep-cleaning-1bhk",
    "Sofa cleaning": "sofa-carpet-shampooing",
    "Tap repair": "tap-shower-repair",
    "Flush tank repair": "toilet-flush-repair",
    "Pipe leakage repair": "pipe-leakage-drain-unclog",
    "Wash basin leakage repair": "pipe-leakage-drain-unclog",
    "Wash basin blockage removal": "pipe-leakage-drain-unclog",
    "Plumber consultation / visit": "pipe-leakage-drain-unclog",
    "Fan repair": "ceiling-exhaust-fan-service",
    "Fan installation": "ceiling-exhaust-fan-service",
    "Fan installation / replacement": "ceiling-exhaust-fan-service",
    "Fan replacement": "ceiling-exhaust-fan-service",
    "Switch replacement": "switch-socket-repair",
    "Socket replacement": "switch-socket-repair",
    "Tube light installation/replacement": "light-fixture-installation",
    "Electrician consultation / visit": "ceiling-exhaust-fan-service",
}

PLATFORM_TYPES = {"Urban Company", "NoBroker", "Justdial", "Sulekha"}
VALID_STATUSES = {
    "VERIFIED_PUBLIC_PRICE",
    "VERIFIED_QUOTE_ONLY",
    "VERIFIED_SERVICE_PRICE_UNAVAILABLE",
    "NOT_FOUND",
    "NEEDS_REVIEW",
}


def load_phase_b_records(path: str | Path = PHASE_B_JSON) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("Phase B artifact does not contain a records list.")
    return records


def validate_phase_b_records(records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for record in records:
        record_id = record.get("record_id")
        if not record_id or record_id in seen:
            errors.append(f"Duplicate or missing record_id: {record_id!r}")
        seen.add(record_id)
        if record.get("platform") not in PLATFORM_TYPES:
            errors.append(f"{record_id}: unsupported platform")
        if record.get("research_status") not in VALID_STATUSES:
            errors.append(f"{record_id}: unsupported research_status")
        if not record.get("source_url") or not record.get("date_researched"):
            errors.append(f"{record_id}: source_url and date_researched are required")
        if record.get("currency") != "INR":
            errors.append(f"{record_id}: currency must be INR")
        for field in ("price_amount", "price_min", "price_max"):
            value = record.get(field)
            if value is not None and (not isinstance(value, (int, float)) or value < 0):
                errors.append(f"{record_id}: invalid {field}")
        if record.get("pricing_type") == "range" and (
            record.get("price_min") is None or record.get("price_max") is None
        ):
            errors.append(f"{record_id}: range requires both bounds")
        if record.get("research_status") != "VERIFIED_PUBLIC_PRICE" and any(
            record.get(field) is not None for field in ("price_amount", "price_min", "price_max")
        ):
            errors.append(f"{record_id}: non-verified record contains a price")
    return errors


def _verification_status(research_status: str) -> str:
    if research_status == "VERIFIED_PUBLIC_PRICE" or research_status == "VERIFIED_QUOTE_ONLY":
        return VerificationStatus.VERIFIED.value
    if research_status == "VERIFIED_SERVICE_PRICE_UNAVAILABLE":
        return VerificationStatus.UNAVAILABLE.value
    return VerificationStatus.UNVERIFIED.value


def _price_type(value: str) -> str:
    return {
        "fixed": PriceType.FIXED.value,
        "starting_at": PriceType.STARTING_AT.value,
        "range": PriceType.RANGE.value,
        "per_unit": PriceType.PER_UNIT.value,
        "consultation_fee": PriceType.CONSULTATION_FEE.value,
        "quote_required": PriceType.QUOTE_REQUIRED.value,
        "fixed_default_option": PriceType.FIXED_DEFAULT_OPTION.value,
        "fixed_by_variant": PriceType.FIXED_BY_VARIANT.value,
        "not_published": PriceType.NOT_PUBLISHED.value,
    }[value]


def import_phase_b(
    db: Session,
    path: str | Path = PHASE_B_JSON,
    dry_run: bool = False,
    *,
    allow_confirmed_development_supabase: bool = False,
) -> dict[str, int]:
    if not is_safe_local_environment(
        db,
        allow_confirmed_development_supabase=allow_confirmed_development_supabase,
    ):
        raise RuntimeError(
            "Phase B import refused: database target is not approved. "
            "Development Supabase imports require explicit opt-in and process confirmation."
        )
    records = load_phase_b_records(path)
    errors = validate_phase_b_records(records)
    if errors:
        raise ValueError("Phase B validation failed: " + "; ".join(errors[:10]))

    services = {service.slug: service for service in db.query(Service).all()}
    stats = {"validated": len(records), "imported": 0, "updated": 0, "needs_review": 0, "prices": 0}
    for record in records:
        slug = SERVICE_NAME_TO_SLUG.get(record["canonical_service_name"])
        service = services.get(slug or "")
        if service is None:
            stats["needs_review"] += 1
            continue
        status = _verification_status(record["research_status"])
        researched_at = datetime.fromisoformat(record["date_researched"])
        title = record["original_service_name"]
        listing = (
            db.query(PlatformListing)
            .filter_by(
                platform=record["platform"],
                service_id=service.id,
                title=title,
            )
            .first()
        )
        description = "; ".join(
            part for part in (
                record.get("evidence_notes"),
                record.get("location_applicability"),
                record.get("access_limitations"),
            ) if part
        ) or None
        if listing is None:
            listing = PlatformListing(
                id=str(uuid4()),
                platform=record["platform"],
                service_id=service.id,
                title=title,
                description=description,
                city="Bengaluru",
                listing_url=record["source_url"],
                booking_url=record["source_url"] if record["platform"] in {"Urban Company", "NoBroker"} else None,
                verification_status=status,
                source=f"{record['platform']} Phase B research",
                last_checked_at=researched_at,
                is_active=True,
            )
            db.add(listing)
            db.flush()
            stats["imported"] += 1
        else:
            listing.description = description
            listing.listing_url = record["source_url"]
            listing.last_checked_at = researched_at
            listing.verification_status = status
            stats["updated"] += 1

        price = db.query(ServicePrice).filter_by(research_record_id=record["record_id"]).first()
        values = dict(
            service_id=service.id,
            platform_listing_id=listing.id,
            price_type=_price_type(record["pricing_type"]),
            amount=record.get("price_amount"),
            price_min=record.get("price_min"),
            price_max=record.get("price_max"),
            currency="INR",
            unit=record.get("unit"),
            conditions="; ".join(
                part for part in (
                    record.get("conditions"),
                    record.get("other_prices_on_same_page"),
                    record.get("displayed_price_text"),
                ) if part
            ) or None,
            inclusions=record.get("inclusions"),
            exclusions=record.get("exclusions"),
            source_url=record["source_url"],
            verification_status=status,
            last_verified_at=researched_at,
            research_record_id=record["record_id"],
            comparison_group=record.get("comparison_group"),
            comparability_label=record.get("comparability_label"),
            comparability_reason=record.get("comparability_reason"),
        )
        if price is None:
            db.add(ServicePrice(id=str(uuid4()), **values))
            stats["prices"] += 1
        else:
            for key, value in values.items():
                setattr(price, key, value)
            stats["prices"] += 1
        if record["research_status"] in {"NEEDS_REVIEW", "NOT_FOUND"}:
            stats["needs_review"] += 1

    if dry_run:
        db.rollback()
    else:
        db.commit()
    return stats
