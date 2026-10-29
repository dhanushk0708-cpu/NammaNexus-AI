"""FastAPI endpoints for NammaServe Provider Research and Booking Requests."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.nammaserve_research import (
    BookingRequest,
    ResearchCandidate,
    ResearchCoverage,
)
from app.schemas.nammaserve_research import (
    BookingRequestCreate,
    BookingRequestRead,
    ResearchCandidateListResponse,
    ResearchCandidateRead,
    ResearchCoverageRead,
    ResearchCoverageResponse,
    ResearchOverviewMetrics,
)
from scripts.import_nammaserve_research import ResearchDatasetImporter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/nammaserve/research",
    tags=["NammaServe Research"],
)


@router.get(
    "/overview",
    response_model=ResearchOverviewMetrics,
    status_code=status.HTTP_200_OK,
)
def get_research_overview(db: Session = Depends(get_db)):
    """Summary metrics calculated directly from database records (or validated dataset)."""
    try:
        cand_count = db.query(ResearchCandidate).count()

        # If database has candidates, compute dynamic metrics from DB
        if cand_count > 0:
            distinct_biz = db.query(func.count(func.distinct(ResearchCandidate.provider_name))).scalar() or 0
            total_areas = db.query(func.count(func.distinct(ResearchCandidate.area_name))).scalar() or 0
            total_cats = db.query(func.count(func.distinct(ResearchCandidate.service_category))).scalar() or 0
            with_prices = db.query(ResearchCandidate).filter(ResearchCandidate.price_amount.isnot(None)).count()
            with_ratings = db.query(ResearchCandidate).filter(ResearchCandidate.rating.isnot(None)).count()
            total_cov = db.query(ResearchCoverage).count()
            completed_cov = db.query(ResearchCoverage).filter(
                ResearchCoverage.research_status == "COMPLETED_WITH_RESULTS"
            ).count()

            # Verification breakdown
            ver_rows = db.query(ResearchCandidate.verification_status, func.count()).group_by(
                ResearchCandidate.verification_status
            ).all()
            ver_breakdown = {status: count for status, count in ver_rows}

            # Price type breakdown
            pt_rows = db.query(ResearchCandidate.price_type, func.count()).group_by(
                ResearchCandidate.price_type
            ).all()
            pt_breakdown = {pt: count for pt, count in pt_rows if pt}

            # Areas & Categories
            areas = [r[0] for r in db.query(ResearchCandidate.area_name).distinct().order_by(ResearchCandidate.area_name).all()]
            cats = [r[0] for r in db.query(ResearchCandidate.service_category).distinct().order_by(ResearchCandidate.service_category).all()]

            return ResearchOverviewMetrics(
                total_candidates=cand_count,
                distinct_businesses=distinct_biz,
                total_areas=total_areas,
                total_categories=total_cats,
                total_coverage_cells=total_cov,
                completed_coverage_cells=completed_cov,
                published_prices_count=with_prices,
                ratings_count=with_ratings,
                verification_breakdown=ver_breakdown,
                price_type_breakdown=pt_breakdown,
                areas_list=areas,
                categories_list=cats,
            )
    except Exception as exc:
        logger.warning(f"Database error in get_research_overview ({exc}), gracefully falling back to dataset.")
        try:
            db.rollback()
        except Exception:
            pass

    # Fallback to dry-run stats from validated local research CSV files
    importer = ResearchDatasetImporter()
    stats = importer.dry_run()
    return ResearchOverviewMetrics(
        total_candidates=stats["total_candidates_to_import"],
        distinct_businesses=stats["distinct_business_names"],
        total_areas=stats["areas_represented"],
        total_categories=stats["categories_represented"],
        total_coverage_cells=stats["total_coverage_cells_to_import"],
        completed_coverage_cells=stats["total_coverage_cells_to_import"],
        published_prices_count=stats["published_prices_count"],
        ratings_count=stats["published_ratings_count"],
        verification_breakdown=stats["verification_status_distribution"],
        price_type_breakdown=stats["price_type_distribution"],
        areas_list=sorted(list(stats["area_distribution"].keys())),
        categories_list=sorted(list(stats["category_distribution"].keys())),
    )


@router.get(
    "/candidates",
    response_model=ResearchCandidateListResponse,
    status_code=status.HTTP_200_OK,
)
def list_research_candidates(
    area: Optional[str] = Query(None, description="Filter by area name (e.g. Kengeri, Vijayanagar)"),
    category: Optional[str] = Query(None, description="Filter by service category (e.g. Plumbing, AC repair)"),
    batch: Optional[str] = Query(None, description="Filter by batch (e.g. batch1, batch2)"),
    verification_status: Optional[str] = Query(None, description="Filter by status (DISCOVERED, SOURCE_CORROBORATED)"),
    price_type: Optional[str] = Query(None, description="Filter by price type"),
    has_price: Optional[bool] = Query(None, description="Filter records that have a published price amount"),
    has_rating: Optional[bool] = Query(None, description="Filter records that have a rating"),
    search: Optional[str] = Query(None, description="Search provider name, specific services, or address"),
    sort_by: str = Query("rank", description="Sort field: rank, rating, price_amount, name"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List research candidate providers with pagination, sorting, and multi-criteria filters."""
    query = select(ResearchCandidate)

    if area:
        query = query.where(
            or_(
                ResearchCandidate.area_name.ilike(f"%{area}%"),
                ResearchCandidate.requested_area.ilike(f"%{area}%"),
            )
        )
    if category:
        query = query.where(ResearchCandidate.service_category.ilike(f"%{category}%"))
    if batch:
        query = query.where(ResearchCandidate.batch_id == batch)
    if verification_status:
        query = query.where(ResearchCandidate.verification_status == verification_status)
    if price_type:
        query = query.where(ResearchCandidate.price_type == price_type)
    if has_price is True:
        query = query.where(ResearchCandidate.price_amount.isnot(None))
    elif has_price is False:
        query = query.where(ResearchCandidate.price_amount.is_(None))
    if has_rating is True:
        query = query.where(ResearchCandidate.rating.isnot(None))
    elif has_rating is False:
        query = query.where(ResearchCandidate.rating.is_(None))
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                ResearchCandidate.provider_name.ilike(search_pattern),
                ResearchCandidate.specific_services.ilike(search_pattern),
                ResearchCandidate.business_address.ilike(search_pattern),
                ResearchCandidate.evidence_summary.ilike(search_pattern),
            )
        )

    # Sorting
    if sort_by == "rating":
        order_col = ResearchCandidate.rating.desc() if sort_dir == "desc" else ResearchCandidate.rating.asc().nulls_last()
    elif sort_by == "price_amount":
        order_col = ResearchCandidate.price_amount.desc() if sort_dir == "desc" else ResearchCandidate.price_amount.asc().nulls_last()
    elif sort_by == "name":
        order_col = ResearchCandidate.provider_name.desc() if sort_dir == "desc" else ResearchCandidate.provider_name.asc()
    else:  # default rank
        order_col = ResearchCandidate.provider_rank.desc() if sort_dir == "desc" else ResearchCandidate.provider_rank.asc()

    query = query.order_by(order_col, ResearchCandidate.provider_name.asc())

    # Execute query with resilience against remote DB timeouts/drops
    use_fallback = False
    items = []
    total = 0
    pages = 1

    try:
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        pages = (total + limit - 1) // limit if total > 0 else 1
        offset = (page - 1) * limit
        items = db.execute(query.offset(offset).limit(limit)).scalars().all()
        if total == 0 and db.query(ResearchCandidate).count() == 0:
            use_fallback = True
    except Exception as exc:
        logger.warning(f"Database error in list_research_candidates ({exc}), falling back to local validated dataset.")
        try:
            db.rollback()
        except Exception:
            pass
        use_fallback = True

    # Gracefully load from local dataset for seamless experience if DB empty or unavailable
    if use_fallback:
        importer = ResearchDatasetImporter()
        all_cands, _ = importer.load_and_validate()
        filtered = []
        for c in all_cands:
            if area and area.lower() not in c["area_name"].lower() and area.lower() not in c["requested_area"].lower():
                continue
            if category and category.lower() not in c["service_category"].lower():
                continue
            if batch and c["batch_id"] != batch:
                continue
            if verification_status and c["verification_status"] != verification_status:
                continue
            if price_type and c["price_type"] != price_type:
                continue
            if has_price is True and c["price_amount"] is None:
                continue
            if has_price is False and c["price_amount"] is not None:
                continue
            if has_rating is True and c["rating"] is None:
                continue
            if has_rating is False and c["rating"] is not None:
                continue
            if search:
                s_lower = search.lower()
                blob = f"{c['provider_name']} {c.get('specific_services') or ''} {c.get('business_address') or ''}".lower()
                if s_lower not in blob:
                    continue
            filtered.append(c)

        if sort_by == "rating":
            filtered.sort(key=lambda x: (x.get("rating") is not None, x.get("rating") or 0), reverse=(sort_dir == "desc"))
        elif sort_by == "price_amount":
            filtered.sort(key=lambda x: (x.get("price_amount") is not None, x.get("price_amount") or 0), reverse=(sort_dir == "desc"))
        elif sort_by == "name":
            filtered.sort(key=lambda x: (x.get("provider_name") or "").lower(), reverse=(sort_dir == "desc"))
        else:
            filtered.sort(key=lambda x: (x.get("provider_rank") or 999), reverse=(sort_dir == "desc"))

        total = len(filtered)
        pages = (total + limit - 1) // limit if total > 0 else 1
        offset = (page - 1) * limit
        paged_raw = filtered[offset : offset + limit]
        
        from datetime import datetime
        now = datetime.utcnow()
        mock_items = []
        for idx, item in enumerate(paged_raw):
            read_item = ResearchCandidateRead(
                id=f"cand-{idx}",
                batch_id=item["batch_id"],
                provider_id=item["provider_id"],
                provider_name=item["provider_name"],
                service_category=item["service_category"],
                raw_service_category=item["raw_service_category"],
                specific_services=item["specific_services"],
                requested_area=item["requested_area"],
                area_name=item["area_name"],
                business_address=item["business_address"],
                public_phone=item["public_phone"],
                public_email=item["public_email"],
                website_url=item["website_url"],
                contact_or_booking_url=item["contact_or_booking_url"],
                advertised_service_areas=item["advertised_service_areas"],
                area_coverage_evidence_url=item["area_coverage_evidence_url"],
                price_type=item["price_type"],
                price_amount=item["price_amount"],
                price_currency=item["price_currency"],
                price_unit=item["price_unit"],
                price_scope=item["price_scope"],
                price_source_url=item["price_source_url"],
                rating=item["rating"],
                review_count=item["review_count"],
                rating_platform=item["rating_platform"],
                rating_source_url=item["rating_source_url"],
                booking_method=item["booking_method"],
                availability_status=item["availability_status"],
                verification_status=item["verification_status"],
                primary_source_url=item["primary_source_url"],
                secondary_source_url=item["secondary_source_url"],
                research_date=item["research_date"],
                confidence=item["confidence"],
                evidence_summary=item["evidence_summary"],
                missing_information=item["missing_information"],
                duplicate_group_id=item["duplicate_group_id"],
                provider_rank=item["provider_rank"],
                notes=item["notes"],
                review_summary=item.get("review_summary"),
                review_positive_themes=item.get("review_positive_themes"),
                review_negative_themes=item.get("review_negative_themes"),
                review_date_range=item.get("review_date_range"),
                review_summary_source_url=item.get("review_summary_source_url"),
                review_summary_limitations=item.get("review_summary_limitations"),
                raw_record=item["raw_record"],
                created_at=now,
                updated_at=now,
            )
            mock_items.append(read_item)
        return ResearchCandidateListResponse(
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            items=mock_items,
        )

    return ResearchCandidateListResponse(
        total=total,
        page=page,
        limit=limit,
        pages=pages,
        items=items,
    )


@router.get(
    "/candidates/{candidate_id}",
    response_model=ResearchCandidateRead,
    status_code=status.HTTP_200_OK,
)
def get_research_candidate_detail(
    candidate_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve full details, corroborated sources, and review limitations for a single provider."""
    try:
        cand = db.get(ResearchCandidate, candidate_id)
        if cand:
            return cand

        # Check by provider_id
        cand = db.query(ResearchCandidate).filter(ResearchCandidate.provider_id == candidate_id).first()
        if cand:
            return cand
    except Exception as exc:
        logger.warning(f"Database error in get_research_candidate_detail ({exc}), falling back to dataset.")
        try:
            db.rollback()
        except Exception:
            pass

    # Fallback to dataset search for local development
    importer = ResearchDatasetImporter()
    candidates, _ = importer.load_and_validate()
    match = next((c for c in candidates if c["provider_id"] == candidate_id or c["provider_name"] == candidate_id), None)
    if match:
        from datetime import datetime
        now = datetime.utcnow()
        return ResearchCandidateRead(
            id=candidate_id,
            created_at=now,
            updated_at=now,
            **match,
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research candidate not found")


@router.get(
    "/coverage",
    response_model=ResearchCoverageResponse,
    status_code=status.HTTP_200_OK,
)
def get_research_coverage(db: Session = Depends(get_db)):
    """Fetch the 64 area-category research matrix cells."""
    try:
        cells = db.query(ResearchCoverage).order_by(
            ResearchCoverage.clean_area.asc(), ResearchCoverage.service_category.asc()
        ).all()

        if len(cells) > 0:
            completed = sum(1 for c in cells if c.research_status == "COMPLETED_WITH_RESULTS")
            return ResearchCoverageResponse(
                total_cells=len(cells),
                completed_cells=completed,
                cells=cells,
            )
    except Exception as exc:
        logger.warning(f"Database error in get_research_coverage ({exc}), falling back to dataset.")
        try:
            db.rollback()
        except Exception:
            pass

    # Fallback to local matrix dataset
    importer = ResearchDatasetImporter()
    _, raw_coverage = importer.load_and_validate()
    from datetime import datetime
    now = datetime.utcnow()
    mock_cells = [
        ResearchCoverageRead(
            id=f"cov-{idx}",
            created_at=now,
            **c,
        )
        for idx, c in enumerate(raw_coverage)
    ]
    return ResearchCoverageResponse(
        total_cells=len(mock_cells),
        completed_cells=len(mock_cells),
        cells=mock_cells,
    )


# Booking request endpoints
booking_router = APIRouter(
    prefix="/nammaserve/booking-requests",
    tags=["NammaServe Bookings"],
)


@booking_router.post(
    "",
    response_model=BookingRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_booking_request(
    request: BookingRequestCreate,
    db: Session = Depends(get_db),
):
    """Customer booking request workflow for home services.
    
    Guaranteed user safety: records request with status PENDING_CONFIRMATION
    and returns transparent notice that provider confirmation is required.
    """
    booking = BookingRequest(
        candidate_id=request.candidate_id,
        provider_name=request.provider_name,
        service_category=request.service_category,
        area=request.area,
        customer_name=request.customer_name,
        customer_phone=request.customer_phone,
        customer_email=request.customer_email,
        customer_address=request.customer_address,
        preferred_date=request.preferred_date,
        preferred_time_slot=request.preferred_time_slot,
        issue_description=request.issue_description,
        status="PENDING_CONFIRMATION",
        is_research_candidate=True,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@booking_router.get(
    "",
    response_model=list[BookingRequestRead],
    status_code=status.HTTP_200_OK,
)
def list_booking_requests(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List recent booking requests."""
    return db.query(BookingRequest).order_by(BookingRequest.created_at.desc()).limit(limit).all()
