# NammaServe AI Intent Extraction Evaluation (v1)

## 1. Overview

AI Evaluation v1 provides a deterministic, reproducible evaluation harness for NammaServe's natural language civic query $\rightarrow$ `ServiceIntent` extraction pipeline.

It measures how accurately the primary (`Groq`) or fallback (`Gemini`) LLM extracts structured parameters (service category, Bengaluru locality, numeric capacity, and urgency) from citizen requests before calling deterministic discovery tools.

---

## 2. Golden Dataset: `intent_eval_v1`

The golden dataset is versioned at [`backend/app/services/nammaserve/ai/evaluation/datasets/intent_eval_v1.json`](file:///c:/Users/dhanu/OneDrive/Desktop/NammaNexus-AI/backend/app/services/nammaserve/ai/evaluation/datasets/intent_eval_v1.json).

It contains 20 curated evaluation cases representing realistic civic queries across Bengaluru:
- **Service Categories**: Water tanker delivery, solar water-heater repair, e-waste recycling, emergency locksmith, construction debris / bulk waste removal.
- **Localities**: Kengeri, Indiranagar, HSR Layout, Koramangala, Whitefield, Jayanagar, Malleswaram, Hebbal, Yelahanka, Marathahalli, Electronic City, Banashankari, Bellandur, BTM Layout, Rajajinagar, Kammanahalli, Sarjapur, Domlur, Richmond Town.
- **Variations**: Abbreviated capacities (`4000L`, `10000 litres`), missing capacities, missing locations, emergency urgency keywords (`ASAP`, `locked out`, `24x7`, `immediately`), conversational phrasing, and non-urgent standard requests.

---

## 3. Evaluation Metrics

Every evaluation case is compared against ground truth on four core dimensions:

1. **Service Accuracy**: Percentage of cases where the extracted service matches the expected canonical category or alias.
2. **Location Accuracy**: Percentage of cases where the extracted Bengaluru locality correctly matches (case- and whitespace-normalized).
3. **Capacity Accuracy**: Percentage of cases where numeric litre volume matches expected value (or both are `None`).
4. **Urgency Accuracy**: Percentage of cases where the boolean emergency/urgency flag matches.
5. **Total Field Accuracy**: Percentage of total evaluated fields across the dataset that match expected values ($\frac{\text{correct fields}}{\text{total cases} \times 4}$).
6. **Case Pass Rate**: Percentage of cases where **all four** core fields match simultaneously.

---

## 4. Key Architectural Decisions

### A. Isolated / Disabled Intent Cache
In production, `IntentCache` avoids repeated LLM calls for identical queries. During evaluation, caching is **explicitly disabled** (`IntentCache(enabled=False)`) so that every test case exercises actual intent extraction rather than serving cached results.

### B. Deterministic Scoring (No LLM-as-a-Judge)
Scoring relies purely on deterministic string normalization, canonical alias maps, numeric tolerance comparison, and boolean matching.
- **Why?** It is 100% reproducible, has zero extra latency or API cost, and eliminates judge hallucination.
- **Future Work**: LLM-as-a-judge or semantic similarity may be introduced in later milestones for unstructured response tone or conversational groundedness, but structured intent extraction is best evaluated deterministically.

### C. Provider & Telemetry Transparency
The runner listens to [`InMemoryTelemetryHandler`](file:///c:/Users/dhanu/OneDrive/Desktop/NammaNexus-AI/backend/app/services/nammaserve/ai/telemetry.py) to report the exact provider (`groq`/`gemini`), model, and latency recorded per evaluation case.

---

## 5. How to Run Evaluation

### Manual Developer Run:
From the backend directory:
```bash
python -m app.services.nammaserve.ai.evaluation
```

### Example Console Output:
```
==================================================
NammaServe AI Intent Extraction Evaluation
==================================================
Dataset:            intent_eval_v1
Provider/Model:     groq (llama-3.3-70b-versatile)
Timestamp:          2026-10-05T08:20:00.000000+00:00
Total Cases:        20
Passed Cases:       20
Failed Cases:       0
--------------------------------------------------
Case Pass Rate:     100.0%
Service Accuracy:   100.0%
Location Accuracy:  100.0%
Capacity Accuracy:  100.0%
Urgency Accuracy:   100.0%
Total Field Acc:    100.0%
==================================================
```

---

## 6. Scope Boundaries

This milestone focuses exclusively on **natural language $\rightarrow$ ServiceIntent accuracy**.
It does **NOT** evaluate:
- Provider search / RankingEngine retrieval relevance
- External Google Places API output
- Final grounded response synthesis or conversational hallucination
These will be addressed in future dedicated evaluation layers.
