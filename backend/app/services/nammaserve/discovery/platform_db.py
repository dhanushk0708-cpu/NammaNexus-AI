import logging
from sqlalchemy.orm import Session, joinedload

from app.models.nammaserve import PlatformListing, Service, SourceType, VerificationStatus
from app.schemas.nammaserve import (
    ConnectorStatus,
    DiscoveryQuery,
    NormalizedProviderResult,
    ServiceMatchLevel,
)
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector
from app.services.nammaserve.discovery.normalizer import format_price_display

logger = logging.getLogger(__name__)


class PlatformListingDiscoveryConnector(BaseDiscoveryConnector):
    """Retrieves legitimate, verified platform listings stored in the local database.
    
    Covers Urban Company, NoBroker, Justdial, and Sulekha verified comparative benchmark listings
    and rate cards without unauthorized web scraping.
    """

    def __init__(self, db: Session):
        self.db = db
        self._last_error: str | None = None

    @property
    def name(self) -> str:
        return "Verified Platform Directory"

    @property
    def source_type(self) -> SourceType:
        return SourceType.LOCAL_DATABASE

    @property
    def is_available(self) -> bool:
        return self._last_error is None

    def get_status(self, results_count: int = 0) -> ConnectorStatus:
        if self._last_error:
            msg = f"Database query failed: {self._last_error}"
        else:
            msg = "Database-backed verified platform listings for Urban Company, NoBroker, Justdial, and Sulekha."
        return ConnectorStatus(
            connector_name=self.name,
            source_type=self.source_type,
            is_available=self.is_available,
            status_message=msg,
            results_count=results_count,
        )

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        """Query platform_listings with linked service prices."""
        self._last_error = None
        try:
            q = (
                self.db.query(PlatformListing)
                .filter(PlatformListing.is_active.is_(True))
                .options(
                    joinedload(PlatformListing.service),
                    joinedload(PlatformListing.prices),
                )
            )

            # Match by resolved service or category
            service_slug = query.resolved_service_slug or query.service
            if service_slug:
                s_term = service_slug.strip().lower()
                q = q.join(PlatformListing.service).filter(
                    (Service.slug == s_term)
                    | (Service.slug.ilike(f"%{s_term}%"))
                    | (Service.name.ilike(f"%{s_term}%"))
                )

            # Locality filter if provided
            if query.area:
                area_term = f"%{query.area.strip().lower()}%"
                q = q.filter(
                    (PlatformListing.locality.ilike(area_term))
                    | (PlatformListing.city.ilike(area_term))
                    | (PlatformListing.locality.is_(None))  # City-wide listing
                )

            if query.verified_only:
                q = q.filter(
                    PlatformListing.verification_status.in_([
                        VerificationStatus.VERIFIED.value,
                        VerificationStatus.PARTIALLY_VERIFIED.value,
                    ])
                )

            listings = q.all()
            results: list[NormalizedProviderResult] = []

            for pl in listings:
                amount = None
                price_min = None
                price_max = None
                price_unit = None
                price_type = None
                currency = "INR"
                inclusions = None
                exclusions = None
                conditions = None
                evidence_notes = None
                is_price_available = True
                price_v_status = None

                if pl.prices:
                    first_price = pl.prices[0]
                    amount = first_price.amount
                    price_min = first_price.price_min if first_price.price_min is not None else (first_price.amount if first_price.price_type != "RANGE" else None)
                    price_max = first_price.price_max
                    price_unit = first_price.unit
                    price_type = str(first_price.price_type) if first_price.price_type else None
                    currency = first_price.currency or "INR"
                    inclusions = first_price.inclusions
                    exclusions = first_price.exclusions
                    conditions = first_price.conditions
                    evidence_notes = getattr(first_price, "evidence_notes", None) or getattr(first_price, "conditions", None)
                    if first_price.verification_status:
                        try:
                            price_v_status = VerificationStatus(first_price.verification_status)
                        except ValueError:
                            pass
                    if price_type == "QUOTE_REQUIRED":
                        is_price_available = False
                        amount = None
                        price_min = None
                        price_max = None
                    elif price_type == "UNAVAILABLE" or price_v_status == VerificationStatus.UNAVAILABLE:
                        is_price_available = False
                        amount = None
                        price_min = None
                        price_max = None
                else:
                    is_price_available = False

                # Platform mapping to SourceType
                try:
                    src_type = SourceType(pl.platform)
                except ValueError:
                    src_type = SourceType.LOCAL_DATABASE

                # Verification Status
                if price_v_status:
                    v_status = price_v_status
                elif pl.verification_status == VerificationStatus.VERIFIED.value:
                    v_status = VerificationStatus.VERIFIED
                elif pl.verification_status == VerificationStatus.PARTIALLY_VERIFIED.value:
                    v_status = VerificationStatus.PARTIALLY_VERIFIED
                else:
                    v_status = VerificationStatus.UNVERIFIED

                formatted_price = format_price_display(
                    price_type=price_type,
                    amount=amount,
                    price_min=price_min,
                    price_max=price_max,
                    unit=price_unit,
                )

                ranking_note = f"Verified platform rate card for {pl.platform}"
                if v_status == VerificationStatus.PARTIALLY_VERIFIED:
                    ranking_note = f"Indicative directory estimate for {pl.platform}"

                item = NormalizedProviderResult(
                    id=pl.id,
                    name=pl.title,
                    phone="Contact via Platform",
                    address=pl.description,
                    area=pl.locality or query.area or "Bengaluru",
                    city=pl.city,
                    matched_service_slug=pl.service.slug if pl.service else query.service,
                    matched_service_name=pl.service.name if pl.service else None,
                    amount=amount,
                    price_min=price_min,
                    price_max=price_max,
                    price_unit=price_unit,
                    price_type=price_type,
                    currency=currency,
                    formatted_price=formatted_price,
                    is_price_available=is_price_available,
                    inclusions=inclusions,
                    exclusions=exclusions,
                    conditions=conditions,
                    evidence_notes=evidence_notes,
                    service_match_level=ServiceMatchLevel.CONFIRMED,
                    service_match_confidence=1.0,
                    sources=[f"{pl.platform} Verified Listing"],
                    external_ids={"platform_listing_id": pl.id},
                    verification_status=v_status,
                    source=f"{pl.platform} Verified Listing",
                    source_type=src_type,
                    source_url=(
                        first_price.source_url
                        if pl.prices and first_price.source_url
                        else pl.booking_url or pl.listing_url
                    ),
                    last_verified_at=(
                        first_price.last_verified_at
                        if pl.prices and first_price.last_verified_at
                        else None
                    ),
                    last_checked_at=pl.last_checked_at,
                    research_record_id=getattr(first_price, "research_record_id", None) if pl.prices else None,
                    comparison_group=getattr(first_price, "comparison_group", None) if pl.prices else None,
                    comparability_label=getattr(first_price, "comparability_label", None) if pl.prices else None,
                    comparability_reason=getattr(first_price, "comparability_reason", None) if pl.prices else None,
                    ranking_reasons=[ranking_note],
                )
                results.append(item)

            return results
        except Exception as exc:
            # Sanitize exception message to avoid credential leaks
            safe_msg = type(exc).__name__
            self._last_error = safe_msg
            logger.error("Error querying PlatformListingDirectory: %s", safe_msg)
            return []
