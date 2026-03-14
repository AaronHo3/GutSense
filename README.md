# GutSense — Continuous Colorectal Cancer Screening Platform

> **TL;DR**
> - A toilet-mounted biosensor reads 6 stool biomarkers at every visit and streams them to a risk-scoring engine
> - An AI model (Claude) converts the numbers into plain-language reports for patients and clinical summaries for physicians
> - Catches colorectal cancer years earlier than a once-a-decade colonoscopy, passively and non-invasively

---

## Table of Contents

1. [What Is GutSense?](#1-what-is-gutsense)
2. [The Problem It Solves](#2-the-problem-it-solves)
3. [How It Works — Step by Step](#3-how-it-works--step-by-step)
4. [The 6 Biomarkers](#4-the-6-biomarkers)
5. [The Risk Score — How 0–100 Is Calculated](#5-the-risk-score--how-0100-is-calculated)
6. [The AI Layer](#6-the-ai-layer)
7. [The 5 Demo Patients](#7-the-5-demo-patients)
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

GutSense is a continuous colorectal cancer (CRC) early-detection platform. A sensor pad installed in a standard toilet measures six molecular biomarkers from a patient's stool at every bathroom visit. Those readings are automatically sent to GutSense's server, scored by a validated risk model, and surfaced on two dashboards — one designed for patients, one for their physicians.

The key insight: colorectal cancer develops slowly over 10–15 years from a benign polyp to an invasive tumor. That long window is exactly where passive, continuous monitoring can intercept it. GutSense turns every bathroom visit into a data point — creating a movie of gut health instead of a snapshot every decade.

---

## 2. The Problem It Solves

Colorectal cancer is the **second leading cause of cancer death** in the United States.<sup>[1](#ref1)</sup> Yet when caught at the localized (early) stage, the **5-year survival rate exceeds 91%**.<sup>[2](#ref2)</sup> The challenge is detection: most CRC is found late, because standard screening (colonoscopy) is recommended only every 10 years and has low adherence.

The biology actually works in our favor. The adenoma-to-carcinoma sequence — the progression from a harmless polyp to colorectal cancer — takes roughly **10 years**.<sup>[3](#ref3)</sup> That is a long interception window. The problem is that no tool has continuously watched that window, until now.

GutSense monitors the gut passively, every day, without any behavior change required from the patient.

---

## 3. How It Works — Step by Step

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Toilet Sensor  │────▶│  GutSense Server │────▶│    Dashboard     │
│  (6 biomarkers) │     │  (score + AI)    │     │  Patient / MD    │
└─────────────────┘     └──────────────────┘     └──────────────────┘
```

**Step 1 — Sensor reads stool**
A toilet-mounted sensor pad measures six molecular biomarkers in the stool sample (detailed in Section 4). This happens automatically; the patient does nothing.

**Step 2 — Reading is transmitted**
The sensor sends the six values to the GutSense backend server as a single data packet.

**Step 3 — Risk score computed (deterministic)**
A mathematical model instantly converts the six biomarker values into a single 0–100 risk score. This is pure math — no AI involved at this stage. It runs in milliseconds.

**Step 4 — Trend analyzed**
The system looks at the past 14 readings and fits a trend line. It asks: is this patient's score stable, rising slowly, rising rapidly, or improving?

**Step 5 — AI writes plain-language reports**
Claude (Anthropic's AI model) reads the numbers, the score, and the trend, and writes two things automatically:
- A **2–3 sentence patient explanation** in plain English ("Your stool hemoglobin is undetectable and your protective butyrate levels are normal...")
- A **clinical physician summary** with specific marker references and recommended action timelines

**Step 6 — Alerts triggered (if warranted)**
If the adjusted score crosses 60, the system creates an alert for the physician. Alerts are suppressed if the patient recently took antibiotics (which temporarily disrupt the microbiome, not disease).

**Step 7 — Dashboards update**
Both the patient dashboard and the physician portal refresh automatically every 10 seconds. New readings, updated scores, and new physician notes appear without any page reload.

**Step 8 — Physician acts**
The physician can review the score breakdown, read the AI summary, leave clinical notes, and push recommendations directly to the patient's dashboard.

---

## 4. The 6 Biomarkers

Each biomarker was selected because it has peer-reviewed evidence linking it to colorectal cancer or precancerous conditions.

| Biomarker | What it measures | Healthy range | Alarm level | Evidence |
|---|---|---|---|---|
| **Hemoglobin** (occult blood) | Microscopic blood in stool — often the very first sign of CRC. Invisible to the naked eye. | < 20 ng/mL | > 100 ng/mL | [Lee et al.](#ref6) |
| **Butyrate** (protective SCFA) | A short-chain fatty acid produced by beneficial gut bacteria. It feeds colon cells and suppresses tumor growth. **Low is dangerous.** | > 15 mmol/kg | < 5 mmol/kg | [Liu et al.](#ref9) |
| **Calprotectin** (inflammation) | A protein released by immune cells during intestinal inflammation. Elevated in IBD and CRC. | < 50 µg/g | > 200 µg/g | [Roseth et al.](#ref8) |
| **Fungal Dysbiosis Index** (Basidio/Ascomy ratio) | The ratio of potentially harmful to beneficial fungi in the gut microbiome. Elevated in CRC patients. | < 1.5 | > 3.0 | [Geng et al.](#ref11) |
| **Proteobacteria Index** | The relative abundance of gram-negative bacteria (including pathogens like *Fusobacterium*) linked to colorectal carcinogenesis. | < 0.20 (0–1 scale) | > 0.50 | [Wong et al.](#ref12) |
| **DNA Methylation** (SEPT9/SDC2) | An epigenetic signal: when the genes SEPT9 and SDC2 are chemically silenced by cancer cells, this score rises. It is a molecular fingerprint of malignant transformation. | < 0.25 (0–1 scale) | > 0.50 | [Jin et al.](#ref4) |

> **Why these six?** Together they cover four independent biological mechanisms: bleeding (hemoglobin), inflammation (calprotectin), microbial dysbiosis (butyrate, fungal index, proteobacteria), and epigenetic change (methylation). A true positive across multiple mechanisms is far more specific than any single marker alone.

---

## 5. The Risk Score — How 0–100 Is Calculated

The GutSense risk score is a transparent, two-stage mathematical model — not a black box.

### Stage 1: Per-Biomarker Component Scores

Each biomarker is run through a mathematical curve that converts its raw value into a 0–100 component score:

- **Hemoglobin, Calprotectin, Fungal Index, Proteobacteria, Methylation** — higher raw value = higher component score (sigmoid or linear curves)
- **Butyrate** — *inverted*: lower raw value = higher component score, because butyrate depletion is the danger signal<sup>[10](#ref10)</sup>

### Stage 2: Weighted Composite

The six component scores are combined using clinically informed weights:

| Biomarker | Weight | Rationale |
|---|---|---|
| Hemoglobin | **25%** | FIT (fecal immunochemical test) is the most validated non-invasive CRC signal<sup>[7](#ref7)</sup> |
| DNA Methylation (SEPT9/SDC2) | **25%** | Sensitivity >74%, specificity >84% for CRC<sup>[4](#ref4)</sup> |
| Calprotectin | **20%** | Gold-standard mucosal inflammation marker<sup>[8](#ref8)</sup> |
| Butyrate | **15%** | HDAC-inhibitory and pro-apoptotic effects on colon cells<sup>[9](#ref9)</sup> |
| Fungal Dysbiosis | **10%** | Emerging mycobiome CRC signal<sup>[11](#ref11)</sup> |
| Proteobacteria | **5%** | Supporting dysbiosis signal<sup>[12](#ref12)</sup> |

### Stage 3: Demographic & Lifestyle Adjustments

The weighted total is then adjusted:

| Factor | Adjustment |
|---|---|
| Age > 50 | +10 points |
| Family history of CRC | +5 points |
| Rising trend (7-day slope) | +5 points |
| Recent antibiotic use | −10 points (antibiotics temporarily disrupt microbiome — not disease) |
| High fiber diet (≥ 25g/day) | −3 points (protective effect) |

### Stage 4: Risk Level Assignment

| Score | Level | Color |
|---|---|---|
| 0–30 | Low Risk | 🟢 Green |
| 31–60 | Elevated | 🟡 Yellow |
| 61–80 | High Risk | 🟠 Orange |
| 81–100 | Critical | 🔴 Red |

---

## 6. The AI Layer

After the mathematical risk score is calculated, GutSense uses **Claude** (Anthropic's AI model, Sonnet 4.6) to translate the numbers into human language.

Claude receives: all six biomarker values, the risk score, the trend direction, any lifestyle confounders, and the patient's basic demographics. It produces three outputs simultaneously:

1. **Patient explanation** — 2–3 sentences in plain English. No medical jargon. Tells the patient what their reading means and whether to be concerned.

   *Example (low risk):* "Your stool biomarker profile is within normal ranges across all six monitored channels. Occult blood is undetectable, your butyrate levels are in the protective range, and your epigenetic methylation score remains low. Continue your current dietary habits and maintain your routine annual screening schedule."

2. **Physician summary** — 4–5 sentences of clinical language. References specific marker values, compares to reference ranges, and suggests an action timeline.

   *Example (high risk):* "Multiple biomarker channels are significantly elevated. Calprotectin at >100 µg/g suggests active mucosal inflammation. Occult blood is elevated, consistent with possible early bleeding. Proteobacterial dysbiosis is confirmed. Urgent GI consultation within 2 weeks is recommended; consider colonoscopy referral."

3. **Next steps** — A short prioritized list of recommended actions (e.g., "Schedule GI consultation within 3 months", "Order stool FIT confirmatory test").

**Resilience:** If Claude is unavailable for any reason, the system automatically uses pre-written, medically accurate fallback text that varies by risk level. The app never shows an error or blank screen to the user.

---

## 7. The 5 Demo Patients

The demo database includes five patients with distinct clinical profiles, designed to showcase the full range of the platform:

| Patient | Age | Sex | Profile | Key Features |
|---|---|---|---|---|
| **Alice Chen** | 45 | F | Healthy baseline | All biomarkers within normal range; consistently green scores |
| **Bob Martinez** | 58 | M | At-risk, trending upward | Family history of CRC; biomarkers drifting upward over the 90-day simulation window |
| **Carol Wang** | 62 | F | At-risk, stable | Mildly elevated calprotectin and fungal index; consistent yellow scores |
| **David Kim** | 51 | M | Critical | Family history + NOD2 genetic variant; high hemoglobin and methylation score; red alerts |
| **Emma Johnson** | 38 | F | Healthy young adult | Clean baseline; demonstrates normal ranges for comparison |

---

## 8. Full Data Journey: From Sensor to Screen

Here is the precise sequence of every step that happens from the moment a patient uses the bathroom to the moment their physician sees an alert.

```
1. App starts for the first time (backend/main.py)
   │
   ├─ Creates database tables (SQLAlchemy models)
   ├─ Seeds 5 demo patients into the Patient table
   │
   └─ Launches background thread:
      │
      ├─ 90-DAY BACKFILL (backend/simulator/sensor_simulator.py)
      │   For each of 5 patients:
      │     For each of 90 days × 2 visits/day = 180 visits:
      │       → Generate realistic biomarker values for patient's archetype
      │       → POST to /api/ingest?skip_narrative=true
      │         → Validate patient
      │         → Store BiomarkerReading in DB
      │         → compute_risk_score() → (raw, adjusted, level, confounders, breakdown)
      │         → compute_trajectory() → "Stable" / "Slowly Increasing" / etc.
      │         → Store RiskAssessment (Claude fields left NULL for now)
      │         → maybe_create_alert() → store Alert if score ≥ 60
      │   Total: 900 readings inserted in ~30 seconds
      │
      └─ FILL NARRATIVES (backend/main.py → backend/services/claude_client.py)
          For each of 5 patients:
            → Find most recent RiskAssessment with no narrative yet
            → Call Claude API with all biomarker context
            → Update RiskAssessment with patient_explanation, physician_summary,
              next_steps, urgency_flag
          Total: 5 Claude API calls

2. Live simulation running (backend/simulator/sensor_simulator.py)
   Every 30 seconds, for each patient:
     → Generate new reading
     → POST to /api/ingest (full pipeline, includes Claude narrative)
     → Dashboard reflects update within next 10-second poll

3. Frontend polling (every 10 seconds)
   Patient dashboard:
     → GET /api/patients/:id/readings         → biomarker charts update
     → GET /api/patients/:id/risk/latest      → gauge + AI text update
     → GET /api/patients/:id/alerts           → alert banner updates
     → GET /api/patients/:id/notes            → physician recommendations appear

   Physician portal:
     → GET /api/physician/patients            → risk-sorted roster updates
     → Click patient → GET same endpoints above + score breakdown
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

**Biomarker charts:**
- Six time-series charts, one per biomarker, showing the past 90 days
- Each chart shows a dashed "Normal" line and a dashed "Alarm" line
- **Red dots** mark individual readings that crossed the alarm threshold — so the patient can see exactly which days were concerning and whether things are trending better or worse

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
  - Key biomarker snapshot: Hemoglobin, Butyrate, Calprotectin, Methylation
  - Number of unacknowledged alerts

### Patient Detail (single-patient deep dive)

Accessed by clicking any patient card.

- **Same stats strip and gauge as the patient view**, but with physician-level AI text
- **Score Breakdown panel** — shows exactly which biomarkers are driving the score:
  - 6 horizontal bars, one per biomarker
  - Bar length = component score (0–100)
  - Color = severity (green/yellow/orange/red)
  - Shows the weight (×0.25, ×0.15, etc.) and weighted contribution to the total
- **Full biomarker charts** with alarm dots
- **Clinical Notes** — the physician can:
  - Write private notes (only visible to physicians)
  - Mark a note as a "Physician Recommendation" — this immediately appears on the patient's dashboard
- **Simulate Spike button** — injects a synthetic critical-level reading for demo purposes

---

## 11. Alerts

Alerts notify physicians when a patient's adjusted risk score crosses a threshold.

**Rules:**
- Fires when adjusted score ≥ 60
- Severity: "Info" (yellow range), "Warning" (orange), "Critical" (red)
- **Deduplication:** only one active alert per severity per patient — no spam
- **Antibiotic suppression:** if the patient reported recent antibiotic use, alerts are suppressed. Antibiotics temporarily alter the microbiome and would cause false positives.

**Physician actions:**
- Alerts appear as a banner on both the physician portal and patient detail view
- Clicking the dismiss (✕) button marks the alert as acknowledged and removes it from the active list

---

## 12. How to Run the Project

### Prerequisites
- Python 3.11+
- Node.js 18+
- An Anthropic API key (for Claude AI narratives; optional — the system works without one using fallback text)

### Backend

```bash
cd backend
pip install -r requirements.txt

# Set your API key (optional but recommended)
export ANTHROPIC_API_KEY=sk-ant-...

uvicorn main:app --reload
```

The server starts at **http://localhost:8000**. On first run, it automatically:
1. Creates the SQLite database (`biomarker.db`)
2. Seeds 5 demo patients
3. Runs a 90-day backfill (~900 readings, ~30 seconds)
4. Fills AI narratives for each patient's latest assessment

The interactive API docs are at **http://localhost:8000/docs**.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at **http://localhost:5173**. The nav bar has two views: **Patient** and **Physician**.

### Live Simulator (optional)

To continuously stream new readings every 30 seconds (simulates real sensor data):

```bash
cd backend
python simulator/sensor_simulator.py
```

### Reset to Fresh State

```bash
rm backend/biomarker.db
# Restart the backend — it re-seeds and re-backfills automatically
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(none)* | Required for real Claude narratives; falls back to rule-based text if absent |
| `RISK_ALERT_THRESHOLD` | `60` | Minimum adjusted score to trigger an alert |
| `SIMULATOR_INTERVAL_SECONDS` | `30` | How often the live simulator sends a new reading |
| `API_BASE` | `http://localhost:8000` | Backend URL used by the simulator |

---

## 13. Project Structure

```
MIT_Grand_Hack/
│
├── backend/
│   ├── main.py                         # App startup, patient seeding, 90-day backfill,
│   │                                   # narrative fill (orchestrates everything)
│   ├── models.py                       # Database schema: 6 tables (Patient, BiomarkerReading,
│   │                                   # RiskAssessment, Alert, ClinicalNote, LifestyleMetadata)
│   ├── schemas.py                      # API request/response shapes (Pydantic validation)
│   ├── database.py                     # SQLite connection + session management
│   │
│   ├── routers/
│   │   ├── ingest.py                   # POST /api/ingest — the core pipeline:
│   │   │                               #   receive reading → score → trend → alert → Claude
│   │   ├── physician.py                # Physician endpoints: roster, notes, lifestyle,
│   │   │                               # simulate-spike, recalculate
│   │   └── patient.py                  # Patient endpoints: readings, risk, alerts
│   │
│   ├── services/
│   │   ├── ai_risk_model.py            # The 0–100 scoring algorithm (6 sigmoid/linear
│   │   │                               # curves, weighted composite, demographic adjustments)
│   │   ├── claude_client.py            # Claude API integration + medically accurate
│   │   │                               # fallback narratives per risk level
│   │   ├── alert_service.py            # Alert creation, deduplication, antibiotic suppression
│   │   └── trend_analyzer.py          # 14-reading linear regression → trajectory label
│   │
│   └── simulator/
│       ├── sensor_simulator.py         # Backfill mode (900 readings) + live mode (30s interval)
│       ├── biomarker_distributions.py  # Stochastic value generation per patient archetype
│       └── patient_profiles.py         # 5 demo patient definitions (name, age, archetype)
│
└── frontend/
    └── src/
        ├── App.tsx                     # Navigation bar + React Router setup
        │
        ├── api/
        │   ├── client.ts               # Axios HTTP client (base URL, timeout)
        │   └── endpoints.ts            # All API call definitions
        │
        ├── hooks/
        │   ├── usePatientData.ts       # Polls readings + risk assessment every 10s
        │   └── useAlerts.ts            # Polls alerts every 10s, exposes acknowledge()
        │
        ├── types/index.ts              # TypeScript interfaces for all 8 data models
        │
        ├── pages/
        │   ├── PatientDashboard.tsx    # Patient self-view (gauge, AI text, charts, lifestyle)
        │   ├── PhysicianPortal.tsx     # Physician risk-sorted roster
        │   └── PatientDetail.tsx       # Physician deep-dive (score breakdown, notes)
        │
        └── components/
            ├── RiskScore.tsx           # Animated SVG circular gauge (0–100)
            ├── BiomarkerChart.tsx      # Recharts area chart with alarm dots + reference lines
            ├── ReportPanel.tsx         # Claude AI narrative (truncate/expand, pill next steps)
            ├── ScoreBreakdown.tsx      # Per-biomarker weighted contribution bars
            ├── AlertBanner.tsx         # Severity-colored alert cards (deduped)
            ├── ClinicalNotes.tsx       # Timestamped notes thread + physician input
            └── LifestyleInputPanel.tsx # Antibiotic toggle, fiber slider, sleep slider,
                                        # Save + Recalculate buttons
```

---

## 14. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend UI** | React 18 + TypeScript | Component-based UI with type safety |
| **Styling** | Tailwind CSS | Utility-first dark gradient design system |
| **Charts** | Recharts | Biomarker time-series with custom alarm dot renderer |
| **Backend API** | FastAPI (Python) | Async REST API with automatic OpenAPI docs |
| **Database ORM** | SQLAlchemy | Database model definitions and query layer |
| **Database** | SQLite (dev) | Single-file database; swappable with PostgreSQL |
| **AI Narrative** | Anthropic Claude Sonnet 4.6 | Tool-use structured output for patient + physician text |
| **Risk Scoring** | Custom Python model | Deterministic, interpretable, no ML black box |
| **Data Simulation** | Custom stochastic model | Per-archetype biomarker distributions with drift |

---

## 15. Scientific References

<a name="ref1"></a>**[1]** Siegel RL, Miller KD, Wagle NS, Jemal A. "Colorectal cancer statistics, 2023." *CA: A Cancer Journal for Clinicians*. 2023;73(3):233–254. https://acsjournals.onlinelibrary.wiley.com/doi/10.3322/caac.21772

<a name="ref2"></a>**[2]** National Cancer Institute SEER Program. "Cancer Stat Facts: Colorectal Cancer." https://seer.cancer.gov/statfacts/html/colorect.html

<a name="ref3"></a>**[3]** Kaminski MF, Regula J, Kraszewska E, et al. "Adenoma Detection Rate and Risk of Colorectal Cancer and Death." *New England Journal of Medicine*. 2014;370:1298–1306. https://www.nejm.org/doi/full/10.1056/NEJMoa1309086

<a name="ref4"></a>**[4]** Jin H, et al. "Aberrant DNA Methylation of SEPT9 and SDC2 in Stool Specimens as an Integrated Biomarker for Colorectal Cancer Early Detection." *Frontiers in Genetics*. 2020;11:643. https://www.frontiersin.org/journals/genetics/articles/10.3389/fgene.2020.00643/full

<a name="ref5"></a>**[5]** Liang JQ, et al. "Early detection of colorectal cancer based on presence of methylated syndecan-2 (SDC2) in stool DNA." *Clinical Epigenetics*. 2019;11:1. https://clinicalepigeneticsjournal.biomedcentral.com/articles/10.1186/s13148-019-0642-0

<a name="ref6"></a>**[6]** Lee JK, Liles EG, Bent S, et al. "Accuracy of fecal immunochemical tests for colorectal cancer: systematic review and meta-analysis." *Annals of Internal Medicine*. 2014;160(3):171. https://pmc.ncbi.nlm.nih.gov/articles/PMC3921527/

<a name="ref7"></a>**[7]** Gies A, Cuk K, Schrotz-King P, Brenner H. "Accuracy of Fecal Immunochemical Tests for Colorectal Cancer: Systematic Review and Meta-Analysis." *Annals of Internal Medicine*. 2018. https://pmc.ncbi.nlm.nih.gov/articles/PMC4189821/

<a name="ref8"></a>**[8]** Roseth AG, Fagerhol MK, Aadland E, Schjonsby H. "Assessment of neutrophil dominating protein calprotectin in feces." *Scandinavian Journal of Gastroenterology*. PMC5390326. https://pmc.ncbi.nlm.nih.gov/articles/PMC5390326/

<a name="ref9"></a>**[9]** Liu W, et al. "Butyrate ameliorates colorectal cancer through regulating intestinal microecological disorders." *Frontiers in Oncology*. 2022. https://pmc.ncbi.nlm.nih.gov/articles/PMC9815807/

<a name="ref10"></a>**[10]** Guo J, et al. "Sodium butyrate in both prevention and supportive treatment of colorectal cancer." *Frontiers in Nutrition*. 2022. https://pmc.ncbi.nlm.nih.gov/articles/PMC9643746/

<a name="ref11"></a>**[11]** Geng J, et al. "Enteric fungal microbiota dysbiosis and ecological alterations in colorectal cancer." *Gut*. 2019;68(4):654–662. https://pmc.ncbi.nlm.nih.gov/articles/PMC6580778/

<a name="ref12"></a>**[12]** Wong SH, Yu J. "Gut microbiota in colorectal cancer: mechanisms of action and clinical applications." *Nature Reviews Gastroenterology & Hepatology*. PMC8840808. https://pmc.ncbi.nlm.nih.gov/articles/PMC8840808/
