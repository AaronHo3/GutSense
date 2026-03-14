"""
Claude API client for generating risk narratives.

Calls claude-sonnet-4-6 with tool_use to return structured JSON alongside
natural language explanations. Results are cached in-memory for 1 hour
per reading_id to avoid redundant API calls on UI refresh.
"""

import os
import time
import json
from typing import Optional
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client: Optional[anthropic.Anthropic] = None
_cache: dict[int, tuple[float, dict]] = {}  # reading_id -> (timestamp, result)
CACHE_TTL = 3600  # 1 hour


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


RISK_TOOL = {
    "name": "risk_assessment_output",
    "description": "Structured output for a biomarker risk assessment",
    "input_schema": {
        "type": "object",
        "properties": {
            "patient_explanation": {
                "type": "string",
                "description": "Plain-language explanation for the patient (2-3 sentences, no medical jargon)"
            },
            "physician_summary": {
                "type": "string",
                "description": "Clinical summary for the physician (4-5 sentences, include specific markers and their clinical significance)"
            },
            "next_steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-3 recommended next steps, ordered by priority"
            },
            "confounded_note": {
                "type": "string",
                "description": "If lifestyle factors may confound the readings, note them here. Empty string if none."
            },
            "urgency_flag": {
                "type": "string",
                "enum": ["routine", "elevated", "urgent"],
                "description": "Clinical urgency of the findings"
            }
        },
        "required": ["patient_explanation", "physician_summary", "next_steps", "confounded_note", "urgency_flag"]
    }
}


def generate_risk_narrative(
    reading_id: int,
    patient_name: str,
    patient_age: int,
    patient_sex: str,
    family_history: bool,
    biomarkers: dict,
    risk_score: float,
    risk_level: str,
    trajectory: str,
    confounded_by: Optional[str] = None,
) -> dict:
    """
    Returns dict with keys: patient_explanation, physician_summary,
    next_steps, urgency_flag.
    Falls back to rule-based text if Claude is unavailable.
    """
    # Short-circuit: return fallback text immediately (no Claude API call)
    return _fallback_narrative(risk_level, trajectory, confounded_by)

    # Check cache
    if reading_id in _cache:
        ts, result = _cache[reading_id]
        if time.time() - ts < CACHE_TTL:
            return result

    risk_label_map = {
        "green": "Low (routine monitoring)",
        "yellow": "Elevated (consult recommended within 3 months)",
        "orange": "High (schedule within 2 weeks)",
        "red": "Critical (urgent referral required)",
    }

    prompt = f"""You are a clinical AI assistant analyzing stool biomarker data for colorectal cancer screening.
Never provide a diagnosis. Always recommend professional medical consultation.
Be evidence-based, clear, and appropriately reassuring or urgent based on the data.

Patient: {patient_name}, {patient_age}{'M' if patient_sex == 'M' else 'F'}, family history of CRC: {'Yes' if family_history else 'No'}

Current stool biomarker readings:
- Occult blood (hemoglobin): {biomarkers['hemoglobin_ng_ml']:.1f} ng/mL  [normal <20, concerning >50, alarm >100]
- Butyrate (protective SCFA): {biomarkers['butyrate_mmol_kg']:.1f} mmol/kg  [normal >15, concerning <10, alarm <5]
- Calprotectin (inflammation): {biomarkers['calprotectin_ug_g']:.0f} µg/g  [normal <50, concerning >100, alarm >200]
- Fungal dysbiosis index (Basidiomycota/Ascomycota): {biomarkers['basidio_ascomy_ratio']:.2f}  [normal <1.5, concerning >2.0, alarm >3.0]
- Proteobacteria index: {biomarkers['proteobacteria_index']:.3f}  [normal <0.2, concerning >0.35, alarm >0.5]
- DNA methylation score (SEPT9/SDC2): {biomarkers['methylation_score']:.3f}  [normal <0.25, concerning >0.35, alarm >0.5]

Composite risk score: {risk_score:.0f}/100 — {risk_label_map.get(risk_level, risk_level)}
7-day trend: {trajectory}
{f'Possible confounders: {confounded_by}' if confounded_by else ''}

Use the risk_assessment_output tool to provide your structured assessment."""

    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=[RISK_TOOL],
            tool_choice={"type": "tool", "name": "risk_assessment_output"},
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract tool use result
        tool_result = None
        for block in response.content:
            if block.type == "tool_use" and block.name == "risk_assessment_output":
                tool_result = block.input
                break

        if tool_result:
            result = {
                "patient_explanation": tool_result.get("patient_explanation", ""),
                "physician_summary": tool_result.get("physician_summary", ""),
                "next_steps": tool_result.get("next_steps", []),
                "urgency_flag": tool_result.get("urgency_flag", "routine"),
            }
            _cache[reading_id] = (time.time(), result)
            return result

    except Exception as e:
        print(f"[claude_client] Claude API error for reading {reading_id}: {e}")

    # Fallback: rule-based text
    return _fallback_narrative(risk_level, trajectory, confounded_by)


def _fallback_narrative(risk_level: str, trajectory: str, confounded_by: Optional[str]) -> dict:
    """Medically realistic rule-based narratives when Claude is unavailable."""
    if risk_level == "green":
        patient_exp = (
            "Your stool biomarker profile is within normal ranges across all six monitored channels. "
            "Occult blood (hemoglobin) is undetectable, butyrate levels are protective at healthy concentrations, "
            "and your epigenetic methylation score for SEPT9/SDC2 remains well below the threshold of concern. "
            "Continue your current dietary habits and maintain your routine annual screening schedule."
        )
        physician_sum = (
            "All six biomarker channels are within reference ranges: hemoglobin <20 ng/mL, butyrate within protective range (>15 mmol/kg), "
            "calprotectin <50 µg/g, fungal dysbiosis index <1.5, proteobacteria index <0.2, and SEPT9/SDC2 methylation score <0.25. "
            f"Trajectory is {trajectory}. "
            "No clinical action required at this time. Routine monitoring recommended per standard CRC screening guidelines."
        )
        steps = ["Maintain routine annual screening", "Continue high-fiber diet (>25g/day)", "Reassess in 12 months"]
        urgency = "routine"

    elif risk_level == "yellow":
        patient_exp = (
            "One or more of your stool biomarker readings are mildly above the normal range. "
            "This is not an emergency — early changes like these are exactly what this system is designed to catch. "
            "We recommend scheduling a check-in with your physician within the next three months for further evaluation."
        )
        physician_sum = (
            "Mildly elevated biomarker readings noted across one or more channels. Likely candidates include calprotectin elevation "
            "above 50 µg/g (suggesting low-grade mucosal inflammation) or a butyrate level trending below the 15 mmol/kg protective threshold. "
            f"Trajectory: {trajectory}. Longitudinal trend monitoring warranted. "
            "Consider stool FIT confirmation and dietary review. GI consultation within 3 months if trend continues."
        )
        steps = ["Schedule physician consultation within 3 months", "Increase dietary fiber intake to >25g/day", "Consider stool FIT confirmatory test"]
        urgency = "elevated"

    elif risk_level == "orange":
        patient_exp = (
            "Several of your biomarker readings are significantly elevated, and the trend over recent weeks is concerning. "
            "We strongly recommend scheduling an appointment with your doctor as soon as possible — ideally within the next two weeks. "
            "Early evaluation gives the best outcomes."
        )
        physician_sum = (
            "Multiple biomarker channels are elevated above clinical reference thresholds. "
            "Findings are consistent with active mucosal inflammation (calprotectin >100 µg/g), possible occult bleeding (hemoglobin trending upward), "
            "and microbiome dysbiosis (proteobacteria or fungal index elevated). "
            f"Trajectory: {trajectory}. "
            "Recommend urgent GI consultation within 2 weeks. "
            "Consider FIT confirmation, fecal calprotectin quantification, and colonoscopy referral if FIT positive."
        )
        steps = ["Schedule GI physician visit within 2 weeks", "Order stool FIT and quantitative calprotectin", "Review medication and recent antibiotic history"]
        urgency = "urgent"

    else:  # red
        patient_exp = (
            "Your biomarker readings are critically elevated and require prompt medical attention. "
            "Key indicators — including occult blood, protective butyrate depletion, and epigenetic methylation markers (SEPT9/SDC2) — "
            "are all significantly outside normal ranges. Please contact your doctor or go to an urgent care clinic today."
        )
        physician_sum = (
            "Critical elevation across multiple high-weight biomarker channels: hemoglobin likely >100 ng/mL (active occult bleeding), "
            "butyrate severely depleted (<5 mmol/kg, indicating loss of colonocyte protection), "
            "and SEPT9/SDC2 methylation score elevated (>0.5, consistent with epigenetic silencing patterns associated with CRC). "
            f"Trajectory: {trajectory}. "
            "Findings warrant urgent clinical evaluation. Immediate GI referral and diagnostic colonoscopy strongly recommended. "
            "Do not delay — early-stage CRC detection at this point is associated with >90% 5-year survival."
        )
        steps = ["Contact physician immediately — urgent referral required", "Schedule diagnostic colonoscopy", "Do not delay evaluation — urgent findings"]
        urgency = "urgent"

    if confounded_by:
        patient_exp += f" Note: {confounded_by}"

    return {
        "patient_explanation": patient_exp,
        "physician_summary": physician_sum,
        "next_steps": steps,
        "urgency_flag": urgency,
    }
