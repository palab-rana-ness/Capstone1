"""Pydantic models for remediation recommendations."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["low", "medium", "high"]
RiskLevel = str


class RemediationAction(BaseModel):
    """A single, non-executed remediation recommendation.

    This is a recommendation only. Nothing in this system ever executes
    the action against a real pipeline, Spark cluster, or Synapse job.
    """

    action: str
    explanation: str
    priority: Priority = "medium"
    risk: str
    requires_approval: bool = True


class RemediationValidationResult(BaseModel):
    """Result of the deterministic post-LLM safety validation step."""

    valid_actions: list[RemediationAction] = Field(default_factory=list)
    rejected_actions: list[str] = Field(default_factory=list)
    reasons: dict[str, str] = Field(default_factory=dict)
