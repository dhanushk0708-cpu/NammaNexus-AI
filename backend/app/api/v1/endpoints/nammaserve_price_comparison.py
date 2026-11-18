"""FastAPI endpoints for NammaServe Bengaluru Home Services Price Comparison.

Provides:
- GET /api/v1/nammaserve/price-comparison/overview
- GET /api/v1/nammaserve/price-comparison/records
- GET /api/v1/nammaserve/price-comparison/benchmarks
- GET /api/v1/nammaserve/price-comparison/filters
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.nammaserve_research import PriceComparisonRecord
from app.schemas.nammaserve_research import (
    BenchmarkTaskComparison,
    PriceComparisonBenchmarksResponse,
    PriceComparisonFiltersResponse,
    PriceComparisonListResponse,
    PriceComparisonOverviewResponse,
    PriceComparisonRecordRead,
)
from scripts.import_nammaserve_price_comparison import PriceComparisonDatasetImporter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/nammaserve/price-comparison",
    tags=["NammaServe Price Comparison"],
)

# Canonical benchmark definitions based on research report cross-platform matrix
BENCHMARK_DEFINITIONS = [
    {
        "category": "Plumbing",
        "benchmark_task": "Plumber Inspection / Visit Fee",
        "match_keywords": ["consultation", "inspection", "plumber arrival", "24 hours plumbing"],
        "notes": "Covers technician diagnosis / visit. Urban Company and NoBroker waive or adjust this fee against service invoices above INR 499.",
    },
    {
        "category": "Plumbing",
        "benchmark_task": "Regular Tap Repair / Installation",
        "match_keywords": ["tap repair", "tap installation", "tap repair/installation"],
        "notes": "Standard single-fixture tap service labour. Replacement fixtures, mixers, and cartridge parts excluded.",
    },
    {
        "category": "Plumbing",
        "benchmark_task": "Toilet Pot Blockage Removal",
        "match_keywords": ["toilet pot blockage", "pot blockage"],
        "notes": "Labour for mechanical clearing of commode blockage. Replacement gaskets and wax rings excluded.",
    },
    {
        "category": "Plumbing",
        "benchmark_task": "Wash Basin Installation",
        "match_keywords": ["wash basin installation"],
        "notes": "Mounting and waste pipe connection labour. Basin unit and silicone sealants excluded.",
    },
    {
        "category": "AC Repair & Servicing",
        "benchmark_task": "Deep Clean / Foam AC Service",
        "match_keywords": ["foam", "deep clean", "power jet", "cleaning services"],
        "notes": "Full indoor & outdoor unit coil/blower pressure cleaning. Gas top-up and capacitor replacements excluded.",
    },
    {
        "category": "AC Repair & Servicing",
        "benchmark_task": "AC Diagnostic Check-up / Inspection",
        "match_keywords": ["ac repair", "check-up", "ac inspection"],
        "notes": "Diagnosis of cooling loss, noise, or electrical issues; adjusted in repair bill.",
    },
    {
        "category": "AC Repair & Servicing",
        "benchmark_task": "Split AC Installation",
        "match_keywords": ["split ac installation", "ac installation"],
        "notes": "Standard wall bracket mounting and copper piping connection. Extra copper pipe, drain hose, and core cutting charged separately.",
    },
    {
        "category": "AC Repair & Servicing",
        "benchmark_task": "AC Gas Refill & Check-up",
        "match_keywords": ["gas refill", "gas charging"],
        "notes": "Full refrigerant evacuation, leak test, and recharge (R32/R410A). Valve replacement extra if damaged.",
    },
    {
        "category": "Electrical Services",
        "benchmark_task": "Electrician Visit / Inspection Fee",
        "match_keywords": ["electrician visit", "electrician consultation", "session fee"],
        "notes": "Standard diagnostic call-out; adjusted in repair total on platform rate cards.",
    },
    {
        "category": "Electrical Services",
        "benchmark_task": "Ceiling Fan Installation",
        "match_keywords": ["ceiling fan installation", "fan installation"],
        "notes": "Assembly and hanging of ceiling fan. Hook installation and down-rod extension extra.",
    },
    {
        "category": "Electrical Services",
        "benchmark_task": "Switch / Socket Replacement",
        "match_keywords": ["switch", "socket replacement"],
        "notes": "Per-unit plate/module labour. Switch plate and modular boxes excluded.",
    },
    {
        "category": "House Cleaning",
        "benchmark_task": "Furnished Apartment Full Deep Clean",
        "match_keywords": ["furnished", "full house deep clean", "cleaning services hk"],
        "notes": "Comprehensive floor scrubbing, bathroom descaling, balcony wash, and kitchen degreasing.",
    },
    {
        "category": "House Cleaning",
        "benchmark_task": "Unfurnished Apartment Deep Clean",
        "match_keywords": ["unfurnished", "vacant", "clean dreamz"],
        "notes": "Full empty home deep cleaning prior to move-in.",
    },
    {
        "category": "House Cleaning",
        "benchmark_task": "Sofa Cleaning",
        "match_keywords": ["sofa cleaning"],
        "notes": "Dry vacuuming and shampoo extraction per seat / set.",
    },
    {
        "category": "Pest Control",
        "benchmark_task": "Apartment Cockroach / General Pest Control",
        "match_keywords": ["cockroach", "pest control", "general pest"],
        "notes": "Gel baiting and spray treatment for apartment kitchens and wet areas.",
    },
    {
        "category": "Appliance Repair",
        "benchmark_task": "Washing Machine Check-up / Diagnostic",
        "match_keywords": ["washing machine"],
        "notes": "Inspection fee for top-load or front-load washing machines.",
    },
    {
        "category": "Appliance Repair",
        "benchmark_task": "Refrigerator Check-up / Diagnostic",
        "match_keywords": ["refrigerator", "fridge"],
        "notes": "Inspection of compressor, thermostat, and cooling cycle.",
    },
    {
        "category": "Water Purifier / RO Services",
        "benchmark_task": "RO Diagnostic / Filter Check-up",
        "match_keywords": ["ro diagnostic", "water purifier service", "filter check-up"],
        "notes": "TDS check, membrane pressure test, and sediment filter check.",
    },
    {
        "category": "Water Purifier / RO Services",
        "benchmark_task": "Complete RO Filter & Membrane Replacement Kit",
        "match_keywords": ["complete ro", "membrane kit", "full service"],
        "notes": "Full filter overhaul (sediment, carbon, RO membrane, post-carbon filter).",
    },
    {
        "category": "Water Purifier / RO Services",
        "benchmark_task": "Wall-Mounted RO Installation",
        "match_keywords": ["ro installation", "water purifier installation"],
        "notes": "Standard inlet valve connection, pre-filter mounting, and purifier hanging.",
    },
    {
        "category": "Carpentry",
        "benchmark_task": "Door Repair / Installation",
        "match_keywords": ["door repair", "door installation", "general carpentry"],
        "notes": "Hinge alignment, latch fitting, or door hanging labour.",
    },
    {
        "category": "Carpentry",
        "benchmark_task": "Bed Assembly",
        "match_keywords": ["bed assembly", "bed repair"],
        "notes": "Assembly of single, double, or hydraulic storage bed.",
    },
    {
        "category": "Carpentry",
        "benchmark_task": "Wardrobe Assembly (1 to 4 Doors)",
        "match_keywords": ["wardrobe assembly", "wardrobe repair"],
        "notes": "Modular panel and hinge alignment labour.",
    },
]


@router.get(
    "/overview",
    response_model=PriceComparisonOverviewResponse,
    status_code=status.HTTP_200_OK,
)
def get_price_comparison_overview(db: Session = Depends(get_db)):
    """Summary statistics for NammaServe Bengaluru Price Comparison."""
    try:
        total = db.query(PriceComparisonRecord).count()
        if total > 0:
            # Platforms count
            plat_rows = db.query(
                PriceComparisonRecord.source_platform, func.count()
            ).group_by(PriceComparisonRecord.source_platform).all()
            plat_count = {p: count for p, count in plat_rows}

            # Categories count
            cat_rows = db.query(
                PriceComparisonRecord.service_category, func.count()
            ).group_by(PriceComparisonRecord.service_category).all()
            cat_count = {c: count for c, count in cat_rows}

            # Price types count
            pt_rows = db.query(
                PriceComparisonRecord.price_type, func.count()
            ).group_by(PriceComparisonRecord.price_type).all()
            pt_count = {pt: count for pt, count in pt_rows}

            # Verification status breakdown
            ver_rows = db.query(
                PriceComparisonRecord.verification_status, func.count()
            ).group_by(PriceComparisonRecord.verification_status).all()
            ver_count = {v: count for v, count in ver_rows}

            # Locality vs Citywide
            local_count = db.query(PriceComparisonRecord).filter(
                PriceComparisonRecord.is_locality_specific.is_(True)
            ).count()
            citywide_count = total - local_count

            return PriceComparisonOverviewResponse(
                total_records=total,
                platforms_count=plat_count,
                categories_count=cat_count,
                price_types_count=pt_count,
                verification_breakdown=ver_count,
                citywide_confirmed_count=citywide_count,
                locality_specific_count=local_count,
                latest_research_date="2026-10-29",
            )
    except Exception as exc:
        logger.warning("Database query failed in price comparison overview (%s), using local fallback.", exc)
        try:
            db.rollback()
        except Exception:
            pass

    # Fallback to local dataset stats
    importer = PriceComparisonDatasetImporter()
    stats = importer.dry_run()
    return PriceComparisonOverviewResponse(
        total_records=stats["total_rows_read"],
        platforms_count=dict(stats["platforms"]),
        categories_count=dict(stats["categories"]),
        price_types_count=dict(stats["price_types"]),
        verification_breakdown=dict(stats["verification_statuses"]),
        citywide_confirmed_count=stats["citywide_confirmed_count"],
        locality_specific_count=stats["locality_specific_count"],
        latest_research_date="2026-10-29",
    )


@router.get(
    "/records",
    response_model=PriceComparisonListResponse,
    status_code=status.HTTP_200_OK,
)
def list_price_comparison_records(
    category: Optional[str] = Query(None, description="Filter by service category"),
    platform: Optional[str] = Query(None, description="Filter by platform (Urban Company, NoBroker, Justdial, Sulekha)"),
    price_type: Optional[str] = Query(None, description="Filter by price type (FIXED, STARTING_FROM, PRICE_RANGE, QUOTATION_REQUIRED, UNPUBLISHED)"),
    geographic_scope: Optional[str] = Query(None, description="Filter by geographic scope"),
    locality_specific_only: Optional[bool] = Query(None, description="Filter only locality-specific or unconfirmed scopes"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    search: Optional[str] = Query(None, description="Search service name, provider name, or notes"),
    sort_by: str = Query("service_name", description="Sort field: service_name, platform, price_min, category, price_type"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List paginated price comparison records with multi-criteria filtering and sorting."""
    use_fallback = False
    items = []
    total = 0
    pages = 1

    try:
        query = select(PriceComparisonRecord)

        if category:
            query = query.where(PriceComparisonRecord.service_category.ilike(f"%{category.strip()}%"))
        if platform:
            query = query.where(PriceComparisonRecord.source_platform.ilike(f"%{platform.strip()}%"))
        if price_type:
            query = query.where(PriceComparisonRecord.price_type == price_type.strip())
        if geographic_scope:
            query = query.where(PriceComparisonRecord.geographic_scope.ilike(f"%{geographic_scope.strip()}%"))
        if locality_specific_only is not None:
            query = query.where(PriceComparisonRecord.is_locality_specific.is_(locality_specific_only))
        if verification_status:
            query = query.where(PriceComparisonRecord.verification_status == verification_status.strip())

        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    PriceComparisonRecord.service_name.ilike(pattern),
                    PriceComparisonRecord.provider_name.ilike(pattern),
                    PriceComparisonRecord.notes.ilike(pattern),
                    PriceComparisonRecord.price_scope.ilike(pattern),
                )
            )

        # Sorting
        if sort_by == "price_min":
            order_col = (
                PriceComparisonRecord.price_min.desc().nulls_last()
                if sort_dir == "desc"
                else PriceComparisonRecord.price_min.asc().nulls_last()
            )
        elif sort_by == "platform":
            order_col = (
                PriceComparisonRecord.source_platform.desc()
                if sort_dir == "desc"
                else PriceComparisonRecord.source_platform.asc()
            )
        elif sort_by == "category":
            order_col = (
                PriceComparisonRecord.service_category.desc()
                if sort_dir == "desc"
                else PriceComparisonRecord.service_category.asc()
            )
        elif sort_by == "price_type":
            order_col = (
                PriceComparisonRecord.price_type.desc()
                if sort_dir == "desc"
                else PriceComparisonRecord.price_type.asc()
            )
        else:  # default service_name
            order_col = (
                PriceComparisonRecord.service_name.desc()
                if sort_dir == "desc"
                else PriceComparisonRecord.service_name.asc()
            )

        query = query.order_by(order_col, PriceComparisonRecord.source_platform.asc())

        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        pages = (total + limit - 1) // limit if total > 0 else 1
        offset = (page - 1) * limit
        items = db.execute(query.offset(offset).limit(limit)).scalars().all()

        if total == 0 and db.query(PriceComparisonRecord).count() == 0:
            use_fallback = True

    except Exception as exc:
        logger.warning("Database error in list_price_comparison_records (%s), using local fallback.", exc)
        try:
            db.rollback()
        except Exception:
            pass
        use_fallback = True

    if use_fallback:
        importer = PriceComparisonDatasetImporter()
        valid_records, _, _ = importer.load_and_validate()
        filtered = []

        for r in valid_records:
            if category and category.lower() not in r["service_category"].lower():
                continue
            if platform and platform.lower() not in r["source_platform"].lower():
                continue
            if price_type and r["price_type"] != price_type:
                continue
            if geographic_scope and geographic_scope.lower() not in r["geographic_scope"].lower():
                continue
            if locality_specific_only is not None and r["is_locality_specific"] != locality_specific_only:
                continue
            if verification_status and r["verification_status"] != verification_status:
                continue
            if search:
                s_lower = search.lower()
                blob = f"{r['service_name']} {r['provider_name']} {r.get('notes') or ''} {r.get('price_scope') or ''}".lower()
                if s_lower not in blob:
                    continue
            filtered.append(r)

        # Sort filtered
        if sort_by == "price_min":
            filtered.sort(
                key=lambda x: (x["price_min"] is not None, x["price_min"] or 0),
                reverse=(sort_dir == "desc"),
            )
        elif sort_by == "platform":
            filtered.sort(key=lambda x: x["source_platform"].lower(), reverse=(sort_dir == "desc"))
        elif sort_by == "category":
            filtered.sort(key=lambda x: x["service_category"].lower(), reverse=(sort_dir == "desc"))
        else:
            filtered.sort(key=lambda x: x["service_name"].lower(), reverse=(sort_dir == "desc"))

        total = len(filtered)
        pages = (total + limit - 1) // limit if total > 0 else 1
        offset = (page - 1) * limit
        paged_records = filtered[offset : offset + limit]

        from datetime import datetime
        now = datetime.utcnow()
        mock_items = [
            PriceComparisonRecordRead(
                id=f"rec-{idx}",
                created_at=now,
                **r,
            )
            for idx, r in enumerate(paged_records)
        ]
        return PriceComparisonListResponse(
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            items=mock_items,
        )

    return PriceComparisonListResponse(
        total=total,
        page=page,
        limit=limit,
        pages=pages,
        items=items,
    )


@router.get(
    "/benchmarks",
    response_model=PriceComparisonBenchmarksResponse,
    status_code=status.HTTP_200_OK,
)
def get_price_comparison_benchmarks(
    category: Optional[str] = Query(None, description="Optional service category filter"),
    db: Session = Depends(get_db),
):
    """Side-by-side comparable task benchmarks across Urban Company, NoBroker, Justdial, and Sulekha."""
    try:
        all_records = db.query(PriceComparisonRecord).all()
    except Exception as exc:
        logger.warning("Database error fetching benchmarks (%s), using local fallback.", exc)
        try:
            db.rollback()
        except Exception:
            pass
        importer = PriceComparisonDatasetImporter()
        valid_records, _, _ = importer.load_and_validate()
        from datetime import datetime
        now = datetime.utcnow()
        all_records = [
            PriceComparisonRecordRead(id=f"rec-{idx}", created_at=now, **r)
            for idx, r in enumerate(valid_records)
        ]

    benchmarks_list: list[BenchmarkTaskComparison] = []

    for defn in BENCHMARK_DEFINITIONS:
        if category and category.lower() not in defn["category"].lower():
            continue

        cat_records = [r for r in all_records if r.service_category == defn["category"]]

        # Find best matching record for each platform
        def find_match(plat_name: str) -> Optional[PriceComparisonRecordRead]:
            plat_recs = [r for r in cat_records if plat_name.lower() in r.source_platform.lower()]
            for kw in defn["match_keywords"]:
                for r in plat_recs:
                    if kw.lower() in r.service_name.lower():
                        return PriceComparisonRecordRead.model_validate(r)
            # fallback if single category card
            return None

        uc_match = find_match("Urban Company")
        nb_match = find_match("NoBroker")
        jd_match = find_match("Justdial")
        su_match = find_match("Sulekha")

        # Only include if at least 2 platforms have data or one platform has verified rate
        if uc_match or nb_match or jd_match or su_match:
            benchmarks_list.append(
                BenchmarkTaskComparison(
                    category=defn["category"],
                    benchmark_task=defn["benchmark_task"],
                    urban_company=uc_match,
                    nobroker=nb_match,
                    justdial=jd_match,
                    sulekha=su_match,
                    comparability_notes=defn.get("notes"),
                )
            )

    return PriceComparisonBenchmarksResponse(
        total_benchmarks=len(benchmarks_list),
        benchmarks=benchmarks_list,
    )


@router.get(
    "/filters",
    response_model=PriceComparisonFiltersResponse,
    status_code=status.HTTP_200_OK,
)
def get_price_comparison_filters(db: Session = Depends(get_db)):
    """Fetch distinct filter options for UI filter dropdowns."""
    try:
        platforms = [
            r[0]
            for r in db.query(PriceComparisonRecord.source_platform)
            .distinct()
            .order_by(PriceComparisonRecord.source_platform.asc())
            .all()
        ]
        categories = [
            r[0]
            for r in db.query(PriceComparisonRecord.service_category)
            .distinct()
            .order_by(PriceComparisonRecord.service_category.asc())
            .all()
        ]
        price_types = [
            r[0]
            for r in db.query(PriceComparisonRecord.price_type)
            .distinct()
            .order_by(PriceComparisonRecord.price_type.asc())
            .all()
        ]
        ver_statuses = [
            r[0]
            for r in db.query(PriceComparisonRecord.verification_status)
            .distinct()
            .order_by(PriceComparisonRecord.verification_status.asc())
            .all()
        ]
        geo_scopes = [
            r[0]
            for r in db.query(PriceComparisonRecord.geographic_scope)
            .distinct()
            .order_by(PriceComparisonRecord.geographic_scope.asc())
            .all()
        ]

        if platforms and categories:
            return PriceComparisonFiltersResponse(
                platforms=platforms,
                categories=categories,
                price_types=price_types,
                verification_statuses=ver_statuses,
                geographic_scopes=geo_scopes,
            )
    except Exception as exc:
        logger.warning("Database error fetching filters (%s), using local fallback.", exc)
        try:
            db.rollback()
        except Exception:
            pass

    importer = PriceComparisonDatasetImporter()
    stats = importer.dry_run()
    return PriceComparisonFiltersResponse(
        platforms=sorted(list(stats["platforms"].keys())),
        categories=sorted(list(stats["categories"].keys())),
        price_types=sorted(list(stats["price_types"].keys())),
        verification_statuses=sorted(list(stats["verification_statuses"].keys())),
        geographic_scopes=sorted(list(stats["geographic_scopes"].keys())),
    )
