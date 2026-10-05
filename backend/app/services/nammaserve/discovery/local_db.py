from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.nammaserve import (
    Provider,
    ProviderService,
    ProviderServiceArea,
    ServiceCategory,
    SourceType,
    VerificationStatus,
)
from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector
from app.services.nammaserve.discovery.distance import haversine_distance_km
from app.services.nammaserve.discovery.normalizer import ResultNormalizer


class LocalDBDiscoveryConnector(BaseDiscoveryConnector):
    """Discovery connector querying the local verified PostgreSQL database."""

    def __init__(self, db: Session):
        self.db = db

    @property
    def name(self) -> str:
        return "Local Verified Database"

    @property
    def source_type(self) -> SourceType:
        return SourceType.LOCAL_DATABASE

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        """Perform database search with spatial and category filtering."""
        db_query = (
            self.db.query(Provider)
            .filter(Provider.is_active.is_(True))
            .options(
                joinedload(Provider.services).joinedload(ProviderService.category),
                joinedload(Provider.service_areas),
            )
        )

        # 1. Emergency service filter
        if query.emergency_only:
            db_query = db_query.filter(Provider.is_emergency_service.is_(True))

        # 2. Verification filter
        if query.verified_only:
            db_query = db_query.filter(
                Provider.verification_status == VerificationStatus.VERIFIED.value
            )

        # 3. Locality text filter
        if query.area:
            area_term = f"%{query.area.strip().lower()}%"
            db_query = db_query.outerjoin(Provider.service_areas).filter(
                or_(
                    Provider.primary_area.ilike(area_term),
                    Provider.address.ilike(area_term),
                    ProviderServiceArea.area_name.ilike(area_term),
                )
            )

        providers = db_query.all()

        results: list[NormalizedProviderResult] = []

        # Service term normalization
        service_term = query.service.strip().lower() if query.service else None

        for provider in providers:
            # Check spatial radius if citizen lat/lng provided
            dist_km = None
            if query.lat is not None and query.lng is not None:
                if provider.latitude is not None and provider.longitude is not None:
                    dist_km = haversine_distance_km(
                        query.lat, query.lng, provider.latitude, provider.longitude
                    )
                    # Filter out if outside search radius (allowing either query radius or provider service radius)
                    max_allowed_dist = max(query.radius_km, provider.service_radius_km)
                    if dist_km > max_allowed_dist:
                        continue
                else:
                    # Provider has no coordinates; keep if area matches, or skip if strict coordinate search
                    if query.area is None:
                        continue

            # Match services offered by this provider
            matched_services = []
            for svc in provider.services:
                if not svc.is_active:
                    continue
                if query.verified_only and svc.verification_status != VerificationStatus.VERIFIED.value:
                    continue

                if service_term:
                    cat_slug = svc.category.slug.lower() if svc.category else ""
                    cat_name = svc.category.name.lower() if svc.category else ""
                    # Match by exact slug or substring in category name/slug
                    if (
                        service_term == cat_slug
                        or service_term in cat_slug
                        or service_term in cat_name
                        or service_term.replace("-", " ") in cat_name
                    ):
                        matched_services.append(svc)
                else:
                    matched_services.append(svc)

            if service_term and not matched_services:
                # Provider does not offer requested service
                continue

            if matched_services:
                for svc in matched_services:
                    normalized = ResultNormalizer.from_db_models(
                        provider=provider,
                        service=svc,
                        user_lat=query.lat,
                        user_lng=query.lng,
                    )
                    results.append(normalized)
            else:
                # No specific service requested or found; return provider-level summary
                normalized = ResultNormalizer.from_db_models(
                    provider=provider,
                    service=None,
                    user_lat=query.lat,
                    user_lng=query.lng,
                )
                results.append(normalized)

        return results
