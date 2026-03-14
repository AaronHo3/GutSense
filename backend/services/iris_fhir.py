"""
IRIS FHIR REST client.

Queries DiagnosticReport and Observation resources from an InterSystems IRIS
FHIR R4 server running on port 52773.  Auto-discovers the correct FHIR
namespace by probing common endpoint patterns.

Caches responses for _CACHE_TTL seconds to avoid hammering IRIS during UI
renders.
"""

import logging
import os
import time
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (override via environment variables)
# ---------------------------------------------------------------------------
IRIS_HOST = os.getenv("IRIS_HOST", "localhost")
IRIS_FHIR_PORT = os.getenv("IRIS_FHIR_PORT", "52773")
IRIS_USER = os.getenv("IRIS_USER", "demo")
IRIS_PASS = os.getenv("IRIS_PASS", "demo")

# Candidate FHIR base URLs — tried in order until one responds with a
# valid CapabilityStatement (resourceType == "CapabilityStatement").
_FHIR_CANDIDATES = [
    f"http://{IRIS_HOST}:{IRIS_FHIR_PORT}/fhir/r4",
    f"http://{IRIS_HOST}:{IRIS_FHIR_PORT}/csp/healthshare/fhirserver/fhir/r4",
    f"http://{IRIS_HOST}:{IRIS_FHIR_PORT}/fhir/FHIRSERVER/r4",
    f"http://{IRIS_HOST}:{IRIS_FHIR_PORT}/api/FHIR/R4",
]

_CACHE_TTL = 120  # seconds

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_fhir_base: Optional[str] = None          # discovered base URL
_auth = HTTPBasicAuth(IRIS_USER, IRIS_PASS)
_headers = {"Accept": "application/fhir+json"}
_cache: dict = {}


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _discover_fhir_base() -> Optional[str]:
    """Return the first reachable FHIR base URL, caching the result."""
    global _fhir_base
    if _fhir_base:
        return _fhir_base

    for base in _FHIR_CANDIDATES:
        try:
            r = requests.get(
                f"{base}/metadata",
                auth=_auth,
                headers=_headers,
                timeout=5,
            )
            if r.status_code == 200 and "CapabilityStatement" in r.text:
                logger.info(f"[IRIS FHIR] Connected: {base}")
                _fhir_base = base
                return _fhir_base
        except Exception:
            continue

    logger.warning(
        f"[IRIS FHIR] No FHIR server reachable on "
        f"{IRIS_HOST}:{IRIS_FHIR_PORT}"
    )
    return None


def is_connected() -> bool:
    return _discover_fhir_base() is not None


def clear_cache():
    """Force-clear in-memory cache and re-discover FHIR base on next call."""
    global _fhir_base
    _cache.clear()
    _fhir_base = None


# ---------------------------------------------------------------------------
# Low-level FHIR GET
# ---------------------------------------------------------------------------

def _fhir_get(resource_type: str, params: Optional[dict] = None) -> Optional[dict]:
    base = _discover_fhir_base()
    if not base:
        return None
    try:
        r = requests.get(
            f"{base}/{resource_type}",
            auth=_auth,
            headers=_headers,
            params=params or {},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"[IRIS FHIR] GET {resource_type} params={params}: {e}")
        return None


def _extract_entries(bundle: Optional[dict]) -> list[dict]:
    if not bundle or bundle.get("resourceType") != "Bundle":
        return []
    return [e["resource"] for e in bundle.get("entry", []) if "resource" in e]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_patients() -> list[dict]:
    """Return all FHIR Patient resources (cached)."""
    key = "patients"
    cached = _cache.get(key)
    if cached and time.time() - cached["ts"] < _CACHE_TTL:
        return cached["data"]

    bundle = _fhir_get("Patient", {"_count": 200})
    result = _extract_entries(bundle)
    _cache[key] = {"data": result, "ts": time.time()}
    return result


def get_diagnostic_reports(patient_fhir_id: str) -> list[dict]:
    """Return DiagnosticReport resources for a patient (cached)."""
    key = f"dr_{patient_fhir_id}"
    cached = _cache.get(key)
    if cached and time.time() - cached["ts"] < _CACHE_TTL:
        return cached["data"]

    bundle = _fhir_get(
        "DiagnosticReport",
        {"patient": patient_fhir_id, "_count": 50, "_sort": "-date"},
    )
    result = _extract_entries(bundle)
    _cache[key] = {"data": result, "ts": time.time()}
    return result


def get_observations(patient_fhir_id: str) -> list[dict]:
    """Return Observation resources for a patient (cached).

    Tries with category=laboratory first; falls back to no category filter
    in case the data isn't categorised.
    """
    key = f"obs_{patient_fhir_id}"
    cached = _cache.get(key)
    if cached and time.time() - cached["ts"] < _CACHE_TTL:
        return cached["data"]

    bundle = _fhir_get(
        "Observation",
        {
            "patient": patient_fhir_id,
            "_count": 200,
            "_sort": "-date",
            "category": "laboratory",
        },
    )
    result = _extract_entries(bundle)

    if not result:
        bundle = _fhir_get(
            "Observation",
            {"patient": patient_fhir_id, "_count": 200, "_sort": "-date"},
        )
        result = _extract_entries(bundle)

    _cache[key] = {"data": result, "ts": time.time()}
    return result
