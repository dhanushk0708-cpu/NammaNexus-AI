# NammaServe AI — Batch 4 Local Provider Research Report (HSR Layout & Marathahalli, Bengaluru)

**Research Date:** `2026-10-25`  
**Batch Identifier:** `BATCH_4`  
**Assigned Geographic Scope:** `HSR Layout, Bengaluru` (`560102` / `560068`) and `Marathahalli, Bengaluru` (`560037` / `560066` border)  
**Assigned Category Scope:** 8 core residential service categories across both areas (`16` area–category combinations)  

**Generated Batch 4 Files:**
* `nammaserve_batch4_providers.csv` — `32` provider–area–category records formatted across the exact `40`-column schema (including all `6` structured Google review-summary columns).
* `nammaserve_batch4_area_category_matrix.csv` — `16` area–category combination rows formatted across the exact `15`-column schema (`batch_id = BATCH_4`).
* `nammaserve_batch4_research_report.md` — Comprehensive analytical synthesis covering all 12 required verification, deduplication, and limitation disclosures.

---

## 1. Research Scope & Research Date

* **Research Date:** `2026-10-25`
* **Target Areas:**
  1. `HSR Layout, Bengaluru` (covering HSR Layout Sectors 1 through 7, Agara Village, Garden Layout, Rajiv Gandhi Nagar, Somasundarapalya, and adjacent Bommanahalli border — PIN `560102` / `560068`).
  2. `Marathahalli, Bengaluru` (covering Marathahalli Market, Aswath Nagar, Krishna Reddy Layout, Munnekolala, Kundalahalli Colony, AECS Layout, Lakshminarayana Pura, Thubarahalli, Doddanekundi, Vignan Nagar, and Yemalur — PIN `560037` / `560066`).
* **Target Service Categories (`8` categories):**
  1. `Plumbing`
  2. `AC repair and servicing`
  3. `Electrical services`
  4. `House cleaning`
  5. `Pest control`
  6. `Appliance repair — washing machines, refrigerators and microwaves`
  7. `Water purifier/RO services`
  8. `Carpentry`
* **Target Density:** Up to `2` verified providers per area–category combination (`16` combinations × `2` providers = `32` target records).

---

## 2. Total Provider–Area Records & Unique Businesses

| Metric | Count | Details |
| :--- | :--- | :--- |
| **Total Area–Category Combinations Researched** | **16 / 16** | `8` categories in `HSR Layout, Bengaluru` + `8` categories in `Marathahalli, Bengaluru` |
| **Total Provider–Area Records in `nammaserve_batch4_providers.csv`** | **32** | `16` records for `HSR Layout, Bengaluru` + `16` records for `Marathahalli, Bengaluru` |
| **Unique Businesses in Batch 4 CSV** | **32** | Every shortlisted provider appears once in Batch 4 (`32` distinct `provider_id` values) |
| **Newly Assigned Batch 4 Provider IDs** | **31** | `PROV_B4_001` through `PROV_B4_031` |
| **Reused Prior-Batch Provider IDs in Batch 4 CSV** | **1** | `PROV_B3_025` (`Smart Services`, `DUP_SMS_01`), reused from Batch 3 (`BTM Layout, Bengaluru`) for `HSR Layout, Bengaluru` Appliance Repair |
| **Cumulative Unique Providers Across Batches 1–4** | **113** | Batch 1 (`25` unique) + Batch 2 (`28` new) + Batch 3 (`29` new) + Batch 4 (`31` new) = `113` unique businesses across `128` total records |

---

## 3. Counts by Area & Service Category

All `16` area–category combinations achieved `COMPLETED_WITH_RESULTS` status with `2` verified providers each:

| Service Category | HSR Layout, Bengaluru | Marathahalli, Bengaluru | Total Records | Matrix Status (`research_status`) |
| :--- | :---: | :---: | :---: | :--- |
| `Plumbing` | 2 (`PROV_B4_001`, `PROV_B4_002`) | 2 (`PROV_B4_016`, `PROV_B4_017`) | **4** | `COMPLETED_WITH_RESULTS` (2/2) |
| `AC repair and servicing` | 2 (`PROV_B4_003`, `PROV_B4_004`) | 2 (`PROV_B4_018`, `PROV_B4_019`) | **4** | `COMPLETED_WITH_RESULTS` (2/2) |
| `Electrical services` | 2 (`PROV_B4_005`, `PROV_B4_006`) | 2 (`PROV_B4_020`, `PROV_B4_021`) | **4** | `COMPLETED_WITH_RESULTS` (2/2) |
| `House cleaning` | 2 (`PROV_B4_007`, `PROV_B4_008`) | 2 (`PROV_B4_022`, `PROV_B4_023`) | **4** | `COMPLETED_WITH_RESULTS` (2/2) |
| `Pest control` | 2 (`PROV_B4_009`, `PROV_B4_010`) | 2 (`PROV_B4_024`, `PROV_B4_025`) | **4** | `COMPLETED_WITH_RESULTS` (2/2) |
| `Appliance repair — washing machines, refrigerators and microwaves` | 2 (`PROV_B4_011`, `PROV_B3_025`) | 2 (`PROV_B4_026`, `PROV_B4_027`) | **4** | `COMPLETED_WITH_RESULTS` (2/2) |
| `Water purifier/RO services` | 2 (`PROV_B4_012`, `PROV_B4_013`) | 2 (`PROV_B4_028`, `PROV_B4_029`) | **4** | `COMPLETED_WITH_RESULTS` (2/2) |
| `Carpentry` | 2 (`PROV_B4_014`, `PROV_B4_015`) | 2 (`PROV_B4_030`, `PROV_B4_031`) | **4** | `COMPLETED_WITH_RESULTS` (2/2) |
| **Total** | **16** | **16** | **32** | **16 / 16 `COMPLETED_WITH_RESULTS`** |

---

## 4. Counts by Verification Status & Confidence

Confidence and verification statuses were assigned conservatively based on independent multi-source corroboration rather than listing appearance:

### A. Breakdown by `verification_status`

| `verification_status` | HSR Layout | Marathahalli | Total Records | Criteria Applied |
| :--- | :---: | :---: | :---: | :--- |
| `SOURCE_CORROBORATED` | 14 | 15 | **29** | Business identity, area relevance, and service category corroborated across at least two distinct public sources (e.g., Google Maps + Official Website and/or Justdial, Sulekha, magicpin, MCA/Tracxn, BrandCompare, Service Bazzar, 5BestINcity, or Chotu). |
| `DISCOVERED` | 2 | 1 | **3** | Verified via a single primary source (Google Maps profile with verified address, phone, and customer reviews) without an accessible independent website or secondary directory listing: `PROV_B4_001` (`Jagan plumber`), `PROV_B4_009` (`Ujala pest control`), and `PROV_B4_019` (`Shree AC Control Pvt Ltd`, whose website `shreeacservices.in` blocked automated browsing). |
| `PROVIDER_CONFIRMED` | 0 | 0 | **0** | Not used; no outbound calls, messages, or direct provider outreach were performed per research rules. |
| `NAMMASERVE_BOOKABLE` | 0 | 0 | **0** | Not used; no provider is integrated into NammaServe booking workflows at this research stage. |

### B. Breakdown by `confidence`

| `confidence` | HSR Layout | Marathahalli | Total Records | Justification |
| :--- | :---: | :---: | :---: | :--- |
| `HIGH` | 14 | 14 | **28** | Multi-source corroborated providers (`SOURCE_CORROBORATED`) with strong area-specific evidence, verified phone numbers, physical addresses in or immediately serving the target area, and substantial customer review history (`39` to `5,319` reviews). |
| `MEDIUM` | 2 | 2 | **4** | Assigned to the 3 single-source `DISCOVERED` records (`PROV_B4_001` `Jagan plumber`, `PROV_B4_009` `Ujala pest control`, and `PROV_B4_019` `Shree AC Control Pvt Ltd`) plus `PROV_B4_021` (`VIKAS ELECTRICAL SERVICES`), which is corroborated via Google Maps (`35` reviews) and a WorkIndia job post in Karthik Nagar/Marathahalli but relies on an Instagram link rather than a standalone website or major service directory. |
| `LOW` | 0 | 0 | **0** | Candidates with weak or ambiguous area/service evidence were excluded rather than padded into the dataset. |

---

## 5. Counts by Price Type & Availability Status

### A. Breakdown by `price_type`

| `price_type` | HSR Layout | Marathahalli | Total Records | Details & Published Examples |
| :--- | :---: | :---: | :---: | :--- |
| `STARTING_AT` | 1 | 0 | **1** | `PROV_B4_015` (`Wood Style Interiors`, [woodstyleinteriors.com](https://woodstyleinteriors.com/)) explicitly publishes a `2BHK Interiors` woodwork package starting at `₹3,99,000` (`INR`, `per_package`, covering modular kitchen, 2 wardrobes, and TV unit in BWP 710 Grade Ply with Hettich hardware, GST extra; `3BHK` package starting at `₹4,99,000`). |
| `QUOTATION_REQUIRED` | 4 | 3 | **7** | Providers whose official websites or listings explicitly require a site inspection, consultation, or quote form before pricing: `PROV_B4_002` (`GBJ Plumbing Services`), `PROV_B4_008` (`Alpha Cleaning Services` — *"Free Estimate"*), `PROV_B4_010` (`DelmanExpert Pest Control` — *"Get free quotes"*), `PROV_B4_012` (`Crystal Pure Water` — *"Please Fill this Form to Get Quotation"*), `PROV_B4_022` (`V Clean and Care Solution` — *"Get a Free Site Inspection & Estimation"*), `PROV_B4_024` (`Sriram pest control & home cleaning.` — *"Get quote"*), and `PROV_B4_031` (`Vishwakarma Woodwork Design Studio` — *"Contact us today for a free consultation"*). |
| `PRICE_NOT_PUBLISHED` | 11 | 13 | **24** | Local technicians and service firms that do not publish numeric tariffs on public web pages or Google Maps profiles. Where customer reviews mention anecdotal prices paid (e.g., `₹2,500` for AC gas refilling at `Hi-Tech Air conditioning & REFRIGERATION`, `₹5,000` for customized home deep cleaning at `Alpha Cleaning Services`, or `~₹6,500` for a 3BHK deep clean at `Home Care Cleaning services`), those figures are documented in `notes`/`missing_information` and never recorded as official published tariffs. |
| `FIXED` / `PRICE_RANGE` / `HOURLY` | 0 | 0 | **0** | No shortlisted Batch 4 provider published a static fixed-rate, range, or hourly rate card on accessible pages. |

### B. Breakdown by `availability_status`

| `availability_status` | HSR Layout | Marathahalli | Total Records | Rationale |
| :--- | :---: | :---: | :---: | :--- |
| `UNKNOWN` | 16 | 16 | **32** | All 32 records are set to `UNKNOWN`. While most listings display general operating hours on Google Maps (including several 24-hour emergency plumbers and electricians), static business hours do not verify real-time technician dispatch availability for a specific booking slot. |
| `CONFIRMED_AVAILABLE` / `CONFIRMED_UNAVAILABLE` | 0 | 0 | **0** | None. |

---

## 6. Explicit Area-Coverage Evidence (`32 / 32` Records)

Every single record (`32 / 32`, `100%`) carries explicit, verifiable evidence of serving `HSR Layout, Bengaluru` or `Marathahalli, Bengaluru` in `area_coverage_evidence_url`:

* **HSR Layout (`16 / 16` records):**
  * **15 providers** have verified physical premises directly inside `HSR Layout, Bengaluru` (`PIN 560102`), spanning Sector 1 (`GBJ Plumbing Services`, `Hi-Tech Air conditioning & REFRIGERATION`, `Kaluram Mali chouhan electrician`, `We Assist`, `Sweet Water Purifier Services`), Sector 2 (`Jagan plumber`, `Sri Electrician Service`, `Wood Style Interiors`), Sector 5 (`Ujala pest control`), Sector 6 (`V3 CARE`), Sector 7 (`A C service expert cooling solutions`, `DelmanExpert Pest Control`, `Crystal Pure Water`, `Quick Carpenter Banglore`), and HSR Layout ITI Layout/Somasundarapalya (`Alpha Cleaning Services`).
  * **1 cross-batch provider** (`PROV_B3_025` `Smart Services`, located on the adjacent Bommanahalli/Devarachikkanahalli border `560076`) surfaced at `#2` in the Google Maps spatial search for HSR Layout appliance repair and serves the Bommanahalli–BTM–HSR corridor.
* **Marathahalli (`16 / 16` records):**
  * **14 providers** have verified physical addresses directly inside the `Marathahalli, Bengaluru` postal zone (`PIN 560037`), spanning Marathahalli Market (`Pureit Water Purifier service | Aquaguard Service in Bangalore` / `rowaterrepair.in`), Aswath Nagar / LRDE Layout (`Home Care Cleaning services`, `DK interior carpenter service`), Krishna Reddy Layout (`V Clean and Care Solution`), Munnekolala (`Shree AC Control Pvt Ltd`, `Darshitha Quick Home Services`, `Sriram pest control & home cleaning.`, `Balaji refrigeration`), AECS Layout (`Excellent cool service point`), Kundalahalli Colony (`SRI RAM PLUMBING MAINTENANCE SERVICES BANGALORE`), Doddanekundi (`VIKAS ELECTRICAL SERVICES`, `I.M.I Pest Control`), Vignan Nagar (`Darshit Plumbing Services and Contractors`), and Yemalur (`Vishwakarma Woodwork Design Studio`).
  * **2 border providers** (`PIN 560066` / `560037` boundary) have explicit Marathahalli coverage proof:
    * `PROV_B4_026` (`Shivaloka service center`) is at the Thubarahalli ICICI Bank Bus Stop (on the Marathahalli–Whitefield border), and its official website ([shivaloka.grabsontechnology.com](https://shivaloka.grabsontechnology.com/)) explicitly lists `Bengaluru, Karnataka 560037` as its service address.
    * `PROV_B4_028` (`Pearl Infotech`) is at Kundalahalli Signal on Varthur Main Road, and both its official Google Maps business description (*"Authorized Sales & Service Partner for Kent Ro Systems Ltd at Marathahalli in Bangalore East since 2013"*) and its Justdial listing ([Pearl Infotech Kent Ro Authorized in Marathahalli](https://www.justdial.com/Bangalore/Pearl-Infotech-Kent-Ro-Authorized-Behind-Mayor-Restaurant-Marathahalli/080PXX80-XX80-140605092022-K5I2_BZDET)) explicitly verify Marathahalli coverage.

---

## 7. Service-Specific Coverage Verification (`32 / 32` Records)

All `32 / 32` records have verified service-specific evidence matching their assigned category. In particular, strict verification was applied to Category 6 (`Appliance repair — washing machines, refrigerators and microwaves`):

* **Strict 3-Appliance Verification in HSR Layout:**
  * `PROV_B4_011` (`We Assist`): Official Google Maps business description explicitly states: *"We offer washing machine repair, AC repair and service, refrigerator repair, TV repair, microwave oven repair, dishwasher repair, water purifier (RO) service..."*
  * `PROV_B3_025` (`Smart Services`): Official website ([bangaloreappliancefix.in](https://www.bangaloreappliancefix.in/)) and dated Google Maps customer reviews (`2026-01-13` to `2026-07-12`) explicitly confirm repairs across **refrigerators**, **washing machines**, and **microwave ovens**.
  * *Excluded Candidate Example:* `Galaxy Service Center` (HSR Layout Sector 2, `4.9` rating, `252` reviews) surfaced at `#1` on Google Maps for HSR Layout appliance repair, but its official business description (*"trusted destination in Bengaluru for professional and affordable home appliance repair services. Specializing in refrigerators and washing machines..."*) and accessible reviews only confirmed refrigerators and washing machines, with no mention of microwave ovens. Rather than assuming microwave coverage, `Galaxy Service Center` was excluded from the top 2 in favor of `We Assist` and `Smart Services`.
* **Strict 3-Appliance Verification in Marathahalli:**
  * `PROV_B4_026` (`Shivaloka service center | Refrigerator Repair | Microwave Repair | Washing Machine Repair | Installation & Maintenance`): Both the official website ([shivaloka.grabsontechnology.com](https://shivaloka.grabsontechnology.com/)) and accessible Google reviews (`2025-09-16`, `2026-10-02`) explicitly verify **Refrigerator Repair**, **Microwave Repair**, and **Washing Machine Repair**.
  * `PROV_B4_027` (`Balaji refrigeration`): Corroborated across Google Maps, Justdial, and Sulekha in Marathahalli (`560037`), with accessible customer reviews (`2023-04-10`, `2023-04-18`, `2023-12-27`, `2025-01-09`) explicitly confirming home technician diagnostic visits and spare parts for **refrigerators**, **washing machines**, **air conditioners**, and **microwave ovens**.

---

## 8. Ratings, Review Counts & Accessible Review Text Summary (`32 / 32` Records)

All `32 / 32` records include verified `Google Maps` ratings, review counts, and qualitative summaries synthesized strictly from the original review text returned by the `google_maps_tool:find_places` tool:

* **Records with Verified Google Rating & Review Count:** `32 / 32` (`100%`)
* **Records with Accessible Original Review Text Snippets:** `32 / 32` (`100%`)
* **Total Cumulative Google Reviews Across 32 Providers:** `15,826` reviews (ranging from `29` reviews for `Shree AC Control Pvt Ltd` up to `5,319` reviews for `Pearl Infotech` and `4,576` reviews for `V3 CARE`).
* **Total Accessible Original Review Snippets Analyzed:** `183` individual review snippets (`4` to `11` accessible reviews per provider, spanning `2022-03-19` to `2026-10-08`).
* **Records with Documented Negative Themes in Accessible Snippets (`4` records):**
  1. `PROV_B4_003` (`Hi-Tech Air conditioning & REFRIGERATION`, HSR Layout): One review (`2026-09-11`) reported paying `₹2,500` for AC gas refilling after which the AC stopped cooling within one month.
  2. `PROV_B4_008` (`Alpha Cleaning Services`, HSR Layout): One review (`2023-11-14`) complained that a cleaning staff member chewed and spat tobacco into the kitchen and bathroom sinks.
  3. `PROV_B4_024` (`Sriram pest control & home cleaning.`, Marathahalli): One review (`2024-07-27`) reported that despite a guarantee that German cockroaches would be completely wiped out, the reduction was bare minimal after treatment.
  4. `PROV_B4_030` (`DK interior carpenter service`, Marathahalli) & `PROV_B4_031` (`Vishwakarma Woodwork Design Studio`, Marathahalli): One review (`2024-07-04`) for `DK interior carpenter service` stated that a more professional carpenter could be hired at the same price; one review (`2026-05-18`) for `Vishwakarma Woodwork Design Studio` noted a slight delivery delay alongside praise for amazing finishing.

---

## 9. Cross-Batch Deduplication & Prior-Batch Overlaps

All `96` records (`82` unique businesses) from **Batch 1** (`Kengeri` & `RR Nagar`), **Batch 2** (`Vijayanagar` & `Jayanagar`), and **Batch 3** (`JP Nagar` & `BTM Layout`) were systematically cross-checked against Batch 4 candidates by business name, phone number, website domain, and Google Place ID. **Zero duplicate checks were left uncompleted.**

### A. Prior-Batch Provider Reused in `nammaserve_batch4_providers.csv`

| Reused `provider_id` | `duplicate_group_id` | Business Name | Prior Batch Appearance | Batch 4 Appearance | Matching Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PROV_B3_025` | `DUP_SMS_01` | `Smart Services` | Batch 3 (`BTM Layout, Bengaluru` — Appliance Repair) | Batch 4 (`HSR Layout, Bengaluru` — Appliance Repair, Rank 2) | Exact match on Google Place ID (`ChIJJdib89kUrjsRz6s_HZTLSj8`), phone (`+91 99458 90113`), website (`https://www.bangaloreappliancefix.in/`), and Bommanahalli address (`560076`). |

### B. Additional Prior-Batch Providers Surfaced During Batch 4 Discovery

Eight additional providers from Batches 1–3 surfaced in our HSR Layout and Marathahalli search/Maps queries. Because each combination already had two strong local specialists (or because a local specialist was prioritized over a city-wide platform), these overlaps are documented below for master database linking:

| Prior `provider_id` | `duplicate_group_id` | Business Name | Prior Batch(es) | Batch 4 Area & Category Surfaced | Evidence & Disposition |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PROV_B3_016` | `DUP_RPS_01` | `Rupachandra Plumbing Services` | Batch 3 (`BTM Layout` — Plumbing) | `HSR Layout` — Plumbing | Surfaced at `#3` on Google Maps (`ChIJ04mC2SwVrjsRF98_R8H8vH4`, phone `+91 79759 06236`) with a review stating *"Best plumbing services around BTM HSR area"*. Retained `Jagan plumber` and `GBJ Plumbing Services` (both physically inside HSR Layout `560102`) as Ranks 1–2. |
| `PROV_B1_008` | `DUP_TST_01` | `TechSquadTeam` | Batch 1 (`Kengeri`, `RR Nagar`) & Batch 2 (`Jayanagar`) | `Marathahalli` & `HSR Layout` — House Cleaning | Surfaced on Google Maps (`ChIJ9432efETrjsRbeSTeNuH-K0`, Neil Rao Towers, Whitefield) and via dedicated area page ([techsquadteam.com/deep-home-cleaning-in-marathahalli-bangalore](https://techsquadteam.com/deep-home-cleaning-in-marathahalli-bangalore), publishing starting price `₹3,300` / 1BHK at `₹3,600`). Retained two local Marathahalli-based specialists (`V Clean and Care Solution` and `Home Care Cleaning services`) as Ranks 1–2. |
| `PROV_B1_002` | `DUP_UC_01` | `Urban Company` | Batch 1 (`Kengeri`, `RR Nagar`) | `HSR Layout` & `Marathahalli` — Plumbing / Electrical | Surfaced via dedicated area pages ([urbancompany.com/bangalore-plumbers-hsr-layout](https://www.urbancompany.com/bangalore-plumbers-hsr-layout), [urbancompany.com/bangalore-plumbers-marathahalli](https://www.urbancompany.com/bangalore-plumbers-marathahalli), [urbancompany.com/bangalore-electricians-marathahalli](https://www.urbancompany.com/bangalore-electricians-marathahalli)). Local businesses with direct phone numbers were prioritized. |
| `PROV_B3_023` | `DUP_PCS_01` | `Pest Control Solutions` | Batch 3 (`BTM Layout` — Pest Control) | `HSR Layout` — Pest Control | Surfaced at `#3` on Google Maps (`ChIJfTbf0fEVrjsRRgP2t03uRGo`, Begur Main Rd, Bommanahalli `560068`, phone `+91 98442 66200`). Retained two HSR Layout `560102` specialists (`Ujala pest control` and `DelmanExpert Pest Control`). |
| `PROV_B3_008` | `DUP_IPC_01` | `Integrated Pest Control Pvt. Ltd.` | Batch 3 (`JP Nagar`, `BTM Layout` — Pest Control) | `HSR Layout` — Pest Control | Surfaced on Google Maps (`ChIJoU8rQdcVrjsRFhH9C2r-yfk`, BTM 2nd Stage `560076`, phone `+91 99869 10557`). |
| `PROV_B1_018` | `DUP_FPC_01` | `Falcon pest control` | Batch 1 (`RR Nagar`) & Batch 2 (`Vijayanagar`, `Jayanagar`) | `HSR Layout` — Pest Control | Surfaced on Google Maps (`ChIJ87T16NoVrjsROm0a4e8t5N0`, Roopena Agrahara, Bommanahalli `560068`, phone `+91 85535 12415`). |
| `PROV_B3_010` | `DUP_ALA_01` | `AL Appliance Repair` | Batch 3 (`JP Nagar` — Appliance Repair) | `HSR Layout` — Appliance Repair | Surfaced on Justdial HSR Layout Sector 2 microwave/washing machine repair directory (`080PXX80-XX80-201116211531-K1X4`). |
| `PROV_B3_029` | `DUP_WLC_01` | `Wood Living | Carpenter` | Batch 3 (`BTM Layout` — Carpentry) | `HSR Layout` — Carpentry | Surfaced on Google Maps (`ChIJf2c8CscVrjsR7_P0T4w2g5w`, BTM 1st Stage `560068`, phone `+91 88844 43381`) for HSR Layout carpentry. |

### C. Intra-Batch Multi-Category Overlap Noted (Not Duplicated)

* `PROV_B4_018` (`Excellent cool service point`, ITPL Main Rd, AECS Layout, Marathahalli `560037`) surfaced in both the Marathahalli `AC repair and servicing` query and the Marathahalli `Appliance repair` query (as it also repairs refrigerators and washing machines). However, because its accessible listings did not explicitly verify **microwave oven** repair, it was recorded solely under `AC repair and servicing` (`PROV_B4_018`), while `Shivaloka service center` (`PROV_B4_026`) and `Balaji refrigeration` (`PROV_B4_027`) — both with verified 3-appliance coverage — were selected for `Appliance repair`.

---

## 10. Important Evidence Gaps & Records Requiring Follow-Up

1. **Unpublished Rate Cards (`24 / 32` records `PRICE_NOT_PUBLISHED`, `7 / 32` `QUOTATION_REQUIRED`):**
   * Only `1` provider in Batch 4 (`PROV_B4_015` `Wood Style Interiors`) publishes a static numeric package starting price (`₹3,99,000` for 2BHK home interior woodwork). NammaServe onboarding teams will need to collect standard inspection/visitation fees and item-level rate cards directly from the remaining `31` providers.
2. **Missing Public Email Addresses (`27 / 32` records):**
   * Only `5` providers publish a verifiable public email address on their official websites (`V3 CARE` `info@v3care.in`, `Alpha Cleaning Services` `info@alphacleaningservices.in`, `We Assist` `care@we-assist.in`, `Crystal Pure Water` `wecare@crystalpurewater.in`, and `Sweet Water Purifier Services` `sweetwater@gmail.com`). The remaining `27` providers rely on phone calls, WhatsApp, or web callback forms.
3. **Single-Source (`DISCOVERED`) Records Requiring Secondary Verification (`3` records):**
   * `PROV_B4_001` (`Jagan plumber`, HSR Layout), `PROV_B4_009` (`Ujala pest control`, HSR Layout), and `PROV_B4_019` (`Shree AC Control Pvt Ltd`, Marathahalli) should be prioritized for phone/KYC verification during NammaServe onboarding because they lack accessible secondary directory profiles or crawlable websites.
4. **Quality & Service-Guarantee Follow-Up Flagged by Customer Reviews (`4` records):**
   * `PROV_B4_003` (`Hi-Tech Air conditioning & REFRIGERATION`): Verify post-service warranty terms on AC gas refilling following aSeptember 2026 review reporting cooling failure within a month of a `₹2,500` refill.
   * `PROV_B4_008` (`Alpha Cleaning Services`): Verify on-site staff hygiene compliance protocols following a review noting tobacco spitting in a customer's sink.
   * `PROV_B4_024` (`Sriram pest control & home cleaning.`): Verify re-service SLA for German cockroach treatments.
   * `PROV_B4_029` (`Pureit Water Purifier service | Aquaguard Service in Bangalore` / `rowaterrepair.in`): Although the Google Maps listing name includes brand names (`Pureit`, `Aquaguard`), the provider's official website (`rowaterrepair.in`) explicitly states that it is an independent multi-brand service provider and *"not presented as an authorized service center for any specific brand."* NammaServe should display it clearly as an independent multi-brand technician rather than an authorized brand center.

---

## 11. Combinations with Fewer Than Two Suitable Providers

* **Count:** `0` combinations.
* Every one of the `16` assigned area–category combinations in `HSR Layout, Bengaluru` and `Marathahalli, Bengaluru` had at least `2` genuine, area-verified providers supported by primary location and service evidence.

---

## 12. Source-Access Limitations & Unverified Information

1. **Google Maps Review Sampling Cap:**
   * The `google_maps_tool:find_places` tool returns between `4` and `7` representative review snippets per business per query (`183` total snippets accessed across `15,826` total Google reviews). Review summaries, positive/negative themes, and date ranges in `nammaserve_batch4_providers.csv` reflect **only** those accessible review snippets and do not claim exhaustive coverage of all historical reviews.
2. **Website Crawler Blocks on 4 Provider Domains:**
   * Direct automated browsing (`google:browse`) was blocked or restricted on four provider URLs: `https://www.we-assist.in/` (corroborated via indexed subpages `we-assist.in/contact.php` and `we-assist.in/about.php` in Google Search), `https://www.delmanexpert.com/pest-control-services-in-bangalore/` (corroborated via Sulekha and Hidoot), `https://sites.google.com/view/gbjplumbingservicesinbangalore/home` (corroborated via Google Search snippet and Justdial), and `https://shreeacservices.in/` (recorded as `DISCOVERED` / `MEDIUM` confidence).
3. **Interactive Booking Price Flows:**
   * Providers such as `V3 CARE` (`https://v3care.in/`) require interactive city/service selection and phone OTP or cart progression to view exact BHK cleaning tariffs; because research rules prohibit creating accounts or submitting fake bookings, `price_type` was recorded as `PRICE_NOT_PUBLISHED`.
4. **What Was Not Independently Verified:**
   * Real-time technician slot availability, background-verification certificates of individual field staff, trade licenses/GSTIN registrations (except `Wood Style Interiors Pvt Ltd`, whose CIN `U74102KA2024PTC190383` was publicly indexed), and unpublished phone-quoted prices were not independently verified.
