import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.dependencies import get_db

logger = logging.getLogger(__name__)
from app.models.nammaserve import (
    CitizenReview,
    PlatformListing,
    PlatformType,
    PriceType,
    Provider,
    ProviderOffering,
    ProviderService,
    ProviderServiceArea,
    Service,
    ServiceCategory,
    ServicePrice,
    SourceType,
    ThirdPartyReview,
    VerificationStatus,
)
from app.schemas.nammaserve import (
    AssistantChatRequest,
    AssistantChatResponse,
    CitizenReviewCreate,
    CitizenReviewRead,
    DiscoveryQuery,
    PlatformListingRead,
    ProviderOfferingRead,
    ProviderRead,
    ProviderServiceRead,
    ServiceCategoryRead,
    ServiceDetailRead,
    ServicePriceRead,
    ServiceRead,
    ThirdPartyReviewRead,
    UnifiedDiscoveryResponse,
    ReviewSummaryRequest,
    ReviewSummaryResponse,
)
from app.services.nammaserve.ai.assistant import ServiceAssistant
from app.services.nammaserve.ai.review_summary import ReviewSummaryService
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


@router.post(
    "/reviews/summary",
    response_model=ReviewSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def summarize_reviews(request: ReviewSummaryRequest):
    """Summarize user-supplied review text without scraping Google links."""
    try:
        return await ReviewSummaryService().summarize(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Review summary service error: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Review summary is temporarily unavailable.",
        ) from exc


@router.get(
    "/search",
    response_model=UnifiedDiscoveryResponse,
    status_code=status.HTTP_200_OK,
)
async def search_services(
    service: str | None = Query(None, description="Service category slug, query, or name (e.g. split AC regular servicing, water-tanker)"),
    slug: str | None = Query(None, description="Canonical service slug (e.g. split-ac-regular-service, toilet-flush-repair)"),
    lat: float | None = Query(None, ge=-90, le=90, description="Citizen latitude"),
    lng: float | None = Query(None, ge=-180, le=180, description="Citizen longitude"),
    radius_km: float = Query(5.0, gt=0, le=50.0, description="Search radius in kilometers"),
    area: str | None = Query(None, description="Locality / Area filter (e.g. Indiranagar, Koramangala)"),
    verified_only: bool = Query(False, description="Filter only verified providers"),
    emergency_only: bool = Query(False, description="Filter only emergency / 24x7 providers"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
):
    """Unified location-aware search for Bengaluru local civic services with canonical catalogue awareness."""
    effective_service = slug or service
    discovery_query = DiscoveryQuery(
        service=effective_service,
        resolved_service_slug=slug,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        area=area,
        verified_only=verified_only,
        emergency_only=emergency_only,
        limit=limit,
    )

    discovery_service = UnifiedDiscoveryService(db=db)
    try:
        return await discovery_service.discover(discovery_query)
    except HTTPException:
        raise
    except Exception as exc:
        safe_name = type(exc).__name__
        logger.error("Unified discovery service error: %s", safe_name)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Civic service search is temporarily unavailable. Please try again shortly.",
        )


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


# ---------------------------------------------------------
# Phase 1: Service Catalogue, Platform Listings & Reviews
# ---------------------------------------------------------


@router.get(
    "/catalogue",
    response_model=list[ServiceRead],
    status_code=status.HTTP_200_OK,
)
async def get_services_catalogue(
    category_slug: str | None = Query(None, description="Optional category slug filter (e.g. ac-repair)"),
    db: Session = Depends(get_db),
):
    """List individual civic catalogue services, optionally filtered by category slug."""
    query = (
        db.query(Service)
        .filter(Service.is_active.is_(True))
        .options(joinedload(Service.category))
    )

    if category_slug:
        query = query.join(Service.category).filter(ServiceCategory.slug == category_slug)

    services = query.order_by(Service.name.asc()).all()

    result: list[ServiceRead] = []
    for s in services:
        result.append(
            ServiceRead(
                id=s.id,
                category_id=s.category_id,
                category_slug=s.category.slug if s.category else None,
                category_name=s.category.name if s.category else None,
                slug=s.slug,
                name=s.name,
                description=s.description,
                unit=s.unit,
                is_active=s.is_active,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
        )
    return result


@router.get(
    "/catalogue/{service_slug}",
    response_model=ServiceDetailRead,
    status_code=status.HTTP_200_OK,
)
async def get_service_detail(
    service_slug: str,
    db: Session = Depends(get_db),
):
    """Get full details of an individual service including platform rate cards and offerings."""
    service = (
        db.query(Service)
        .filter(Service.slug == service_slug)
        .options(
            joinedload(Service.category),
            joinedload(Service.platform_listings).joinedload(PlatformListing.prices),
            joinedload(Service.provider_offerings).joinedload(ProviderOffering.prices),
            joinedload(Service.prices),
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_slug}' not found.",
        )

    # Format platform listings
    listings_read: list[PlatformListingRead] = []
    for pl in service.platform_listings:
        if not pl.is_active:
            continue
        prices_read = [
            ServicePriceRead(
                id=p.id,
                service_id=p.service_id,
                price_type=PriceType(p.price_type),
                amount=p.amount,
                price_min=p.price_min,
                price_max=p.price_max,
                currency=p.currency,
                unit=p.unit,
                platform_listing_id=p.platform_listing_id,
                provider_offering_id=p.provider_offering_id,
                conditions=p.conditions,
                inclusions=p.inclusions,
                exclusions=p.exclusions,
                source_url=p.source_url,
                verification_status=VerificationStatus(p.verification_status),
                last_verified_at=p.last_verified_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in pl.prices
        ]
        listings_read.append(
            PlatformListingRead(
                id=pl.id,
                platform=PlatformType(pl.platform),
                service_id=pl.service_id,
                service_slug=service.slug,
                service_name=service.name,
                title=pl.title,
                description=pl.description,
                locality=pl.locality,
                city=pl.city,
                listing_url=pl.listing_url,
                booking_url=pl.booking_url,
                verification_status=VerificationStatus(pl.verification_status),
                source=pl.source,
                last_checked_at=pl.last_checked_at,
                is_active=pl.is_active,
                prices=prices_read,
                created_at=pl.created_at,
                updated_at=pl.updated_at,
            )
        )

    # Format offerings
    offerings_read: list[ProviderOfferingRead] = []
    for po in service.provider_offerings:
        if not po.is_active:
            continue
        po_prices = [
            ServicePriceRead(
                id=p.id,
                service_id=p.service_id,
                price_type=PriceType(p.price_type),
                amount=p.amount,
                price_min=p.price_min,
                price_max=p.price_max,
                currency=p.currency,
                unit=p.unit,
                platform_listing_id=p.platform_listing_id,
                provider_offering_id=p.provider_offering_id,
                conditions=p.conditions,
                inclusions=p.inclusions,
                exclusions=p.exclusions,
                source_url=p.source_url,
                verification_status=VerificationStatus(p.verification_status),
                last_verified_at=p.last_verified_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in po.prices
        ]
        offerings_read.append(
            ProviderOfferingRead(
                id=po.id,
                provider_id=po.provider_id,
                provider_name=po.provider.name if po.provider else None,
                service_id=po.service_id,
                service_slug=service.slug,
                service_name=service.name,
                custom_name=po.custom_name,
                description=po.description,
                is_available=po.is_available,
                is_active=po.is_active,
                verification_status=VerificationStatus(po.verification_status),
                source=po.source,
                source_url=po.source_url,
                last_verified_at=po.last_verified_at,
                prices=po_prices,
                created_at=po.created_at,
                updated_at=po.updated_at,
            )
        )

    # Direct benchmark prices
    direct_prices: list[ServicePriceRead] = [
        ServicePriceRead(
            id=p.id,
            service_id=p.service_id,
            price_type=PriceType(p.price_type),
            amount=p.amount,
            price_min=p.price_min,
            price_max=p.price_max,
            currency=p.currency,
            unit=p.unit,
            platform_listing_id=p.platform_listing_id,
            provider_offering_id=p.provider_offering_id,
            conditions=p.conditions,
            inclusions=p.inclusions,
            exclusions=p.exclusions,
            source_url=p.source_url,
            verification_status=VerificationStatus(p.verification_status),
            last_verified_at=p.last_verified_at,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in service.prices
    ]

    return ServiceDetailRead(
        id=service.id,
        category_id=service.category_id,
        category_slug=service.category.slug if service.category else None,
        category_name=service.category.name if service.category else None,
        slug=service.slug,
        name=service.name,
        description=service.description,
        unit=service.unit,
        is_active=service.is_active,
        platform_listings=listings_read,
        provider_offerings=offerings_read,
        prices=direct_prices,
    )


@router.get(
    "/platforms/listings",
    response_model=list[PlatformListingRead],
    status_code=status.HTTP_200_OK,
)
async def get_platform_listings(
    service_slug: str | None = Query(None, description="Optional service slug filter (e.g. split-ac-regular-service)"),
    platform: PlatformType | None = Query(None, description="Optional platform filter (e.g. URBAN_COMPANY, NOBROKER)"),
    locality: str | None = Query(None, description="Optional Bengaluru locality filter (e.g. Kengeri)"),
    db: Session = Depends(get_db),
):
    """List comparative external platform listings and verified rate cards."""
    query = (
        db.query(PlatformListing)
        .filter(PlatformListing.is_active.is_(True))
        .options(
            joinedload(PlatformListing.service),
            joinedload(PlatformListing.prices),
        )
    )

    if service_slug:
        query = query.join(PlatformListing.service).filter(Service.slug == service_slug)
    if platform:
        query = query.filter(PlatformListing.platform == platform.value)
    if locality:
        query = query.filter(PlatformListing.locality.ilike(f"%{locality.strip()}%"))

    listings = query.order_by(PlatformListing.title.asc()).all()

    result: list[PlatformListingRead] = []
    for pl in listings:
        prices_read = [
            ServicePriceRead(
                id=p.id,
                service_id=p.service_id,
                price_type=PriceType(p.price_type),
                amount=p.amount,
                price_min=p.price_min,
                price_max=p.price_max,
                currency=p.currency,
                unit=p.unit,
                platform_listing_id=p.platform_listing_id,
                provider_offering_id=p.provider_offering_id,
                conditions=p.conditions,
                inclusions=p.inclusions,
                exclusions=p.exclusions,
                source_url=p.source_url,
                verification_status=VerificationStatus(p.verification_status),
                last_verified_at=p.last_verified_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in pl.prices
        ]
        result.append(
            PlatformListingRead(
                id=pl.id,
                platform=PlatformType(pl.platform),
                service_id=pl.service_id,
                service_slug=pl.service.slug if pl.service else None,
                service_name=pl.service.name if pl.service else None,
                title=pl.title,
                description=pl.description,
                locality=pl.locality,
                city=pl.city,
                listing_url=pl.listing_url,
                booking_url=pl.booking_url,
                verification_status=VerificationStatus(pl.verification_status),
                source=pl.source,
                last_checked_at=pl.last_checked_at,
                is_active=pl.is_active,
                prices=prices_read,
                created_at=pl.created_at,
                updated_at=pl.updated_at,
            )
        )
    return result


@router.post(
    "/reviews",
    response_model=CitizenReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_citizen_review(
    review_in: CitizenReviewCreate,
    db: Session = Depends(get_db),
):
    """Submit a verified citizen review for a Bengaluru service provider."""
    # Ensure provider exists
    provider = db.query(Provider).filter(Provider.id == review_in.provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found.",
        )

    # Optional service check
    if review_in.service_id:
        svc = db.query(Service).filter(Service.id == review_in.service_id).first()
        if not svc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found.",
            )

    review = CitizenReview(
        provider_id=review_in.provider_id,
        service_id=review_in.service_id,
        citizen_user_id=review_in.citizen_user_id,
        rating=review_in.rating,
        review_title=review_in.review_title,
        review_text=review_in.review_text,
        locality=review_in.locality,
        service_date=review_in.service_date,
        is_verified_resident=False,
        is_published=True,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
