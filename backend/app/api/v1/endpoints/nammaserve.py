from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.dependencies import get_db
from app.models.nammaserve import (
    Provider,
    ProviderService,
    ProviderServiceArea,
    ServiceCategory,
    SourceType,
    VerificationStatus,
)
from app.schemas.nammaserve import (
    AssistantChatRequest,
    AssistantChatResponse,
    DiscoveryQuery,
    ProviderRead,
    ProviderServiceRead,
    ServiceCategoryRead,
    UnifiedDiscoveryResponse,
)
from app.services.nammaserve.ai.assistant import ServiceAssistant
from app.services.nammaserve.discovery.service import UnifiedDiscoveryService

router = APIRouter(
    prefix="/nammaserve",
    tags=["NammaServe"],
)


@router.post(
    "/assistant",
    response_model=AssistantChatResponse,
    status_code=status.HTTP_200_OK,
)
async def assistant_chat(
    request: AssistantChatRequest,
    db: Session = Depends(get_db),
):
    """Natural-language AI assistant for NammaServe civic service discovery."""
    assistant = ServiceAssistant(db=db)
    return await assistant.process_chat(request)


@router.get(
    "/search",
    response_model=UnifiedDiscoveryResponse,
    status_code=status.HTTP_200_OK,
)
async def search_services(
    service: str | None = Query(None, description="Service category slug or name (e.g. water-tanker, locksmith)"),
    lat: float | None = Query(None, ge=-90, le=90, description="Citizen latitude"),
    lng: float | None = Query(None, ge=-180, le=180, description="Citizen longitude"),
    radius_km: float = Query(5.0, gt=0, le=50.0, description="Search radius in kilometers"),
    area: str | None = Query(None, description="Locality / Area filter (e.g. Indiranagar, Koramangala)"),
    verified_only: bool = Query(False, description="Filter only verified providers"),
    emergency_only: bool = Query(False, description="Filter only emergency / 24x7 providers"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
):
    """Unified location-aware search for Bengaluru local civic services."""
    discovery_query = DiscoveryQuery(
        service=service,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        area=area,
        verified_only=verified_only,
        emergency_only=emergency_only,
        limit=limit,
    )

    discovery_service = UnifiedDiscoveryService(db=db)
    return await discovery_service.discover(discovery_query)


@router.get(
    "/categories",
    response_model=list[ServiceCategoryRead],
    status_code=status.HTTP_200_OK,
)
async def get_service_categories(
    db: Session = Depends(get_db),
):
    """List all active civic service categories."""
    categories = (
        db.query(ServiceCategory)
        .filter(ServiceCategory.is_active.is_(True))
        .order_by(ServiceCategory.name.asc())
        .all()
    )
    return categories


@router.get(
    "/providers/{provider_id}",
    response_model=ProviderRead,
    status_code=status.HTTP_200_OK,
)
async def get_provider_details(
    provider_id: str,
    db: Session = Depends(get_db),
):
    """Get full details, service rate cards, and verification evidence for a specific provider."""
    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id)
        .options(
            joinedload(Provider.services).joinedload(ProviderService.category),
            joinedload(Provider.service_areas),
        )
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found.",
        )

    services_read = []
    for svc in provider.services:
        services_read.append(
            ProviderServiceRead(
                id=svc.id,
                category_id=svc.category_id,
                category_slug=svc.category.slug if svc.category else None,
                category_name=svc.category.name if svc.category else None,
                price_min=svc.price_min,
                price_max=svc.price_max,
                price_unit=svc.price_unit,
                minimum_order=svc.minimum_order,
                capacity=svc.capacity,
                water_type=svc.water_type,
                availability=svc.availability,
                payment_methods=svc.payment_methods,
                notes=svc.notes,
                verification_status=VerificationStatus(svc.verification_status),
                source=svc.source,
                source_type=SourceType(svc.source_type),
                source_url=svc.source_url,
                last_verified_at=svc.last_verified_at,
            )
        )

    return ProviderRead(
        id=provider.id,
        name=provider.name,
        contact_person=provider.contact_person,
        phone=provider.phone,
        alternate_phone=provider.alternate_phone,
        address=provider.address,
        primary_area=provider.primary_area,
        city=provider.city,
        latitude=provider.latitude,
        longitude=provider.longitude,
        service_radius_km=provider.service_radius_km,
        operating_hours=provider.operating_hours,
        is_emergency_service=provider.is_emergency_service,
        verification_status=VerificationStatus(provider.verification_status),
        source=provider.source,
        source_type=SourceType(provider.source_type),
        source_url=provider.source_url,
        last_verified_at=provider.last_verified_at,
        services=services_read,
        serviced_areas=[area.area_name for area in provider.service_areas],
    )
