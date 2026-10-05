from datetime import datetime
from uuid import uuid4

from app.models.nammaserve import Provider, ProviderService, SourceType, VerificationStatus
from app.schemas.nammaserve import NormalizedProviderResult
from app.services.nammaserve.discovery.distance import haversine_distance_km


class ResultNormalizer:
    """Standardizes heterogeneous provider data into NormalizedProviderResult objects."""

    @staticmethod
    def from_db_models(
        provider: Provider,
        service: ProviderService | None = None,
        user_lat: float | None = None,
        user_lng: float | None = None,
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

        # Verification status preference: use service verification if present, else provider verification
        v_status = (
            VerificationStatus(service.verification_status)
            if service and service.verification_status
            else VerificationStatus(provider.verification_status)
        )
        source = (service.source if service and service.source else provider.source)
        source_type = (
            SourceType(service.source_type)
            if service and service.source_type
            else SourceType(provider.source_type)
        )
        source_url = (service.source_url if service and service.source_url else provider.source_url)
        last_verified_at = (
            service.last_verified_at if service and service.last_verified_at else provider.last_verified_at
        )

        return NormalizedProviderResult(
            id=provider.id,
            name=provider.name,
            phone=provider.phone,
            alternate_phone=provider.alternate_phone,
            contact_person=provider.contact_person,
            address=provider.address,
            area=provider.primary_area,
            city=provider.city,
            latitude=provider.latitude,
            longitude=provider.longitude,
            distance_km=distance_km,
            matched_service_slug=service.category.slug if service and service.category else None,
            matched_service_name=service.category.name if service and service.category else None,
            price_min=service.price_min if service else None,
            price_max=service.price_max if service else None,
            price_unit=service.price_unit if service else None,
            minimum_order=service.minimum_order if service else None,
            capacity=service.capacity if service else None,
            water_type=service.water_type if service else None,
            availability=service.availability if service else None,
            payment_methods=service.payment_methods if service else None,
            operating_hours=provider.operating_hours,
            is_emergency_service=provider.is_emergency_service,
            notes=service.notes if service else None,
            verification_status=v_status,
            source=source,
            source_type=source_type,
            source_url=source_url,
            last_verified_at=last_verified_at,
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
    ) -> NormalizedProviderResult:
        """Create a normalized unverified result from external public listings (e.g. Google Places)."""
        return NormalizedProviderResult(
            id=str(uuid4()),
            name=name.strip(),
            phone=phone.strip(),
            address=address,
            area=area,
            city="Bengaluru",
            latitude=latitude,
            longitude=longitude,
            distance_km=distance_km,
            matched_service_slug=matched_service_slug,
            matched_service_name=matched_service_name,
            operating_hours=operating_hours,
            verification_status=VerificationStatus.UNVERIFIED,
            source=source,
            source_type=source_type,
            source_url=source_url,
            last_verified_at=None,
        )
