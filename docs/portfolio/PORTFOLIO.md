# GutSense, Portfolio Brief

> Continuous, non-invasive colorectal cancer (CRC) screening platform. A toilet-mounted
> biosensor reads 8 stool biomarkers at every visit, a two-stage neural-network model scores
> CRC risk 0 to 100, and Claude turns the numbers into plain-language reports for patients and
> clinical summaries for physicians, grounded in similar historical cases retrieved from a
> vector database (InterSystems IRIS).

**Stack:** React 18 · TypeScript · Tailwind · Recharts · FastAPI · SQLAlchemy · SQLite · scikit-learn (MLP) · InterSystems IRIS (vector search) · Anthropic Claude (Sonnet 4.6) · OpenAI embeddings
**Role:** Full-stack and ML (MIT Grand Hack 2026)

---

## One-liner (for a project card)

> A continuous CRC early-detection platform that scores stool-biomarker risk with a neural
> network and explains it with a RAG-grounded LLM, turning a once-a-decade colonoscopy into a
> passive, every-visit signal.

## Short summary (2 to 3 sentences, for a portfolio page)

GutSense reimagines colorectal cancer screening as a passive, continuous signal instead of a
once-a-decade colonoscopy. A toilet-mounted sensor streams 8 molecular biomarkers to a FastAPI
backend, where interpretable sigmoid feature-engineering feeds a small neural network that
produces a 0 to 100 risk score, enriched by similar-patient context retrieved via kNN. Claude
then writes patient- and physician-facing narratives grounded in semantically similar historical
cases pulled from an InterSystems IRIS vector store, with graceful fallbacks so the product
never breaks when an external AI service is unavailable.

---

## Tech highlights (resume / bullet form)

- **Two-stage risk model.** Engineered 8 clinically-calibrated sigmoid transforms (per-biomarker
  midpoint and steepness) feeding a scikit-learn MLP (13 to 32 to 16 to 1) trained on 5,000
  synthetic patient samples; output clamped to a 0 to 100 CRC risk score.
- **Dual retrieval-augmented design.** (1) SQLite kNN over normalized 8-dimensional Manhattan
  distance injects the 3 most-similar patients' scores as model features; (2) IRIS
  `VECTOR_COSINE` search retrieves similar historical cases to ground the LLM's narrative. Two
  different RAG roles in one pipeline.
- **LLM narrative layer with structured tool-use.** Integrated Claude (Sonnet 4.6) to emit three
  structured outputs (patient explanation, physician summary, prioritized next steps) plus
  one-click formal GI referral letters, generated in a background thread so ingestion stays fast.
- **Production-grade resilience.** Every external dependency degrades gracefully. Claude
  unavailable falls back to medically-accurate rule-based text per risk level; IRIS unavailable
  lets the pipeline continue without vector context; no error screens are shown to users.
- **Real-time async backend.** FastAPI ingestion pipeline (`POST /api/ingest`) chains
  reading, kNN, NN scoring, 14-reading trend regression, and alerting, with AI enrichment
  offloaded to a background thread; dashboards poll and live-update every 10s.
- **Clinically-grounded data simulation.** Built a stochastic per-archetype biomarker simulator
  with longitudinal drift to generate a 90-day backfill (~2,700 readings across 15 demo patients)
  and a live 30s/patient stream.
- **Typed, component-driven frontend.** React 18 + TypeScript SPA with an animated SVG risk
  gauge, Recharts biomarker time-series, weighted score-breakdown table, and a custom editorial
  design system spanning patient, physician-roster, and physician-deep-dive views.
- **Interpretable-by-design.** Lifestyle confounders (recent antibiotics minus 10, high-fiber
  minus 3) applied as transparent post-NN overrides; alerts suppressed when biomarkers are
  confounded by recent antibiotic use to reduce false positives.

## Design notes

The UI was rebuilt around a **clinical-editorial** design language: a warm paper background,
hairline rules instead of glows, a single muted signal color reserved for risk, and a three-part
type system (Fraunces serif display, Instrument Sans body, Spline Sans Mono data). Biomarker
charts are intentionally monochrome so eight of them read as one cohesive data spread. The goal
was a sophisticated, trustworthy medical-publication feel rather than a generic dashboard look.

## Architecture diagram

`architecture-diagram.png` (rendered from `architecture.html`, same design language as the app).

```
Toilet sensor  --POST /api/ingest-->  FastAPI backend
  (8 biomarkers)                        1. sigmoid feature engineering (8 component scores)
                                        2. SQLite kNN, 3 similar-patient scores (model features)
                                        3. MLP risk model (13 to 32 to 16 to 1), 0 to 100 score
                                        4. 14-reading trend regression, trajectory label
                                        5. alert service (threshold + antibiotic suppression)
                                        6. [background] IRIS VECTOR_COSINE RAG, Claude narrative,
                                                        write back to IRIS
                                                  |
React + TS dashboards  <-- poll every 10s --------+
  Patient view · Physician roster · Physician deep-dive · IRIS vector view · Analytics
```

---

## Screenshots

All in [`screenshots/`](./screenshots/). Captured from the live app (1600x900 desktop, 390x844 mobile),
clinical-editorial redesign.

| File | What it shows | Suggested use |
|---|---|---|
| `01-hero-patient-critical.png` | Patient dashboard, critical case. Brick-red gauge, alert banners, AI analysis | **Hero / cover** (dramatic) |
| `02-hero-patient-healthy.png` | Patient dashboard, healthy case. Forest-green gauge, calm AI summary | **Hero / cover** (clean, calm alt) |
| `03-patient-dashboard-full.png` | Full patient view including health-signal cards | Feature screen |
| `04-physician-roster.png` | Risk-ranked ledger of 15 patients with signal-colored scores | Feature screen |
| `05-physician-deep-dive.png` | Physician deep-dive: score breakdown table, 8 monochrome biomarker charts, clinical notes | Feature screen |
| `06-mobile-patient.png` | Patient dashboard, mobile (above the fold) | Mobile view |
| `07-mobile-patient-full.png` | Patient dashboard, mobile (full scroll) | Mobile view |
| `08-mobile-physician.png` | Physician roster, mobile | Mobile view |

**Not captured:** the IRIS Vector Search and Analytics dashboards require a running IRIS Docker
container (port 1972) plus an `OPENAI_API_KEY` to populate embeddings. See note below.

---

## How these were produced

- App run locally: backend `uvicorn main:app` (:8000), frontend `npm run dev` (:5173).
- Screenshots captured via headless Chromium at desktop (1600x900) and mobile (390x844) viewports.
- Narratives shown are the built-in rule-based fallbacks (no `ANTHROPIC_API_KEY` was set during
  capture); with a key set, the same panels render live Claude output.

### Optional follow-up: capture IRIS + Analytics views

To screenshot the two remaining dashboards:
1. Start Docker, then run an InterSystems IRIS community container exposing port 1972
   (user/pass `demo`/`demo`, namespace `USER`).
2. Set `OPENAI_API_KEY` (used to embed FHIR clinical text for vector search) and
   `ANTHROPIC_API_KEY` (for live narratives).
3. Restart the backend; visit `/iris` and `/analytics` and re-capture.
