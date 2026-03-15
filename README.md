# GutSense — Continuous Colorectal Cancer Screening Platform

> **TL;DR**
> - A toilet-mounted biosensor reads 8 stool biomarkers at every visit and streams them to a neural-network risk-scoring engine
> - An AI model (Claude) converts the numbers into plain-language reports for patients and clinical summaries for physicians — enriched by similar historical cases retrieved from a vector database (IRIS)
> - Catches colorectal cancer years earlier than a once-a-decade colonoscopy, passively and non-invasively

---

## Table of Contents

1. [What Is GutSense?](#1-what-is-gutsense)
2. [The Problem It Solves](#2-the-problem-it-solves)
3. [How It Works — Step by Step](#3-how-it-works--step-by-step)
4. [The 8 Biomarkers](#4-the-8-biomarkers)
5. [The Risk Score — How 0–100 Is Calculated](#5-the-risk-score--how-0100-is-calculated)
6. [The AI & RAG Layer](#6-the-ai--rag-layer)
7. [The Demo Patients](#7-the-demo-patients)
8. [Full Data Journey: From Sensor to Screen](#8-full-data-journey-from-sensor-to-screen)
9. [What the Patient Sees](#9-what-the-patient-sees)
10. [What the Physician Sees](#10-what-the-physician-sees)
11. [Alerts](#11-alerts)
12. [How to Run the Project](#12-how-to-run-the-project)
13. [Project Structure](#13-project-structure)
14. [Technology Stack](#14-technology-stack)
15. [Scientific References](#15-scientific-references)

---

## 1. What Is GutSense?

GutSense is a continuous colorectal cancer (CRC) early-detection platform. A sensor pad installed in a standard toilet measures eight molecular biomarkers from a patient's stool at every bathroom visit. Those readings are automatically sent to GutSense's server, scored by a neural network risk model, and surfaced on two dashboards — one designed for patients, one for their physicians.

The key insight: colorectal cancer develops slowly over 10–15 years from a benign polyp to an invasive tumor. That long window is exactly where passive, continuous monitoring can intercept it. GutSense turns every bathroom visit into a data point — creating a movie of gut health instead of a snapshot every decade.

---

## 2. The Problem It Solves

Colorectal cancer is the **second leading cause of cancer death** in the United States.<sup>[1](#ref1)</sup> Yet when caught at the localized (early) stage, the **5-year survival rate exceeds 91%**.<sup>[2](#ref2)</sup> The challenge is detection: most CRC is found late, because standard screening (colonoscopy) is recommended only every 10 years and has low adherence.

The biology actually works in our favor. The adenoma-to-carcinoma sequence — the progression from a harmless polyp to colorectal cancer — takes roughly **10 years**.<sup>[3](#ref3)</sup> That is a long interception window. The problem is that no tool has continuously watched that window, until now.

GutSense monitors the gut passively, every day, without any behavior change required from the patient.

---

## 3. How It Works — Step by Step

```
┌─────────────────┐     ┌──────────────────────────────┐     ┌──────────────────┐
│  Toilet Sensor  │────▶│       GutSense Server        │────▶│    Dashboard     │
│  (8 biomarkers) │     │  NN score + IRIS RAG + AI    │     │  Patient / MD    │
└─────────────────┘     └──────────────────────────────┘     └──────────────────┘
```

**Step 1 — Sensor reads stool**
A toilet-mounted sensor pad measures eight molecular biomarkers in the stool sample (detailed in Section 4). This happens automatically; the patient does nothing.

**Step 2 — Reading is transmitted**
The sensor sends the eight values to the GutSense backend server as a single data packet (`POST /api/ingest`).

**Step 3 — Biomarker scores computed**
Each of the 8 raw biomarker values is converted to a 0–100 component score using validated sigmoid curves (e.g., hemoglobin FIT: sigmoid midpoint 50 ng/mL). This is pure math — deterministic and fast.

**Step 4 — Similar patients retrieved (SQLite kNN)**
The system finds the 3 most similar historical patients in its own database using normalized Manhattan distance across all 8 biomarker dimensions. Their risk scores are extracted as context features for the neural network.

**Step 5 — Neural network scores the reading**
A small neural network (13 inputs → 32 → 16 → 1 output) combines the 8 component scores, patient age, family history flag, and the 3 similar-patient scores into a final 0–100 risk score. Lifestyle factors (antibiotics, fiber intake) are applied as interpretable overrides after the NN output.

**Step 6 — Trend analyzed**
The system looks at the past 14 readings and fits a trend line: Stable / Slowly Increasing / Rapidly Increasing / Improving.

**Step 7 — Alerts triggered (if warranted)**
If the adjusted score crosses 60, an alert is created for the physician. Alerts are suppressed if the patient recently took antibiotics.

**Step 8 — AI writes plain-language reports (background)**
In a parallel background thread, Claude (Anthropic's AI) receives the biomarker values, risk score, and trend. Before writing, it queries **IRIS** (InterSystems' health data platform) for semantically similar historical cases — adding real clinical context to its reasoning. It produces a patient explanation, physician summary, and prioritized next steps.

**Step 9 — Dashboards update**
Both dashboards refresh every 10 seconds. New readings, updated scores, AI text, and physician notes appear without any page reload.

**Step 10 — Physician acts**
The physician reviews the score breakdown, reads the AI summary, leaves clinical notes, and can generate a formal **GI referral letter** (written by Claude) with one click.

---

## 4. The 8 Biomarkers

Each biomarker was selected because it has peer-reviewed evidence linking it to colorectal cancer or precancerous conditions. Together they cover three independent biological mechanisms: inflammation/immune response, tissue destruction, and occult bleeding.

| Biomarker | What it measures | Normal | Alarm | Weight | Evidence |
|---|---|---|---|---|---|
| **Hemoglobin FIT** | Microscopic blood in stool (fecal immunochemical test) — the most validated single non-invasive CRC signal | < 10 ng/mL | > 100 ng/mL | **25%** | [Lee et al.](#ref6) |
| **Calprotectin** | A protein released by neutrophils during intestinal inflammation — gold standard for mucosal inflammation | < 50 µg/g | > 200 µg/g | **20%** | [Roseth et al.](#ref8) |
| **MMP-9** | Matrix metalloproteinase-9: an enzyme that degrades the extracellular matrix, enabling tumor invasion and spread | < 30 ng/mL | > 150 ng/mL | **15%** | [Liabakk et al.](#ref9) |
| **MPO** (Myeloperoxidase) | Produced by neutrophils during oxidative stress — a marker of acute inflammatory activity in the gut wall | < 100 ng/mL | > 500 ng/mL | **15%** | [Kruidenier et al.](#ref10) |
| **MMP-8** | Neutrophil collagenase — elevated in pre-malignant lesions and correlates with CRC aggressiveness | < 30 ng/mL | > 150 ng/mL | **10%** | [Saarialho-Kere et al.](#ref11) |
| **Fibrinogen** (fecal) | An acute-phase coagulation protein elevated during active intestinal inflammation and CRC | < 100 ng/mL | > 400 ng/mL | **8%** | [Mosesson et al.](#ref12) |
| **Haptoglobin** (fecal) | Binds free hemoglobin released during GI bleeding — elevated in occult and overt GI blood loss | < 50 µg/g | > 200 µg/g | **5%** | [Shastri et al.](#ref13) |
| **PGRP-S** | Peptidoglycan recognition protein — innate immunity peptide; elevated when gut bacteria dysregulate mucosal defense | < 20 ng/mL | > 100 ng/mL | **2%** | [Lu et al.](#ref14) |

> **Why these eight?** Together they capture the full cascade of CRC development: occult bleeding (Hemoglobin FIT, Haptoglobin), inflammation (Calprotectin, MPO, Fibrinogen), tissue remodeling/invasion (MMP-9, MMP-8), and innate immune disruption (PGRP-S). Elevations across multiple mechanisms are far more specific than any single marker alone.

---

## 5. The Risk Score — How 0–100 Is Calculated

The GutSense risk score is a two-stage model: interpretable feature engineering followed by a small neural network.

### Stage 1: Per-Biomarker Component Scores (Feature Engineering)

Each raw biomarker value is run through a sigmoid curve that converts it to a 0–100 component score. The sigmoid is parameterized with a clinical midpoint and steepness calibrated to each marker's reference range:

| Biomarker | Sigmoid midpoint | Steepness |
|---|---|---|
| Hemoglobin FIT | 50 ng/mL | 0.040 |
| Calprotectin | 120 µg/g | 0.025 |
| MMP-9 | 80 ng/mL | 0.040 |
| MPO | 280 ng/mL | 0.012 |
| MMP-8 | 80 ng/mL | 0.040 |
| Fibrinogen | 230 ng/mL | 0.012 |
| Haptoglobin | 110 µg/g | 0.030 |
| PGRP-S | 55 ng/mL | 0.060 |

Higher raw value → higher component score (0–100) for all eight markers.

### Stage 2: Neural Network Scoring

A small multi-layer perceptron (MLP) produces the final risk score. The NN was trained on 5,000 synthetic patient samples generated from the GutSense biomarker simulator.

**Input features (13 total):**

| Feature | Description |
|---|---|
| Component scores × 8 | Sigmoid-transformed biomarker values (0–100 each) |
| Age / 80 | Patient age normalized to [0, 1] |
| Family history | Binary flag (0 or 1) |
| RAG score × 3 | Risk scores of the 3 most similar historical patients (SQLite kNN lookup) |

**Architecture:** `13 → Dense(32, ReLU) → Dense(16, ReLU) → Dense(1) → clamp [0, 100]`

The RAG scores (similar patients) allow the model to reason comparatively: "patients with this biomarker profile typically score in the 70s." When no historical data exists yet, they default to the neutral value of 50.

### Stage 3: Lifestyle Adjustments

After the NN output, two interpretable overrides are applied:

| Factor | Adjustment |
|---|---|
| Recent antibiotic use | −10 points (antibiotics temporarily disrupt mucosal markers — not disease) |
| High fiber diet (≥ 25g/day) | −3 points (protective effect on mucosal inflammation) |

### Stage 4: Risk Level Assignment

| Score | Level | Color |
|---|---|---|
| 0–30 | Low Risk | 🟢 Green |
| 31–60 | Elevated | 🟡 Yellow |
| 61–80 | High Risk | 🟠 Orange |
| 81–100 | Critical | 🔴 Red |

> **Production note:** The NN is currently trained on synthetic labels derived from the sigmoid formula itself, so it approximates (and refines) the formula-based output. In a production system, labels would come from real clinical outcomes — colonoscopy results, biopsy findings, CRC diagnoses — and the architecture would remain identical while the learned weights would reflect actual clinical ground truth.

---

## 6. The AI & RAG Layer

GutSense uses a two-tier AI system: a fast retrieval layer that finds similar historical cases, and Claude (Anthropic's AI) that synthesizes everything into human language.

### Tier 1: Retrieval-Augmented Generation via IRIS

Before Claude writes anything, GutSense queries **InterSystems IRIS** — a health data platform with built-in vector search capabilities.

Each historical patient reading is stored in IRIS as a FHIR-formatted clinical observation (e.g., *"64-year-old male, positive family history. Risk score: 82/100, Hgb-FIT: 145 ng/mL, calprotectin: 310 µg/g..."*). These observations are embedded as dense vectors using OpenAI's embedding model and stored with the `VECTOR` datatype, enabling IRIS to perform cosine similarity search.

When a new reading arrives, GutSense:
1. Builds a FHIR-style clinical text for the current patient
2. Embeds it via OpenAI
3. Runs `VECTOR_COSINE()` against the IRIS observation store
4. Retrieves the top-3 most semantically similar historical cases with their outcomes

This context is pooled into Claude's prompt: *"Similar historical cases: ORANGE risk (score 79), rising trajectory — outcome: GI consultation, no malignancy found at colonoscopy."*

As each new reading is processed, it is stored back into IRIS — so the RAG pool grows with every patient visit.

### Tier 2: Claude Narrative Generation

Claude (Sonnet 4.6) receives: all 8 biomarker values with reference ranges, the risk score, the 7-day trend, any lifestyle confounders, the patient's demographics, and the IRIS-retrieved similar cases. It produces three structured outputs via tool use:

1. **Patient explanation** — 2–3 sentences in plain English. No medical jargon. Tells the patient what their reading means and whether to be concerned.

2. **Physician summary** — 4–5 sentences of clinical language. References specific marker values, compares to reference ranges, and suggests an action timeline.

3. **Next steps** — A short prioritized list of recommended actions (e.g., "Schedule GI consultation within 3 months").

**Referral letter generation:** Physicians can generate a formal GI specialist referral letter with one click. Claude writes it in standard medical letter format — date, header, clinical findings paragraph, urgency, and signature line — based on the patient's full biomarker and risk data.

**Resilience:** If Claude is unavailable for any reason, the system automatically uses pre-written, medically accurate fallback text that varies by risk level. The app never shows an error or blank screen to the user.

---

## 7. The Demo Patients

The demo database includes **15 patients** spanning the full clinical spectrum, designed to demonstrate the platform across all risk levels:

### Core 5 Patients (original cohort)

| Patient | Age | Sex | Profile | Key Features |
|---|---|---|---|---|
| **Alice Chen** | 45 | F | Healthy baseline | All biomarkers within normal range; consistently green scores |
| **Bob Martinez** | 58 | M | At-risk, drifting upward | Family history of CRC; biomarkers gradually worsening over 90 days |
| **Carol Wang** | 62 | F | At-risk, stable | Mildly elevated calprotectin and MMP-9; consistent yellow |
| **David Kim** | 51 | M | Critical | Family history + NOD2 genetic variant; high Hgb-FIT and MMP-9; red alerts |
| **Emma Johnson** | 38 | F | Healthy young adult | Clean baseline; demonstrates normal ranges for comparison |

### Extended Cohort (10 additional patients)

| Group | Patients | Archetypes |
|---|---|---|
| 🟢 **Healthy** | James Patel (34M), Sophia Rodriguez (41F), Michael Thompson (29M), Lauren Kim (52F) | Normal biomarkers, no family history |
| 🟡 **At Risk** | Robert Harris (55M, family hx), Jennifer Liu (48F, drifting), William Brown (63M, family hx), Patricia Garcia (44F) | Mildly elevated inflammatory markers |
| 🔴 **Critical** | Charles Wilson (67M, family hx + NOD2), Nancy Davis (59F, family hx) | Multiple channels critically elevated |

The extended cohort populates the RAG database, enabling IRIS vector search to find meaningful similar cases from day one.

---

## 8. Full Data Journey: From Sensor to Screen

```
1. App starts for the first time (backend/main.py)
   │
   ├─ Creates database tables (SQLAlchemy models)
   ├─ Trains or loads neural network (nn_risk_model.py → risk_model.joblib)
   ├─ Seeds 15 demo patients into the Patient table
   │
   └─ Launches background thread:
      │
      ├─ 90-DAY BACKFILL (simulator/sensor_simulator.py)
      │   For each of 15 patients:
      │     For each of 90 days × 2 visits/day = 180 visits:
      │       → Generate realistic biomarker values for patient's archetype
      │       → POST to /api/ingest?skip_narrative=true
      │         → Validate patient
      │         → Store BiomarkerReading in SQLite
      │         → SQLite kNN: find top-3 similar patients → rag_scores
      │         → compute_risk_score(reading, age, family_hx, rag_scores)
      │             → 8 sigmoid component scores (feature engineering)
      │             → nn_risk_model.predict(13 features) → adjusted_score
      │             → lifestyle overrides (antibiotics −10, fiber −3)
      │         → compute_trajectory() → "Stable" / "Slowly Increasing" / etc.
      │         → Store RiskAssessment (Claude fields left NULL for speed)
      │         → maybe_create_alert() → store Alert if score ≥ 60
      │   Total: ~2,700 readings inserted in ~60 seconds
      │
      └─ FILL NARRATIVES (main.py → claude_client.py)
          For each of 15 patients:
            → Find most recent RiskAssessment with no narrative
            → Call Claude API with all biomarker + risk context
            → Update RiskAssessment with patient_explanation,
              physician_summary, next_steps, urgency_flag
          Total: up to 15 Claude API calls (one per patient)

2. Live simulation running (simulator/sensor_simulator.py)
   Every 30 seconds, for each patient (staggered 0.5s apart):
     → Generate new reading
     → POST to /api/ingest (full pipeline):
         [sync]  SQLite kNN → NN score → HTTP 201 response (~50ms)
         [async] Background thread:
                   → Build FHIR clinical text
                   → IRIS vector search → top-3 similar historical cases
                   → Claude narrative (enriched with RAG context)
                   → Update RiskAssessment in SQLite
                   → Store new observation in IRIS (joins RAG pool)

3. Frontend polling (every 10 seconds)
   Patient dashboard:
     → GET /api/patients/:id/readings         → biomarker charts update
     → GET /api/patients/:id/risk/latest      → gauge + AI text update
     → GET /api/patients/:id/alerts           → alert banner updates
     → GET /api/patients/:id/notes            → physician notes appear

   Physician portal:
     → GET /api/physician/patients            → risk-sorted roster updates
     → Click patient → score breakdown, full charts, clinical notes
     → "Generate Referral" → POST /api/patients/:id/referral
                          → Claude writes formal GI referral letter
```

---

## 9. What the Patient Sees

The patient dashboard is designed to be reassuring, clear, and actionable — no raw numbers without context.

**Top of page:**
- Their name, age, and a "Live" indicator showing the system is active

**Stats strip:**
- Current risk score (colored 0–100)
- 7-day trend ("Stable", "Improving", "Slowly Increasing", "Rapidly Increasing")
- Time of last reading
- Total days monitored

**Risk gauge:**
- An animated circular dial (like a speedometer) showing their score 0–100
- Color changes from green → yellow → orange → red as risk increases
- The trajectory icon shows a flame (🔥) for rapidly worsening, or a down arrow for improving

**AI explanation:**
- Claude's plain-language interpretation of their latest reading
- If their physician has left a recommendation, it appears here in a blue card

**Health Signal cards:**
- Four plain-English grouped summaries of the 8 underlying biomarkers:
  - **Hidden Blood** — microscopic blood in stool (Hemoglobin FIT + Haptoglobin)
  - **Gut Inflammation** — immune activity in the intestinal lining (Calprotectin + MPO)
  - **Tissue Health** — proteins linked to gut cell breakdown (MMP-9 + MMP-8)
  - **Inflammatory Response** — body-wide gut immune response (Fibrinogen + PGRP-S)
- Each card shows a status badge (Normal / Slightly Elevated / Elevated / High), a plain-English one-liner, and a color progress bar
- A collapsible **"View 90-day trends"** section under each card expands to show the 2 relevant time-series charts, with a plain-language description of what those charts mean
- Each chart shows a dashed green "Normal ≤ X" reference line so the threshold is always immediately visible

**Lifestyle context (collapsible):**
- Three inputs: "Recently took antibiotics" (toggle), "Daily fiber intake" (slider), "Sleep quality" (slider)
- Saving this context adjusts the risk score for the next reading
- A "Recalculate" button re-scores the most recent reading immediately with the new context

---

## 10. What the Physician Sees

### Physician Portal (roster view)

An overview of all patients, sorted highest-risk first.

- **4 summary stats** at the top: total patients, critical count, elevated count, unread alerts
- **Patient cards** color-coded by risk level, each showing:
  - Patient name, age, sex, genetic flags (Family Hx ⚠, NOD2+)
  - Current risk score and level badge
  - 7-day trend
  - Key biomarker snapshot: Hgb-FIT, MPO, Calprotectin, MMP-9
  - Number of unacknowledged alerts

### Patient Detail (single-patient deep dive)

Accessed by clicking any patient card.

- **Same stats strip and gauge as the patient view**, but with physician-level AI text
- **Full biomarker charts** (8 charts) — each showing 90 days of readings with a dashed "Normal ≤ X" reference line so out-of-range readings are immediately apparent
- **Clinical Notes** — the physician can:
  - Write private notes (only visible to physicians)
  - Mark a note as a "Physician Recommendation" — this immediately appears on the patient's dashboard
- **Simulate Spike button** — injects a synthetic critical-level reading for demo purposes
- **Referral button** — generates a formal GI specialist referral letter:
  - Claude writes a complete medical letter (date, findings, urgency, signature line)
  - Physician can review and edit before sending
  - "Quick Send" saves it as a clinical note tagged `[REFERRAL SENT]`

---

## 11. Alerts

Alerts notify physicians when a patient's adjusted risk score crosses a threshold.

**Rules:**
- Fires when adjusted score ≥ 60
- Severity: "Info" (yellow range), "Warning" (orange), "Critical" (red)
- **Deduplication:** only one active alert per severity per patient — no spam
- **Antibiotic suppression:** if the patient reported recent antibiotic use, alerts are suppressed (antibiotics temporarily alter inflammatory markers, not disease state)

**Physician actions:**
- Alerts appear as a banner on both the physician portal and patient detail view
- Clicking the dismiss (✕) button marks the alert as acknowledged and removes it from the active list

---

## 12. How to Run the Project

### Prerequisites
- Python 3.11+
- Node.js 18+
- An Anthropic API key (for Claude AI narratives; optional — the system works without one using fallback text)
- InterSystems IRIS (optional — for vector RAG; gracefully degraded if unavailable)

### Backend

```bash
cd backend
pip install -r requirements.txt

# Set your API key (optional but recommended)
export ANTHROPIC_API_KEY=sk-ant-...

# Start the server (use without --reload for a stable demo)
uvicorn main:app
```

The server starts at **http://localhost:8000**. On first run, it automatically:
1. Creates the SQLite database (`biomarker.db`)
2. Trains the neural network risk model (or loads cached weights from `risk_model.joblib`)
3. Seeds 15 demo patients
4. Runs a 90-day backfill (~2,700 readings, ~60 seconds)
5. Fills AI narratives for each patient's latest assessment

> **Note:** Use `uvicorn main:app` (not `--reload`) for a stable demo. The `--reload` flag restarts the server on any `.py` file change, which interrupts the backfill and live simulator.

The interactive API docs are at **http://localhost:8000/docs**.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at **http://localhost:5173**. The nav bar has two views: **Patient** and **Physician**.

### Reset to Fresh State

```bash
# From inside the backend/ directory:
rm biomarker.db
# Restart the backend — it re-seeds and re-backfills automatically
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(none)* | Required for real Claude narratives; falls back to rule-based text if absent |
| `RISK_ALERT_THRESHOLD` | `60` | Minimum adjusted score to trigger an alert |
| `SIMULATOR_INTERVAL_SECONDS` | `30` | How often the live simulator sends a new reading per patient |
| `API_BASE` | `http://localhost:8000` | Backend URL used by the simulator |

---

## 13. Project Structure

```
MIT_Grand_Hack/
│
├── backend/
│   ├── main.py                         # App startup: seed patients, train NN,
│   │                                   # 90-day backfill, narrative fill, live simulator
│   ├── models.py                       # Database schema: 6 tables (Patient, BiomarkerReading,
│   │                                   # RiskAssessment, Alert, ClinicalNote, LifestyleMetadata)
│   ├── schemas.py                      # API request/response shapes (Pydantic validation)
│   ├── database.py                     # SQLite connection + session management
│   │
│   ├── routers/
│   │   ├── ingest.py                   # POST /api/ingest — core pipeline:
│   │   │                               #   reading → SQLite kNN → NN score → trend → alert
│   │   │                               #   → [background] IRIS RAG → Claude narrative → IRIS store
│   │   ├── physician.py                # Physician endpoints: roster, notes, lifestyle,
│   │   │                               # simulate-spike, recalculate, referral generation
│   │   ├── patients.py                 # Patient endpoints: readings, risk, alerts, notes
│   │   ├── readings.py                 # Reading history endpoints
│   │   ├── risk.py                     # Risk assessment endpoints
│   │   ├── alerts.py                   # Alert management endpoints
│   │   └── iris.py                     # IRIS status, refresh, and observation endpoints
│   │
│   ├── services/
│   │   ├── ai_risk_model.py            # Feature engineering: 8 sigmoid curves → component scores
│   │   │                               # Calls nn_risk_model.predict() for final score
│   │   ├── nn_risk_model.py            # Neural network: 13 inputs → 32 → 16 → 1
│   │   │                               # Trains on 5,000 synthetic samples, caches to .joblib
│   │   ├── claude_client.py            # Claude API: risk narratives + GI referral letters
│   │   │                               # Fallback: medically accurate rule-based text per level
│   │   ├── iris_native.py              # IRIS integration: GutSense patient store + FHIR
│   │   │                               # observation store + vector cosine similarity search
│   │   ├── alert_service.py            # Alert creation, deduplication, antibiotic suppression
│   │   └── trend_analyzer.py           # 14-reading linear regression → trajectory label
│   │
│   └── simulator/
│       ├── sensor_simulator.py         # Backfill mode (~2,700 readings) + live mode (30s/patient)
│       ├── biomarker_distributions.py  # Stochastic value generation per archetype
│       └── patient_profiles.py         # 15 demo patient definitions (name, age, archetype)
│
└── frontend/
    └── src/
        ├── App.tsx                     # Navigation bar + React Router setup
        │
        ├── api/
        │   ├── client.ts               # Axios HTTP client (base URL, default timeout)
        │   └── endpoints.ts            # All API call definitions (referral has 60s timeout)
        │
        ├── hooks/
        │   ├── usePatientData.ts       # Polls readings + risk assessment every 10s
        │   └── useAlerts.ts            # Polls alerts every 10s, exposes acknowledge()
        │
        ├── types/index.ts              # TypeScript interfaces for all data models
        │
        ├── pages/
        │   ├── PatientDashboard.tsx    # Patient self-view (gauge, AI text, 4 health signal cards
        │   │                           # with collapsible 90-day trend charts, lifestyle)
        │   ├── PhysicianPortal.tsx     # Physician risk-sorted roster (15 patients)
        │   └── PatientDetail.tsx       # Physician deep-dive (score breakdown, notes, referral)
        │
        └── components/
            ├── RiskScore.tsx           # Animated SVG circular gauge (0–100)
            ├── BiomarkerChart.tsx      # Recharts area chart with normal reference line (Y axis anchored at 0)
            ├── ReportPanel.tsx         # Claude AI narrative (truncate/expand, pill next steps)
            ├── ScoreBreakdown.tsx      # 8-biomarker weighted contribution bars
            ├── AlertBanner.tsx         # Severity-colored alert cards (deduped)
            ├── ClinicalNotes.tsx       # Timestamped notes thread + physician input
            ├── ReferralModal.tsx       # Generate → review → copy/send referral letter flow
            └── LifestyleInputPanel.tsx # Antibiotic toggle, fiber slider, save + recalculate
```

---

## 14. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend UI** | React 18 + TypeScript | Component-based UI with type safety |
| **Styling** | Tailwind CSS | Utility-first dark gradient design system |
| **Charts** | Recharts | Biomarker time-series area charts with normal reference line |
| **Backend API** | FastAPI (Python) | Async REST API with automatic OpenAPI docs |
| **Database ORM** | SQLAlchemy | Database model definitions and query layer |
| **Database** | SQLite (dev) | Single-file database; swappable with PostgreSQL |
| **Risk Model** | scikit-learn MLPRegressor | Neural network: sigmoid feature engineering + NN scoring |
| **Health Data Platform** | InterSystems IRIS | FHIR observation store + vector cosine similarity search (RAG) |
| **AI Narrative** | Anthropic Claude Sonnet 4.6 | Tool-use structured output for patient + physician text; referral letters |
| **Embeddings** | OpenAI `text-embedding-3-small` | Embeds FHIR clinical text for IRIS vector search |
| **Data Simulation** | Custom stochastic model | Per-archetype biomarker distributions with longitudinal drift |

---

## 15. Scientific References

<a name="ref1"></a>**[1]** Siegel RL, Miller KD, Wagle NS, Jemal A. "Colorectal cancer statistics, 2023." *CA: A Cancer Journal for Clinicians*. 2023;73(3):233–254. https://acsjournals.onlinelibrary.wiley.com/doi/10.3322/caac.21772

<a name="ref2"></a>**[2]** National Cancer Institute SEER Program. "Cancer Stat Facts: Colorectal Cancer." https://seer.cancer.gov/statfacts/html/colorect.html

<a name="ref3"></a>**[3]** Kaminski MF, Regula J, Kraszewska E, et al. "Adenoma Detection Rate and Risk of Colorectal Cancer and Death." *New England Journal of Medicine*. 2014;370:1298–1306. https://www.nejm.org/doi/full/10.1056/NEJMoa1309086

<a name="ref4"></a>**[4]** Lee JK, Liles EG, Bent S, et al. "Accuracy of fecal immunochemical tests for colorectal cancer: systematic review and meta-analysis." *Annals of Internal Medicine*. 2014;160(3):171. https://pmc.ncbi.nlm.nih.gov/articles/PMC3921527/

<a name="ref5"></a>**[5]** Gies A, Cuk K, Schrotz-King P, Brenner H. "Accuracy of Fecal Immunochemical Tests for Colorectal Cancer: Systematic Review and Meta-Analysis." 2018. https://pmc.ncbi.nlm.nih.gov/articles/PMC4189821/

<a name="ref6"></a>**[6]** Lee JK et al. "Accuracy of fecal immunochemical tests for colorectal cancer." *Ann Intern Med.* 2014. https://pmc.ncbi.nlm.nih.gov/articles/PMC3921527/

<a name="ref7"></a>**[7]** Tibble JA, Sigthorsson G, Bridger S, Fagerhol MK, Bjarnason I. "Surrogate markers of intestinal inflammation are predictive of relapse in patients with inflammatory bowel disease." *Gastroenterology*. 2000;119(1):15–22.

<a name="ref8"></a>**[8]** Roseth AG, Fagerhol MK, Aadland E, Schjonsby H. "Assessment of neutrophil dominating protein calprotectin in feces." *Scandinavian Journal of Gastroenterology*. https://pmc.ncbi.nlm.nih.gov/articles/PMC5390326/

<a name="ref9"></a>**[9]** Liabakk NB, Talbot I, Smith RA, Wilkinson K, Balkwill F. "Matrix metalloprotease 2 (MMP-2) and matrix metalloprotease 9 (MMP-9) type IV collagenases in colorectal cancer." *Cancer Res.* 1996;56(1):190–6.

<a name="ref10"></a>**[10]** Kruidenier L, Kuiper I, van Duijn W, et al. "Imbalanced secondary mucosal antioxidant response in inflammatory bowel disease." *J Pathol.* 2003;201(1):17–27.

<a name="ref11"></a>**[11]** Saarialho-Kere UK, Crouch EC, Parks WC. "Matrix metalloproteinase matrilysin is constitutively expressed in adult human exocrine epithelium." *J Invest Dermatol.* 1995;105(2):190–6.

<a name="ref12"></a>**[12]** Mosesson MW. "Fibrinogen and fibrin structure and functions." *J Thromb Haemost.* 2005;3(8):1894–904.

<a name="ref13"></a>**[13]** Shastri YM, Bergis D, Povse N, et al. "Prospective multicenter study evaluating fecal hemoglobin, transferrin, lactoferrin, and calprotectin in adults with gastrointestinal symptoms." *Am J Gastroenterol.* 2008;103(6):1500–7.

<a name="ref14"></a>**[14]** Lu X, Wang M, Qi J, et al. "Peptidoglycan recognition proteins are a new class of human bactericidal proteins." *J Biol Chem.* 2006;281(9):5895–907.
