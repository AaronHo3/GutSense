"""
LangChain + IRIS Vector Search RAG pipeline.

Architecture:
  1. FHIR Bundle text for each patient is embedded (OpenAI text-embedding-3-small)
  2. Embeddings stored in IRIS via IRISVector (LangChain's IRIS vector store)
  3. On patient lookup: retrieve k most similar FHIR cases from IRIS
  4. Feed retrieved cases as context to GPT-4o-mini → RAG-generated clinical narrative

If OPENAI_API_KEY is not set, the module degrades gracefully:
  - Vector operations are skipped
  - RAG summary falls back to the rule-based text from openai_client.py
"""

import logging
import os
import warnings
from typing import Optional

# Suppress Pydantic v1 compatibility warning on Python 3.14
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

logger = logging.getLogger(__name__)

def _iris_conn() -> str:
    host = os.getenv("IRIS_HOST", "localhost")
    port = os.getenv("IRIS_PORT", "1972")
    user = os.getenv("IRIS_USER", "demo")
    pw   = os.getenv("IRIS_PASS", "demo")
    ns   = os.getenv("IRIS_NAMESPACE", "USER")
    return f"iris://{user}:{pw}@{host}:{port}/{ns}"
COLLECTION = "gutsense_fhir_v1"
EMBED_MODEL = "text-embedding-3-small"
VECTOR_DIM = 1536

_store = None          # IRISVector instance (lazy)
_seeded = False        # whether documents have been added


# ---------------------------------------------------------------------------
# Lazy initialisation helpers
# ---------------------------------------------------------------------------

def _api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "")


def _get_store():
    """Return (and lazily create) the IRISVector store."""
    global _store
    if _store is not None:
        return _store
    if not _api_key():
        return None
    try:
        from langchain_iris import IRISVector
        from langchain_openai import OpenAIEmbeddings

        emb = OpenAIEmbeddings(model=EMBED_MODEL, api_key=_api_key())
        _store = IRISVector(
            embedding_function=emb,
            dimension=VECTOR_DIM,
            collection_name=COLLECTION,
            connection_string=_iris_conn(),
        )
        logger.info(f"[LangChain] IRISVector store ready (collection={COLLECTION})")
        return _store
    except Exception as e:
        logger.warning(f"[LangChain] Could not initialise IRISVector: {e}")
        return None


def is_available() -> bool:
    return bool(_api_key()) and _get_store() is not None


def clear():
    global _store, _seeded
    _store = None
    _seeded = False


# ---------------------------------------------------------------------------
# Seeding: add FHIR documents to IRIS vector store
# ---------------------------------------------------------------------------

def seed_fhir_documents(patients: list[dict]) -> int:
    """
    Store FHIR bundle text for each patient as a LangChain Document in IRIS.

    patients: list of dicts with keys
      patient_id, name, risk_level, risk_score, fhir_text
    Returns number of documents added.
    """
    global _seeded
    if _seeded:
        return 0

    store = _get_store()
    if not store:
        # Bug #7 fix: don't permanently block seeding when store is unavailable
        # (OPENAI_API_KEY may be added after first call). Leave _seeded=False to allow retry.
        return 0

    try:
        from langchain_core.documents import Document

        # Dedup: use a high k to reliably scan all existing docs (not just top similarity match)
        existing_ids = {p["patient_id"] for p in patients}
        try:
            results = store.similarity_search("patient biomarker risk", k=max(100, len(patients) * 10))
            stored_ids = {
                r.metadata.get("patient_id") for r in results
                if r.metadata.get("patient_id") in existing_ids
            }
        except Exception:
            stored_ids = set()

        to_add = [p for p in patients if p["patient_id"] not in stored_ids]
        if not to_add:
            logger.info("[LangChain] IRIS vector store already populated, skipping seed")
            _seeded = True
            return 0

        docs = [
            Document(
                page_content=p["fhir_text"],
                metadata={
                    "patient_id":   p["patient_id"],
                    "patient_name": p["name"],
                    "risk_level":   p["risk_level"],
                    "risk_score":   str(p["risk_score"]),
                },
            )
            for p in to_add
        ]

        store.add_documents(docs)
        _seeded = True
        logger.info(f"[LangChain] Seeded {len(docs)} FHIR documents into IRIS Vector Search")
        return len(docs)

    except Exception as e:
        logger.error(f"[LangChain] Seeding failed: {e}")
        _seeded = True
        return 0


# ---------------------------------------------------------------------------
# RAG: retrieve similar cases → generate clinical narrative
# ---------------------------------------------------------------------------

def generate_rag_summary(
    patient_name: str,
    patient_fhir_text: str,
    risk_level: str,
    risk_score: int,
    patient_id: str = "",  # Bug #3 fix: use ID for self-exclusion, not name
    k: int = 3,
) -> Optional[dict]:
    """
    Retrieve similar FHIR cases from IRIS and use them as RAG context
    to generate a richer clinical narrative.

    Returns:
      {"summary": str, "similar_cases": list, "powered_by": "LangChain + IRIS Vector Search"}
    or None if LangChain is unavailable.
    """
    store = _get_store()
    if not store:
        return None

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate

        # Retrieve similar patients from IRIS Vector Search
        similar_docs = store.similarity_search_with_score(patient_fhir_text, k=k + 1)

        # Bug #3 fix: exclude by patient_id (unique), not patient_name (can collide)
        similar_docs = [
            (doc, score)
            for doc, score in similar_docs
            if doc.metadata.get("patient_id") != patient_id
        ][:k]

        _valid_levels = {"low", "medium", "high"}
        similar_cases = [
            {
                "patient_name": doc.metadata.get("patient_name", "Anonymous"),
                # Bug #4 fix: coerce invalid risk_level to "low" to satisfy TypeScript enum
                "risk_level":   doc.metadata.get("risk_level", "low") if doc.metadata.get("risk_level") in _valid_levels else "low",
                "risk_score":   int(float(doc.metadata.get("risk_score", 0))),
                "similarity":   round(float(score), 3),
                "summary":      doc.page_content[:300],
            }
            for doc, score in similar_docs
        ]

        # Build RAG prompt
        context_text = "\n\n".join(
            f"Case {i+1} (similarity {s['similarity']:.0%}, risk={s['risk_level']}):\n{s['summary']}"
            for i, s in enumerate(similar_cases)
        ) or "No similar cases found."

        prompt = ChatPromptTemplate.from_template(
            "You are a clinical AI assistant specialising in colorectal cancer risk.\n"
            "Using similar historical patient cases retrieved from the IRIS Vector Search "
            "database, generate a concise clinical summary for the current patient.\n\n"
            "Similar cases from IRIS:\n{context}\n\n"
            "Current patient — {patient_name} (risk={risk_level}, score={risk_score}/100):\n"
            "{fhir_text}\n\n"
            "Provide a 2-3 sentence plain-language clinical summary for the physician, "
            "highlighting key findings and recommended next steps."
        )

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=_api_key())
        chain = prompt | llm
        result = chain.invoke({
            "context":      context_text,
            "patient_name": patient_name,
            "risk_level":   risk_level,
            "risk_score":   risk_score,
            "fhir_text":    patient_fhir_text[:1500],
        })

        return {
            "summary":      result.content,
            "similar_cases": similar_cases,
            "powered_by":   "LangChain + IRIS Vector Search",
        }

    except Exception as e:
        logger.error(f"[LangChain] RAG generation failed for {patient_name}: {e}")
        return None
