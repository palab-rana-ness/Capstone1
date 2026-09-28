import reflex as rx
import logging
import reflex_xy
from autonomous_pipeline_incident_ui.models import Metric, Incident, Pipeline
from autonomous_pipeline_incident_ui.service import (
    load_catalog,
    load_dashboard,
    ServiceError,
)
from urllib.parse import quote
from autonomous_pipeline_incident_ui.states.scope_state import ScopeState


class DashboardState(rx.State):
    metrics: list[Metric] = []
    incidents: list[Incident] = []
    pipelines: list[Pipeline] = []
    page_loading: bool = False
    dashboard_refreshing: bool = False
    tenant_switching: bool = False
    platform_switching: bool = False
    loaded: bool = False
    error_kind: str = ""
    updated_at: str = ""
    window: str = ""
    summary: str = ""
    demo: bool = False
    _running: bool = False
    selecting: bool = False
    _loaded_scope: tuple[str, str] = ("", "")

    @rx.var
    def busy(self) -> bool:
        return (
            self.page_loading
            or self.dashboard_refreshing
            or self.tenant_switching
            or self.platform_switching
        )

    @rx.var
    def feedback(self) -> str:
        if self.tenant_switching:
            return "Switching tenant · loading isolated workspace…"
        if self.platform_switching:
            return "Switching platform · loading pipeline telemetry…"
        if self.dashboard_refreshing:
            return "Refreshing · waiting for a confirmed snapshot…"
        return "Connecting to your operations workspace…"

    @rx.var
    def error_title(self) -> str:
        return {
            "request_invalid": "Request was rejected",
            "conflict": "Another action is already running",
            "validation": "Request validation failed",
            "timeout": "The request timed out",
            "unauthorized": "Workspace access was denied",
            "unavailable": "Backend is unavailable",
            "api": "Unable to load this snapshot",
            "empty": "No snapshot available",
        }.get(self.error_kind, "Unable to load dashboard")

    @rx.var
    def error_description(self) -> str:
        return {
            "request_invalid": "Review the workspace context and retry.",
            "conflict": "Wait for the current operation, then refresh.",
            "validation": "The service rejected this workspace context. Select an authorized workspace.",
            "timeout": "The service did not respond in time. Retry to request a fresh snapshot.",
            "unauthorized": "The service rejected this request. Check your access with your administrator or select another workspace.",
            "unavailable": "We could not connect to the operations service. No cached data is being displayed.",
            "api": "The service returned an unsuccessful or invalid response. No partial results have been displayed.",
            "empty": "The service has no dashboard snapshot for this workspace. Retry or select another workspace.",
        }.get(self.error_kind, "")

    @reflex_xy.data
    def health_chart(self) -> dict[str, list[str] | list[float]]:
        return {
            "pipeline": [p.name for p in self.pipelines],
            "health": [p.health for p in self.pipelines],
        }

    def _begin(self, operation: str):
        self.selecting = False
        self._loaded_scope = ("", "")
        self.page_loading = operation == "load"
        self.dashboard_refreshing = operation == "refresh"
        self.tenant_switching = operation == "tenant"
        self.platform_switching = operation == "platform"
        self.metrics = []
        self.incidents = []
        self.pipelines = []
        self.updated_at = ""
        self.summary = ""
        self.window = ""
        self.loaded = False
        self.demo = False
        self.error_kind = ""

    @rx.event
    async def page_load(self):
        if self.busy:
            return
        scope = await self.get_state(ScopeState)
        scope.selected_incident = ""
        self._begin("load")
        yield DashboardState.fetch_dashboard

    @rx.event
    async def refresh_dashboard(self):
        if self.busy:
            return
        scope = await self.get_state(ScopeState)
        scope.selected_incident = ""
        self._begin("refresh")
        yield DashboardState.fetch_dashboard

    @rx.event
    async def select_incident(self, identifier: str):
        if self.busy or self.selecting or not self.loaded:
            return
        scope = await self.get_state(ScopeState)
        if self._loaded_scope != (
            scope.tenant_id,
            scope.platform_id,
        ) or not any(row.id == identifier for row in self.incidents):
            return
        self.selecting = True
        scope.selected_incident = identifier
        return rx.redirect(f"/incidents/{quote(identifier, safe='')}")

    @rx.event(background=True)
    async def fetch_dashboard(self):
        async with self:
            if self._running or not self.busy:
                return
            self._running = True
            scope = await self.get_state(ScopeState)
            needs_catalog = not scope.tenants or not scope.platforms
            tenant, platform = scope.tenant_id, scope.platform_id
        try:
            if needs_catalog:
                catalog = await load_catalog()
                if not catalog.tenants or not catalog.platforms:
                    raise ServiceError("unauthorized")
                async with self:
                    scope = await self.get_state(ScopeState)
                    scope.tenants = catalog.tenants
                    scope.platforms = catalog.platforms
                    scope.tenant_id = scope.tenant_id or catalog.tenants[0].id
                    scope.platform_id = (
                        scope.platform_id or catalog.platforms[0].id
                    )
                    tenant, platform = scope.tenant_id, scope.platform_id
            result = await load_dashboard(tenant, platform)
            async with self:
                scope = await self.get_state(ScopeState)
                if (scope.tenant_id, scope.platform_id) == (tenant, platform):
                    if not result.demo:
                        scope.tenant_id, scope.platform_id = (
                            result.tenant_id,
                            result.platform_id,
                        )
                        scope.tenants = scope.tenants or result.tenants
                        scope.platforms = scope.platforms or result.platforms
                    self._loaded_scope = (result.tenant_id, result.platform_id)
                    self.metrics = result.metrics
                    self.incidents = result.incidents
                    self.pipelines = result.pipelines
                    self.updated_at = result.updated_at
                    self.window = result.window
                    self.summary = result.summary
                    self.demo = result.demo
                    self.loaded = True
        except Exception as error:
            kind = error.kind if isinstance(error, ServiceError) else "api"
            try:
                raise ServiceError(kind) from None
            except ServiceError as e:
                logging.exception(f"Error: {e}")
            async with self:
                self.error_kind = kind
        finally:
            async with self:
                self.page_loading = False
                self.dashboard_refreshing = False
                self.tenant_switching = False
                self.platform_switching = False
                self._running = False
