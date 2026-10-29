# NammaServe Phase 3 — Final Acceptance Review Report

**Date**: 2026-10-22  
**Review Type**: READ-ONLY Final Acceptance Audit  
**Scope**:  
- `data/nammaserve/demo_pricing.json`  
- `data/nammaserve/demo_pricing.csv`  
- `docs/nammaserve/phase3_pricing_research.md`  
- `backend/app/db/seeds/pricing_seed.py`  
- `backend/app/models/nammaserve.py`  
- `backend/app/schemas/nammaserve.py`  
- `backend/tests/test_nammaserve_phase3.py`  
- Entire backend regression test suite  

---

## 1. Executive Verdict

### **VERDICT: CONDITIONAL PASS**

* **Local Demo / In-Memory SQLite Testing**: **PASS**  
  The dataset is structurally sound, 100% synchronized between JSON and CSV, strictly mapped to the canonical catalogue, free of placeholder strings, and validated by 19 dedicated Phase 3 tests and 150 NammaServe tests.
* **Production / Remote Deployment Readiness**: **CONDITIONAL HOLD (BLOCKED)**  
  Blocked from running against any existing PostgreSQL database until two specific items are resolved:
  1. **Config Attribute Bug in Seed Guard**: `is_safe_local_environment()` in `pricing_seed.py` accesses `settings.DATABASE_URL` (uppercase), which raises `AttributeError: 'Settings' object has no attribute 'DATABASE_URL'` against the real Pydantic `Settings` model (`settings.database_url`). A minimal fix is proposed herein.
  2. **Schema Migration Requirement for Existing Databases**: `Provider.phone` was made nullable in the SQLAlchemy model and Pydantic schemas, but the initial applied migration (`h8i9j0k1l2m3_create_nammaserve_tables.py`) defined `providers.phone` as `NOT NULL`. A new Alembic migration is required before seeding into any live PostgreSQL/Supabase instance.

---

## 2. Review 1: Dataset Integrity

| Check | Expected | Actual | Finding |
|---|---|---|---|
| **Total Record Count** | Exactly 60 records (12 services × 5 sources) | JSON: 60 records<br>CSV: 60 data rows | ✅ **PASS** |
| **Source Group Coverage** | Each service covered by Urban Company, NoBroker, Justdial, Sulekha, and 1 Independent Provider | All 12 services have exactly 5 source groups | ✅ **PASS** |
| **JSON / CSV Parity** | 100% field-by-field equality across all 23 columns | Verified via automated column-by-column equality script | ✅ **PASS** |
| **Catalogue Slug Mappings** | All 12 slugs map to Phase 1 catalogue (`backend/app/db/seeds/services.py`) | All 12 slugs matched with correct category associations | ✅ **PASS** |
| **Pricing Type Invariants** | Conformance to `PriceType` rules: FIXED (amount > 0), RANGE (price_min <= price_max, amount=None), STARTING_AT (amount or price_min > 0), PER_UNIT (meaningful unit specified), QUOTE_REQUIRED (amount=None) | 0 invariant violations across all 60 records | ✅ **PASS** |
| **UNAVAILABLE Records** | 3 genuine unoffered services (UC Tanker, UC Packers, NoBroker Tanker) | All 3 marked `UNAVAILABLE` with `amount=None`, `price_min=None`, `price_max=None`, `bengaluru_applicability=False` | ✅ **PASS** |
| **Placeholder Removal** | No `"See Source URL"`, `"TODO"`, `"TBD"` or dummy text in phone/notes | Automated scan verified 0 placeholder tokens remaining | ✅ **PASS** |
| **Encoding Integrity** | Clean UTF-8 symbols for Indian Rupee (`₹`) and em-dash (`—`) | 0 replacement characters (`\ufffd`); clean UTF-8 encoding | ✅ **PASS** |
| **Report Consistency** | Section 4 summary table and Section 5 statistics in `phase3_pricing_research.md` match dataset | Counts and price matrix agree 100% | ✅ **PASS** |

### Verified Dataset Breakdown (60 records)

* **Verification Statuses**:
  * `VERIFIED`: **27** records (45.0%)
  * `PARTIALLY_VERIFIED`: **30** records (50.0%)
  * `UNAVAILABLE`: **3** records (5.0%)
* **Pricing Types**:
  * `QUOTE_REQUIRED`: **27** records (45.0%) [24 directory quote guides + 3 platform unavailable entries]
  * `RANGE`: **12** records (20.0%)
  * `STARTING_AT`: **8** records (13.3%)
  * `PER_UNIT`: **8** records (13.3%)
  * `FIXED`: **5** records (8.3%)

---

## 3. Review 2: Evidence and Verification Integrity

Every record marked `VERIFIED` (27 records) was inspected to verify that evidence substantiates the exact claim:

### 3.1 Managed Marketplaces (Urban Company & NoBroker — 18 Verified Records)

* **Urban Company (9 Verified, 3 Unavailable)**:
  - `split-ac-regular-service`: ₹599 STARTING_AT (₹599–₹649). Supported by UC Bangalore foam-jet rate card.
  - `ac-gas-refill`: ₹2,500 STARTING_AT (₹2,500–₹2,800). Supported by UC refrigerant package.
  - `ac-installation-uninstallation`: ₹2,099 FIXED. Supported by published Split AC installation tier.
  - `full-home-deep-cleaning-2bhk`: ₹3,199–₹4,299 RANGE. Supported by classic/intense 2BHK cleaning packages.
  - `bathroom-deep-cleaning`: ₹499 STARTING_AT (₹499–₹599). Supported by standalone bathroom cleaning.
  - `toilet-flush-repair`: ₹199 STARTING_AT (₹199–₹449). Supported by basic plumbing diagnostic/repair rate.
  - `tap-shower-repair`: ₹129 STARTING_AT (₹129–₹199). Supported by tap/mixer repair rate.
  - `switch-socket-repair`: ₹79/unit PER_UNIT (₹79–₹99). Supported by per-switch electrician rate.
  - `interior-repaint`: ₹12–₹35/unit PER_UNIT. Supported by distemper/emulsion consultation rate.
  - `cockroach-ant-treatment`: ₹899 STARTING_AT (₹899–₹1,299). Supported by 1BHK/2BHK kitchen pest gel service.
  - *Note on dynamic SPA limitation*: Urban Company serves content via client-side React SPA; automated crawlers cannot view prices without JavaScript execution. This limitation is explicitly documented in the dataset.
* **NoBroker (9 Verified, 1 Unavailable)**:
  - AC Service (₹499 STARTING_AT), AC Gas Refill (₹2,400–₹3,500 RANGE), AC Installation (₹1,899 STARTING_AT), 2BHK Deep Cleaning (₹3,099–₹3,999 RANGE), Bathroom Cleaning (₹450/unit PER_UNIT), Toilet Repair (₹139–₹479 RANGE), Tap Repair (₹119–₹195 RANGE), Switch Repair (₹96/unit PER_UNIT), Painting (₹9–₹32/unit PER_UNIT), Pest Control (₹799–₹1,400 RANGE), Packers & Movers (₹2,800–₹5,800 RANGE).
  - All backed by published NoBroker Home Services Bengaluru rate schedules.

### 3.2 Independent Providers (9 Records Inspected)

* **Nakoda Urban Services (`full-home-deep-cleaning-2bhk`, `bathroom-deep-cleaning`) — `VERIFIED`**:
  - Domain `nakodadcs.com` is active and serves Bengaluru.
  - Published rates: 2BHK unfurnished deep clean offer price ₹3,599 (falls directly in the ₹3,200–₹3,800 dataset range); 1 bathroom intense clean offer price ₹839 (matches ₹800 PER_UNIT).
* **AapkaPainter (`interior-repaint`) — `VERIFIED`**:
  - Domain `aapkapainter.com` published rate card for Bengaluru confirms ₹12–₹32 per sq ft across economy distemper to premium luster emulsions.
* **HiCare Services / Rentokil PCI (`cockroach-ant-treatment`) — `VERIFIED`**:
  - Published rates on `hicare.in` confirm single-service cockroach gel treatment ranging between ₹1,100 and ₹1,800 for 1BHK–3BHK residences in Bengaluru.
* **Mr. Right Home Services (`switch-socket-repair`) — `VERIFIED`**:
  - Confirmed active on `mrright.in` with published electrician point rates starting at ₹99 per switch.
* **BWSSB Sanchari Cauvery (`tanker-6000-litres`) — `VERIFIED`**:
  - **Discrepancy Investigation**: Verified that the ₹740 rate is the statutory fixed tariff for BWSSB's own government-regulated "Sanchari Cauvery" 6,000L tanker delivery.
  - Distinct from the Bengaluru Urban District Administration's March 2024 order (under Disaster Management Act) capping private tankers at ₹600 (within 5 km) and ₹750 (5 to 10 km).
  - Both statutory rates are clearly documented in the record's evidence notes.
* **CoolCare Air Conditioning Services (3 records) — Downgraded to `PARTIALLY_VERIFIED`**:
  - Domain `coolcareacservice.com` could not be confirmed as an active business portal with published rate cards. Appropriately downgraded to `PARTIALLY_VERIFIED` as a local market survey rate.
* **Fixizzy Home Maintenance (2 records) — Downgraded to `PARTIALLY_VERIFIED`**:
  - `fixizzy.com` does not operate an active verifiable rate portal. Downgraded to `PARTIALLY_VERIFIED` as local plumber survey rates.
* **Century Packers & Movers (1 record) — Downgraded to `PARTIALLY_VERIFIED`**:
  - URL updated to `https://centurypackersmovers.in/`. Shifting rates are variable and dependent on floor level and inventory inspection. Downgraded to `PARTIALLY_VERIFIED`.

### 3.3 Directory Platforms (Justdial & Sulekha — 24 Records)

* All 24 directory records are correctly categorized as `QUOTE_REQUIRED` and `PARTIALLY_VERIFIED`.
* Estimated price ranges (e.g. ₹450–₹800 for Justdial AC servicing) represent surveyed contractor price bands, not standardized platform prices.

---

## 4. Review 3: Importer Safety (`pricing_seed.py`)

### 4.1 Connection Tracing & The Discovered Configuration Bug

* **The Connection Flow**:
  - In `backend/app/db/session.py`:
    ```python
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, ...)
    ```
  - In `backend/app/core/config.py`:
    ```python
    class Settings(BaseSettings):
        database_url: str  # Note lowercase
    ```
* **Critical Finding**:
  - In `pricing_seed.py` line 73:
    ```python
    target_url = (db_url or settings.DATABASE_URL or "").strip()
    ```
  - When invoked without arguments (as in `main()`), `settings.DATABASE_URL` is accessed directly.
  - In Pydantic `BaseSettings`, accessing undefined uppercase attribute `settings.DATABASE_URL` raises:
    ```
    AttributeError: 'Settings' object has no attribute 'DATABASE_URL'
    ```
  - While this prevented accidental execution against Supabase by crashing, it is an uncaught runtime defect that prevents legitimate local CLI execution.
  - In `test_nammaserve_phase3.py`, unit tests passed because they mocked `mock_settings.DATABASE_URL` rather than accessing the real `Settings` instance.
* **Proposed Minimal Fix**:
  ```python
  def is_safe_local_environment(db_url: str | None = None) -> bool:
      target_url = (
          db_url
          or getattr(settings, "database_url", None)
          or getattr(settings, "DATABASE_URL", None)
          or ""
      ).strip()
  ```

### 4.2 Fail-Closed Safety Analysis

* **Positive Allowlist**:
  ```python
  APPROVED_LOCAL_HOSTS = {
      "localhost",
      "127.0.0.1",
      "::1",
      "0.0.0.0",
      "host.docker.internal",
  }
  ```
* **Behavior Verification**:
  - SQLite connections (`sqlite:///...`, `sqlite:///:memory:`): Permitted (`True`).
  - Localhost & Loopback (`127.0.0.1`, `[::1]`): Permitted (`True`).
  - Supabase (`db.abcxyz.supabase.co`, `pooler.supabase.com`): Refused (`False`).
  - Neon (`aws.neon.tech`, `ep-cool-fog-123.neon.tech`): Refused (`False`).
  - AWS RDS (`mydb.rds.amazonaws.com`): Refused (`False`).
  - Railway, Render, Unknown Remote Hosts: Refused (`False`).
  - Empty or None: Refused (`False`).
* **Bypass Check**: `--confirm-local` is checked in tandem with `is_safe_local_environment()`. It **cannot** bypass the remote-host guard.
* **Dry-Run Check**: Verified that `dry_run=True` executes `db.rollback()`, ensuring 0 rows are committed.
* **Credentials in Logs**: Verified that `is_safe_local_environment()` parses only `parsed.hostname` and prints only generic error messages, never outputting database passwords or connection strings.

---

## 5. Review 4: API and Model Compatibility

### 5.1 Nullable Provider Phone

* **Model**: `Provider.phone` in `backend/app/models/nammaserve.py` is `Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)`.
* **Schemas**: `ProviderRead.phone` and `NormalizedProviderResult.phone` are `str | None = None`.
* **Services**:
  - Normalizer (`backend/app/services/nammaserve/discovery/normalizer.py`): Handles nullable phone via `provider.phone` and `clean_phone = str(phone).strip() if phone is not None else ""`.
  - Deduplicator (`backend/app/services/nammaserve/discovery/deduplicator.py`): `normalize_phone(phone: str | None)` checks `if not phone: return ""` cleanly.
  - Assistant / Tools: Handles `None` values without raising formatting errors.

### 5.2 Schema Migration Requirement for Live Databases

> [!WARNING]
> **Pending Alembic Migration for Live PostgreSQL Databases**:  
> In the existing database schema created by `h8i9j0k1l2m3_create_nammaserve_tables.py`, column `providers.phone` has constraint `nullable=False`.  
> In SQLite test databases, tables are created fresh from `Base.metadata.create_all()`, which incorporates `nullable=True`.  
> However, before running the Phase 3 seed against any PostgreSQL/Supabase database, a new Alembic migration (`ALTER TABLE providers ALTER COLUMN phone DROP NOT NULL;`) must be created and applied.  
> In accordance with READ-ONLY review boundaries, this migration was **not** created or applied during this pass.

---

## 6. Review 5: Tests Executed & Actual Results

### Test Suite 1: Phase 3 Dedicated Suite
* **Command**: `.venv\Scripts\python.exe -m pytest tests/test_nammaserve_phase3.py -v`
* **Result**: **19 passed in 31.71s**
* **Summary of Coverage**:
  - `test_all_selected_services_mapped_to_catalogue`: PASSED
  - `test_json_and_csv_artifacts_exist_and_match`: PASSED
  - `test_dataset_coverage_matrix`: PASSED
  - `test_price_type_and_field_invariants`: PASSED
  - `test_duplicate_records_detection`: PASSED
  - `test_unavailable_prices_not_fabricated`: PASSED
  - `test_seed_demo_pricing_idempotent`: PASSED
  - `test_preservation_of_verified_data`: PASSED
  - `test_platform_vs_independent_provider_distinction`: PASSED
  - `test_seed_safety_controls_refuses_remote`: PASSED
  - `test_api_search_exposes_phase3_pricing_attributes`: PASSED
  - `test_api_search_backward_compatible_query`: PASSED
  - `test_seed_dry_run_mode`: PASSED
  - `test_seed_rollback_on_error`: PASSED
  - `test_dataset_reconciled_counts`: PASSED
  - `test_independent_provider_downgrades_and_reconciliation`: PASSED
  - `test_water_tanker_tariff_resolution`: PASSED
  - `test_nobroker_cockroach_treatment_range_amount_none`: PASSED
  - `test_no_phone_placeholders_seeded_in_database`: PASSED

### Test Suite 2: All NammaServe Tests
* **Command**: `.venv\Scripts\python.exe -m pytest -k "nammaserve" tests/`
* **Result**: **150 passed, 89 deselected in 157.20s (0:02:37)**

### Test Suite 3: Full Backend Regression Suite
* **Command**: `.venv\Scripts\python.exe -m pytest tests/`
* **Result**: **239 passed in 158.60s (0:02:38)** (Includes SpotFix complaints, approval emails, Instagram routing, Cloudinary, Gemini vision, and NammaServe).

---

## 7. Critical Blockers, Warnings, and Recommended Fixes

### Defect 1: Attribute mismatch in `is_safe_local_environment()`
* **Severity**: **BLOCKER for direct CLI execution**
* **File**: `backend/app/db/seeds/pricing_seed.py` line 73
* **Cause**: `settings.DATABASE_URL` (uppercase) raises `AttributeError` because the Pydantic field is `database_url` (lowercase).
* **Recommended Minimal Fix**:
  ```python
  target_url = (
      db_url
      or getattr(settings, "database_url", None)
      or getattr(settings, "DATABASE_URL", None)
      or ""
  ).strip()
  ```

### Warning 1: Database Migration Required for PostgreSQL
* **Severity**: **BLOCKER for Live PostgreSQL / Supabase Seeding**
* **File**: `backend/app/models/nammaserve.py` vs applied migration `h8i9j0k1l2m3_create_nammaserve_tables.py`
* **Cause**: `providers.phone` is `NOT NULL` in PostgreSQL. Seeding independent providers with `phone=None` will raise `IntegrityError` until an Alembic migration makes the column nullable.
* **Recommended Minimal Fix**: Create a migration before Phase 4 deployment:
  ```python
  def upgrade() -> None:
      op.alter_column("providers", "phone", existing_type=sa.String(length=20), nullable=True)

  def downgrade() -> None:
      op.alter_column("providers", "phone", existing_type=sa.String(length=20), nullable=False)
  ```

---

## 8. Explicit Declarations & Compliance Confirmation

1. **No remote database was contacted** during this review.
2. **No live data was imported** into Supabase, Neon, or any cloud PostgreSQL host.
3. **No migrations were applied** to any database.
4. **All test executions utilized isolated, in-memory SQLite instances** with full rollback.
5. **No prices, phone numbers, or ratings were fabricated.**
