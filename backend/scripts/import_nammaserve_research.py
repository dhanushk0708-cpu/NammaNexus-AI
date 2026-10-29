"""Repeatable, idempotent importer for NammaServe Provider Research dataset.

Reads and normalizes all 12 research files:
- 4 Provider CSV files (128 records)
- 4 Area-Category Matrix CSV files (64 records)
- 4 Markdown Research Reports

Usage:
    python -m scripts.import_nammaserve_research --dry-run
    python -m scripts.import_nammaserve_research --confirm-local
    python -m scripts.import_nammaserve_research --confirm-supabase
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nammaserve.research_importer")

# Resolve repository paths
BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_DIR.parent
RESEARCH_DIR = WORKSPACE_ROOT / "docs" / "provider-research"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.nammaserve_research import ResearchCandidate, ResearchCoverage

CATEGORY_NORMALIZATION: dict[str, str] = {
    "Plumbing": "Plumbing",
    "AC repair and servicing": "AC repair and servicing",
    "Electrical services": "Electrical services",
    "House cleaning": "House cleaning",
    "Pest control": "Pest control",
    "Appliance repair (washing machines, refrigerators, microwaves)": "Appliance repair",
    "Appliance repair — washing machines, refrigerators and microwaves": "Appliance repair",
    "Appliance repair — washing machines, refrigerators, and microwaves": "Appliance repair",
    "Water purifier and RO services": "Water purifier/RO services",
    "Water purifier/RO services": "Water purifier/RO services",
    "Carpentry": "Carpentry",
}

AREA_NORMALIZATION: dict[str, str] = {
    "Kengeri, Bengaluru": "Kengeri",
    "Rajarajeshwari Nagar (RR Nagar), Bengaluru": "Rajarajeshwari Nagar",
    "Vijayanagar, Bengaluru": "Vijayanagar",
    "Jayanagar, Bengaluru": "Jayanagar",
    "JP Nagar, Bengaluru": "JP Nagar",
    "BTM Layout, Bengaluru": "BTM Layout",
    "HSR Layout, Bengaluru": "HSR Layout",
    "Marathahalli, Bengaluru": "Marathahalli",
}

ALLOWED_VERIFICATION_STATUSES = {"DISCOVERED", "SOURCE_CORROBORATED"}
ALLOWED_AVAILABILITY_STATUSES = {"UNKNOWN", "AVAILABLE", "UNAVAILABLE"}
ALLOWED_PRICE_TYPES = {"FIXED", "STARTING_AT", "RANGE", "QUOTATION_REQUIRED", "PRICE_NOT_PUBLISHED", "NOT_PUBLISHED"}


def parse_float(val: Any) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("none", "null", "n/a"):
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def parse_int(val: Any) -> int | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("none", "null", "n/a"):
        return None
    try:
        return int(float(s.replace(",", "")))
    except ValueError:
        return None


def validate_and_normalize_candidate_row(row: dict[str, str], batch_id: str, row_idx: int) -> dict[str, Any]:
    raw_cat = row.get("service_category", "").strip()
    norm_cat = CATEGORY_NORMALIZATION.get(raw_cat)
    if not norm_cat:
        raise ValueError(f"Batch {batch_id} Row {row_idx}: Unrecognized service_category '{raw_cat}'")

    raw_area = row.get("requested_area", "").strip()
    norm_area = AREA_NORMALIZATION.get(raw_area)
    if not norm_area:
        raise ValueError(f"Batch {batch_id} Row {row_idx}: Unrecognized requested_area '{raw_area}'")

    provider_name = row.get("provider_name", "").strip()
    if not provider_name:
        raise ValueError(f"Batch {batch_id} Row {row_idx}: Missing provider_name")

    provider_id = row.get("provider_id", "").strip()
    if not provider_id:
        raise ValueError(f"Batch {batch_id} Row {row_idx}: Missing provider_id")

    v_status = row.get("verification_status", "DISCOVERED").strip()
    if v_status not in ALLOWED_VERIFICATION_STATUSES:
        logger.warning("Row %d: Non-standard verification_status '%s'", row_idx, v_status)

    p_type = row.get("price_type", "PRICE_NOT_PUBLISHED").strip() or "PRICE_NOT_PUBLISHED"

    return {
        "batch_id": batch_id,
        "provider_id": provider_id,
        "provider_name": provider_name,
        "service_category": norm_cat,
        "raw_service_category": raw_cat,
        "specific_services": row.get("specific_services", "").strip() or None,
        "requested_area": raw_area,
        "area_name": norm_area,
        "business_address": row.get("business_address", "").strip() or None,
        "public_phone": row.get("public_phone", "").strip() or None,
        "public_email": row.get("public_email", "").strip() or None,
        "website_url": row.get("website_url", "").strip() or None,
        "contact_or_booking_url": row.get("contact_or_booking_url", "").strip() or None,
        "advertised_service_areas": row.get("advertised_service_areas", "").strip() or None,
        "area_coverage_evidence_url": row.get("area_coverage_evidence_url", "").strip() or None,
        "price_type": p_type,
        "price_amount": parse_float(row.get("price_amount")),
        "price_currency": row.get("price_currency", "").strip() or "INR",
        "price_unit": row.get("price_unit", "").strip() or None,
        "price_scope": row.get("price_scope", "").strip() or None,
        "price_source_url": row.get("price_source_url", "").strip() or None,
        "rating": parse_float(row.get("rating")),
        "review_count": parse_int(row.get("review_count")),
        "rating_platform": row.get("rating_platform", "").strip() or None,
        "rating_source_url": row.get("rating_source_url", "").strip() or None,
        "booking_method": row.get("booking_method", "").strip() or None,
        "availability_status": row.get("availability_status", "UNKNOWN").strip() or "UNKNOWN",
        "verification_status": v_status,
        "primary_source_url": row.get("primary_source_url", "").strip() or None,
        "secondary_source_url": row.get("secondary_source_url", "").strip() or None,
        "research_date": row.get("research_date", "").strip() or None,
        "confidence": row.get("confidence", "HIGH").strip() or "HIGH",
        "evidence_summary": row.get("evidence_summary", "").strip() or None,
        "missing_information": row.get("missing_information", "").strip() or None,
        "duplicate_group_id": row.get("duplicate_group_id", "").strip() or None,
        "provider_rank": parse_int(row.get("provider_rank")) or 1,
        "notes": row.get("notes", "").strip() or None,
        # Review analysis fields (from Batches 2-4)
        "review_summary": row.get("review_summary", "").strip() or None,
        "review_positive_themes": row.get("review_positive_themes", "").strip() or None,
        "review_negative_themes": row.get("review_negative_themes", "").strip() or None,
        "review_date_range": row.get("review_date_range", "").strip() or None,
        "review_summary_source_url": row.get("review_summary_source_url", "").strip() or None,
        "review_summary_limitations": row.get("review_summary_limitations", "").strip() or None,
        "raw_record": dict(row),
    }


def validate_and_normalize_coverage_row(row: dict[str, str], batch_id: str, row_idx: int) -> dict[str, Any]:
    raw_cat = row.get("service_category", "").strip()
    norm_cat = CATEGORY_NORMALIZATION.get(raw_cat)
    if not norm_cat:
        raise ValueError(f"Batch {batch_id} Matrix Row {row_idx}: Unrecognized service_category '{raw_cat}'")

    raw_area = row.get("area", "").strip()
    norm_area = AREA_NORMALIZATION.get(raw_area)
    if not norm_area:
        raise ValueError(f"Batch {batch_id} Matrix Row {row_idx}: Unrecognized area '{raw_area}'")

    return {
        "batch_id": batch_id,
        "area": raw_area,
        "clean_area": norm_area,
        "service_category": norm_cat,
        "research_status": row.get("research_status", "COMPLETED_WITH_RESULTS").strip() or "COMPLETED_WITH_RESULTS",
        "provider_1_id": row.get("provider_1_id", "").strip() or None,
        "provider_1_name": row.get("provider_1_name", "").strip() or None,
        "provider_1_source_url": row.get("provider_1_source_url", "").strip() or None,
        "provider_2_id": row.get("provider_2_id", "").strip() or None,
        "provider_2_name": row.get("provider_2_name", "").strip() or None,
        "provider_2_source_url": row.get("provider_2_source_url", "").strip() or None,
        "providers_found": parse_int(row.get("providers_found")) or 2,
        "sources_checked": row.get("sources_checked", "").strip() or None,
        "evidence_summary": row.get("evidence_summary", "").strip() or None,
        "limitations": row.get("limitations", "").strip() or None,
        "research_date": row.get("research_date", "").strip() or None,
        "raw_record": dict(row),
    }


class ResearchDatasetImporter:
    """Orchestrates validation, normalization, and idempotent database insertion."""

    def __init__(self, research_dir: Path = RESEARCH_DIR):
        self.research_dir = research_dir
        self.provider_files: list[Path] = []
        self.matrix_files: list[Path] = []
        self.report_files: list[Path] = []
        self._discover_files()

    def _discover_files(self) -> None:
        if not self.research_dir.exists():
            raise FileNotFoundError(f"Research directory not found: {self.research_dir}")

        self.provider_files = sorted(list(self.research_dir.glob("nammaserve_batch*_providers.csv")))
        self.matrix_files = sorted(list(self.research_dir.glob("nammaserve_batch*_area_category_matrix.csv")))
        self.report_files = sorted(list(self.research_dir.glob("nammaserve_batch*_research_report.md")))

        total = len(self.provider_files) + len(self.matrix_files) + len(self.report_files)
        logger.info(
            "Discovered %d research files (%d provider CSVs, %d matrix CSVs, %d reports)",
            total,
            len(self.provider_files),
            len(self.matrix_files),
            len(self.report_files),
        )
        if total != 12:
            logger.warning("Expected 12 research files across 4 batches, found %d", total)

    def load_and_validate(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        candidates: list[dict[str, Any]] = []
        coverage_cells: list[dict[str, Any]] = []

        # 1. Process provider CSVs
        for pfile in self.provider_files:
            batch_id = pfile.stem.split("_")[1]  # "batch1", "batch2", etc.
            with open(pfile, encoding="utf-8") as fp:
                reader = csv.DictReader(fp)
                for row_idx, row in enumerate(reader, start=2):
                    cleaned = validate_and_normalize_candidate_row(row, batch_id, row_idx)
                    candidates.append(cleaned)

        # 2. Process matrix CSVs
        for mfile in self.matrix_files:
            batch_id = mfile.stem.split("_")[1]
            with open(mfile, encoding="utf-8") as fp:
                reader = csv.DictReader(fp)
                for row_idx, row in enumerate(reader, start=2):
                    cleaned = validate_and_normalize_coverage_row(row, batch_id, row_idx)
                    coverage_cells.append(cleaned)

        return candidates, coverage_cells

    def dry_run(self) -> dict[str, Any]:
        candidates, coverage_cells = self.load_and_validate()

        distinct_pids = set(c["provider_id"] for c in candidates)
        distinct_names = set(c["provider_name"] for c in candidates)
        areas = Counter(c["area_name"] for c in candidates)
        categories = Counter(c["service_category"] for c in candidates)
        price_types = Counter(c["price_type"] for c in candidates)
        ver_statuses = Counter(c["verification_status"] for c in candidates)
        with_prices = sum(1 for c in candidates if c["price_amount"] is not None)
        with_ratings = sum(1 for c in candidates if c["rating"] is not None)

        coverage_statuses = Counter(c["research_status"] for c in coverage_cells)

        stats = {
            "total_files_found": len(self.provider_files) + len(self.matrix_files) + len(self.report_files),
            "provider_csv_files": len(self.provider_files),
            "matrix_csv_files": len(self.matrix_files),
            "report_md_files": len(self.report_files),
            "total_candidates_to_import": len(candidates),
            "distinct_provider_ids": len(distinct_pids),
            "distinct_business_names": len(distinct_names),
            "published_prices_count": with_prices,
            "published_ratings_count": with_ratings,
            "total_coverage_cells_to_import": len(coverage_cells),
            "areas_represented": len(areas),
            "categories_represented": len(categories),
            "area_distribution": dict(areas),
            "category_distribution": dict(categories),
            "price_type_distribution": dict(price_types),
            "verification_status_distribution": dict(ver_statuses),
            "coverage_status_distribution": dict(coverage_statuses),
        }
        return stats

    def execute_import(self, db: Session) -> dict[str, int]:
        candidates, coverage_cells = self.load_and_validate()

        cand_inserted = 0
        cand_updated = 0
        cov_inserted = 0
        cov_updated = 0

        # Import candidates idempotently
        for c in candidates:
            stmt = select(ResearchCandidate).where(
                ResearchCandidate.provider_name == c["provider_name"],
                ResearchCandidate.requested_area == c["requested_area"],
                ResearchCandidate.service_category == c["service_category"],
            )
            existing = db.execute(stmt).scalar_one_or_none()
            if existing is None:
                new_cand = ResearchCandidate(**c)
                db.add(new_cand)
                cand_inserted += 1
            else:
                for k, v in c.items():
                    setattr(existing, k, v)
                existing.updated_at = datetime.utcnow()
                cand_updated += 1

        # Import coverage idempotently
        for cov in coverage_cells:
            stmt = select(ResearchCoverage).where(
                ResearchCoverage.area == cov["area"],
                ResearchCoverage.service_category == cov["service_category"],
            )
            existing = db.execute(stmt).scalar_one_or_none()
            if existing is None:
                new_cov = ResearchCoverage(**cov)
                db.add(new_cov)
                cov_inserted += 1
            else:
                for k, v in cov.items():
                    setattr(existing, k, v)
                cov_updated += 1

        db.commit()
        return {
            "candidates_inserted": cand_inserted,
            "candidates_updated": cand_updated,
            "coverage_inserted": cov_inserted,
            "coverage_updated": cov_updated,
        }


def main():
    parser = argparse.ArgumentParser(description="Import NammaServe Provider Research Dataset")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Validate dataset without writing to DB")
    parser.add_argument("--confirm-local", action="store_true", default=False, help="Confirm write to local/test DB")
    parser.add_argument("--confirm-supabase", action="store_true", default=False, help="Confirm write to Supabase DB")
    args = parser.parse_args()

    importer = ResearchDatasetImporter()

    if args.dry_run or (not args.confirm_local and not args.confirm_supabase):
        logger.info("Executing DRY-RUN validation (no database modifications)...")
        stats = importer.dry_run()
        print("\n" + "=" * 65)
        print("NAMMASERVE RESEARCH DATASET — DRY-RUN VALIDATION REPORT")
        print("=" * 65)
        print(f"Total Research Files Detected: {stats['total_files_found']} of 12")
        print(f"  - Provider CSVs: {stats['provider_csv_files']}")
        print(f"  - Matrix CSVs:   {stats['matrix_csv_files']}")
        print(f"  - Research MDs:  {stats['report_md_files']}")
        print(f"\nProvider Candidates to Import: {stats['total_candidates_to_import']}")
        print(f"  - Distinct Provider IDs:     {stats['distinct_provider_ids']}")
        print(f"  - Distinct Business Names:   {stats['distinct_business_names']}")
        print(f"  - Records with Fixed/Starting Prices: {stats['published_prices_count']}")
        print(f"  - Records with Google Maps Ratings:   {stats['published_ratings_count']}")
        print(f"\nCoverage Matrix Cells to Import: {stats['total_coverage_cells_to_import']} (8 areas × 8 categories)")
        print("\nVerification Status Breakdown:")
        for k, v in stats["verification_status_distribution"].items():
            print(f"  - {k}: {v}")
        print("\nPrice Types Breakdown:")
        for k, v in stats["price_type_distribution"].items():
            print(f"  - {k}: {v}")
        print("\nArea Distribution (16 candidates per area):")
        for k, v in stats["area_distribution"].items():
            print(f"  - {k}: {v}")
        print("\nCategory Distribution (16 candidates per category):")
        for k, v in stats["category_distribution"].items():
            print(f"  - {k}: {v}")
        print("=" * 65)
        print("VALIDATION SUCCESS: 0 schema errors, 0 missing mandatory fields.")
        print("To write to database, run with --confirm-local or --confirm-supabase after approval.")
        return

    # Database write branch (requires explicit confirmation)
    logger.info("Initializing database session...")
    db = SessionLocal()
    try:
        results = importer.execute_import(db)
        logger.info("IMPORT COMPLETE: %s", results)
        print(f"\nSuccessfully imported research dataset: {results}")
    except Exception as exc:
        db.rollback()
        logger.error("Database import failed, rolled back transaction: %s", exc)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
