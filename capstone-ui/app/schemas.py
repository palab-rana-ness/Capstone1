from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
IncidentStatus = Literal[
    "DETECTED",
    "QUEUED",
    "ANALYSIS_QUEUED",
    "SENDING",
    "SENDING_TO_AGENT",
    "ANALYZING",
    "EXECUTING",
    "INVESTIGATING",
    "DIAGNOSED",
    "REMEDIATION_PROPOSED",
    "AWAITING_APPROVAL",
    "REMEDIATING",
    "VALIDATING",
    "RESOLVED",
    "REJECTED",
    "ESCALATED",
]


class IncidentCreate(BaseModel):
    tenant_id: str
    pipeline: str
    platform: str
    severity: Severity
    problem: str
    source: str = "NEW_RELIC"


class Incident(BaseModel):
    incident_id: str
    tenant_id: str
    tenant_name: str = ""
    platform_id: str
    platform_name: str = ""
    pipeline: str
    severity: Severity
    status: IncidentStatus
    problem: str
    created_at: datetime
    updated_at: datetime
    source: str


class IncidentListResponse(BaseModel):
    items: list[Incident]


class LogEntry(BaseModel):
    log_id: str
    timestamp: datetime
    level: str
    source: str
    message: str
    fields: dict = Field(default_factory=dict)


class LogsResponse(BaseModel):
    incident_id: str
    items: list[LogEntry]


class AnalyzeRequest(BaseModel):
    requested_by: str
    reason: str = ""


class AnalyzeResponse(BaseModel):
    incident_id: str
    status: IncidentStatus


class Diagnosis(BaseModel):
    incident_id: str
    root_cause: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    severity: Severity


class HistoricalMatch(BaseModel):
    incident_id: str
    similarity: float = 0
    summary: str = ""


class HistoryResponse(BaseModel):
    incident_id: str
    items: list[HistoricalMatch]


class Remediation(BaseModel):
    incident_id: str
    action: str
    reason: str
    risk: Literal["LOW", "MEDIUM", "HIGH"]
    approval_required: bool
    allowed: bool


class ApproveRequest(BaseModel):
    approved_by: str
    comment: str = ""


class RejectRequest(BaseModel):
    rejected_by: str
    comment: str = ""


class RetryRequest(BaseModel):
    requested_by: str
    reason: str = ""


class ExecutionStatus(BaseModel):
    incident_id: str
    status: str
    action: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message: str = ""


class ValidationStatus(BaseModel):
    incident_id: str
    status: str
    recovery_confirmed: bool
    pipeline_status: str
    checked_at: datetime


class AuditEvent(BaseModel):
    event_id: str
    event: str
    timestamp: datetime
    actor: str
    details: dict = Field(default_factory=dict)


class TimelineResponse(BaseModel):
    incident_id: str
    events: list[AuditEvent]


class Tenant(BaseModel):
    tenant_id: str
    name: str


class TenantListResponse(BaseModel):
    items: list[Tenant]


class TenantConfig(BaseModel):
    tenant_id: str
    monitoring_enabled: bool = True
    remediation_policy: str = ""
    allowed_actions: list[Literal["Retry", "Restart", "Rollback"]] = Field(
        default_factory=list
    )


class Platform(BaseModel):
    platform_id: str
    name: str = ""


class PlatformListResponse(BaseModel):
    items: list[Platform]


class PlatformConfig(BaseModel):
    platform_id: str
    config: dict = Field(default_factory=dict)
