from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.nammaserve import (
    Provider,
    ProviderOffering,
    ProviderService,
    ProviderServiceArea,
    Service,
    ServiceCategory,
    SourceType,
    VerificationStatus,
)
from app.schemas.nammaserve import ConnectorStatus, DiscoveryQuery, NormalizedProviderResult, ServiceMatchLevel
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector
from app.services.nammaserve.discovery.distance import haversine_distance_km
from app.services.nammaserve.discovery.normalizer import ResultNormalizer


class LocalDBDiscoveryConnector(BaseDiscoveryConnector):
    """Discovery connector querying the local verified PostgreSQL database."""

    def __init__(self, db: Session):
        self.db = db
        self._last_error: str | None = None

    @property
    def name(self) -> str:
        return "Local Verified Database"

    @property
    def source_type(self) -> SourceType:
        return SourceType.LOCAL_DATABASE

    @property
    def is_available(self) -> bool:
        return self._last_error is None

    def get_status(self, results_count: int = 0) -> ConnectorStatus:
        msg = f"Database query failed: {self._last_error}" if self._last_error else "Local verified provider database."
        return ConnectorStatus(
            connector_name=self.name,
            source_type=self.source_type,
            is_available=self.is_available,
            status_message=msg,
            results_count=results_count,
        )

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        """Perform database search with catalogue awareness, spatial and category filtering."""
        self._last_error = None
        try:
            db_query = (
                self.db.query(Provider)
                .filter(Provider.is_active.is_(True))
                .options(
                    joinedload(Provider.offerings).joinedload(ProviderOffering.service),
                    joinedload(Provider.offerings).joinedload(ProviderOffering.prices),
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

            target_service_slug = (query.resolved_service_slug or "").strip().lower()
            target_category_slug = (query.resolved_category_slug or "").strip().lower()
            raw_service_term = (query.service or "").strip().lower()

            for provider in providers:
                # Check spatial radius if citizen lat/lng provided
                dist_km = None
                if query.lat is not None and query.lng is not None:
                    if provider.latitude is not None and provider.longitude is not None:
                        dist_km = haversine_distance_km(
                            query.lat, query.lng, provider.latitude, provider.longitude
                        )
                        max_allowed_dist = max(query.radius_km, provider.service_radius_km)
                        if dist_km > max_allowed_dist:
                            continue
                    else:
                        if query.area is None:
                            continue

                matched_offering = None
                matched_service = None

                # 1. Check exact individual service offerings first (CONFIRMED match)
                if target_service_slug:
                    for off in getattr(provider, "offerings", []):
                        if not off.is_active:
                            continue
                        if query.verified_only and off.verification_status != VerificationStatus.VERIFIED.value:
                            continue
                        if off.service and off.service.slug.lower() == target_service_slug:
                            matched_offering = off
                            break

                # 2. Check category services (PROBABLE or fallback match)
                for svc in getattr(provider, "services", []):
                    if not svc.is_active:
                        continue
                    if query.verified_only and svc.verification_status != VerificationStatus.VERIFIED.value:
                        continue

                    cat_slug = svc.category.slug.lower() if svc.category else ""
                    cat_name = svc.category.name.lower() if svc.category else ""

                    if target_category_slug and cat_slug == target_category_slug:
                        matched_service = svc
                        break
                    elif raw_service_term and (
                        raw_service_term == cat_slug
                        or raw_service_term in cat_slug
                        or raw_service_term in cat_name
                        or raw_service_term.replace("-", " ") in cat_name
                    ):
                        matched_service = svc
                        break

                # If user queried for a specific service or category, enforce matching
                if (target_service_slug or target_category_slug or raw_service_term) and not (
                    matched_offering or matched_service
                ):
                    continue

                # Construct normalized result with appropriate match confidence and level
                if matched_offering:
                    normalized = ResultNormalizer.from_db_models(
                        provider=provider,
                        service=None,
                        offering=matched_offering,
                        user_lat=query.lat,
                        user_lng=query.lng,
                        service_match_level=ServiceMatchLevel.CONFIRMED,
                        service_match_confidence=1.0,
                        ranking_reasons=[f"Verified provider offering for {matched_offering.service.name}"],
                    )
                    results.append(normalized)
                elif matched_service:
                    # Matched at category level: PROBABLE if user asked for a specific service, CONFIRMED if general category
                    is_prob = bool(target_service_slug)
                    lvl = ServiceMatchLevel.PROBABLE if is_prob else ServiceMatchLevel.CONFIRMED
                    conf = 0.65 if is_prob else 0.90
                    reason = (
                        f"Provider offers {matched_service.category.name if matched_service.category else 'category'}; specific offering unconfirmed"
                        if is_prob
                        else f"Provider verified for {matched_service.category.name if matched_service.category else 'category'}"
                    )
                    normalized = ResultNormalizer.from_db_models(
                        provider=provider,
                        service=matched_service,
                        offering=None,
                        user_lat=query.lat,
                        user_lng=query.lng,
                        service_match_level=lvl,
                        service_match_confidence=conf,
                        ranking_reasons=[reason],
                    )
                    results.append(normalized)
                else:
                    # General provider result
                    normalized = ResultNormalizer.from_db_models(
                        provider=provider,
                        service=None,
                        offering=None,
                        user_lat=query.lat,
                        user_lng=query.lng,
                        service_match_level=ServiceMatchLevel.UNCONFIRMED,
                        service_match_confidence=0.30,
                        ranking_reasons=["General provider listing"],
                    )
                    results.append(normalized)

            return results
        except Exception as exc:
            safe_msg = type(exc).__name__
            self._last_error = safe_msg
            return []
