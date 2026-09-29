"""Service that produces remediation recommendations from a diagnosis."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.models.diagnosis import Diagnosis, SimilarIncident
from app.models.incident import Incident
from app.models.remediation import RemediationAction
from app.prompts.remediation import REMEDIATION_SYSTEM_PROMPT, build_remediation_prompt

logger = logging.getLogger(__name__)


class RemediationList(BaseModel):
    """Wrapper schema so the LLM can return multiple remediation actions."""

    remedies: list[RemediationAction] = Field(default_factory=list)


class StructuredLLM(Protocol):
    """Minimal interface required from an LLM client for this service."""

    def invoke(self, messages: list[Any]) -> RemediationList: ...


def recommend_remediation(
    incident: Incident,
    diagnosis: Diagnosis,
    allowed_actions: list[str],
    similar_incidents: list[SimilarIncident],
    llm: StructuredLLM | None = None,
) -> list[RemediationAction]:
    """Run the remediation LLM step and return a list of proposed actions.

    These are recommendations only; nothing here executes any action.
    """
    prompt = build_remediation_prompt(
        incident, diagnosis, allowed_actions, similar_incidents
    )

    if llm is None:
        from app.services.llm_client import build_chat_llm

        base_llm = build_chat_llm()
        llm = base_llm.with_structured_output(  # type: ignore[assignment]
            RemediationList, method="json_schema"
        )

    result = llm.invoke(
        [
            {"role": "system", "content": REMEDIATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    if not isinstance(result, RemediationList):
        raise TypeError(
            f"Remediation LLM returned unexpected type: {type(result)!r}"
        )

    return list(result.remedies)
