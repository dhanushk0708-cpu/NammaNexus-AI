# NammaServe AI — Phase B Codex Handoff

Research only; no repo access. Inspect the existing schema and decide the mapping. Date researched: 2026-10-23. Files: `nammaserve_phase_b_research.json` (authoritative), `.csv` (same records, flattened), report `.md`.

## Research statuses
- `VERIFIED_PUBLIC_PRICE` — service and displayed price seen on an accessible official page.
- `VERIFIED_QUOTE_ONLY` — defined but unused in this dataset (no page verified a quote-only listing).
- `VERIFIED_SERVICE_PRICE_UNAVAILABLE` — listing seen, no usable price (UC standalone bathroom/kitchen/sofa cleaning; Sulekha category-level AC, cleaning, electricians).
- `NOT_FOUND` — no matching listing on the page checked (UC pipe-leakage repair).
- `NEEDS_REVIEW` — unverifiable (all Justdial; Sulekha plumbing).

## Field mapping hints
platform -> provider/platform; category + canonical_service_name -> service taxonomy; original_service_name -> display/source label; service_subtype; pricing_type + price_amount/price_min/price_max + unit + currency -> pricing model; variants -> per-variant prices; inclusions/exclusions/conditions -> scope text; source_url, page_title, date_researched, evidence_notes -> provenance; research_status, comparability_label, comparison_group -> verification/comparison flags; access_limitations -> caveat text.

## Price types that must stay distinct
`fixed`, `fixed_default_option` (NB cleaning cards: price is for the default option, other options exist), `fixed_by_variant`, `starting_at`, `consultation_fee` (visit/inspection fee only — repair cost is quoted later), `not_published`. Do not collapse `starting_at` into fixed. `price_amount` is null for unknowns — never store 0.

## Records suitable for comparison
Group by `comparison_group`. Only `ac_gas` is DIRECTLY_COMPARABLE. PARTIALLY_COMPARABLE groups may be shown side by side only with the group's `comparability_reason`. INSUFFICIENT_EVIDENCE / NOT_COMPARABLE must not be ranked.

## Do not display as verified prices
All NEEDS_REVIEW, NOT_FOUND and VERIFIED_SERVICE_PRICE_UNAVAILABLE records (price fields are null). NB records flagged with catalog-vs-rate-table conflicts (see `other_prices_on_same_page`, `access_limitations`) should show the catalog price with a note that the platform's own page shows other figures.

## UI limitations to preserve
- Show 'Starts at' wording and the research date; prices are snapshots and can change.
- UC cleaning prices are locality samples (Cooke Town); home size/BHK is unspecified on both platforms.
- Show consultation fees as visit fees, not service prices.
- No 'cheapest platform' badge from these data. Do not show ratings (none collected).
- Show 'not available / not verified' for Justdial and Sulekha instead of blanks or zeros.

## Highest-value follow-up research
1. Justdial and Sulekha listing/price pages for Bengaluru via a permitted route (API/partner access or manual review).
2. Checkout-level prices for NB (catalog vs rate-table conflicts) and UC option variants behind 'Starts at'.
3. Cleaning prices normalised by BHK/bathroom count; UC standalone bathroom/kitchen/sofa prices.
4. Multiple Bengaluru localities for UC to measure locality variation.
