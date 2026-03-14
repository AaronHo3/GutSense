"""
Sensor simulator — two modes:

1. backfill(db): seeds 90 days of historical readings (2 visits/day) for all demo patients.
2. run_live(interval_seconds): continuously generates new readings and POSTs to the API.

Run directly:  python sensor_simulator.py
"""

import sys
import os
import time
import random
import requests
from datetime import datetime, timedelta

# Allow importing from parent directory when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.biomarker_distributions import BiomarkerState
from simulator.patient_profiles import DEMO_PATIENTS

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
INGEST_URL = f"{API_BASE}/api/ingest"
INGEST_URL_SKIP = f"{API_BASE}/api/ingest?skip_narrative=true"
INTERVAL_SECONDS = int(os.getenv("SIMULATOR_INTERVAL_SECONDS", "30"))


def _post_reading(payload: dict, skip_narrative: bool = False) -> bool:
    url = INGEST_URL_SKIP if skip_narrative else INGEST_URL
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[simulator] Failed to post reading: {e}")
        return False


def backfill(db_session, patient_id_map: dict[str, int]):
    """
    Generate 90 days of historical readings directly into the DB via the ingest API.
    patient_id_map: { patient_name -> db_id }
    """
    print("[simulator] Starting 90-day historical backfill...")
    now = datetime.utcnow()
    start = now - timedelta(days=90)

    states: dict[str, BiomarkerState] = {}
    for profile in DEMO_PATIENTS:
        states[profile["name"]] = BiomarkerState(
            archetype=profile["archetype"],
            enable_drift=profile.get("drift", False),
        )

    # Iterate day by day, 2 visits per day
    total = 0
    for day_offset in range(90):
        visit_date = start + timedelta(days=day_offset)
        for visit in range(1, 3):  # 2 visits per day
            # Randomize visit time within morning and evening windows
            if visit == 1:
                hour = random.randint(6, 10)
            else:
                hour = random.randint(18, 22)
            visit_time = visit_date.replace(hour=hour, minute=random.randint(0, 59))

            for profile in DEMO_PATIENTS:
                patient_id = patient_id_map.get(profile["name"])
                if patient_id is None:
                    continue
                reading = states[profile["name"]].next_reading()
                payload = {
                    "patient_id": patient_id,
                    "timestamp": visit_time.isoformat(),
                    "visit_number": day_offset * 2 + visit,
                    **reading,
                }
                _post_reading(payload, skip_narrative=True)
                total += 1

    print(f"[simulator] Backfill complete — {total} readings inserted.")


def run_live():
    """
    Continuously generate new readings and POST to the API.
    Each iteration represents one bathroom visit per patient.
    """
    print(f"[simulator] Live mode — generating visits every {INTERVAL_SECONDS}s...")

    # Fetch existing patient IDs from the API
    try:
        resp = requests.get(f"{API_BASE}/api/patients", timeout=10)
        resp.raise_for_status()
        patients = resp.json()
    except Exception as e:
        print(f"[simulator] Could not fetch patients: {e}")
        return

    name_to_id = {p["name"]: p["id"] for p in patients}

    states: dict[str, BiomarkerState] = {}
    visit_counts: dict[str, int] = {}
    for profile in DEMO_PATIENTS:
        states[profile["name"]] = BiomarkerState(
            archetype=profile["archetype"],
            enable_drift=profile.get("drift", False),
        )
        visit_counts[profile["name"]] = 0

    while True:
        for profile in DEMO_PATIENTS:
            patient_id = name_to_id.get(profile["name"])
            if patient_id is None:
                continue
            visit_counts[profile["name"]] += 1
            reading = states[profile["name"]].next_reading()
            payload = {
                "patient_id": patient_id,
                "timestamp": datetime.utcnow().isoformat(),
                "visit_number": visit_counts[profile["name"]],
                **reading,
            }
            if _post_reading(payload):
                score_label = ""
                print(
                    f"[simulator] {profile['name']} visit #{visit_counts[profile['name']]} "
                    f"— hgb={reading['hemoglobin_ng_ml']:.1f} "
                    f"but={reading['butyrate_mmol_kg']:.1f} "
                    f"cal={reading['calprotectin_ug_g']:.0f}"
                )

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    run_live()
