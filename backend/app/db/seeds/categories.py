"""Idempotent seed script for NammaServe canonical service categories.

Canonical categories:
- ac-repair
- home-cleaning
- plumbing
- electrical
- painting
- pest-control
- water-tanker
- packers-movers
- e-waste
"""
import logging
from uuid import uuid4
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.nammaserve import ServiceCategory

logger = logging.getLogger(__name__)

CANONICAL_CATEGORIES = [
    {
        "slug": "ac-repair",
        "name": "AC Repair",
        "description": "AC servicing, installation, gas refill, and maintenance services.",
        "icon_name": "snowflake",
    },
    {
        "slug": "home-cleaning",
        "name": "Home Cleaning",
        "description": "Deep home cleaning, bathroom, kitchen, and sofa cleaning.",
        "icon_name": "broom",
    },
    {
        "slug": "plumbing",
        "name": "Plumbing",
        "description": "Pipe repair, leak fixing, tap installation, and drainage solutions.",
        "icon_name": "wrench",
    },
    {
        "slug": "electrical",
        "name": "Electrical",
        "description": "Wiring, switchboard repair, appliance installation, and fuse replacement.",
        "icon_name": "zap",
    },
    {
        "slug": "painting",
        "name": "Painting",
        "description": "Interior and exterior wall painting, waterproofing, and putty work.",
        "icon_name": "paint-brush",
    },
    {
        "slug": "pest-control",
        "name": "Pest Control",
        "description": "Termite, cockroach, rodent, and general pest management treatments.",
        "icon_name": "shield-alert",
    },
    {
        "slug": "water-tanker",
        "name": "Water Tanker",
        "description": "Private water supply delivery (4000L, 6000L, 12000L tankers).",
        "icon_name": "droplet",
    },
    {
        "slug": "packers-movers",
        "name": "Packers & Movers",
        "description": "Local house shifting, office relocation, and packing assistance.",
        "icon_name": "truck",
    },
    {
        "slug": "e-waste",
        "name": "E-Waste",
        "description": "Electronic scrap collection, recycling, and appliance disposal.",
        "icon_name": "recycle",
    },
]


def seed_categories(db: Session) -> dict[str, int]:
    """Seed canonical categories into service_categories idempotently."""
    inserted = 0
    existing = 0

    for cat_data in CANONICAL_CATEGORIES:
        slug = cat_data["slug"]
        record = db.query(ServiceCategory).filter(ServiceCategory.slug == slug).first()

        if record is None:
            new_cat = ServiceCategory(
                id=str(uuid4()),
                slug=slug,
                name=cat_data["name"],
                description=cat_data["description"],
                icon_name=cat_data["icon_name"],
                is_active=True,
            )
            db.add(new_cat)
            inserted += 1
        else:
            # Update attributes to ensure consistency
            record.name = cat_data["name"]
            record.description = cat_data["description"]
            record.icon_name = cat_data["icon_name"]
            record.is_active = True
            existing += 1

    db.commit()
    return {"inserted": inserted, "existing": existing, "total": len(CANONICAL_CATEGORIES)}


if __name__ == "__main__":
    db = SessionLocal()
    try:
        result = seed_categories(db)
        print(f"Categories seeding completed: {result['inserted']} inserted, {result['existing']} updated/existing.")
    finally:
        db.close()
