from datetime import datetime
from uuid import uuid4

from app.models.nammaserve import (
    Provider,
    ProviderOffering,
    ProviderService,
    SourceType,
    VerificationStatus,
)
from app.schemas.nammaserve import NormalizedProviderResult, ServiceMatchLevel
from app.services.nammaserve.discovery.distance import haversine_distance_km


def format_price_display(
    price_type: str | None,
    amount: float | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    unit: str | None = None,
    currency_symbol: str = "₹",
) -> str:
    """Format price transparently according to strict Phase 3 & 4 semantic requirements."""
    if not price_type:
        if price_min is not None and price_max is not None:
            min_s = int(price_min) if float(price_min).is_integer() else price_min
            max_s = int(price_max) if float(price_max).is_integer() else price_max
            unit_s = f" {unit}" if unit else ""
            return f"{currency_symbol}{min_s} – {currency_symbol}{max_s}{unit_s}"
        if price_min is not None:
            min_s = int(price_min) if float(price_min).is_integer() else price_min
            unit_s = f" {unit}" if unit else ""
            return f"{currency_symbol}{min_s}{unit_s} onwards"
        return "Contact for price"

    pt = price_type.upper()
    unit_str = f" {unit}" if unit else ""

    if pt == "FIXED":
        val = amount if amount is not None else price_min
        if val is not None:
            val_s = int(val) if float(val).is_integer() else val
            return f"{currency_symbol}{val_s}{unit_str} (Fixed)"
        return "Fixed price"

    elif pt == "STARTING_AT":
        val = price_min if price_min is not None else amount
        if val is not None:
            val_s = int(val) if float(val).is_integer() else val
            return f"{currency_symbol}{val_s}{unit_str} onwards"
        return "Starting price available on inquiry"

    elif pt == "RANGE":
        if price_min is not None and price_max is not None:
            min_s = int(price_min) if float(price_min).is_integer() else price_min
            max_s = int(price_max) if float(price_max).is_integer() else price_max
            return f"{currency_symbol}{min_s} – {currency_symbol}{max_s}{unit_str}"
        elif price_min is not None:
            min_s = int(price_min) if float(price_min).is_integer() else price_min
            return f"{currency_symbol}{min_s}{unit_str} onwards"
        return "Price range available on inquiry"

    elif pt == "PER_UNIT":
        val = amount if amount is not None else price_min
        if val is not None:
            val_s = int(val) if float(val).is_integer() else val
            return f"{currency_symbol}{val_s}{unit_str}"
        return f"Per-unit pricing{unit_str}"

    elif pt == "HOURLY":
        val = amount if amount is not None else price_min
        if val is not None:
            val_s = int(val) if float(val).is_integer() else val
            return f"{currency_symbol}{val_s} / hr"
        return "Hourly rate available on inquiry"

    elif pt == "CONSULTATION_FEE":
        val = amount if amount is not None else price_min
        if val is not None:
            val_s = int(val) if float(val).is_integer() else val
            return f"{currency_symbol}{val_s} Inspection / Consultation Fee"
        return "Consultation fee applies"

    elif pt == "QUOTE_REQUIRED":
        return "Custom quote required"

    elif pt == "UNAVAILABLE":
        return "Service unavailable"

    return "Contact for price"


class ResultNormalizer:
    """Standardizes heterogeneous provider data into NormalizedProviderResult objects."""

    @staticmethod
    def from_db_models(
        provider: Provider,
        service: ProviderService | None = None,
        offering: ProviderOffering | None = None,
        user_lat: float | None = None,
        user_lng: float | None = None,
        service_match_level: ServiceMatchLevel = ServiceMatchLevel.UNCONFIRMED,
        service_match_confidence: float = 0.0,
        ranking_reasons: list[str] | None = None,
    ) -> NormalizedProviderResult:
        # Calculate distance if user coordinates provided
        distance_km = None
        if (
            user_lat is not None
            and user_lng is not None
            and provider.latitude is not None
            and provider.longitude is not None
        ):
            distance_km = haversine_distance_km(
                user_lat, user_lng, provider.latitude, provider.longitude
            )

        # Verification status preference: offering > service > provider
        if offering and offering.verification_status:
            try:
                v_status = VerificationStatus(offering.verification_status)
            except ValueError:
                v_status = VerificationStatus.UNVERIFIED
        elif service and service.verification_status:
            try:
                v_status = VerificationStatus(service.verification_status)
            except ValueError:
                v_status = VerificationStatus.UNVERIFIED
        elif provider and provider.verification_status:
            try:
                v_status = VerificationStatus(provider.verification_status)
            except ValueError:
                v_status = VerificationStatus.UNVERIFIED
        else:
            v_status = VerificationStatus.UNVERIFIED

        source = (
            offering.source if offering and offering.source
            else (service.source if service and service.source else provider.source)
        )
        source_type = (
            SourceType.LOCAL_DATABASE
        )
        source_url = (
            offering.source_url if offering and offering.source_url
            else (service.source_url if service and service.source_url else provider.source_url)
        )
        last_verified_at = (
            offering.last_verified_at if offering and offering.last_verified_at
            else (service.last_verified_at if service and service.last_verified_at else provider.last_verified_at)
        )

        # Matched service details
        if offering and offering.service:
            matched_slug = offering.service.slug
            matched_name = offering.service.name
        elif service and service.category:
            matched_slug = service.category.slug
            matched_name = service.category.name
        else:
            matched_slug = None
            matched_name = None

        # Price extraction: check offering prices first, then service
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

        if offering and offering.prices:
            first_p = offering.prices[0]
            amount = first_p.amount
            price_min = first_p.price_min if first_p.price_min is not None else (first_p.amount if first_p.price_type != "RANGE" else None)
            price_max = first_p.price_max
            price_unit = first_p.unit
            price_type = str(first_p.price_type) if first_p.price_type else None
            currency = first_p.currency or "INR"
            inclusions = first_p.inclusions
            exclusions = first_p.exclusions
            conditions = first_p.conditions
            evidence_notes = getattr(first_p, "evidence_notes", None) or getattr(first_p, "conditions", None)
            if first_p.verification_status:
                try:
                    v_status = VerificationStatus(first_p.verification_status)
                except ValueError:
                    pass
            if first_p.source_url:
                source_url = first_p.source_url
            if first_p.last_verified_at:
                last_verified_at = first_p.last_verified_at
            if price_type == "QUOTE_REQUIRED":
                is_price_available = False
                amount = None
                price_min = None
                price_max = None
            elif price_type == "UNAVAILABLE" or v_status == VerificationStatus.UNAVAILABLE:
                is_price_available = False
                amount = None
                price_min = None
                price_max = None
        elif service:
            price_min = service.price_min
            price_max = service.price_max
            price_unit = service.price_unit
            if price_min is None and price_max is None:
                is_price_available = False
        else:
            is_price_available = False

        formatted_price = format_price_display(
            price_type=price_type,
            amount=amount,
            price_min=price_min,
            price_max=price_max,
            unit=price_unit,
        )

        provider_id_str = str(provider.id) if provider.id is not None else "unknown"

        return NormalizedProviderResult(
            id=provider_id_str,
            name=provider.name or "Unknown Provider",
            phone=provider.phone,
            alternate_phone=provider.alternate_phone,
            contact_person=provider.contact_person,
            address=provider.address,
            area=provider.primary_area,
            city=provider.city or "Bengaluru",
            latitude=provider.latitude,
            longitude=provider.longitude,
            distance_km=distance_km,
            matched_service_slug=matched_slug,
            matched_service_name=matched_name,
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
            minimum_order=service.minimum_order if service else None,
            capacity=service.capacity if service else None,
            water_type=service.water_type if service else None,
            availability=service.availability if service else None,
            payment_methods=service.payment_methods if service else None,
            operating_hours=provider.operating_hours,
            is_emergency_service=bool(provider.is_emergency_service) if provider.is_emergency_service is not None else False,
            notes=service.notes if service else (offering.description if offering else None),
            service_match_level=service_match_level,
            service_match_confidence=service_match_confidence,
            sources=["Local Verified Database"],
            external_ids={"provider_id": provider_id_str},
            verification_status=v_status,
            source=source or "Local Verified Database",
            source_type=source_type,
            source_url=source_url,
            last_verified_at=last_verified_at,
            research_record_id=getattr(first_p, "research_record_id", None) if offering and offering.prices else None,
            comparison_group=getattr(first_p, "comparison_group", None) if offering and offering.prices else None,
            comparability_label=getattr(first_p, "comparability_label", None) if offering and offering.prices else None,
            comparability_reason=getattr(first_p, "comparability_reason", None) if offering and offering.prices else None,
            ranking_reasons=ranking_reasons or [],
        )

    @staticmethod
    def from_external_payload(
        name: str,
        phone: str,
        source_type: SourceType,
        source: str,
        address: str | None = None,
        area: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        distance_km: float | None = None,
        matched_service_slug: str | None = None,
        matched_service_name: str | None = None,
        operating_hours: str | None = None,
        source_url: str | None = None,
        service_match_level: ServiceMatchLevel = ServiceMatchLevel.UNCONFIRMED,
        service_match_confidence: float = 0.0,
        ranking_reasons: list[str] | None = None,
        sources: list[str] | None = None,
        external_ids: dict[str, str] | None = None,
        website: str | None = None,
        discovered_at: datetime | None = None,
        last_checked_at: datetime | None = None,
    ) -> NormalizedProviderResult:
        """Create a normalized unverified result from external public listings (e.g. Geoapify, OSM, Foursquare)."""
        all_sources = list(sources) if sources else [source]
        clean_name = str(name).strip() if name else "Unknown Provider"
        clean_phone = str(phone).strip() if phone is not None else ""
        return NormalizedProviderResult(
            id=str(uuid4()),
            name=clean_name,
            phone=clean_phone,
            address=address,
            area=area,
            city="Bengaluru",
            latitude=latitude,
            longitude=longitude,
            distance_km=distance_km,
            matched_service_slug=matched_service_slug,
            matched_service_name=matched_service_name,
            operating_hours=operating_hours,
            service_match_level=service_match_level,
            service_match_confidence=service_match_confidence,
            sources=all_sources,
            external_ids=external_ids or {},
            website=website,
            discovered_at=discovered_at,
            last_checked_at=last_checked_at,
            verification_status=VerificationStatus.UNVERIFIED,
            source=source,
            source_type=source_type,
            source_url=source_url,
            last_verified_at=None,
            ranking_reasons=ranking_reasons or [],
        )
