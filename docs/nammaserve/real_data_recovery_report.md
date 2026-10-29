# NammaServe real-data recovery report

## Confirmed root cause

The configured target is a remote Supabase PostgreSQL database. It is at Alembic revision `h8i9j0k1l2m3`; code queries the `services` table introduced by pending revision `i9j0k1l2m3n4`. A safe read-only check reproduced the failure: `relation "services" does not exist`. No migration or seed was run against that remote database.

`CatalogueResolver` now catches this schema mismatch, rolls back the failed transaction, and resolves from the checked-in canonical catalogue. It does not manufacture providers or prices. Local/platform database connectors continue to report their unavailable database state rather than returning fabricated records.

## Data source matrix

| UI section | Source | Current behavior |
| --- | --- | --- |
| Nearby providers | Local database, OpenStreetMap, configured Places connectors | Only returned records are rendered; no demo fallback. |
| Google discovery | Official Google Places API (server-side) | Implemented, but requires `GOOGLE_PLACES_API_KEY`. |
| Ratings | Google Places field-mask response when configured | Place-specific aggregate rating/count only. |
| Reviews / AI summary | Identifiable source reviews for the selected business | Unavailable state shown; no generic or synthetic review text is displayed. |
| Prices | Local provider/platform records with evidence | Only source-backed records render. Otherwise the page says no sourced price is available. |

## UI and cache fixes

- Search sends the typed service and submitted locality, plus current coordinates and radius.
- Empty/API-error searches clear prior results; static AC cards, ₹499/₹400 claims, generic images, and fallback providers are not rendered.
- Price cards are generated only from `price_comparison` response items and retain source, verification, scope, conditions, and URL.
- Cache key version is now `v2` and includes `limit`, preventing a small result request from satisfying a larger request.

## Files changed for this recovery

- `backend/app/services/nammaserve/discovery/resolver.py`
- `backend/app/services/nammaserve/discovery/cache.py`
- `backend/app/services/nammaserve/discovery/google_places.py`
- `backend/.env.example`
- `backend/tests/test_nammaserve_real_data_recovery.py`
- `frontend/src/app/nammaserve/page.tsx`
- `frontend/src/components/nammaserve/TopPlatformsSection.tsx`
- `frontend/src/components/nammaserve/NearbyProvidersList.tsx`
- `frontend/src/components/nammaserve/AIReviewSummaryCard.tsx`

## Configuration and cost

- `DATABASE_URL`: local PostgreSQL/PostGIS target for local development. Do not point migrations at a remote project.
- `GOOGLE_PLACES_API_KEY`: backend-only key for Places API (New); requires a Google Cloud project, enabled Places API, billing, field-mask/quota controls.
- `GEOAPIFY_API_KEY`, `FOURSQUARE_API_KEY`: optional authorized alternatives; their own quotas/billing apply.

Google Places is not live-verified in this workspace because no credential value was inspected or used. The shortest remaining step is to configure `GOOGLE_PLACES_API_KEY` locally, then run one controlled search and confirm the returned `Google Places API` connector status.

## Tests actually run

`backend\.venv\Scripts\python.exe -m pytest tests/test_nammaserve_real_data_recovery.py tests/test_nammaserve_phase4.py -q` — **29 passed**.

`npm.cmd run build` (from `frontend`) — **passed**; TypeScript completed and `/nammaserve` was prerendered.

`npm.cmd run lint` ran and reports **7 errors / 25 warnings**. The errors are in existing SpotFix components (`ImageIntake.tsx`, `LocationPickerMap.tsx`, and `SubmissionSummary.tsx`); no NammaServe lint errors remain. It is therefore not a passing full-project lint gate.

## Migration approval required

Revision `i9j0k1l2m3n4_create_service_catalogue_and_pricing_tables.py` is required for database-backed catalogue/pricing tables. It was not applied because the current `DATABASE_URL` targets remote Supabase. Before applying it, configure a confirmed local development database and review the migration/seed provenance.

## Local verification

1. Configure a local database in `backend/.env`; do not use the remote Supabase URL.
2. Apply reviewed migrations to that local database and load only explicitly approved, provenance-labelled records.
3. Start API and frontend, then search two distinct service/locality combinations.
4. Confirm the network request contains each submitted `service`, `area`, `lat`, `lng`, and `radius_km` and that UI headings/results change together.
5. With no providers/prices, confirm the page shows an honest empty state rather than demo content.

## Controlled Google Places smoke test (2026-10-22)

- Local configuration check: `GOOGLE_PLACES_API_KEY` is loaded by `pydantic-settings` from `backend/.env`; only a boolean presence check and key length were inspected, never the value.
- Request: Places API (New) `POST https://places.googleapis.com/v1/places:searchText`; text query `AC repair in Rajajinagar, Bengaluru`; coordinates `12.9915, 77.5530`; circular location bias radius `5000.0` metres; `maxResultCount=5`; client timeout `5.0s`.
- Result: Google returned HTTP **403 Forbidden / PERMISSION_DENIED**. The adapter returned **0 results** and connector status `Google Places request failed: HTTP 403 Forbidden`.
- No business identifiers, source URLs, ratings, or reviews were claimed from this failed request.
- Likely remaining action: verify that the Google Cloud project has Places API (New) enabled, the key is permitted for this API and endpoint, billing is enabled, and API restrictions allow the request. Quota/permission changes must be made by the account owner.
- Automated mapping test: `python -m pytest tests/test_nammaserve_google_places_mapping.py tests/test_nammaserve_discovery.py -q` — **13 passed** (mocked response mapping; not live evidence).
