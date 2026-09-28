import reflex as rx
from pydantic import (
    BaseModel,
    Field,
    AwareDatetime,
    ConfigDict,
    model_validator,
)
from typing import Literal


class DetailEntry(BaseModel):
    label: str
    value: str
    timestamp: str = ""


class DetailSection(BaseModel):
    progress: str = "Not reported"
    summary: str = ""
    entries: list[DetailEntry] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=100)
    severity: str = ""
    outcome: str = ""
    available: bool = False
    confidence_supplied: bool = False
    recovery_confirmed: bool = Field(default=False, strict=True)


class ActionCapability(BaseModel):
    operation: Literal[
        "request_approval", "analyze", "approve", "reject", "execute_retry"
    ]
    label: str
    confirmation: str = ""


class DetailResponse(BaseModel):
    tenant_id: str
    platform_id: str
    incident: "IncidentRecord"
    sections: dict[str, DetailSection]
    capabilities: list[ActionCapability] = Field(default_factory=list)
    approval_required: bool = Field(strict=True)
    execution_policy: str
    revision: int = 0
    summary: str = ""
    demo: bool = False
    tenants: list["ScopeOption"] = Field(default_factory=list)
    platforms: list["ScopeOption"] = Field(default_factory=list)


class ConfigurationValues(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    monitoring_enabled: bool = False
    interval_seconds: int = Field(default=60, ge=15, le=3600)
    failure_threshold: int = Field(default=3, ge=1, le=100)
    latency_seconds: int = Field(default=120, ge=10, le=3600)
    remediation_policy: str = ""
    allowed_actions: list[Literal["Retry", "Restart", "Rollback"]] = Field(
        default_factory=list
    )


class ScopeOption(BaseModel):
    id: str
    label: str


class ConfigurationResponse(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def require_complete_values(cls, data: object) -> object:
        if isinstance(data, dict):
            values = data.get("values")
            if isinstance(values, dict) and not set(
                ConfigurationValues.model_fields
            ).issubset(values):
                raise ValueError("Incomplete configuration values")
        return data

    tenant_id: str = Field(min_length=1)
    platform_id: str = Field(min_length=1)
    values: ConfigurationValues
    revision: int = Field(ge=0)
    updated_at: str = Field(min_length=1)
    can_edit: bool = Field(strict=True)
    policies: list[ScopeOption]
    action_options: list[Literal["Retry", "Restart", "Rollback"]]
    demo: bool = False


class ConfigurationSavedResponse(ConfigurationResponse):
    saved: Literal[True]
    request_id: str = Field(min_length=1)


class Catalog(BaseModel):
    tenants: list["ScopeOption"]
    platforms: list[ScopeOption]


class Metric(BaseModel):
    label: str
    value: str
    note: str


class Incident(BaseModel):
    id: str
    pipeline: str
    tenant: str
    platform: str
    severity: str
    status: str
    detected: str
    recovery_confirmed: bool = False


class IncidentRecord(Incident):
    tenant_id: str
    platform_id: str
    detected_at: AwareDatetime
    status: Literal[
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
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]


DetailResponse.model_rebuild()


class IncidentsResponse(BaseModel):
    tenants: list[ScopeOption] = Field(default_factory=list)
    platforms: list[ScopeOption] = Field(default_factory=list)
    tenant_id: str
    platform_id: str
    updated_at: str
    incidents: list[IncidentRecord]
    metrics: list[Metric] = Field(default_factory=list)
    pipelines: list["Pipeline"] = Field(default_factory=list)
    window: str = ""
    summary: str = ""
    demo: bool = False


class WorkflowResponse(BaseModel):
    section: DetailSection = Field(default_factory=DetailSection)
    status: str = ""
    accepted: bool = False
    capabilities: list[ActionCapability] = Field(default_factory=list)
    capabilities_supplied: bool = False
    approval_required: bool = False
    approval_supplied: bool = False


class PlatformConfiguration(BaseModel):
    platform_id: str
    summary: str = ""
    entries: list[DetailEntry] = Field(default_factory=list)


class LogEntry(BaseModel):
    timestamp: str
    level: str = "UNKNOWN"
    source: str = ""
    message: str = ""
    fields_json: str = "{}"


class LogsResponse(BaseModel):
    entries: list[LogEntry] = Field(default_factory=list)


class Pipeline(BaseModel):
    name: str
    health: float = Field(ge=0, le=100)
    status: str
    detail: str


class DashboardResponse(BaseModel):
    tenants: list[ScopeOption] = Field(default_factory=list)
    platforms: list[ScopeOption] = Field(default_factory=list)
    tenant_id: str
    platform_id: str
    updated_at: str
    window: str
    metrics: list[Metric]
    incidents: list[Incident]
    pipelines: list[Pipeline]
    summary: str
    demo: bool = False
