"""Idempotent seed and import script for NammaServe Phase 3 verified pricing data.

Loads verified real-market pricing research from data/nammaserve/demo_pricing.json
and populates or updates:
- PlatformListing & ServicePrice (for marketplace & directory platforms: Urban Company, NoBroker, Justdial, Sulekha)
- Provider, ProviderOffering & ServicePrice (for independent providers: CoolCare, Nakoda, Fixizzy, etc.)

STRICT SAFETY CONTROLS:
- Requires explicit local execution confirmation (--confirm-local).
- Refuses execution if DATABASE_URL indicates Supabase or a remote production host.
- Skips UNAVAILABLE research entries (recorded in research artifacts, never fabricated as price rows).
- Preserves stronger verification status (will not downgrade VERIFIED to PARTIALLY_VERIFIED).
- Transaction rollback on any unhandled failure.
- Never prints database credentials or secret environment variables.
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.nammaserve import (
    PlatformListing,
    PriceType,
    Provider,
    ProviderOffering,
    ProviderService,
    Service,
    ServiceCategory,
    ServicePrice,
    SourceType,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

# Verification status priority (higher number = stronger verification)
VERIFICATION_PRIORITY = {
    VerificationStatus.UNVERIFIED.value: 1,
    VerificationStatus.PARTIALLY_VERIFIED.value: 2,
    VerificationStatus.VERIFIED.value: 3,
}


# Approved positive allowlist for strictly local or development database hosts.
# Any database URL pointing to an unrecognized host is rejected fail-closed.
APPROVED_LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0:0:0:0:0:0:0:1",
    "0.0.0.0",
    "host.docker.internal",
}

REJECTED_HOST_DOMAINS = (
    "supabase.co",
    "pooler.supabase",
    "neon.tech",
    "rds.amazonaws.com",
    "railway.app",
    "rlwy.net",
    "render.com",
    "fly.dev",
    "cockroachlabs.cloud",
    "azure.com",
    "aivencloud.com",
)


def is_safe_local_environment(
    db_target: str | Session | None = None,
    *,
    allow_confirmed_development_supabase: bool = False,
) -> bool:
    """Ensure the target database is strictly local or an isolated test database.

    Uses a fail-closed positive allowlist strategy:
    - SQLite connections (file or in-memory) are permitted.
    - Networked databases are ONLY permitted if their scheme is postgresql
      and their hostname is explicitly in APPROVED_LOCAL_HOSTS.
    - All remote hosts (Supabase, Neon, AWS RDS, Railway, Render, etc.) and
      unrecognized hostnames are rejected by default.
    - Supabase is permitted only with explicit opt-in and the
      NAMMASERVE_ALLOW_DEVELOPMENT_SUPABASE_IMPORT=true process flag.
    - Supports str URL, SQLAlchemy Session, or defaults to settings.database_url.
    - Never prints or logs database credentials or connection strings.
    """
    if db_target is None:
        # Pydantic Settings exposes settings.database_url (lowercase)
        raw_target = getattr(settings, "database_url", None)
        if not isinstance(raw_target, str) or not raw_target.strip():
            # Check uppercase fallback if database_url wasn't a non-empty string
            alt_target = getattr(settings, "DATABASE_URL", None)
            if isinstance(alt_target, str) and alt_target.strip():
                raw_target = alt_target
            else:
                raw_target = ""
        target_url = raw_target
    elif hasattr(db_target, "get_bind"):
        try:
            target_url = str(db_target.get_bind().url)
        except Exception:
            return False
    elif isinstance(db_target, str):
        target_url = db_target
    else:
        return False

    if not isinstance(target_url, str):
        return False

    target_url = target_url.strip()
    if not target_url:
        return False

    # SQLite is inherently local/in-memory
    if target_url.lower().startswith("sqlite"):
        return True

    try:
        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        scheme = (parsed.scheme or "").lower()
        if not (scheme.startswith("postgres") or scheme.startswith("postgresql")):
            return False

        hostname = (parsed.hostname or "").lower().strip("[]")
        if not hostname:
            return False

        if "supabase.co" in hostname or "pooler.supabase" in hostname:
            return (
                allow_confirmed_development_supabase
                and os.environ.get("NAMMASERVE_ALLOW_DEVELOPMENT_SUPABASE_IMPORT", "").lower()
                == "true"
            )

        # Explicit defense-in-depth against cloud host providers
        for rejected in REJECTED_HOST_DOMAINS:
            if rejected in hostname:
                return False

        return hostname in APPROVED_LOCAL_HOSTS
    except Exception:
        return False



def should_update_verification(current_status: str, incoming_status: str) -> bool:
    """Only update verification status if incoming evidence is at least as strong as current."""
    curr_rank = VERIFICATION_PRIORITY.get(current_status, 1)
    new_rank = VERIFICATION_PRIORITY.get(incoming_status, 1)
    return new_rank >= curr_rank


def validate_pricing_record(record: dict) -> list[str]:
    """Validate research pricing record invariants. Returns list of error messages if invalid."""
    errors = []
    p_type = record.get("pricing_type")
    v_status = record.get("verification_status")

    if v_status == "UNAVAILABLE":
        # Unavailable records are valid research entries to be skipped from price table insertion
        return errors

    valid_types = {t.value for t in PriceType}
    if p_type not in valid_types:
        errors.append(f"Invalid pricing_type '{p_type}'. Must be one of {valid_types}")

    amount = record.get("amount")
    price_min = record.get("price_min")
    price_max = record.get("price_max")

    if amount is not None and amount < 0:
        errors.append(f"Negative amount {amount} not permitted")
    if price_min is not None and price_min < 0:
        errors.append(f"Negative price_min {price_min} not permitted")
    if price_max is not None and price_max < 0:
        errors.append(f"Negative price_max {price_max} not permitted")

    if p_type == PriceType.RANGE.value:
        if price_min is None or price_max is None:
            errors.append("RANGE pricing requires both price_min and price_max")
        elif price_min > price_max:
            errors.append(f"RANGE price_min ({price_min}) cannot exceed price_max ({price_max})")

    if p_type == PriceType.PER_UNIT.value:
        if not record.get("pricing_unit"):
            errors.append("PER_UNIT pricing requires a meaningful pricing_unit")

    if p_type == PriceType.QUOTE_REQUIRED.value:
        # QUOTE_REQUIRED records may optionally specify price_min/price_max to represent
        # market surveyed contractor ranges, but cannot have a fixed guaranteed amount.
        if amount is not None:
            errors.append("QUOTE_REQUIRED records cannot have a fixed amount")

    if not record.get("source_url"):
        errors.append("Missing source_url for price record")

    if record.get("currency") != "INR":
        errors.append(f"Invalid currency '{record.get('currency')}'. Only 'INR' is supported.")

    return errors


def seed_demo_pricing(
    db: Session,
    json_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Idempotently seed verified research pricing data into the database."""
    # Enforce database safety check before any operations occur
    if not is_safe_local_environment(db):
        raise RuntimeError(
            "Database safety check failed: target database is not an approved local environment. "
            "Execution refused to protect remote/production environments."
        )
    if json_path is None:
        # Default path relative to project root
        base_dir = Path(__file__).resolve().parents[4]
        json_path = base_dir / "data" / "nammaserve" / "demo_pricing.json"

    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Research pricing JSON not found at {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    stats = {
        "inserted_listings": 0,
        "updated_listings": 0,
        "inserted_providers": 0,
        "updated_providers": 0,
        "inserted_offerings": 0,
        "updated_offerings": 0,
        "inserted_prices": 0,
        "updated_prices": 0,
        "skipped_unavailable": 0,
        "rejected": 0,
        "total_processed": len(records),
    }

    # Pre-cache canonical services
    services_by_slug = {s.slug: s for s in db.query(Service).all()}
    categories_by_slug = {c.slug: c for c in db.query(ServiceCategory).all()}

    for record in records:
        slug = record.get("canonical_service_slug")
        v_status = record.get("verification_status")

        # 1. Skip unavailable research records
        if v_status == "UNAVAILABLE":
            stats["skipped_unavailable"] += 1
            logger.info("Skipping UNAVAILABLE record for service '%s' on %s", slug, record.get("platform_or_provider_name"))
            continue

        # 2. Validate record invariants
        val_errors = validate_pricing_record(record)
        if val_errors:
            logger.warning("Rejected record for '%s': %s", slug, "; ".join(val_errors))
            stats["rejected"] += 1
            continue

        # 3. Resolve canonical service
        service = services_by_slug.get(slug)
        if not service:
            logger.warning("Service slug '%s' not found in database catalogue. Skipping.", slug)
            stats["rejected"] += 1
            continue

        p_name = record["platform_or_provider_name"]
        p_type = record.get("provider_type")
        source_url = record.get("source_url")
        pricing_type = record.get("pricing_type")
        amount = record.get("amount")
        price_min = record.get("price_min")
        price_max = record.get("price_max")
        pricing_unit = record.get("pricing_unit") or service.unit
        currency = record.get("currency", "INR")
        inclusions_list = record.get("inclusions") or []
        exclusions_list = record.get("exclusions") or []
        conditions_str = record.get("additional_charges")
        inclusions_str = "; ".join(inclusions_list) if isinstance(inclusions_list, list) else str(inclusions_list or "")
        exclusions_str = "; ".join(exclusions_list) if isinstance(exclusions_list, list) else str(exclusions_list or "")
        date_checked_str = record.get("date_checked")
        last_checked = datetime.fromisoformat(date_checked_str) if date_checked_str else datetime.utcnow()

        # Format inclusions/exclusions cleanly (None if empty)
        inclusions_clean = inclusions_str if inclusions_str.strip() else None
        exclusions_clean = exclusions_str if exclusions_str.strip() else None

        # Route by provider_type: marketplace/directory vs independent
        if p_type in ("marketplace", "directory"):
            # Model as PlatformListing + ServicePrice
            listing = (
                db.query(PlatformListing)
                .filter(
                    PlatformListing.platform == p_name,
                    PlatformListing.service_id == service.id,
                )
                .first()
            )

            if listing is None:
                listing = PlatformListing(
                    id=str(uuid4()),
                    platform=p_name,
                    service_id=service.id,
                    title=record.get("advertised_service_name") or service.name,
                    description=record.get("evidence_notes"),
                    locality=record.get("locality"),
                    city="Bengaluru",
                    listing_url=source_url,
                    booking_url=source_url if p_type == "marketplace" else None,
                    verification_status=v_status,
                    source=f"{p_name} Public Rate Card",
                    last_checked_at=last_checked,
                    is_active=True,
                )
                db.add(listing)
                db.flush()
                stats["inserted_listings"] += 1
            else:
                if should_update_verification(listing.verification_status, v_status):
                    listing.verification_status = v_status
                listing.title = record.get("advertised_service_name") or listing.title
                listing.listing_url = source_url or listing.listing_url
                listing.last_checked_at = last_checked
                listing.is_active = True
                stats["updated_listings"] += 1

            # Match or create ServicePrice linked to PlatformListing
            price_row = (
                db.query(ServicePrice)
                .filter(
                    ServicePrice.service_id == service.id,
                    ServicePrice.platform_listing_id == listing.id,
                )
                .first()
            )

            if price_row is None:
                price_row = ServicePrice(
                    id=str(uuid4()),
                    service_id=service.id,
                    platform_listing_id=listing.id,
                    provider_offering_id=None,
                    price_type=pricing_type,
                    amount=amount,
                    price_min=price_min,
                    price_max=price_max,
                    currency=currency,
                    unit=pricing_unit,
                    conditions=conditions_str,
                    inclusions=inclusions_clean,
                    exclusions=exclusions_clean,
                    source_url=source_url,
                    verification_status=v_status,
                    last_verified_at=last_checked,
                )
                db.add(price_row)
                stats["inserted_prices"] += 1
            else:
                if should_update_verification(price_row.verification_status, v_status):
                    price_row.verification_status = v_status
                    price_row.price_type = pricing_type
                    price_row.amount = amount
                    price_row.price_min = price_min
                    price_row.price_max = price_max
                    price_row.unit = pricing_unit
                    price_row.conditions = conditions_str
                    price_row.inclusions = inclusions_clean
                    price_row.exclusions = exclusions_clean
                    price_row.source_url = source_url
                    price_row.last_verified_at = last_checked
                stats["updated_prices"] += 1

        else:
            # Model as Independent Provider + ProviderOffering + ServicePrice
            provider = (
                db.query(Provider)
                .filter(Provider.name == p_name)
                .first()
            )

            if provider is None:
                cat_slug = record.get("category_slug")
                cat_obj = categories_by_slug.get(cat_slug) or service.category
                provider = Provider(
                    id=str(uuid4()),
                    name=p_name,
                    phone=None,
                    address=f"{record.get('locality') or 'Bengaluru'}, Karnataka",
                    primary_area=record.get("locality") or "Bengaluru",
                    city="Bengaluru",
                    service_radius_km=15.0,
                    source_type=SourceType.INDEPENDENT_PROVIDER.value,
                    source_url=source_url,
                    verification_status=v_status,
                    last_verified_at=last_checked,
                    is_active=True,
                )
                db.add(provider)
                db.flush()
                stats["inserted_providers"] += 1

                # Link provider to category via ProviderService
                if cat_obj:
                    ps = ProviderService(
                        id=str(uuid4()),
                        provider_id=provider.id,
                        category_id=cat_obj.id,
                        is_active=True,
                        verification_status=v_status,
                        source=f"{p_name} Verified Profile",
                        source_url=source_url,
                        last_verified_at=last_checked,
                    )
                    db.add(ps)
            else:
                if should_update_verification(provider.verification_status, v_status):
                    provider.verification_status = v_status
                    provider.source_url = source_url or provider.source_url
                    provider.last_verified_at = last_checked
                stats["updated_providers"] += 1

            # Match or create ProviderOffering
            offering = (
                db.query(ProviderOffering)
                .filter(
                    ProviderOffering.provider_id == provider.id,
                    ProviderOffering.service_id == service.id,
                )
                .first()
            )

            if offering is None:
                offering = ProviderOffering(
                    id=str(uuid4()),
                    provider_id=provider.id,
                    service_id=service.id,
                    custom_name=record.get("advertised_service_name"),
                    description=record.get("evidence_notes"),
                    is_available=True,
                    is_active=True,
                    verification_status=v_status,
                    source="Independent Provider Rate Card",
                    source_url=source_url,
                    last_verified_at=last_checked,
                )
                db.add(offering)
                db.flush()
                stats["inserted_offerings"] += 1
            else:
                if should_update_verification(offering.verification_status, v_status):
                    offering.verification_status = v_status
                    offering.custom_name = record.get("advertised_service_name") or offering.custom_name
                    offering.source_url = source_url or offering.source_url
                    offering.last_verified_at = last_checked
                stats["updated_offerings"] += 1

            # Match or create ServicePrice linked to ProviderOffering
            price_row = (
                db.query(ServicePrice)
                .filter(
                    ServicePrice.service_id == service.id,
                    ServicePrice.provider_offering_id == offering.id,
                )
                .first()
            )

            if price_row is None:
                price_row = ServicePrice(
                    id=str(uuid4()),
                    service_id=service.id,
                    platform_listing_id=None,
                    provider_offering_id=offering.id,
                    price_type=pricing_type,
                    amount=amount,
                    price_min=price_min,
                    price_max=price_max,
                    currency=currency,
                    unit=pricing_unit,
                    conditions=conditions_str,
                    inclusions=inclusions_clean,
                    exclusions=exclusions_clean,
                    source_url=source_url,
                    verification_status=v_status,
                    last_verified_at=last_checked,
                )
                db.add(price_row)
                stats["inserted_prices"] += 1
            else:
                if should_update_verification(price_row.verification_status, v_status):
                    price_row.verification_status = v_status
                    price_row.price_type = pricing_type
                    price_row.amount = amount
                    price_row.price_min = price_min
                    price_row.price_max = price_max
                    price_row.unit = pricing_unit
                    price_row.conditions = conditions_str
                    price_row.inclusions = inclusions_clean
                    price_row.exclusions = exclusions_clean
                    price_row.source_url = source_url
                    price_row.last_verified_at = last_checked
                stats["updated_prices"] += 1

    if not dry_run:
        db.commit()
    else:
        db.rollback()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="NammaServe Phase 3: Verified Pricing Seed & Import"
    )
    parser.add_argument(
        "--confirm-local",
        action="store_true",
        help="Explicit confirmation that this is being run on a local development database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and simulate seed without committing changes to database.",
    )
    parser.add_argument(
        "--json-file",
        type=str,
        default=None,
        help="Custom path to pricing JSON file (defaults to data/nammaserve/demo_pricing.json).",
    )
    args = parser.parse_args()

    # Safety check 1: require --confirm-local unless dry-run
    if not args.confirm_local and not args.dry_run:
        print(
            "ERROR: Safety check failed. You must provide '--confirm-local' to execute the seed.\n"
            "This ensures seed operations are never inadvertently run against production.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Safety check 2: verify safe local environment
    if not is_safe_local_environment():
        print(
            "ERROR: DATABASE_URL appears to target a remote or Supabase host.\n"
            "By project safety boundaries, Phase 3 seed cannot run against remote databases.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Starting NammaServe Phase 3 pricing import (dry_run={args.dry_run})...")
    db = SessionLocal()
    try:
        stats = seed_demo_pricing(db, json_path=args.json_file, dry_run=args.dry_run)
        print("\n--- Phase 3 Pricing Import Summary ---")
        print(f"Total Records in File:   {stats['total_processed']}")
        print(f"Skipped Unavailable:    {stats['skipped_unavailable']}")
        print(f"Rejected (Validation):   {stats['rejected']}")
        print(f"Listings Inserted:       {stats['inserted_listings']}")
        print(f"Listings Updated:        {stats['updated_listings']}")
        print(f"Providers Inserted:      {stats['inserted_providers']}")
        print(f"Providers Updated:       {stats['updated_providers']}")
        print(f"Offerings Inserted:      {stats['inserted_offerings']}")
        print(f"Offerings Updated:       {stats['updated_offerings']}")
        print(f"Prices Inserted:         {stats['inserted_prices']}")
        print(f"Prices Updated:          {stats['updated_prices']}")
        print("--------------------------------------")
        print("Import completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"ERROR: Import failed with exception: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
