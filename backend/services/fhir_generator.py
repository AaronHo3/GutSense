"""
FHIR R4 resource generator.

Converts GutSense SQLite patient data into standards-compliant FHIR R4 resources:
  Patient          → hl7.org/fhir/R4/patient.html
  Observation ×8   → one per biomarker (LOINC-coded)
  DiagnosticReport → wraps the 8 observations into a stool panel report
  RiskAssessment   → FHIR RiskAssessment (risk score + level)

All resources are returned as a FHIR Bundle (type=collection).

LOINC codes used:
  2335-8   Hemoglobin [Mass/volume] in Stool (FIT)
  35548-6  Calprotectin [Mass/volume] in Stool
  72289-1  MMP-9 [Mass/volume] in Serum or Plasma
  35341-6  Myeloperoxidase (MPO) [Mass/volume]
  72291-7  MMP-8 [Mass/volume] in Serum or Plasma
  3255-7   Fibrinogen [Mass/volume] in Platelet poor plasma
  4542-7   Haptoglobin [Mass/volume] in Serum
  LP436285-3  PGRP-S (Peptidoglycan Recognition Protein S)
"""

import sqlite3
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Interpretation thresholds (mirrors ai_risk_model.py logic)
# ---------------------------------------------------------------------------

def _mpo_interp(val: float) -> Optional[str]:
    if val > 500:  return "HH"
    if val > 300:  return "H"
    return None

def _haptoglobin_interp(val: float) -> Optional[str]:
    if val > 200:  return "HH"
    if val > 120:  return "H"
    return None

def _fibrinogen_interp(val: float) -> Optional[str]:
    if val > 400:  return "HH"
    if val > 250:  return "H"
    return None

def _mmp9_interp(val: float) -> Optional[str]:
    if val > 150:  return "HH"
    if val > 80:   return "H"
    return None

def _hemoglobin_fit_interp(val: float) -> Optional[str]:
    if val > 100:  return "HH"
    if val > 50:   return "H"
    return None

def _mmp8_interp(val: float) -> Optional[str]:
    if val > 150:  return "HH"
    if val > 80:   return "H"
    return None

def _pgrp_s_interp(val: float) -> Optional[str]:
    if val > 100:  return "HH"
    if val > 55:   return "H"
    return None

def _calprotectin_interp(val: float) -> Optional[str]:
    if val > 300:  return "HH"
    if val > 150:  return "H"
    return None


_INTERP_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"

def _interp_coding(code: Optional[str]) -> list:
    if not code:
        return []
    label = {
        "H": "High", "HH": "Critical High",
        "L": "Low",  "LL": "Critical Low",
    }.get(code, code)
    return [{"coding": [{"system": _INTERP_SYSTEM, "code": code, "display": label}]}]


# ---------------------------------------------------------------------------
# Individual FHIR resource builders
# ---------------------------------------------------------------------------

def _fhir_patient(p: sqlite3.Row) -> dict:
    return {
        "resourceType": "Patient",
        "id": f"gutsense-patient-{p['id']}",
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]},
        "identifier": [{"system": "https://gutsense.ai/patients", "value": str(p["id"])}],
        "name": [{"use": "official", "text": p["name"],
                  "family": p["name"].split()[-1],
                  "given": p["name"].split()[:-1]}],
        "gender": "male" if p["sex"] == "M" else "female",
        "extension": [
            {
                "url": "https://gutsense.ai/fhir/StructureDefinition/family-history-crc",
                "valueBoolean": bool(p["family_history"]),
            },
            {
                "url": "https://gutsense.ai/fhir/StructureDefinition/nod2-variant",
                "valueBoolean": bool(p["has_nod2_variant"]) if "has_nod2_variant" in p.keys() else False,
            },
        ],
    }


def _fhir_observation(
    patient_ref: str,
    reading: sqlite3.Row,
    loinc: str,
    display: str,
    value: float,
    unit: str,
    unit_code: str,
    interp_fn,
) -> dict:
    obs_id = str(uuid.uuid4())
    interp_code = interp_fn(value)
    obs = {
        "resourceType": "Observation",
        "id": obs_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory",
                    }
                ]
            }
        ],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": loinc, "display": display}],
            "text": display,
        },
        "subject": {"reference": patient_ref},
        "effectiveDateTime": reading["timestamp"] if reading["timestamp"] else datetime.now(timezone.utc).isoformat(),
        "valueQuantity": {
            "value": round(float(value), 4),
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit_code,
        },
    }
    if interp_code:
        obs["interpretation"] = _interp_coding(interp_code)
    return obs


def _fhir_diagnostic_report(
    patient_ref: str,
    reading: sqlite3.Row,
    obs_refs: list[str],
    risk_level: str,
) -> dict:
    conclusion_map = {
        "green":  "Stool biomarker panel within normal limits. No significant findings.",
        "yellow": "Mildly abnormal stool biomarker findings. Clinical correlation recommended.",
        "orange": "Multiple significantly elevated stool biomarkers. Prompt clinical evaluation advised.",
        "red":    "Critically abnormal stool biomarker panel. Immediate physician review required.",
    }
    return {
        "resourceType": "DiagnosticReport",
        "id": str(uuid.uuid4()),
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "MB",
                        "display": "Microbiology",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "47527-7",
                    "display": "GI pathogens panel",
                }
            ],
            "text": "GutSense Stool Biomarker Panel (8-marker)",
        },
        "subject": {"reference": patient_ref},
        "effectiveDateTime": reading["timestamp"] if reading["timestamp"] else datetime.now(timezone.utc).isoformat(),
        "result": [{"reference": f"Observation/{ref}"} for ref in obs_refs],
        "conclusion": conclusion_map.get(risk_level, ""),
        "conclusionCode": [
            {
                "coding": [
                    {
                        "system": "https://gutsense.ai/fhir/CodeSystem/risk-level",
                        "code": risk_level,
                        "display": risk_level.capitalize() + " Risk",
                    }
                ]
            }
        ],
    }


def _fhir_risk_assessment(
    patient_ref: str,
    adjusted_score: float,
    risk_level: str,
    trajectory: str,
) -> dict:
    probability = round(adjusted_score / 100, 3)
    return {
        "resourceType": "RiskAssessment",
        "id": str(uuid.uuid4()),
        "status": "final",
        "subject": {"reference": patient_ref},
        "occurrenceDateTime": datetime.now(timezone.utc).isoformat(),
        "basis": [{"reference": patient_ref}],
        "prediction": [
            {
                "outcome": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "363346000",
                            "display": "Malignant neoplastic disease",
                        }
                    ]
                },
                "probabilityDecimal": probability,
                "relativeRisk": round(adjusted_score / 20, 2),
                "whenPeriod": {"start": datetime.now(timezone.utc).isoformat()},
                "rationale": f"GutSense composite biomarker risk score {adjusted_score:.1f}/100. Trajectory: {trajectory}.",
            }
        ],
        "note": [{"text": f"Risk level: {risk_level}. Trajectory: {trajectory}."}],
    }


# ---------------------------------------------------------------------------
# Bundle builder
# ---------------------------------------------------------------------------

def generate_fhir_bundle(patient_id: int) -> Optional[dict]:
    """
    Generate a FHIR R4 Bundle (type=collection) for a patient.
    Returns None if patient not found.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(here, "biomarker.db")
    if not os.path.exists(db_path):
        return None

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    p = con.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not p:
        con.close()
        return None

    ra = con.execute(
        "SELECT * FROM risk_assessments WHERE patient_id = ? ORDER BY timestamp DESC LIMIT 1",
        (patient_id,),
    ).fetchone()

    br = None
    if ra and ra["reading_id"]:
        br = con.execute(
            "SELECT * FROM biomarker_readings WHERE id = ?", (ra["reading_id"],)
        ).fetchone()
    con.close()

    if not br or not ra:
        return None

    patient_resource = _fhir_patient(p)
    patient_ref = f"Patient/{patient_resource['id']}"

    # 8 Observation resources
    observations = [
        _fhir_observation(patient_ref, br, "2335-8",     "Hemoglobin (FIT) in Stool",
                          br["hemoglobin_fit_ng_ml"],  "ng/mL", "ng/mL", _hemoglobin_fit_interp),
        _fhir_observation(patient_ref, br, "35548-6",    "Calprotectin in Stool",
                          br["calprotectin_ug_g"],     "ug/g",  "ug/g",  _calprotectin_interp),
        _fhir_observation(patient_ref, br, "72289-1",    "MMP-9 (Matrix Metalloproteinase-9)",
                          br["mmp9_ng_ml"],            "ng/mL", "ng/mL", _mmp9_interp),
        _fhir_observation(patient_ref, br, "35341-6",    "MPO (Myeloperoxidase)",
                          br["mpo_ng_ml"],             "ng/mL", "ng/mL", _mpo_interp),
        _fhir_observation(patient_ref, br, "72291-7",    "MMP-8 (Neutrophil Collagenase)",
                          br["mmp8_ng_ml"],            "ng/mL", "ng/mL", _mmp8_interp),
        _fhir_observation(patient_ref, br, "3255-7",     "Fibrinogen (Fecal)",
                          br["fibrinogen_ng_ml"],      "ng/mL", "ng/mL", _fibrinogen_interp),
        _fhir_observation(patient_ref, br, "4542-7",     "Haptoglobin (Fecal)",
                          br["haptoglobin_ug_g"],      "ug/g",  "ug/g",  _haptoglobin_interp),
        _fhir_observation(patient_ref, br, "LP436285-3", "PGRP-S (Peptidoglycan Recognition Protein S)",
                          br["pgrp_s_ng_ml"],          "ng/mL", "ng/mL", _pgrp_s_interp),
    ]

    diag_report = _fhir_diagnostic_report(
        patient_ref, br, [o["id"] for o in observations], ra["risk_level"]
    )

    risk_assessment = _fhir_risk_assessment(
        patient_ref, float(ra["adjusted_score"]), ra["risk_level"], ra["trajectory"]
    )

    bundle_id = f"gutsense-bundle-{patient_id}-{int(datetime.now().timestamp())}"
    entries = [patient_resource, diag_report, risk_assessment] + observations

    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {"lastUpdated": datetime.now(timezone.utc).isoformat()},
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": [{"resource": r} for r in entries],
    }


def bundle_to_text(bundle: dict) -> str:
    """Convert a FHIR Bundle into a rich plain-text string suitable for embedding."""
    lines = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        rt = r.get("resourceType")

        if rt == "Patient":
            gender = r.get("gender", "")
            name = r.get("name", [{}])[0].get("text", "Unknown")
            fhx = next(
                (e["valueBoolean"] for e in r.get("extension", [])
                 if "family-history" in e.get("url", "")),
                False,
            )
            lines.append(
                f"Patient: {name}, {gender}. Family history of CRC: {'yes' if fhx else 'no'}."
            )

        elif rt == "Observation":
            display = r.get("code", {}).get("text", "")
            vq = r.get("valueQuantity", {})
            val = vq.get("value", "")
            unit = vq.get("unit", "")
            interps = r.get("interpretation", [])
            interp_code = ""
            if interps:
                coding = interps[0].get("coding", [{}])
                interp_code = coding[0].get("code", "") if coding else ""
            flag = f" [{interp_code}]" if interp_code else ""
            lines.append(f"  {display}: {val} {unit}{flag}")

        elif rt == "DiagnosticReport":
            conclusion = r.get("conclusion", "")
            lines.append(f"DiagnosticReport: {conclusion}")

        elif rt == "RiskAssessment":
            pred = r.get("prediction", [{}])[0]
            prob = pred.get("probabilityDecimal", 0)
            rationale = pred.get("rationale", "")
            lines.append(f"RiskAssessment: probability={prob:.1%}. {rationale}")

    return "\n".join(lines)
