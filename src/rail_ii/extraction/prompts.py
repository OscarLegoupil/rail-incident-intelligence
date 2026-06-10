"""
Prompt templates for LLM-based incident extraction.

Prompts are stored as plain strings, separate from extraction logic, so they
can be iterated on, diffed, and evaluated independently of the calling code.
"""

from __future__ import annotations

from rail_ii.ingestion.document import Document
from rail_ii.schema.incident import IncidentSeverity, IncidentSystem

SYSTEM_VALUES = ", ".join(s.value for s in IncidentSystem)
SEVERITY_VALUES = ", ".join(s.value for s in IncidentSeverity)


SYSTEM_PROMPT = f"""You are an information extraction system for rail maintenance reports.

Read a maintenance report and produce a single JSON object describing the
incident. Output ONLY the JSON object - no prose, no markdown fences, no
explanation before or after.

The JSON object must contain exactly these keys:
- report_id (string, required): the report identifier provided by the caller
- operator (string or null)
- train_id (string or null)
- incident_datetime (ISO 8601 datetime string or null)
- location (string or null)
- system (one of: {SYSTEM_VALUES})
- component (string or null)
- symptom (string, required, non-empty): concise description of the failure
- severity (one of: {SEVERITY_VALUES})
- service_impact (string or null)
- confidence (number between 0.0 and 1.0): your confidence in the extraction
- source_text (string or null): the most relevant verbatim excerpt

Rules:
- Use null when a field is not present or cannot be inferred reliably.
- Use "unknown" for system or severity if they cannot be determined.
- Do not invent identifiers, dates, locations, or operators.
- Keep symptom to a single sentence when possible.
"""


USER_PROMPT_TEMPLATE = """Report ID: {report_id}

--- REPORT TEXT ---
{report_text}
--- END REPORT ---

Return the JSON object now."""


def build_user_prompt(document: Document) -> str:
    """Render the user prompt for a given document."""
    text = document.normalized_text or document.raw_text or ""
    return USER_PROMPT_TEMPLATE.format(
        report_id=document.document_id,
        report_text=text.strip(),
    )
