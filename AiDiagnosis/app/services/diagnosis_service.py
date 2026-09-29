"""Service that produces a structured Diagnosis from an incident + context."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from app.models.diagnosis import Diagnosis, SimilarIncident
from app.models.incident import Incident
from app.prompts.diagnosis import DIAGNOSIS_SYSTEM_PROMPT, build_diagnosis_prompt

logger = logging.getLogger(__name__)


class StructuredLLM(Protocol):
    """Minimal interface required from an LLM client for this service."""

    def invoke(self, messages: list[Any]) -> Diagnosis: ...


def diagnose_incident(
    incident: Incident,
    adapter_context: str,
    similar_incidents: list[SimilarIncident],
    llm: StructuredLLM | None = None,
) -> Diagnosis:
    """Run the diagnosis LLM step and return a validated Diagnosis.

    `llm` may be injected (e.g. in tests) as any object exposing an
    `invoke(messages) -> Diagnosis` method that already performs structured
    output parsing.
    """
    prompt = build_diagnosis_prompt(incident, adapter_context, similar_incidents)

    if llm is None:
        from app.services.llm_client import build_chat_llm

        base_llm = build_chat_llm()
        structured_llm = base_llm.with_structured_output(Diagnosis, method="json_schema")
        llm = structured_llm  # type: ignore[assignment]

    result = llm.invoke(
        [
            {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    if not isinstance(result, Diagnosis):
        raise TypeError(
            f"Diagnosis LLM returned unexpected type: {type(result)!r}"
        )

    if result.confidence >= 0.7 and not result.evidence:
        # Never allow a high-confidence diagnosis without any evidence.
        result = result.model_copy(
            update={
                "confidence": 0.3,
                "reasoning_summary": (
                    result.reasoning_summary
                    + " [confidence reduced: no supporting evidence provided]"
                ),
            }
        )

    return result
