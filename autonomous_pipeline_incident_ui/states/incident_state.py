import reflex as rx
import logging
from urllib.parse import quote
from autonomous_pipeline_incident_ui.models import IncidentRecord
from autonomous_pipeline_incident_ui.service import (
    get_incidents,
    load_catalog,
    ServiceError,
)
from autonomous_pipeline_incident_ui.states.scope_state import ScopeState


class IncidentState(rx.State):
    raw_incidents: list[IncidentRecord] = []
    search_query: str = ""
    status_filter: str = "ALL"
    severity_filter: str = "ALL"
    selected_sort: str = "Newest first"
    statuses: list[str] = [
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
    severities: list[str] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    sorts: list[str] = [
        "Newest first",
        "Oldest first",
        "Severity",
        "Incident ID",
        "Pipeline",
    ]
    page_loading: bool = False
    refreshing: bool = False
    switching: bool = False
    loaded: bool = False
    selecting: bool = False
    error_kind: str = ""
    feedback: str = "Connecting to the incident service…"
    updated_at: str = ""
    demo: bool = False
    _generation: int = 0
    _running_generation: int = -1
    _demo_detection: bool = False
    _previous_ids: list[str] = []
    _loaded_scope: tuple[str, str] = ("", "")

    @rx.var
    def busy(self) -> bool:
        return self.page_loading or self.refreshing or self.switching

    @rx.var
    def visible_incidents(self) -> list[IncidentRecord]:
        query = self.search_query.strip().casefold()
        rows = [
            row
            for row in self.raw_incidents
            if (self.status_filter == "ALL" or row.status == self.status_filter)
            and (
                self.severity_filter == "ALL"
                or row.severity == self.severity_filter
            )
            and (
                not query
                or query
                in f"{row.id} {row.pipeline} {row.tenant} {row.platform}".casefold()
            )
        ]
        if self.selected_sort == "Severity":
            ranks = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            return sorted(
                rows, key=lambda row: (ranks.get(row.severity, 4), row.id)
            )
        if self.selected_sort == "Incident ID":
            return sorted(rows, key=lambda row: row.id)
        if self.selected_sort == "Pipeline":
            return sorted(
                rows, key=lambda row: (row.pipeline.casefold(), row.id)
            )
        return sorted(
            rows,
            key=lambda row: (row.detected_at, row.id),
            reverse=self.selected_sort != "Oldest first",
        )

    @rx.var
    def error_title(self) -> str:
        return {
            "request_invalid": "Request was rejected",
            "conflict": "Another action is already running",
            "validation": "Request validation failed",
            "timeout": "The request timed out",
            "unauthorized": "Workspace access was denied",
            "unavailable": "Backend is unavailable",
            "api": "Unable to load incidents",
            "empty": "No incident register available",
        }.get(self.error_kind, "")

    @rx.var
    def error_description(self) -> str:
        return {
            "request_invalid": "Review the selected workspace and retry.",
            "conflict": "Wait for the current operation, then refresh.",
            "validation": "The service rejected this workspace context. Select an authorized workspace.",
            "timeout": "The service did not respond in time. Retry to request a fresh incident list.",
            "unauthorized": "Check your access with your administrator or select another workspace.",
            "unavailable": "The incident service could not be reached. No cached incidents are displayed.",
            "api": "The service returned an unsuccessful or invalid response. No partial results are displayed.",
            "empty": "No incident register was found for this workspace. Retry or select another workspace.",
        }.get(self.error_kind, "")

    def _invalidate(self):
        self._generation += 1
        self.raw_incidents = []
        self._previous_ids = []
        self._loaded_scope = ("", "")
        self.loaded = False
        self.selecting = False
        self.demo = False
        self._demo_detection = False
        self.search_query = ""
        self.status_filter = "ALL"
        self.severity_filter = "ALL"
        self.selected_sort = "Newest first"
        self.updated_at = ""
        self.error_kind = ""
        self.page_loading = False
        self.refreshing = False
        self.switching = False

    def _begin(self, operation: str):
        previous = [row.id for row in self.raw_incidents]
        detection = self._demo_detection
        filters = (
            self.search_query,
            self.status_filter,
            self.severity_filter,
            self.selected_sort,
        )
        self._invalidate()
        if operation in {"refresh", "detection"}:
            (
                self.search_query,
                self.status_filter,
                self.severity_filter,
                self.selected_sort,
            ) = filters
        self._previous_ids = (
            previous if operation in {"refresh", "detection"} else []
        )
        self._demo_detection = (
            detection if operation in {"refresh", "detection"} else False
        )
        self.page_loading = operation == "load"
        self.refreshing = operation in {"refresh", "detection"}
        self.switching = operation == "switch"
        self.feedback = {
            "load": "Loading authorized incidents…",
            "refresh": "Refreshing · waiting for the service…",
            "detection": "Checking for new detections · development demo…",
            "switch": "Switching workspace · loading authorized incidents…",
        }[operation]

    @rx.event
    async def page_load(self):
        scope = await self.get_state(ScopeState)
        scope.selected_incident = ""
        self.selecting = False
        if self.busy:
            return
        self._begin("load")
        yield IncidentState.fetch_incidents

    @rx.event
    async def refresh(self):
        if self.busy or self.selecting:
            return
        scope = await self.get_state(ScopeState)
        scope.selected_incident = ""
        self._begin("refresh")
        yield IncidentState.fetch_incidents

    @rx.event
    async def new_detection(self):
        if self.busy or self.selecting or not self.demo or self._demo_detection:
            return
        scope = await self.get_state(ScopeState)
        scope.selected_incident = ""
        self._demo_detection = True
        self._begin("detection")
        yield IncidentState.fetch_incidents

    @rx.event
    def set_query(self, value: str):
        self.search_query = value

    @rx.event
    def set_status(self, value: str):
        if value == "ALL" or value in self.statuses:
            self.status_filter = value

    @rx.event
    def set_severity(self, value: str):
        if value == "ALL" or value in self.severities:
            self.severity_filter = value

    @rx.event
    def set_sort(self, value: str):
        if value in self.sorts:
            self.selected_sort = value

    @rx.event
    def clear_filters(self):
        self.search_query = ""
        self.status_filter = "ALL"
        self.severity_filter = "ALL"
        self.selected_sort = "Newest first"

    @rx.event
    async def select_incident(self, identifier: str):
        if self.busy or self.selecting or not self.loaded:
            return
        scope = await self.get_state(ScopeState)
        if self._loaded_scope != (scope.tenant_id, scope.platform_id):
            return
        if not any(row.id == identifier for row in self.raw_incidents):
            return
        self.selecting = True
        scope.selected_incident = identifier
        return rx.redirect(f"/incidents/{quote(identifier, safe='')}")

    @rx.event(background=True)
    async def fetch_incidents(self):
        async with self:
            generation = self._generation
            if not self.busy or self._running_generation == generation:
                return
            self._running_generation = generation
            scope = await self.get_state(ScopeState)
            tenant, platform = scope.tenant_id, scope.platform_id
            needs_catalog = not scope.tenants or not scope.platforms
            detection = self._demo_detection
        try:
            if needs_catalog:
                catalog = await load_catalog()
                if not catalog.tenants or not catalog.platforms:
                    raise ServiceError("unauthorized")
                async with self:
                    if generation != self._generation:
                        return
                    scope = await self.get_state(ScopeState)
                    scope.tenants, scope.platforms = (
                        catalog.tenants,
                        catalog.platforms,
                    )
                    if not scope.tenant_id:
                        scope.tenant_id = catalog.tenants[0].id
                    if not scope.platform_id:
                        scope.platform_id = catalog.platforms[0].id
                    tenant, platform = scope.tenant_id, scope.platform_id
            result = await get_incidents(tenant, platform, detection)
            async with self:
                scope = await self.get_state(ScopeState)
                if generation != self._generation or (
                    scope.tenant_id,
                    scope.platform_id,
                ) != (tenant, platform):
                    return
                new_count = len(
                    {row.id for row in result.incidents}
                    - set(self._previous_ids)
                )
                self.feedback = (
                    f"{new_count} newly detected incident(s) · snapshot confirmed"
                    if self.refreshing and new_count
                    else "Incident snapshot confirmed"
                )
                if not result.demo:
                    scope.tenant_id, scope.platform_id = (
                        result.tenant_id,
                        result.platform_id,
                    )
                    scope.tenants = scope.tenants or result.tenants
                    scope.platforms = scope.platforms or result.platforms
                    tenant, platform = result.tenant_id, result.platform_id
                self.raw_incidents = result.incidents
                self.updated_at = result.updated_at
                self.demo = result.demo
                self.loaded = True
                self._loaded_scope = (tenant, platform)
        except Exception as error:
            kind = error.kind if isinstance(error, ServiceError) else "api"
            try:
                raise ServiceError(kind) from None
            except ServiceError as e:
                logging.exception(f"Error: {e}")
            async with self:
                scope = await self.get_state(ScopeState)
                if generation == self._generation and (
                    scope.tenant_id,
                    scope.platform_id,
                ) == (tenant, platform):
                    self.error_kind = kind
                    self.feedback = "No incident data is displayed."
        finally:
            async with self:
                if generation == self._generation:
                    self.page_loading = False
                    self.refreshing = False
                    self.switching = False
                    self._running_generation = -1
