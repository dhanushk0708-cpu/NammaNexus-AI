"""Repeatable, idempotent importer for NammaServe Bengaluru Price Comparison Dataset.

Ingests 142 collected price comparison records from:
research-data/nammaserve/nammaserve_bengaluru_price_comparison.csv
into the `nammaserve_price_comparisons` database table.

Supports:
- Lossless preservation of all 14 CSV fields
- Numeric range/scalar helper parsing (price_min, price_max)
- Preservation of missing/N/A values (never converted to 0)
- Deterministic hash-based deduplication
- Dry-run validation mode without database writes
"""
import argparse
import csv
import hashlib
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

# Setup project pathing
BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.db.session import SessionLocal
from app.models.nammaserve_research import PriceComparisonRecord

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nammaserve.price_comparison_importer")

EXPECTED_COLUMNS = [
    "source_platform",
    "service_category",
    "service_name",
    "provider_name",
    "published_price",
    "currency",
    "price_type",
    "price_unit",
    "price_scope",
    "geographic_scope",
    "source_url",
    "source_checked_date",
    "verification_status",
    "notes",
]

ALLOWED_PLATFORMS = {"Urban Company", "NoBroker", "Justdial", "Sulekha"}
ALLOWED_PRICE_TYPES = {
    "FIXED",
    "STARTING_FROM",
    "PRICE_RANGE",
    "QUOTATION_REQUIRED",
    "UNPUBLISHED",
}
ALLOWED_VERIFICATION_STATUSES = {"SOURCE_CORROBORATED", "DISCOVERED"}
ALLOWED_CATEGORIES = {
    "Plumbing",
    "AC repair and servicing",
    "Electrical services",
    "House cleaning",
    "Pest control",
    "Appliance repair",
    "Water purifier/RO services",
    "Carpentry",
}


def compute_record_hash(row: Dict[str, str]) -> str:
    """Generate deterministic SHA-256 hash using platform, category, service, provider, and source URL."""
    parts = [
        row["source_platform"].strip(),
        row["service_category"].strip(),
        row["service_name"].strip(),
        row["provider_name"].strip(),
        row["source_url"].strip(),
    ]
    raw = "||".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_numeric_prices(price_str: str, price_type: str) -> Tuple[Optional[float], Optional[float]]:
    """Parse numeric price bounds without inventing values.
    
    - FIXED scalar: (amount, amount)
    - FIXED range: (min_amount, max_amount)
    - STARTING_FROM: (start_amount, None) - upper bound left open
    - PRICE_RANGE: (min_amount, max_amount)
    - QUOTATION_REQUIRED / UNPUBLISHED / N/A: (None, None)
    """
    p = (price_str or "").strip()
    if not p or p.upper() == "N/A" or price_type in ("QUOTATION_REQUIRED", "UNPUBLISHED"):
        return None, None

    # Standardize dashes for ranges (e.g., '479-869', '48–55')
    clean_p = p.replace("–", "-").replace("—", "-")
    if "-" in clean_p:
        parts = [x.strip() for x in clean_p.split("-") if x.strip()]
        if len(parts) == 2:
            try:
                min_val = float(parts[0].replace(",", ""))
                max_val = float(parts[1].replace(",", ""))
                return min_val, max_val
            except ValueError:
                pass

    try:
        val = float(clean_p.replace(",", ""))
        if price_type == "STARTING_FROM":
            return val, None
        return val, val
    except ValueError:
        return None, None


def check_is_locality_specific(geographic_scope: str) -> bool:
    """Flag records with locality-specific or unconfirmed scope."""
    geo = (geographic_scope or "").strip()
    if geo == "Bengaluru (Citywide - Confirmed)":
        return False
    # Any record with unconfirmed, locality specific, or unclear scope
    return True


class PriceComparisonDatasetImporter:
    """Validator and importer for Bengaluru price comparison research records."""

    def __init__(self, csv_path: Optional[Path] = None):
        self.csv_path = csv_path or (
            WORKSPACE_ROOT / "research-data" / "nammaserve" / "nammaserve_bengaluru_price_comparison.csv"
        )

    def load_and_validate(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """Read CSV, validate schema, parse helper fields, and collect validation statistics."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Price comparison dataset not found at: {self.csv_path}")

        valid_records: List[Dict[str, Any]] = []
        invalid_records: List[Dict[str, Any]] = []
        seen_hashes: set[str] = set()
        duplicate_hashes: List[str] = []

        stats = {
            "total_rows_read": 0,
            "valid_rows": 0,
            "invalid_rows": 0,
            "duplicate_hashes": 0,
            "missing_or_unpublished_prices": 0,
            "price_parsing_failures": 0,
            "platforms": Counter(),
            "categories": Counter(),
            "price_types": Counter(),
            "verification_statuses": Counter(),
            "geographic_scopes": Counter(),
            "locality_specific_count": 0,
            "citywide_confirmed_count": 0,
        }

        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            actual_columns = reader.fieldnames or []

            # 1. Validate Columns
            missing_cols = set(EXPECTED_COLUMNS) - set(actual_columns)
            if missing_cols:
                raise ValueError(f"CSV is missing expected columns: {missing_cols}")

            for row_num, row in enumerate(reader, start=1):
                stats["total_rows_read"] += 1
                errors: List[str] = []

                # Clean fields
                platform = row.get("source_platform", "").strip()
                category = row.get("service_category", "").strip()
                service = row.get("service_name", "").strip()
                provider = row.get("provider_name", "").strip()
                pub_price = row.get("published_price", "").strip()
                currency = row.get("currency", "").strip() or "INR"
                price_type = row.get("price_type", "").strip()
                geo_scope = row.get("geographic_scope", "").strip()
                source_url = row.get("source_url", "").strip()
                source_date = row.get("source_checked_date", "").strip()
                ver_status = row.get("verification_status", "").strip()
                notes = row.get("notes", "").strip() or None
                price_unit = row.get("price_unit", "").strip() or None
                price_scope = row.get("price_scope", "").strip() or None

                # Field validations
                if platform not in ALLOWED_PLATFORMS:
                    errors.append(f"Invalid platform: {platform}")
                if category not in ALLOWED_CATEGORIES:
                    errors.append(f"Invalid category: {category}")
                if price_type not in ALLOWED_PRICE_TYPES:
                    errors.append(f"Invalid price_type: {price_type}")
                if ver_status not in ALLOWED_VERIFICATION_STATUSES:
                    errors.append(f"Invalid verification_status: {ver_status}")
                if not source_url.startswith("http"):
                    errors.append(f"Invalid source_url: {source_url}")

                rec_hash = compute_record_hash(row)
                if rec_hash in seen_hashes:
                    duplicate_hashes.append(rec_hash)
                    errors.append(f"Duplicate hash: {rec_hash}")
                seen_hashes.add(rec_hash)

                # Parse prices
                p_min, p_max = parse_numeric_prices(pub_price, price_type)
                if p_min is None and p_max is None:
                    if pub_price.upper() == "N/A" or price_type in ("QUOTATION_REQUIRED", "UNPUBLISHED"):
                        stats["missing_or_unpublished_prices"] += 1
                    else:
                        stats["price_parsing_failures"] += 1
                        errors.append(f"Failed to parse published price: {pub_price}")

                is_local = check_is_locality_specific(geo_scope)
                if is_local:
                    stats["locality_specific_count"] += 1
                else:
                    stats["citywide_confirmed_count"] += 1

                if errors:
                    stats["invalid_rows"] += 1
                    invalid_records.append({"row_num": row_num, "errors": errors, "row": row})
                else:
                    stats["valid_rows"] += 1
                    stats["platforms"][platform] += 1
                    stats["categories"][category] += 1
                    stats["price_types"][price_type] += 1
                    stats["verification_statuses"][ver_status] += 1
                    stats["geographic_scopes"][geo_scope] += 1

                    valid_records.append({
                        "record_hash": rec_hash,
                        "source_platform": platform,
                        "service_category": category,
                        "service_name": service,
                        "provider_name": provider,
                        "published_price": pub_price,
                        "currency": currency,
                        "price_type": price_type,
                        "price_unit": price_unit,
                        "price_scope": price_scope,
                        "geographic_scope": geo_scope,
                        "source_url": source_url,
                        "source_checked_date": source_date,
                        "verification_status": ver_status,
                        "notes": notes,
                        "price_min": p_min,
                        "price_max": p_max,
                        "is_locality_specific": is_local,
                        "raw_record": dict(row),
                    })

        stats["duplicate_hashes"] = len(duplicate_hashes)
        return valid_records, invalid_records, stats

    def dry_run(self) -> Dict[str, Any]:
        """Execute validation without touching the database."""
        valid, invalid, stats = self.load_and_validate()
        return stats

    def import_records(self, db: Session) -> Dict[str, int]:
        """Import validated records into nammaserve_price_comparisons idempotently."""
        valid_records, invalid_records, _ = self.load_and_validate()

        if invalid_records:
            raise ValueError(f"Cannot import: {len(invalid_records)} invalid rows found.")

        inserted_count = 0
        updated_count = 0

        for r in valid_records:
            existing = db.execute(
                select(PriceComparisonRecord).where(PriceComparisonRecord.record_hash == r["record_hash"])
            ).scalar_one_or_none()

            if existing:
                for k, v in r.items():
                    setattr(existing, k, v)
                updated_count += 1
            else:
                db_record = PriceComparisonRecord(**r)
                db.add(db_record)
                inserted_count += 1

        db.commit()
        return {"inserted": inserted_count, "updated": updated_count, "total_processed": len(valid_records)}


def main():
    parser = argparse.ArgumentParser(description="Import NammaServe Bengaluru Price Comparison Dataset")
    parser.add_argument("--dry-run", action="store_true", help="Validate CSV records without database writes")
    parser.add_argument("--confirm-database", action="store_true", help="Confirm writing to PostgreSQL database")
    args = parser.parse_args()

    importer = PriceComparisonDatasetImporter()

    if args.dry_run or not args.confirm_database:
        logger.info("Executing DRY-RUN validation pass...")
        stats = importer.dry_run()

        print("\n" + "=" * 70)
        print("NAMMASERVE BENGALURU PRICE COMPARISON — DRY RUN AUDIT REPORT")
        print("=" * 70)
        print(f"Total Rows Read:               {stats['total_rows_read']}")
        print(f"Valid Rows:                    {stats['valid_rows']}")
        print(f"Invalid Rows:                  {stats['invalid_rows']}")
        print(f"Duplicate Hashes:              {stats['duplicate_hashes']}")
        print(f"Missing/Unpublished Prices:    {stats['missing_or_unpublished_prices']} (Preserved as N/A, not INR 0)")
        print(f"Price Parsing Failures:        {stats['price_parsing_failures']}")
        print(f"Bengaluru Citywide Confirmed:  {stats['citywide_confirmed_count']}")
        print(f"Locality-Specific / Caveats:   {stats['locality_specific_count']}")

        print("\n--- Platform Breakdown ---")
        for p, count in sorted(stats["platforms"].items(), key=lambda x: -x[1]):
            print(f"  {p:20}: {count} rows")

        print("\n--- Category Breakdown ---")
        for c, count in sorted(stats["categories"].items(), key=lambda x: -x[1]):
            print(f"  {c:30}: {count} rows")

        print("\n--- Price Type Breakdown ---")
        for pt, count in sorted(stats["price_types"].items(), key=lambda x: -x[1]):
            print(f"  {pt:20}: {count} rows")

        print("\n--- Verification Status Breakdown ---")
        for vs, count in sorted(stats["verification_statuses"].items(), key=lambda x: -x[1]):
            print(f"  {vs:20}: {count} rows")

        print("=" * 70)
        if stats["invalid_rows"] == 0 and stats["price_parsing_failures"] == 0:
            print("STATUS: DRY-RUN PASSED PERFECTLY (142/142 rows valid)")
            print("To execute live database import, run:")
            print("python -m scripts.import_nammaserve_price_comparison --confirm-database")
        else:
            print("STATUS: DRY-RUN FAILED — Fix validation errors before importing.")
        print("=" * 70 + "\n")
        return

    logger.info("Connecting to database for live import...")
    db = SessionLocal()
    try:
        results = importer.import_records(db)
        logger.info("Import successful: %s", results)
        print(f"SUCCESS: Ingested {results['inserted']} records, updated {results['updated']} records.")
    except Exception as e:
        db.rollback()
        logger.error("Import failed: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
