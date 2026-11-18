# NammaServe Price Comparison — Agent Build Brief

## Goal
Build a centralized Bengaluru home-service price comparison feature inside the **existing NammaServe application** using the supplied CSV as its initial dataset and the accompanying report as explanatory context. Do not rebuild NammaServe, create a separate app, or replace the existing database/UI architecture.

## Input files
- `nammaserve_bengaluru_price_comparison.csv` — 142 collected pricing records.
- `nammaserve_bengaluru_price_comparison_report.md` — research notes, source URLs, caveats and category benchmarks.

Keep the CSV as an import/source artifact. Load its records into the existing database using the project's current ORM, migrations, service and API conventions. First inspect the repository and existing NammaServe research/comparison feature, models, migrations, endpoints, UI, and tests. Reuse what exists; avoid duplicate tables, endpoints, or screens.

## Dataset audit findings (before implementation)
- CSV has 142 rows, 14 expected columns, 4 platforms and 8 categories.
- Platform rows: Urban Company 52; NoBroker 51; Justdial 20; Sulekha 19.
- Price types: FIXED 56; STARTING_FROM 50; PRICE_RANGE 29; QUOTATION_REQUIRED 3; UNPUBLISHED 4.
- `published_price` is empty on 7 records, consistent with records where no numeric price is published.
- No exact duplicate rows and no duplicate combination of platform + category + service + provider + source URL were found.
- Verification status: 122 `SOURCE_CORROBORATED`, 20 `DISCOVERED`. Do not describe all 142 rows as independently verified. `SOURCE_CORROBORATED` means the research file says the source was corroborated; it is not a guarantee the price remains current.
- The report says 142 “verified pricing records”; revise this wording to “142 collected pricing records; verification status varies.”
- Some prices are vendor- or locality-specific, geographic scope is unconfirmed, or source pages may contain cross-city contamination. Preserve and display these caveats.
- NoBroker can have different interactive-card and static-table prices for the same service. Do not silently merge or select one; retain separate records and show notes/source context.
- The research date is 2026-10-29. Display it clearly and avoid implying live pricing.

## User-facing feature
Add a page/section to the current NammaServe UI titled **Bengaluru Price Comparison**.

### Filters
- Service category (all 8 categories in the CSV)
- Service/task
- Platform (Urban Company, NoBroker, Justdial, Sulekha)
- Price type (FIXED, STARTING_FROM, PRICE_RANGE, QUOTATION_REQUIRED, UNPUBLISHED)
- Geographic scope / locality
- Verification status

### Comparison results
Show comparable services grouped by category/task, with one platform column/card per platform when suitable records exist. Each result should display:
- Platform and service name
- Published price and currency, exactly as sourced
- Price type label: Fixed, Starting from, Range, Quote required, or Not published
- Unit/scope (e.g. per visit, per unit, per hour) and what is included/excluded
- Geographic scope/locality
- Verification status
- Research checked date
- Clickable source URL
- Notes/caveats

Do not compare non-equivalent tasks as if they were identical. If no exact match exists, show “No comparable published price found” instead of inventing a price. Do not treat a blank price as zero. Do not convert a starting price into a fixed price. Keep source prices in INR and preserve ranges as ranges.

### Price display rules
- `FIXED`: show “₹X fixed” only within the listed scope; explain exclusions in notes.
- `STARTING_FROM`: show “From ₹X”. Never present it as the final price.
- `PRICE_RANGE`: show the full range exactly as provided.
- `QUOTATION_REQUIRED`: show “Quote required”; do not display a numeric price.
- `UNPUBLISHED`: show “Price not published”; do not display a numeric price.
- If geographic scope contains “Unconfirmed”, “Citywide Applicability Unconfirmed”, “Geographic Applicability Unclear”, or a locality list, visibly flag the price as **Locality-specific / coverage unconfirmed**. Do not label it citywide.
- Show a visible note: “Prices are research snapshots, not live quotes. Final cost may vary by locality, job scope, parts/materials, access and provider assessment.”
- Clearly distinguish platform rate cards (Urban Company/NoBroker) from vendor/listing prices and approximate cost guides (Justdial/Sulekha), based on the dataset notes. Do not claim the platforms have identical pricing models.

## Data model / import
Inspect existing tables first. Extend the existing comparison/research schema if present; do not create parallel equivalents. Preserve all 14 CSV fields:
`source_platform, service_category, service_name, provider_name, published_price, currency, price_type, price_unit, price_scope, geographic_scope, source_url, source_checked_date, verification_status, notes`

Requirements:
- Add a migration only if the existing schema cannot represent these fields.
- Store the original published price as text or another lossless representation because it can be a scalar, range, or blank. If a numeric helper is needed for sorting, add separate parsed min/max fields and never discard the original string.
- Import idempotently. A second import must not duplicate records. Use a stable natural key or dataset record ID/hash and document it.
- Validate allowed `price_type` and `verification_status` values, but do not discard rows with missing `published_price`.
- Preserve the source URL and research date for every row.
- Do not change or delete existing provider, booking, complaint, service catalogue, or pricing data.

## API and security
Follow the project's existing API naming, pagination, error handling, authentication, and response-envelope conventions. Reuse existing research/comparison endpoints if they already cover this use case. If new endpoints are necessary, support:
- Filtered, paginated comparison records
- Available categories/platforms/price types for filter controls
- A summary/overview with counts and last research date
- Optional detail view for a selected record

Validate filter inputs, limit page sizes, and use parameterized ORM/database queries. Do not expose secrets or internal database details. A public read-only comparison can be unauthenticated only if that matches the existing NammaServe access policy; follow current project policy rather than inventing a new one.

## UI/UX
- Follow the current NammaServe visual system and responsive layout.
- Include loading, empty, error and retry states.
- Make source links open safely in a new tab.
- Keep caveats visible, not hidden only in tooltips.
- Make the UI usable on mobile.
- Avoid showing a “best/cheapest” winner unless the tasks, units, geography and price types are genuinely comparable. If a “lowest listed price” sort exists, label it carefully and exclude quote-required/unpublished rows from numeric sorting.

## Tests and acceptance criteria
1. Inspect and explain the current architecture before editing.
2. Import all 142 rows and verify counts by platform/category/type against the audit above.
3. Re-running import creates no duplicates.
4. Blank prices remain blank and render as quote-required/unpublished where applicable, never as ₹0.
5. Fixed, starting-from, range, quote-required and unpublished states render distinctly.
6. Source links, notes, research date, verification status and geographic caveats are shown.
7. Locality-specific or unconfirmed data is never presented as citywide confirmed.
8. Filters can be combined and pagination works.
9. Existing NammaServe marketplace, booking flow and existing data continue to work.
10. Add/update backend and frontend tests; run relevant test suites and report exact results.
11. Provide a concise final summary listing files changed, migrations, import command, endpoints, UI route, tests run, and known limitations.

## Work order
1. Inspect repository, existing feature and data schema; report the proposed minimal change plan.
2. Implement the smallest compatible migration/import/API/UI changes.
3. Add tests and run them.
4. Do not claim live scraping or real-time pricing. This feature is based on the supplied research snapshot unless a separately approved refresh mechanism is implemented.
