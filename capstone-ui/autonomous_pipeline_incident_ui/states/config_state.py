import reflex as rx
import logging
from uuid import uuid4
from autonomous_pipeline_incident_ui.models import (
    ConfigurationResponse,
    ConfigurationValues,
    ScopeOption,
    PlatformConfiguration,
    DetailEntry,
)
from autonomous_pipeline_incident_ui.service import (
    get_tenant_config,
    get_platform_config,
    save_configuration,
    load_catalog,
    ServiceError,
)
from autonomous_pipeline_incident_ui.states.scope_state import ScopeState


class ConfigState(rx.State):
    confirmed: list[ConfigurationResponse] = []
    platform_configuration: list[PlatformConfiguration] = []
    platform_entries: list[DetailEntry] = []
    platform_error: str = ""
    draft: ConfigurationValues = ConfigurationValues()
    loading: bool = False
    saving: bool = False
    error_kind: str = ""
    success: str = ""
    _generation: int = 0
    _running_generation: int = -1
    _request_id: str = ""
    _scope: tuple[str, str] = ("", "")

    @rx.var
    def busy(self) -> bool:
        return self.loading or self.saving

    @rx.var
    def dirty(self) -> bool:
        return bool(self.confirmed and self.draft != self.confirmed[0].values)

    @rx.var
    def editable(self) -> bool:
        return bool(
            self.confirmed and self.confirmed[0].can_edit and not self.busy
        )

    @rx.var
    def policies(self) -> list[ScopeOption]:
        return self.confirmed[0].policies if self.confirmed else []

    @rx.var
    def action_options(self) -> list[str]:
        return list(self.confirmed[0].action_options) if self.confirmed else []

    @rx.var
    def error_message(self) -> str:
        return {
            "request_invalid": "Request rejected. Review the configuration and reload before saving.",
            "conflict": "Another action is already running. Reload to reconcile before saving.",
            "timeout": "Request timed out. Save outcome may be unknown; reload confirmed values before making another change.",
            "unauthorized": "Access denied by the service. Select another workspace or contact your administrator.",
            "unavailable": "Configuration service unavailable. No save success is assumed. Reload to reconcile.",
            "empty": "No configuration exists for this workspace. Contact your administrator or select another workspace.",
            "validation": "The service rejected these values or the revision is out of date. Reload confirmed values and review your changes.",
            "save_failed": "Save was not confirmed. Your local edits are retained; reload to reconcile before trying again.",
            "api": "Invalid or unsuccessful service response. Reload to request a valid configuration.",
        }.get(self.error_kind, "")

    def _invalidate(self):
        self._generation += 1
        self.confirmed = []
        self.platform_configuration = []
        self.platform_entries = []
        self.platform_error = ""
        self.draft = ConfigurationValues()
        self.loading = False
        self.saving = False
        self.error_kind = ""
        self.success = ""
        self._scope = ("", "")
        self._request_id = ""

    def _begin(self):
        self._invalidate()
        self.loading = True

    def _accept(self, result: ConfigurationResponse):
        self.confirmed = [result]
        self.draft = result.values.model_copy(deep=True)
        self._scope = (result.tenant_id, result.platform_id)
        self.error_kind = ""

    @rx.event
    def page_load(self):
        if self.busy:
            return
        self._begin()
        yield ConfigState.fetch_configuration

    @rx.event
    def reset_edits(self):
        if not self.busy and self.confirmed:
            self.draft = self.confirmed[0].values.model_copy(deep=True)
            self.success = ""

    @rx.event
    def set_rule(self, field: str, value: str):
        if not self.editable:
            return
        bounds = {
            "interval_seconds": (15, 3600),
            "failure_threshold": (1, 100),
            "latency_seconds": (10, 3600),
        }
        if field not in bounds or not value.isdecimal():
            return
        number = int(value)
        low, high = bounds[field]
        if low <= number <= high:
            setattr(self.draft, field, number)
            self.success = ""

    @rx.event
    def toggle_monitoring(self):
        if self.editable:
            self.draft.monitoring_enabled = not self.draft.monitoring_enabled
            self.success = ""

    @rx.event
    def set_policy(self, value: str):
        if self.editable and value in {p.id for p in self.policies}:
            self.draft.remediation_policy = value
            self.success = ""

    @rx.event
    def toggle_action(self, value: str):
        if not self.editable or value not in self.action_options:
            return
        actions = list(self.draft.allowed_actions)
        if value in actions:
            actions.remove(value)
        else:
            actions.append(value)
        self.draft.allowed_actions = sorted(actions)
        self.success = ""

    @rx.event
    async def save(self):
        if not self.editable or not self.dirty or self.error_kind:
            return
        scope = await self.get_state(ScopeState)
        if self._scope != (scope.tenant_id, scope.platform_id):
            self._invalidate()
            return
        self.saving = True
        self.success = ""
        self._request_id = str(uuid4())
        yield ConfigState.fetch_configuration

    @rx.event(background=True)
    async def fetch_configuration(self):
        async with self:
            generation = self._generation
            if not self.busy or self._running_generation == generation:
                return
            self._running_generation = generation
            scope = await self.get_state(ScopeState)
            tenant, platform = scope.tenant_id, scope.platform_id
            needs_catalog = not scope.tenants or not scope.platforms
            saving = self.saving
            values = self.draft.model_copy(deep=True)
            revision = self.confirmed[0].revision if self.confirmed else 0
            request_id = self._request_id
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
                    scope.tenant_id = scope.tenant_id or catalog.tenants[0].id
                    scope.platform_id = (
                        scope.platform_id or catalog.platforms[0].id
                    )
                    tenant, platform = scope.tenant_id, scope.platform_id
            if saving:
                result = await save_configuration(
                    tenant, platform, values, request_id, revision
                )
            else:
                result = await get_tenant_config(tenant, platform)
                try:
                    platform_result = await get_platform_config(
                        tenant, platform
                    )
                    async with self:
                        if generation != self._generation:
                            return
                        self.platform_configuration = [platform_result]
                        self.platform_entries = platform_result.entries
                        self.platform_error = ""
                except ServiceError as error:
                    logging.exception("Unexpected error")
                    if error.kind == "unauthorized":
                        raise
                    async with self:
                        if generation != self._generation:
                            return
                        self.platform_configuration = []
                        self.platform_entries = []
                        self.platform_error = f"Platform configuration: {error.kind}. Reload to retry."
            async with self:
                scope = await self.get_state(ScopeState)
                if generation != self._generation or (tenant, platform) != (
                    scope.tenant_id,
                    scope.platform_id,
                ):
                    return
                self._accept(result)
                self.success = (
                    "Configuration saved · confirmed by service."
                    if saving
                    else ""
                )
        except Exception as error:
            kind = error.kind if isinstance(error, ServiceError) else "api"
            try:
                raise ServiceError(kind) from None
            except ServiceError as e:
                logging.exception(f"Error: {e}")
            async with self:
                if generation == self._generation:
                    if kind == "unauthorized":
                        self.platform_configuration = []
                        self.platform_entries = []
                        self.platform_error = ""
                        self.confirmed = []
                        self.draft = ConfigurationValues()
                        self._scope = ("", "")
                    self.error_kind = kind
                    self.success = ""
        finally:
            async with self:
                if generation == self._generation:
                    self.loading = False
                    self.saving = False
                    self._running_generation = -1
