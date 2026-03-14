# GutSense Demo Script — MIT Grand Hack

## Setup (before presenting)

1. Set your Anthropic API key in `backend/.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

2. Start the backend (Terminal 1):
   ```bash
   cd backend
   uvicorn main:app --reload
   ```
   Wait ~30 seconds for the 90-day backfill to complete (watch the logs).

3. Start the frontend (Terminal 2):
   ```bash
   cd frontend
   npm run dev
   ```
   Open http://localhost:5173

4. (Optional) Start the live simulator (Terminal 3) for continuous new readings:
   ```bash
   cd backend
   python simulator/sensor_simulator.py
   ```

---

## Demo Flow (~5 minutes)

### Act 1: The Problem (30 sec)
> "Colorectal cancer is the second-leading cause of cancer death. Current screening — colonoscopy or at-home stool tests — requires active patient effort, so compliance is less than 50%. We're building passive, continuous monitoring right into the toilet."

### Act 2: Patient View (90 sec)

Navigate to **http://localhost:5173/patient/1** (Alice Chen — Healthy)

> "This is what a patient sees. Alice's risk score is 20/100 — green. Her 6 biomarkers are all within normal ranges. The AI explains her results in plain language."

Navigate to **/patient/4** (David Kim — Critical)

> "David is 51, has a strong family history of CRC. His score is 88/100 — critical. Notice: elevated occult blood, severely depleted butyrate — a protective short-chain fatty acid — and a high methylation score on two FDA-recognized epigenetic markers, SEPT9 and SDC2."

> "The AI has already generated a recommendation: 'Contact your physician immediately. Urgent colonoscopy referral.'"

Point out the Lifestyle panel:

> "Watch what happens when I indicate David took antibiotics recently..."
Toggle antibiotics → score drops, yellow "Confounded" badge appears.

> "The system understands that antibiotics cause transient microbiome disruption. It adjusts the score and suppresses the alert so we're not crying wolf."

Toggle antibiotics off.

### Act 3: Physician Portal (90 sec)

Navigate to **/physician**

> "The physician sees all their patients ranked by risk score. David Kim is at the top in red. They can see trends, unacknowledged alerts, and raw marker values at a glance."

Click the **⚡ (lightning)** button next to David Kim:

> "I'm going to simulate the sensor detecting a new visit with highly abnormal readings..."

Wait 5–10 seconds → score jumps → red badge pulsing → alert count increments.

Click on David Kim → **PatientDetail**

> "The physician drills down. They see the full 90-day trend — you can see the methylation score creeping upward over the past 3 months. The AI provides a clinical summary using language physicians expect."

Add a note:

> "I'll add a clinical note and push it to David's patient app..."
Type: "Referred to gastroenterology. Urgent colonoscopy scheduled for next week."
Check "Push as physician recommendation" → click Add Note.

Navigate back to **/patient/4**

> "David's patient app now shows his physician's recommendation directly."

### Act 4: The Vision (30 sec)
> "Today we demonstrated the full loop: passive sensor data → AI risk scoring using 6 validated biomarkers — occult blood, butyrate, calprotectin, fungal dysbiosis, proteobacteria proliferation, and epigenetic methylation — → patient alert → physician action → patient notification."

> "No scheduling. No active compliance. The toilet does the work. We catch colorectal cancer at the trend level, weeks before symptoms emerge."

---

## Key Talking Points

| Question | Answer |
|---|---|
| Why these 6 markers? | Hemoglobin and methylation (SEPT9/SDC2) are FDA-recognized CRC markers. Butyrate depletion is an anti-tumor SCFA. Calprotectin is a validated inflammation marker. Fungal dysbiosis (elevated Basidiomycota/Ascomycota ratio) and Proteobacteria expansion are emerging CRC microbiome signatures from recent literature. |
| How often does it measure? | Once per bathroom visit — event-driven, not continuous. Typically 1–3 readings per day. |
| What about false positives? | Lifestyle context (antibiotics, fiber, sleep) is fed to the AI to reduce confounded signals. The system labels readings as "confounded" and suppresses alerts when lifestyle explains the dysbiosis. |
| Longitudinal tracking? | The system fits a linear regression over the last 14 readings to compute trajectory. "Slowly Increasing" is flagged before individual readings hit alarm thresholds. |
| Clinical validation? | Not yet — this is a prototype. The biomarker weights and reference ranges are based on published literature and would require clinical trials to validate before deployment. |

---

## Quick API Reference

- API docs: http://localhost:8000/docs
- Patient list: http://localhost:8000/api/patients
- Simulate spike (David Kim = id 4): `POST http://localhost:8000/api/patients/4/simulate-spike`
- Reset DB: delete `backend/biomarker.db` and restart the server
