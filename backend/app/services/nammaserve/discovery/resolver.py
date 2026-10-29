from dataclasses import dataclass, field
import logging
import re
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.nammaserve import Service, ServiceCategory
from app.schemas.nammaserve import ServiceMatchLevel
from app.db.seeds.services import CANONICAL_SERVICES
from app.db.seeds.categories import CANONICAL_CATEGORIES

logger = logging.getLogger(__name__)


@dataclass
class ResolvedCatalogueIntent:
    """Structured resolution of a service query to the canonical catalogue."""
    service_id: str | None = None
    service_slug: str | None = None
    service_name: str | None = None
    category_id: str | None = None
    category_slug: str = "ac-repair"
    category_name: str = "AC Repair"
    is_specific_service: bool = False
    search_keywords: list[str] = field(default_factory=list)
    match_level: ServiceMatchLevel = ServiceMatchLevel.UNCONFIRMED
    match_confidence: float = 0.0
    match_reason: str | None = None
    is_ambiguous: bool = False
    possible_matches: list[dict[str, str]] = field(default_factory=list)

    @property
    def is_resolved(self) -> bool:
        """True if successfully mapped to a canonical service or category."""
        return bool(self.service_slug or (self.category_slug and self.match_level != ServiceMatchLevel.UNCONFIRMED))


# Natural language keyword mappings to canonical service slugs
KEYWORD_TO_SERVICE_MAP: list[tuple[re.Pattern, str, str]] = [
    # (Regex pattern, service_slug, category_slug)
    (re.compile(r"\b(split\s*ac\s*regular|ac\s*filter|ac\s*wash|split\s*ac)\b", re.I), "split-ac-regular-service", "ac-repair"),
    (re.compile(r"\b(foam\s*wash|jet\s*clean|deep\s*ac|deep\s*clean\s*ac)\b", re.I), "split-ac-deep-clean", "ac-repair"),
    (re.compile(r"\b(window\s*ac)\b", re.I), "window-ac-service", "ac-repair"),
    (re.compile(r"\b(gas\s*refill|gas\s*leak|ac\s*gas|r32|r410a|freon)\b", re.I), "ac-gas-refill", "ac-repair"),
    (re.compile(r"\b(ac\s*install|ac\s*uninstal|ac\s*relocat|ac\s*fitting)\b", re.I), "ac-installation-uninstallation", "ac-repair"),
    (re.compile(r"\b(ac\s*repair|air\s*condition|cooling)\b", re.I), None, "ac-repair"),

    (re.compile(r"\b(1\s*bhk|1bhk)\b", re.I), "full-home-deep-cleaning-1bhk", "home-cleaning"),
    (re.compile(r"\b(2\s*bhk|2bhk)\b", re.I), "full-home-deep-cleaning-2bhk", "home-cleaning"),
    (re.compile(r"\b(3\s*bhk|3bhk)\b", re.I), "full-home-deep-cleaning-3bhk", "home-cleaning"),
    (re.compile(r"\b(bathroom|toilet\s*clean|tile\s*descal)\b", re.I), "bathroom-deep-cleaning", "home-cleaning"),
    (re.compile(r"\b(kitchen|chimney|degreas)\b", re.I), "kitchen-deep-cleaning", "home-cleaning"),
    (re.compile(r"\b(sofa|carpet|upholstery)\b", re.I), "sofa-carpet-shampooing", "home-cleaning"),
    (re.compile(r"\b(cleaning|deep\s*clean|house\s*clean)\b", re.I), "full-home-deep-cleaning-1bhk", "home-cleaning"),

    (re.compile(r"\b(tap|faucet|shower)\b", re.I), "tap-shower-repair", "plumbing"),
    (re.compile(r"\b(flush|cistern)\b", re.I), "toilet-flush-repair", "plumbing"),
    (re.compile(r"\b(pipe\s*leak|drain|unclog|chok)\b", re.I), "pipe-leakage-drain-unclog", "plumbing"),
    (re.compile(r"\b(sump|overhead\s*tank|tank\s*clean)\b", re.I), "overhead-tank-cleaning", "plumbing"),
    (re.compile(r"\b(water\s*purifier|ro\s*inlet|ro\s*plumb)\b", re.I), "water-purifier-plumbing", "plumbing"),
    (re.compile(r"\b(plumber|plumbing)\b", re.I), None, "plumbing"),

    (re.compile(r"\b(switch|socket|mcb|plug)\b", re.I), "switch-socket-repair", "electrical"),
    (re.compile(r"\b(ceiling\s*fan|exhaust\s*fan|fan)\b", re.I), "ceiling-exhaust-fan-service", "electrical"),
    (re.compile(r"\b(light|chandelier|fixture|led)\b", re.I), "light-fixture-installation", "electrical"),
    (re.compile(r"\b(inverter|ups|battery\s*lead)\b", re.I), "inverter-ups-connection", "electrical"),
    (re.compile(r"\b(short\s*circuit|rewiring|tripping)\b", re.I), "short-circuit-rewiring", "electrical"),
    (re.compile(r"\b(electric|electrician)\b", re.I), None, "electrical"),

    (re.compile(r"\b(waterproofing|damp|dampness|seepage)\b", re.I), "waterproofing-dampness-treatment", "painting"),
    (re.compile(r"\b(exterior\s*paint|weatherproof)\b", re.I), "exterior-weatherproof-painting", "painting"),
    (re.compile(r"\b(repaint|touchup)\b", re.I), "interior-repaint", "painting"),
    (re.compile(r"\b(fresh\s*paint|interior\s*paint|painting|painter)\b", re.I), "interior-fresh-painting", "painting"),

    (re.compile(r"\b(termite|wood\s*borer)\b", re.I), "termite-control-drilling", "pest-control"),
    (re.compile(r"\b(bed\s*bug|mattress\s*bug)\b", re.I), "bed-bug-eradication", "pest-control"),
    (re.compile(r"\b(cockroach|ant|herbal\s*gel)\b", re.I), "cockroach-ant-treatment", "pest-control"),
    (re.compile(r"\b(rodent|rat|mouse)\b", re.I), "rodent-control", "pest-control"),
    (re.compile(r"\b(pest|pest\s*control)\b", re.I), "cockroach-ant-treatment", "pest-control"),

    (re.compile(r"\b(4000\s*l|4000l|4k\s*litres)\b", re.I), "tanker-4000-litres", "water-tanker"),
    (re.compile(r"\b(12000\s*l|12000l|12k\s*litres)\b", re.I), "tanker-12000-litres", "water-tanker"),
    (re.compile(r"\b(tanker|water\s*tanker|6000\s*l|6000l|water\s*supply)\b", re.I), "tanker-6000-litres", "water-tanker"),

    (re.compile(r"\b(bike|motorcycle|scooter|two\s*wheeler)\b", re.I), "vehicle-transport-two-wheeler", "packers-movers"),
    (re.compile(r"\b(1\s*bhk\s*shift|1bhk\s*shift)\b", re.I), "within-city-1bhk-shifting", "packers-movers"),
    (re.compile(r"\b(2\s*bhk\s*shift|2bhk\s*shift)\b", re.I), "within-city-2bhk-shifting", "packers-movers"),
    (re.compile(r"\b(3\s*bhk\s*shift|3bhk\s*shift)\b", re.I), "within-city-3bhk-shifting", "packers-movers"),
    (re.compile(r"\b(packers|movers|shifting|relocation)\b", re.I), "within-city-1bhk-shifting", "packers-movers"),

    (re.compile(r"\b(scrap|appliance|refrigerator\s*scrap|fridge\s*scrap)\b", re.I), "bulk-appliance-pickup", "e-waste"),
    (re.compile(r"\b(computer|laptop|monitor|server|it\s*scrap)\b", re.I), "it-computer-scrap-pickup", "e-waste"),
    (re.compile(r"\b(battery|phone\s*recycle|e-waste|electronic\s*waste)\b", re.I), "small-electronics-drop", "e-waste"),
]


class CatalogueResolver:
    """Resolves natural language queries and slugs to the canonical service catalogue."""

    AMBIGUOUS_GENERIC_KEYWORDS = {
        "repair", "repairs", "service", "services", "maintenance", "fix", "help",
        "contractor", "home service", "urban", "local help", "emergency help"
    }

    @classmethod
    def resolve(cls, query_text: str | None, db: Session | None = None) -> ResolvedCatalogueIntent:
        """Resolve a query string to a specific Service and/or ServiceCategory with confidence."""
        if not query_text or not query_text.strip():
            return ResolvedCatalogueIntent(
                category_slug="",
                category_name="",
                is_specific_service=False,
                search_keywords=[],
                match_level=ServiceMatchLevel.UNCONFIRMED,
                match_confidence=0.0,
                match_reason="Empty service query provided",
                is_ambiguous=False,
            )

        clean_text = query_text.strip().lower()
        slug_candidate = re.sub(r"[^a-z0-9\-]+", "-", clean_text).strip("-")

        # Check for overly broad or ambiguous generic terms
        if clean_text in cls.AMBIGUOUS_GENERIC_KEYWORDS or slug_candidate in cls.AMBIGUOUS_GENERIC_KEYWORDS:
            return ResolvedCatalogueIntent(
                category_slug="",
                category_name="",
                is_specific_service=False,
                search_keywords=[clean_text],
                match_level=ServiceMatchLevel.UNCONFIRMED,
                match_confidence=0.30,
                match_reason=f"Query '{query_text}' is ambiguous across multiple civic categories.",
                is_ambiguous=True,
                possible_matches=[
                    {"slug": "ac-repair", "name": "AC Repair"},
                    {"slug": "home-cleaning", "name": "Home Cleaning"},
                    {"slug": "plumbing", "name": "Plumbing"},
                    {"slug": "electrical", "name": "Electrical"},
                    {"slug": "painting", "name": "Painting"},
                    {"slug": "pest-control", "name": "Pest Control"},
                    {"slug": "water-tanker", "name": "Water Tanker"},
                ],
            )

        # 1. Database Resolution (if db session available)
        if db is not None:
            # A. Check exact service slug
            try:
                svc = db.query(Service).filter(Service.slug == slug_candidate).first()
                if not svc:
                    svc = db.query(Service).filter(Service.slug == clean_text).first()
                if svc:
                    return ResolvedCatalogueIntent(
                        service_id=svc.id,
                        service_slug=svc.slug,
                        service_name=svc.name,
                        category_id=svc.category_id,
                        category_slug=svc.category.slug if svc.category else "ac-repair",
                        category_name=svc.category.name if svc.category else "AC Repair",
                        is_specific_service=True,
                        search_keywords=[svc.name, svc.slug.replace("-", " ")],
                        match_level=ServiceMatchLevel.CONFIRMED,
                        match_confidence=1.0,
                        match_reason=f"Exact canonical match for '{svc.name}'",
                        is_ambiguous=False,
                    )

                # B. Check exact category slug
                cat = db.query(ServiceCategory).filter(ServiceCategory.slug == slug_candidate).first()
                if not cat:
                    cat = db.query(ServiceCategory).filter(ServiceCategory.slug == clean_text).first()
                if cat:
                    return ResolvedCatalogueIntent(
                        category_id=cat.id,
                        category_slug=cat.slug,
                        category_name=cat.name,
                        is_specific_service=False,
                        search_keywords=[cat.name, cat.slug.replace("-", " ")],
                        match_level=ServiceMatchLevel.CONFIRMED,
                        match_confidence=0.85,
                        match_reason=f"Exact match for category '{cat.name}'",
                        is_ambiguous=False,
                    )
            except SQLAlchemyError:
                # The catalogue migrations may not be applied yet.  Continue with
                # the checked-in catalogue; do not turn a schema mismatch into
                # invented provider data or a generic endpoint failure.
                db.rollback()
                logger.warning(
                    "NammaServe catalogue lookup failed; using static catalogue resolution only."
                )

        # 2. In-Memory Static Catalogue Resolution (works before migrations or in tests)
        # Check canonical service slugs directly
        for cat_slug, services in CANONICAL_SERVICES.items():
            for s in services:
                if s["slug"] == slug_candidate or s["slug"] == clean_text:
                    cat_name = cat_slug.replace("-", " ").title()
                    return ResolvedCatalogueIntent(
                        service_slug=s["slug"],
                        service_name=s["name"],
                        category_slug=cat_slug,
                        category_name=cat_name,
                        is_specific_service=True,
                        search_keywords=[s["name"], s["slug"].replace("-", " ")],
                        match_level=ServiceMatchLevel.CONFIRMED,
                        match_confidence=1.0,
                        match_reason=f"Exact canonical match for '{s['name']}'",
                        is_ambiguous=False,
                    )

        # Check canonical category slugs directly
        for cat in CANONICAL_CATEGORIES:
            if cat["slug"] == slug_candidate or cat["slug"] == clean_text:
                return ResolvedCatalogueIntent(
                    category_slug=cat["slug"],
                    category_name=cat["name"],
                    is_specific_service=False,
                    search_keywords=[cat["name"], cat["slug"].replace("-", " ")],
                    match_level=ServiceMatchLevel.CONFIRMED,
                    match_confidence=0.85,
                    match_reason=f"Exact match for category '{cat['name']}'",
                    is_ambiguous=False,
                )

        # 3. Regex / Keyword Mapping
        for pattern, mapped_service_slug, mapped_cat_slug in KEYWORD_TO_SERVICE_MAP:
            if pattern.search(clean_text):
                cat_name = mapped_cat_slug.replace("-", " ").title()
                if mapped_service_slug:
                    svc_name = mapped_service_slug.replace("-", " ").title()
                    services_for_cat = CANONICAL_SERVICES.get(mapped_cat_slug, [])
                    for s in services_for_cat:
                        if s["slug"] == mapped_service_slug:
                            svc_name = s["name"]
                            break
                    return ResolvedCatalogueIntent(
                        service_slug=mapped_service_slug,
                        service_name=svc_name,
                        category_slug=mapped_cat_slug,
                        category_name=cat_name,
                        is_specific_service=True,
                        search_keywords=[svc_name, clean_text],
                        match_level=ServiceMatchLevel.CONFIRMED,
                        match_confidence=0.90,
                        match_reason=f"Pattern match for canonical service '{svc_name}'",
                        is_ambiguous=False,
                    )
                else:
                    return ResolvedCatalogueIntent(
                        category_slug=mapped_cat_slug,
                        category_name=cat_name,
                        is_specific_service=False,
                        search_keywords=[cat_name, clean_text],
                        match_level=ServiceMatchLevel.PROBABLE,
                        match_confidence=0.65,
                        match_reason=f"Category pattern match for '{cat_name}'",
                        is_ambiguous=False,
                    )

        # Unmapped or custom category: preserve query_text as category_slug without fabricating AC Repair
        return ResolvedCatalogueIntent(
            category_slug=slug_candidate,
            category_name=slug_candidate.replace("-", " ").title(),
            is_specific_service=False,
            search_keywords=[clean_text],
            match_level=ServiceMatchLevel.UNCONFIRMED,
            match_confidence=0.20,
            match_reason=f"Query '{query_text}' could not be resolved confidently to catalogue.",
            is_ambiguous=False,
        )
