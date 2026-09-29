import reflex as rx
from autonomous_pipeline_incident_ui.models import ScopeOption


class ScopeState(rx.State):
    tenants: list[ScopeOption] = []
    platforms: list[ScopeOption] = []
    tenant_id: str = ""
    platform_id: str = ""
    selected_incident: str = ""

    @rx.var
    def tenant_label(self) -> str:
        return next(
            (item.label for item in self.tenants if item.id == self.tenant_id),
            "Select tenant",
        )

    @rx.var
    def platform_label(self) -> str:
        return next(
            (
                item.label
                for item in self.platforms
                if item.id == self.platform_id
            ),
            "Select platform",
        )

    async def _switch(self, value: str, dimension: str) -> bool:
        from autonomous_pipeline_incident_ui.states.dashboard_state import DashboardState
        from autonomous_pipeline_incident_ui.states.incident_state import IncidentState

        from autonomous_pipeline_incident_ui.states.detail_state import DetailState
        from autonomous_pipeline_incident_ui.states.config_state import ConfigState
        from autonomous_pipeline_incident_ui.states.pipeline_state import PipelineRunState

        dashboard = await self.get_state(DashboardState)
        incidents = await self.get_state(IncidentState)
        details = await self.get_state(DetailState)
        config = await self.get_state(ConfigState)
        pipeline = await self.get_state(PipelineRunState)
        options = self.tenants if dimension == "tenant" else self.platforms
        current = self.tenant_id if dimension == "tenant" else self.platform_id
        if (
            dashboard.busy
            or incidents.busy
            or details.busy
            or config.busy
            or pipeline.busy
            or value == current
            or value not in {item.id for item in options}
        ):
            return False
        if dimension == "tenant":
            self.tenant_id = value
        else:
            self.platform_id = value
        self.selected_incident = ""
        incidents._invalidate()
        details._invalidate()
        dashboard._begin("invalidate")
        config._invalidate()
        pipeline._invalidate()
        path = self.router.url.path.rstrip("/")
        if path == "/configuration":
            config._begin()
        elif path == "/incidents":
            incidents._begin("switch")
        elif not path.startswith("/incidents/"):
            dashboard._begin(dimension)
        return True

    @rx.event
    async def switch_tenant(self, value: str):
        if await self._switch(value, "tenant"):
            yield ScopeState.load_current_scope

    @rx.event
    async def switch_platform(self, value: str):
        if await self._switch(value, "platform"):
            yield ScopeState.load_current_scope

    @rx.event
    async def load_current_scope(self):
        from autonomous_pipeline_incident_ui.states.dashboard_state import DashboardState
        from autonomous_pipeline_incident_ui.states.incident_state import IncidentState
        from autonomous_pipeline_incident_ui.states.config_state import ConfigState

        path = self.router.url.path.rstrip("/")
        if path == "/configuration":
            return ConfigState.fetch_configuration
        elif path == "/incidents":
            return IncidentState.fetch_incidents
        elif path.startswith("/incidents/"):
            return rx.redirect("/incidents")
        else:
            return DashboardState.fetch_dashboard
