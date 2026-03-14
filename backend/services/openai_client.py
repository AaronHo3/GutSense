"""
OpenAI client for generating plain-language stool diagnostic summaries.

Given a patient's FHIR Observation and DiagnosticReport resources:
1. Extracts relevant findings (values, interpretation flags, LOINC codes)
2. Computes a deterministic risk score (0-100) from interpretation flags
3. Calls GPT-4o-mini to generate a concise clinical summary
4. Falls back to rule-based text if the API key is missing or the call fails
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LOINC codes for stool / GI-related tests
# ---------------------------------------------------------------------------
_STOOL_LOINC = {
    "2335-8":  "Fecal occult blood (guaiac)",
    "27396-1": "Fecal occult blood (immunochemical)",
    "56490-6": "Fecal immunochemical test (FIT)",
    "80688-0": "FIT quantitative",
    "35548-6": "Fecal calprotectin",
    "14684-3": "Stool culture",
    "618-7":   "Stool bacteria culture",
    "51552-1": "Ova and parasites",
    "21414-3": "C. difficile toxin",
    "6349-5":  "C. difficile culture",
    "2093-3":  "Total cholesterol (stool)",
}

# These carry extra weight because a positive result strongly suggests CRC risk
_HIGH_WEIGHT_LOINC = {"2335-8", "27396-1", "56490-6", "80688-0", "21414-3"}

_ABNORMAL_INTERP = {"H", "HH", "L", "LL", "A", "AA", "POS", "R"}
_CRITICAL_INTERP = {"HH", "LL", "AA"}


# ---------------------------------------------------------------------------
# Observation extraction
# ---------------------------------------------------------------------------

def extract_observation_summary(obs: dict) -> Optional[dict]:
    """Pull key fields from a FHIR Observation resource into a flat dict."""
    code_block = obs.get("code", {})
    codings = code_block.get("coding", [])
    loinc_code: Optional[str] = None
    display = code_block.get("text") or "Unknown test"

    for c in codings:
        if "loinc.org" in c.get("system", ""):
            loinc_code = c.get("code")
            if not display or display == "Unknown test":
                display = c.get("display", display)
            break

    # Value
    value_str: Optional[str] = None
    unit: Optional[str] = None
    if "valueQuantity" in obs:
        vq = obs["valueQuantity"]
        value_str = str(vq.get("value", ""))
        unit = vq.get("unit") or vq.get("code")
    elif "valueString" in obs:
        value_str = obs["valueString"]
    elif "valueCodeableConcept" in obs:
        value_str = obs["valueCodeableConcept"].get("text", "")

    # Interpretation flag
    interpretation: Optional[str] = None
    for interp_block in obs.get("interpretation", []):
        for c in interp_block.get("coding", []):
            code = c.get("code", "")
            if code in _ABNORMAL_INTERP or code in _CRITICAL_INTERP:
                interpretation = code
                break
        if interpretation:
            break

    effective = (
        obs.get("effectiveDateTime")
        or obs.get("effectivePeriod", {}).get("start")
        or ""
    )

    return {
        "loinc": loinc_code,
        "display": display,
        "value": value_str,
        "unit": unit,
        "interpretation": interpretation,
        "status": obs.get("status", ""),
        "date": effective[:10] if effective else None,
        "is_stool_related": loinc_code in _STOOL_LOINC,
        "is_high_weight": loinc_code in _HIGH_WEIGHT_LOINC,
    }


# ---------------------------------------------------------------------------
# Deterministic risk scoring
# ---------------------------------------------------------------------------

def compute_fhir_risk(observations: list[dict], reports: list[dict]) -> dict:
    """
    Rule-based risk score (0-100) derived from FHIR interpretation flags.

    Scoring:
      +25  per observation with a critical flag (HH / LL / AA)
      +15  per high-weight stool test with any abnormal flag
      +8   per observation with any other abnormal flag
      +20  if a DiagnosticReport conclusion contains cancer / malignancy keywords
    """
    score = 5  # baseline — having data at all is non-zero
    risk_factors: list[str] = []

    summaries = [extract_observation_summary(o) for o in observations]
    summaries = [s for s in summaries if s]

    for s in summaries:
        interp = s.get("interpretation")
        if not interp:
            continue

        val_label = f"{s['value'] or 'positive'} {s.get('unit') or ''}".strip()

        if interp in _CRITICAL_INTERP:
            score += 25
            risk_factors.append(f"Critical value — {s['display']}: {val_label}")
        elif s["is_high_weight"] and interp in _ABNORMAL_INTERP:
            score += 15
            risk_factors.append(
                f"Abnormal stool test — {s['display']}: {val_label}"
            )
        elif interp in _ABNORMAL_INTERP:
            score += 8
            risk_factors.append(f"Abnormal — {s['display']}: {val_label}")

    for report in reports:
        conclusion = (report.get("conclusion") or "").lower()
        if any(
            kw in conclusion
            for kw in ("malignant", "cancer", "carcinoma", "positive", "neoplasm")
        ):
            score += 20
            snippet = report.get("conclusion", "")[:120]
            risk_factors.append(f"Report conclusion: {snippet}")

    score = min(score, 100)

    if score < 30:
        risk_level = "low"
    elif score < 60:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "risk_factors": risk_factors[:6],
    }


# ---------------------------------------------------------------------------
# OpenAI client (lazy-initialised)
# ---------------------------------------------------------------------------

_openai_client = None


def _get_client():
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=api_key)
        return _openai_client
    except ImportError:
        logger.warning(
            "[OpenAI] 'openai' package not installed. "
            "Run: pip install openai"
        )
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_summary(
    patient_name: str,
    patient_info: dict,
    observations: list[dict],
    reports: list[dict],
) -> dict:
    """
    Generate a plain-language clinical summary for a patient.

    Returns a dict with keys:
      summary, key_findings, recommendation, risk_score, risk_level, risk_factors
    """
    risk_data = compute_fhir_risk(observations, reports)
    summaries = [extract_observation_summary(o) for o in observations]
    summaries = [s for s in summaries if s]

    if not summaries and not reports:
        return {
            "summary": (
                f"No diagnostic data found in IRIS for {patient_name}. "
                "Ensure FHIR resources have been loaded into this IRIS instance."
            ),
            "key_findings": ["No observations or reports found"],
            "recommendation": "Load patient data into IRIS and refresh.",
            **risk_data,
        }

    client = _get_client()
    if not client:
        return _fallback_summary(patient_name, summaries, risk_data)

    # Build the prompt
    obs_lines = [
        f"- {s['date'] or '?'}: {s['display']}: "
        f"{s['value'] or 'N/A'} {s.get('unit') or ''} "
        f"[{'ABNORMAL' if s['interpretation'] in _ABNORMAL_INTERP else 'normal'}]"
        for s in summaries[:25]
    ]
    report_lines = [
        f"- Status={r.get('status','?')} "
        f"Type={r.get('code',{}).get('text','DiagnosticReport')} "
        f"Conclusion={r.get('conclusion','—')[:200]}"
        for r in reports[:5]
    ]

    prompt = (
        f"Patient: {patient_name}, "
        f"Age: {patient_info.get('age','unknown')}, "
        f"Gender: {patient_info.get('gender','unknown')}\n\n"
        f"Lab Observations:\n"
        + ("\n".join(obs_lines) or "None")
        + f"\n\nDiagnostic Reports:\n"
        + ("\n".join(report_lines) or "None")
        + f"\n\nComputed risk score: {risk_data['risk_score']}/100 "
        f"({risk_data['risk_level']} risk)\n\n"
        "Respond with a JSON object containing exactly these keys:\n"
        '  "summary": "2-3 sentence plain-language summary for a physician",\n'
        '  "key_findings": ["finding 1", "finding 2", ...] (up to 4 items),\n'
        '  "recommendation": "one-sentence clinical next step"'
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a clinical AI assistant summarising stool sample "
                        "diagnostics for physicians. Be concise and clinically precise. "
                        "Always respond with valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=400,
            temperature=0.2,
        )
        content = json.loads(response.choices[0].message.content)
        return {
            "summary": content.get("summary", ""),
            "key_findings": content.get("key_findings", risk_data["risk_factors"]),
            "recommendation": content.get("recommendation", ""),
            **risk_data,
        }
    except Exception as e:
        logger.error(f"[OpenAI] Generation failed for {patient_name}: {e}")
        return _fallback_summary(patient_name, summaries, risk_data)


def _fallback_summary(
    patient_name: str,
    obs_summaries: list[dict],
    risk_data: dict,
) -> dict:
    """Rule-based summary used when OpenAI is unavailable."""
    level = risk_data["risk_level"]
    score = risk_data["risk_score"]
    factors = risk_data["risk_factors"]

    if level == "high":
        summary = (
            f"{patient_name} has multiple abnormal stool diagnostic findings "
            f"(risk score {score}/100). Immediate physician review is recommended."
        )
        recommendation = (
            "Refer for colonoscopy or gastroenterology evaluation within 2 weeks."
        )
    elif level == "medium":
        summary = (
            f"{patient_name} has some irregular stool diagnostic results "
            f"(risk score {score}/100). Follow-up testing is advised."
        )
        recommendation = (
            "Repeat stool testing in 3 months or refer to gastroenterology."
        )
    else:
        summary = (
            f"{patient_name}'s stool diagnostic results are within acceptable ranges "
            f"(risk score {score}/100). Continue routine screening."
        )
        recommendation = "Continue routine annual colorectal cancer screening."

    return {
        "summary": summary,
        "key_findings": factors or ["No significant abnormalities detected"],
        "recommendation": recommendation,
        **risk_data,
    }
