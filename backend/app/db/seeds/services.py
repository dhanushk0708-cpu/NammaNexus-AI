"""Idempotent seed script for NammaServe individual catalogue services.

Linked to the 9 canonical categories:
- ac-repair
- home-cleaning
- plumbing
- electrical
- painting
- pest-control
- water-tanker
- packers-movers
- e-waste

Strictly authentic catalogue definitions with no fabricated providers, prices, or reviews.
"""
import logging
from uuid import uuid4
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.nammaserve import Service, ServiceCategory

logger = logging.getLogger(__name__)

CANONICAL_SERVICES: dict[str, list[dict[str, str]]] = {
    "ac-repair": [
        {
            "slug": "split-ac-regular-service",
            "name": "Split AC Regular Service",
            "description": "Air filter cleanup, cooling coil wash, drain tray flushing, and blower inspection.",
            "unit": "per AC unit",
        },
        {
            "slug": "split-ac-deep-clean",
            "name": "Split AC Deep Foam / Jet Clean",
            "description": "High-pressure jet wash with coil cleaning foam and outdoor condenser coil degreasing.",
            "unit": "per AC unit",
        },
        {
            "slug": "window-ac-service",
            "name": "Window AC Servicing",
            "description": "Disassembly, filter wash, condenser fin flushing, and fan motor lubrication.",
            "unit": "per AC unit",
        },
        {
            "slug": "ac-gas-refill",
            "name": "AC Gas Leak Testing & Refill",
            "description": "Nitrogen pressure hold test, leak identification, vacuum evacuation, and gas recharging (R32 / R410A / R22).",
            "unit": "per refill",
        },
        {
            "slug": "ac-installation-uninstallation",
            "name": "AC Installation & Relocation",
            "description": "Wall bracket mounting, indoor/outdoor unit installation, copper flare connection, and testing.",
            "unit": "per unit",
        },
    ],
    "home-cleaning": [
        {
            "slug": "full-home-deep-cleaning-1bhk",
            "name": "Full Home Deep Cleaning (1 BHK)",
            "description": "Single bedroom apartment intensive cleaning: floor scrubbing, kitchen degreasing, bathroom descaling, and balcony wash.",
            "unit": "per apartment",
        },
        {
            "slug": "full-home-deep-cleaning-2bhk",
            "name": "Full Home Deep Cleaning (2 BHK)",
            "description": "Two bedroom apartment deep cleaning including two bathrooms, kitchen chimney exterior, window tracks, and living area.",
            "unit": "per apartment",
        },
        {
            "slug": "full-home-deep-cleaning-3bhk",
            "name": "Full Home Deep Cleaning (3 BHK)",
            "description": "Three bedroom apartment deep cleaning with mechanized floor scrubbers, tile buffing, and chemical sanitization.",
            "unit": "per apartment",
        },
        {
            "slug": "bathroom-deep-cleaning",
            "name": "Bathroom Deep Cleaning & Descaling",
            "description": "Hard water stain removal from tiles and glass partitions, WC descaling, tap buffing, and exhaust cleaning.",
            "unit": "per bathroom",
        },
        {
            "slug": "kitchen-deep-cleaning",
            "name": "Kitchen Deep Cleaning & Degreasing",
            "description": "Stovetop, tile backsplash, exhaust fan, chimney surface, cabinet interiors, and countertop degreasing.",
            "unit": "per kitchen",
        },
        {
            "slug": "sofa-carpet-shampooing",
            "name": "Sofa & Upholstery Wet Shampooing",
            "description": "Dry vacuuming, fabric foam extraction, anti-allergen treatment, and moisture removal for fabric sofas and carpets.",
            "unit": "per seat",
        },
    ],
    "plumbing": [
        {
            "slug": "tap-shower-repair",
            "name": "Tap, Faucet & Shower Repair",
            "description": "Fixing leaking or dripping faucets, cartridge/spindle replacement, showerhead descaling, and washer replacement.",
            "unit": "per fitting",
        },
        {
            "slug": "toilet-flush-repair",
            "name": "Toilet Flush & Cistern Repair",
            "description": "Dual-flush valve repair, siphon mechanism replacement, ball valve adjustment, and water inlet leakage resolution.",
            "unit": "per toilet",
        },
        {
            "slug": "pipe-leakage-drain-unclog",
            "name": "Pipe Leakage & Drain Unclogging",
            "description": "Clearing choked kitchen sinks, bathroom floor traps, and soil pipe leaks using mechanical snakes and pressure jetting.",
            "unit": "per drain/pipe",
        },
        {
            "slug": "overhead-tank-cleaning",
            "name": "Overhead & Sump Water Tank Cleaning",
            "description": "Complete dewatering, sludge vacuum removal, rotary brush scrub, high-pressure jet wash, and antibacterial UV treatment.",
            "unit": "per tank",
        },
        {
            "slug": "water-purifier-plumbing",
            "name": "Water Purifier (RO) Inlet Plumbing",
            "description": "Direct supply diverter valve installation, dedicated angle valve plumbing, and drain line routing.",
            "unit": "per installation",
        },
    ],
    "electrical": [
        {
            "slug": "switch-socket-repair",
            "name": "Switch, Socket & MCB Replacement",
            "description": "Burned switch replacement, modular 6A/16A socket installation, miniature circuit breaker (MCB) troubleshooting.",
            "unit": "per point",
        },
        {
            "slug": "ceiling-exhaust-fan-service",
            "name": "Ceiling & Exhaust Fan Installation/Repair",
            "description": "Motor capacitor replacement, blade balancing, downrod mounting, and wall regulator troubleshooting.",
            "unit": "per fan",
        },
        {
            "slug": "light-fixture-installation",
            "name": "Light Fixture & LED Installation",
            "description": "Batten fitting, cove light wiring, decorative wall sconce installation, and chandelier ceiling mounting.",
            "unit": "per fixture",
        },
        {
            "slug": "inverter-ups-connection",
            "name": "Inverter & UPS Wiring Setup",
            "description": "Battery lead connection, home inverter phase separation wiring, changeover switch mounting, and earthing check.",
            "unit": "per setup",
        },
        {
            "slug": "short-circuit-rewiring",
            "name": "Short Circuit Inspection & Rewiring",
            "description": "Megger insulation resistance testing, neutral fault identification, and conduit wiring replacement.",
            "unit": "per room",
        },
    ],
    "painting": [
        {
            "slug": "interior-fresh-painting",
            "name": "Interior Fresh Wall Painting",
            "description": "Two coats acrylic putty, one coat primer, and two coats premium washable emulsion paint.",
            "unit": "per sq ft",
        },
        {
            "slug": "interior-repaint",
            "name": "Interior Repainting & Touchup",
            "description": "Surface sanding, crack filling, primer spot coat, and two coats of acrylic emulsion.",
            "unit": "per sq ft",
        },
        {
            "slug": "exterior-weatherproof-painting",
            "name": "Exterior Weatherproof Painting",
            "description": "Power washing, exterior acrylic primer, and two coats of elastomeric anti-fungal paint.",
            "unit": "per sq ft",
        },
        {
            "slug": "waterproofing-dampness-treatment",
            "name": "Wall Dampness & Waterproofing Treatment",
            "description": "Polymer-modified cementitious coating, fiber mesh crack repair, and damp-proof chemical barrier.",
            "unit": "per sq ft",
        },
    ],
    "pest-control": [
        {
            "slug": "cockroach-ant-treatment",
            "name": "Cockroach & Ant Herbal Gel Treatment",
            "description": "Odorless food-grade gel application in kitchen hinges, electrical boards, and skirting edges.",
            "unit": "per home",
        },
        {
            "slug": "termite-control-drilling",
            "name": "Anti-Termite Drill-Fill-Seal Treatment",
            "description": "Drilling holes along wall baseboards, termiticide chemical injection under pressure, and mortar sealing.",
            "unit": "per linear ft",
        },
        {
            "slug": "bed-bug-eradication",
            "name": "Bed Bug Multi-Stage Eradication",
            "description": "Two-visit insecticide spray treatment on mattress seams, wooden slats, headboards, and wall joints.",
            "unit": "per bedroom",
        },
        {
            "slug": "rodent-control",
            "name": "Rodent Trapping & Management",
            "description": "Tamper-resistant bait stations, sticky glue pads along foraging paths, and exterior entry inspection.",
            "unit": "per setup",
        },
    ],
    "water-tanker": [
        {
            "slug": "tanker-4000-litres",
            "name": "4,000 Litres Water Tanker",
            "description": "Potable or domestic water delivery via 4,000-litre private tanker for residential sumps.",
            "unit": "per tanker load",
        },
        {
            "slug": "tanker-6000-litres",
            "name": "6,000 Litres Water Tanker",
            "description": "Standard 6,000-litre tanker delivery suitable for apartments and medium residential sumps.",
            "unit": "per tanker load",
        },
        {
            "slug": "tanker-12000-litres",
            "name": "12,000 Litres Water Tanker",
            "description": "Heavy commercial volume tanker supply for large communities, institutions, and bulk storage.",
            "unit": "per tanker load",
        },
    ],
    "packers-movers": [
        {
            "slug": "within-city-1bhk-shifting",
            "name": "1 BHK Within-City Shifting",
            "description": "Disassembly of basic furniture, bubble wrapping, loading into mini truck, transit, and unloading.",
            "unit": "per shift",
        },
        {
            "slug": "within-city-2bhk-shifting",
            "name": "2 BHK Within-City Shifting",
            "description": "Multi-layer packing of electronic appliances, wardrobe packing, 14-ft container transport, and placement.",
            "unit": "per shift",
        },
        {
            "slug": "within-city-3bhk-shifting",
            "name": "3 BHK Within-City Shifting",
            "description": "Full household packing, heavy furniture dismantling, transit insurance guidance, and reassembly.",
            "unit": "per shift",
        },
        {
            "slug": "vehicle-transport-two-wheeler",
            "name": "Two-Wheeler Local Relocation",
            "description": "Corrugated wrapping of motorcycle or scooter, ramp loading with secure tie-down, and delivery.",
            "unit": "per vehicle",
        },
    ],
    "e-waste": [
        {
            "slug": "bulk-appliance-pickup",
            "name": "Large Appliance E-Waste Pickup",
            "description": "Doorstep pickup and authorized recycling of scrap refrigerators, washing machines, and ACs.",
            "unit": "per pickup",
        },
        {
            "slug": "it-computer-scrap-pickup",
            "name": "IT & Computer Hardware Scrap Collection",
            "description": "Environmentally safe disposal of motherboards, towers, monitors, laptops, and networking switches.",
            "unit": "per pickup",
        },
        {
            "slug": "small-electronics-drop",
            "name": "Small Electronics & Battery Disposal",
            "description": "Certified recycling of feature phones, smartphones, power banks, chargers, and household batteries.",
            "unit": "per collection",
        },
    ],
}


def seed_services(db: Session) -> dict[str, int]:
    """Seed canonical individual services idempotently under existing categories."""
    inserted = 0
    updated = 0
    skipped_no_cat = 0

    for cat_slug, services_list in CANONICAL_SERVICES.items():
        category = db.query(ServiceCategory).filter(ServiceCategory.slug == cat_slug).first()
        if not category:
            logger.warning("Category '%s' not found in database. Skipping services.", cat_slug)
            skipped_no_cat += len(services_list)
            continue

        for svc_data in services_list:
            slug = svc_data["slug"]
            record = db.query(Service).filter(Service.slug == slug).first()

            if record is None:
                new_service = Service(
                    id=str(uuid4()),
                    category_id=category.id,
                    slug=slug,
                    name=svc_data["name"],
                    description=svc_data["description"],
                    unit=svc_data["unit"],
                    is_active=True,
                )
                db.add(new_service)
                inserted += 1
            else:
                record.category_id = category.id
                record.name = svc_data["name"]
                record.description = svc_data["description"]
                record.unit = svc_data["unit"]
                record.is_active = True
                updated += 1

    db.commit()
    total = sum(len(items) for items in CANONICAL_SERVICES.values())
    return {
        "inserted": inserted,
        "updated": updated,
        "skipped_no_cat": skipped_no_cat,
        "total": total,
    }


if __name__ == "__main__":
    db = SessionLocal()
    try:
        res = seed_services(db)
        print(
            f"Service catalogue seeding completed: {res['inserted']} inserted, "
            f"{res['updated']} updated, {res['skipped_no_cat']} skipped (no category)."
        )
    finally:
        db.close()
