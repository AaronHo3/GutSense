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
    rag_context: list = None,
) -> dict:
    """
    Returns dict with keys: patient_explanation, physician_summary,
    next_steps, urgency_flag.
    Falls back to rule-based text if Claude is unavailable.
    rag_context: list of similar historical cases from IRIS vector search.
    """
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

    rag_section = ""
    if rag_context:
        cases = []
        for i, c in enumerate(rag_context, 1):
            cases.append(
                f"  {i}. {c['risk_level'].upper()} risk (score {c['risk_score']:.0f}/100), "
                f"trajectory: {c['trajectory']}. Clinical outcome: {c['outcome']}"
            )
        rag_section = "\nSimilar historical cases (from IRIS vector search):\n" + "\n".join(cases) + "\n"

    prompt = f"""You are a clinical AI assistant analyzing stool biomarker data for colorectal cancer screening.
Never provide a diagnosis. Always recommend professional medical consultation.
Be evidence-based, clear, and appropriately reassuring or urgent based on the data.
{rag_section}
Patient: {patient_name}, {patient_age}{'M' if patient_sex == 'M' else 'F'}, family history of CRC: {'Yes' if family_history else 'No'}

Current stool biomarker readings:
- MPO (Myeloperoxidase): {biomarkers['mpo_ng_ml']:.1f} ng/mL  [normal <100, concerning >300, alarm >500]
- Haptoglobin (fecal): {biomarkers['haptoglobin_ug_g']:.1f} µg/g  [normal <50, concerning >120, alarm >200]
- Fibrinogen (fecal): {biomarkers['fibrinogen_ng_ml']:.1f} ng/mL  [normal <100, concerning >250, alarm >400]
- MMP-9: {biomarkers['mmp9_ng_ml']:.1f} ng/mL  [normal <30, concerning >80, alarm >150]
- Hemoglobin FIT: {biomarkers['hemoglobin_fit_ng_ml']:.1f} ng/mL  [normal <10, concerning >50, alarm >100]
- MMP-8: {biomarkers['mmp8_ng_ml']:.1f} ng/mL  [normal <30, concerning >80, alarm >150]
- PGRP-S: {biomarkers['pgrp_s_ng_ml']:.1f} ng/mL  [normal <20, concerning >55, alarm >100]
- Calprotectin: {biomarkers['calprotectin_ug_g']:.0f} µg/g  [normal <50, concerning >100, alarm >200]

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


def generate_referral(
    patient_name: str,
    patient_age: int,
    patient_sex: str,
    family_history: bool,
    has_nod2_variant: bool,
    biomarkers: dict,
    risk_score: float,
    risk_level: str,
    trajectory: str,
    physician_summary: str,
    next_steps: list,
) -> str:
    """
    Generate a formal GI referral letter. Returns the letter as a plain string.
    Falls back to a structured template if Claude is unavailable.
    """
    from datetime import date
    today = date.today().strftime("%B %d, %Y")
    sex_label = "male" if patient_sex == "M" else "female"
    urgency_map = {
        "green":  ("Routine", "within 3–6 months"),
        "yellow": ("Non-urgent", "within 3 months"),
        "orange": ("Semi-urgent", "within 2 weeks"),
        "red":    ("URGENT", "as soon as possible — within 48–72 hours"),
    }
    urgency_label, urgency_timeline = urgency_map.get(risk_level, ("Routine", "within 3 months"))

    prompt = f"""You are a clinical documentation assistant. Write a formal GI specialist referral letter on behalf of a primary care physician using the patient data below.

The letter must follow this exact structure:
1. Date and header (To: Gastroenterology, From: Primary Care Physician, Re: patient)
2. Opening: reason for referral in one sentence
3. Clinical findings paragraph: summarize the biomarker results and composite risk score in clinical language
4. Urgency and requested evaluation
5. Closing with signature line for the physician

Patient: {patient_name}, {patient_age}-year-old {sex_label}
Family history of CRC: {'Yes' if family_history else 'No'}
NOD2 variant: {'Yes' if has_nod2_variant else 'No'}

Biomarker results:
- Hemoglobin FIT: {biomarkers['hemoglobin_fit_ng_ml']:.1f} ng/mL (normal <10)
- Calprotectin: {biomarkers['calprotectin_ug_g']:.0f} µg/g (normal <50)
- MPO: {biomarkers['mpo_ng_ml']:.1f} ng/mL (normal <100)
- MMP-9: {biomarkers['mmp9_ng_ml']:.1f} ng/mL (normal <30)
- MMP-8: {biomarkers['mmp8_ng_ml']:.1f} ng/mL (normal <30)
- Fibrinogen (fecal): {biomarkers['fibrinogen_ng_ml']:.1f} ng/mL (normal <100)
- Haptoglobin (fecal): {biomarkers['haptoglobin_ug_g']:.1f} µg/g (normal <50)
- PGRP-S: {biomarkers['pgrp_s_ng_ml']:.1f} ng/mL (normal <20)

Composite GutSense risk score: {risk_score:.0f}/100
7-day trend: {trajectory}
Urgency: {urgency_label} — {urgency_timeline}

Clinical assessment: {physician_summary}

Write the letter in formal medical language. Today's date is {today}. Do not include a subject line like "Subject:" — use "Re:" inline in the header."""

    try:
        c = _get_client()
        response = c.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"[claude_client] Referral generation failed: {e}")

    # Fallback template
    elevated = [
        name for name, val, threshold in [
            ("Hemoglobin FIT", biomarkers['hemoglobin_fit_ng_ml'], 10),
            ("Calprotectin", biomarkers['calprotectin_ug_g'], 50),
            ("MPO", biomarkers['mpo_ng_ml'], 100),
            ("MMP-9", biomarkers['mmp9_ng_ml'], 30),
            ("MMP-8", biomarkers['mmp8_ng_ml'], 30),
            ("Fibrinogen", biomarkers['fibrinogen_ng_ml'], 100),
            ("Haptoglobin", biomarkers['haptoglobin_ug_g'], 50),
            ("PGRP-S", biomarkers['pgrp_s_ng_ml'], 20),
        ] if val > threshold
    ]
    elevated_str = ", ".join(elevated) if elevated else "multiple markers"
    fhx = "with a positive family history of colorectal cancer" if family_history else ""
    nod2 = " and a known NOD2 variant" if has_nod2_variant else ""
    return f"""{today}

To: Gastroenterology Department
From: Primary Care Physician (via GutSense Monitoring Platform)
Re: {patient_name} — GI Referral

Dear Gastroenterology Colleague,

I am writing to refer {patient_name}, a {patient_age}-year-old {sex_label} {fhx}{nod2}, for gastroenterological evaluation following abnormal stool biomarker results obtained through continuous GutSense monitoring.

Clinical Findings:
The patient's composite GutSense risk score is {risk_score:.0f}/100 (risk level: {risk_level.upper()}), with a 7-day trend of {trajectory}. Notably elevated biomarkers include: {elevated_str}. {physician_summary}

Urgency: {urgency_label}
Please evaluate {urgency_timeline}. Diagnostic colonoscopy is recommended given the above findings.

Requested Evaluation:
- Gastroenterological consultation
- Diagnostic colonoscopy
- Correlation with clinical history and symptom review

Thank you for your prompt attention to this referral. Please contact our office with any questions.

Sincerely,

_______________________________
Primary Care Physician
GutSense Monitoring Program
"""


def _fallback_narrative(risk_level: str, trajectory: str, confounded_by: Optional[str]) -> dict:
    """Medically realistic rule-based narratives when Claude is unavailable."""
    if risk_level == "green":
        patient_exp = (
            "Your stool biomarker profile is within normal ranges across all eight monitored channels. "
            "Hemoglobin FIT (occult blood) is undetectable, inflammatory markers MPO and calprotectin are at healthy levels, "
            "and tissue-remodeling enzymes MMP-8 and MMP-9 show no signs of mucosal degradation. "
            "Continue your current dietary habits and maintain your routine annual screening schedule."
        )
        physician_sum = (
            "All eight biomarker channels within reference ranges: Hgb-FIT <10 ng/mL, MPO <100 ng/mL, "
            "calprotectin <50 µg/g, MMP-9 <30 ng/mL, MMP-8 <30 ng/mL, haptoglobin <50 µg/g, "
            f"fibrinogen <100 ng/mL, PGRP-S <20 ng/mL. Trajectory: {trajectory}. "
            "No clinical action required. Routine monitoring per standard CRC screening guidelines."
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
            "Mildly elevated readings in one or more inflammatory channels. Likely candidates include calprotectin "
            "above 50 µg/g (low-grade mucosal inflammation), MPO trending above 100 ng/mL (neutrophil activation), "
            f"or MMP-9/MMP-8 showing early ECM remodeling activity. Trajectory: {trajectory}. "
            "Longitudinal trend monitoring warranted. GI consultation within 3 months if trend continues."
        )
        steps = ["Schedule physician consultation within 3 months", "Increase dietary fiber intake to >25g/day", "Consider confirmatory FIT test"]
        urgency = "elevated"

    elif risk_level == "orange":
        patient_exp = (
            "Several of your biomarker readings are significantly elevated, and the trend over recent weeks is concerning. "
            "We strongly recommend scheduling an appointment with your doctor as soon as possible — ideally within the next two weeks. "
            "Early evaluation gives the best outcomes."
        )
        physician_sum = (
            "Multiple biomarker channels elevated above clinical thresholds. Findings suggest active mucosal inflammation "
            "(calprotectin >100 µg/g, MPO >300 ng/mL), possible occult bleeding (Hgb-FIT trending upward), "
            f"and matrix remodeling activity (MMP-9 or MMP-8 elevated). Trajectory: {trajectory}. "
            "Urgent GI consultation within 2 weeks. Consider confirmatory FIT, quantitative calprotectin, "
            "and colonoscopy referral if FIT positive."
        )
        steps = ["Schedule GI physician visit within 2 weeks", "Order confirmatory FIT and quantitative calprotectin", "Review medication and recent antibiotic history"]
        urgency = "urgent"

    else:  # red
        patient_exp = (
            "Your biomarker readings are critically elevated and require prompt medical attention. "
            "Key indicators — including occult blood (Hemoglobin FIT), the inflammatory enzymes MPO, MMP-8 and MMP-9, "
            "and fecal haptoglobin — are all significantly outside normal ranges. "
            "Please contact your doctor or go to an urgent care clinic today."
        )
        physician_sum = (
            "Critical elevation across multiple high-weight channels: Hgb-FIT likely >100 ng/mL (active occult bleeding), "
            "MPO >500 ng/mL (severe neutrophil-mediated oxidative stress), MMP-9 and MMP-8 markedly elevated "
            "(aggressive ECM degradation consistent with invasive lesion), calprotectin >200 µg/g, "
            f"fibrinogen and haptoglobin acutely elevated. Trajectory: {trajectory}. "
            "Findings warrant immediate clinical evaluation. Urgent GI referral and diagnostic colonoscopy strongly recommended. "
            "Do not delay — early-stage detection is associated with >90% 5-year survival."
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
