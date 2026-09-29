import reflex as rx
import logging
import asyncio
from datetime import UTC
from uuid import uuid4
from autonomous_pipeline_incident_ui.models import (
    IncidentRecord,
    DetailSection,
    DetailResponse,
    ActionCapability,
    LogEntry,
    WorkflowResponse,
)
from autonomous_pipeline_incident_ui.service import (
    detail_operation,
    load_catalog,
    ServiceError,
    get_timeline,
    get_logs,
    start_analysis,
    polling_settings,
)
from autonomous_pipeline_incident_ui.states.scope_state import ScopeState


class DetailState(rx.State):
    records: list[IncidentRecord] = []
    analysis_reason: str = ""
    lifecycle_message: str = ""
    _polling: bool = False

    @rx.event
    def set_analysis_reason(self, value: str):
        if not self.busy and not self._polling:
            self.analysis_reason = value[:2000]

    log_entries: list[LogEntry] = []
    logs_loading: bool = False
    logs_refreshing: bool = False
    logs_loaded: bool = False
    logs_error_kind: str = ""

    @rx.var
    def logs_empty(self) -> bool:
        return self.logs_loaded and not self.log_entries

    @rx.var
    def logs_error_message(self) -> str:
        return {
            "request_invalid": "Logs request rejected. Review the current incident context.",
            "conflict": "Another log refresh is already running. Retry the read later.",
            "validation": "Log request validation failed. Reload the incident context.",
            "timeout": "Logs request timed out. Retry when ready.",
            "unauthorized": "Log access denied for this workspace.",
            "unavailable": "Log service unavailable. Retry when reachable.",
            "empty": "No logs found for this incident.",
            "api": "Invalid or unsuccessful logs response. No new logs were accepted.",
        }.get(self.logs_error_kind, "")

    sections: dict[str, DetailSection] = {
        "evidence": DetailSection(),
        "diagnosis": DetailSection(),
        "history": DetailSection(),
        "audit": DetailSection(),
        "remediation": DetailSection(),
        "execution": DetailSection(),
        "validation": DetailSection(),
    }
    section_status: dict[str, str] = {
        "facts": "",
        "evidence": "",
        "diagnosis": "",
        "history": "",
        "audit": "",
        "remediation": "",
        "execution": "",
        "validation": "",
    }
    errors: dict[str, str] = {
        "facts": "",
        "evidence": "",
        "diagnosis": "",
        "history": "",
        "audit": "",
        "remediation": "",
        "execution": "",
        "validation": "",
    }
    capabilities: list[ActionCapability] = []
    execution_policy: str = ""
    approval_required: bool = True
    confirmation: str = ""
    confirmation_label: str = ""
    confirmation_text: str = ""
    operation_locks: dict[str, bool] = {}
    demo: bool = False
    revision: int = 0
    _generation: int = 0
    _identifier: str = ""
    _scope: tuple[str, str] = ("", "")
    _running: list[str] = []

    @rx.var
    def detected_at_label(self) -> str:
        if not self.records:
            return "—"
        return (
            self.records[0]
            .detected_at.astimezone(UTC)
            .strftime("%d %b %Y, %H:%M:%S UTC")
        )

    @rx.var
    def busy(self) -> bool:
        return any(self.operation_locks.values())

    @rx.var
    def action_busy(self) -> bool:
        return self.busy or self._polling

    def _invalidate(self):
        self._polling = False
        self.analysis_reason = ""
        self.lifecycle_message = ""
        self.log_entries = []
        self.logs_loading = False
        self.logs_refreshing = False
        self.logs_loaded = False
        self.logs_error_kind = ""
        self._generation += 1
        self.records = []
        self.sections = {key: DetailSection() for key in self.sections}
        self.section_status = {key: "" for key in self.section_status}
        self.errors = {key: "" for key in self.errors}
        self.capabilities = []
        self.execution_policy = ""
        self.approval_required = True
        self.confirmation = ""
        self.confirmation_label = ""
        self.confirmation_text = ""
        self.operation_locks = {}
        self.demo = False
        self.revision = 0
        self._identifier = ""
        self._scope = ("", "")
        self._running = []

    def _accept(self, result: DetailResponse):
        if result.revision < self.revision:
            return
        if self.sections["validation"].recovery_confirmed:
            result.incident.recovery_confirmed = True
        self.records = [result.incident]
        self.revision = result.revision
        self.capabilities = result.capabilities
        self.execution_policy = result.execution_policy
        self.approval_required = result.approval_required
        self.demo = result.demo
        for name, section in result.sections.items():
            if name in self.sections and (
                result.demo or section != DetailSection()
            ):
                self.sections[name] = section

    def _accept_workflow(self, result: WorkflowResponse, section: str):
        self.sections[section] = result.section
        if result.capabilities_supplied:
            self.capabilities = result.capabilities
        if result.approval_supplied:
            self.approval_required = result.approval_required
        if section == "validation" and self.records:
            self.records[
                0
            ].recovery_confirmed = result.section.recovery_confirmed
            if result.section.outcome == "ESCALATED":
                self.records[0].status = "ESCALATED"
            elif (
                result.section.outcome == "RESOLVED"
                and result.section.recovery_confirmed
            ):
                self.records[0].status = "RESOLVED"

    async def _matches(
        self, generation: int, tenant: str, platform: str, identifier: str
    ) -> bool:
        scope = await self.get_state(ScopeState)
        return (
            generation == self._generation
            and identifier == self._identifier
            and identifier == self.incident_id
            and self.router.url.path.startswith("/incidents/")
            and (tenant, platform) == (scope.tenant_id, scope.platform_id)
        )

    def _error_message(self, kind: str) -> str:
        return {
            "configuration": "Configuration error · current user or polling settings are missing or invalid. No action success is assumed.",
            "request_invalid": "Request rejected · review the request before retrying.",
            "conflict": "Another action is already running. Refresh to reconcile.",
            "validation": "Validation rejected · reconcile the current backend state.",
            "timeout": "Timeout · outcome unknown. Refresh to reconcile before acting again.",
            "unauthorized": "Unauthorized · access denied for this workspace.",
            "empty": "No data available for this incident.",
            "unavailable": "Backend unavailable · retry when reachable.",
            "policy_rejected": "Policy rejected · refresh authorized actions.",
        }.get(
            kind,
            "Invalid or unsuccessful service response · no success is assumed.",
        )

    def _start(self, operation: str, section: str):
        if operation in {"analyze", "approve", "reject", "execute_retry"}:
            self.sections["validation"] = DetailSection()
            if self.records:
                self.records[0].recovery_confirmed = False
        self.operation_locks[operation] = True
        self.section_status[section] = (
            "Loading · waiting for a definitive service response…"
        )
        self.errors[section] = ""

    @rx.event
    async def page_load(self):
        scope = await self.get_state(ScopeState)
        identifier = self.incident_id
        if self.busy and self._identifier == identifier:
            return
        self._invalidate()
        self._identifier = identifier
        scope.selected_incident = ""
        self._start("get_incident", "facts")
        yield DetailState.fetch("get_incident", "facts", self._generation, "")

    @rx.event
    def refresh_section(self, section: str):
        operations = {
            "facts": "get_incident",
            "evidence": "get_incident_evidence",
            "diagnosis": "get_incident_diagnosis",
            "history": "get_historical_incidents",
            "audit": "get_audit_timeline",
            "remediation": "get_remediation",
            "execution": "get_execution_status",
            "validation": "get_validation_status",
        }
        if (
            self.busy
            or self._polling
            or self.confirmation
            or section not in operations
            or not self._identifier
        ):
            return
        operation = operations[section]
        self._start(operation, section)
        yield DetailState.fetch(operation, section, self._generation, "")

    @rx.event
    def choose_action(self, operation: str):
        if self.busy or self._polling or self.confirmation:
            return
        capability = next(
            (c for c in self.capabilities if c.operation == operation), None
        )
        if capability is None:
            return
        if capability.confirmation or operation in {
            "approve",
            "execute_retry",
            "reject",
        }:
            self.confirmation = operation
            self.confirmation_label = capability.label
            self.confirmation_text = (
                capability.confirmation
                or "Confirm this action on the selected incident?"
            )
            return
        self._start(operation, "remediation")
        self.lifecycle_message = (
            "Sending to Agent"
            if operation == "analyze"
            else "Submitting action…"
        )
        self.capabilities = []
        yield DetailState.fetch(
            operation, "remediation", self._generation, str(uuid4())
        )

    @rx.event
    def cancel_confirmation(self):
        if not self.busy:
            self.confirmation = ""
            self.confirmation_label = ""
            self.confirmation_text = ""

    @rx.event
    def confirm_action(self):
        if self.busy or self._polling or not self.confirmation:
            return
        operation = self.confirmation
        if operation not in {c.operation for c in self.capabilities}:
            self.confirmation = ""
            return
        self.confirmation = ""
        self._start(operation, "remediation")
        self.lifecycle_message = (
            "Sending to Agent"
            if operation == "analyze"
            else "Submitting action…"
        )
        self.capabilities = []
        yield DetailState.fetch(
            operation, "remediation", self._generation, str(uuid4())
        )

    @rx.event(background=True)
    async def fetch(
        self, operation: str, section: str, generation: int, request_id: str
    ):
        async with self:
            if (
                generation != self._generation
                or not self.operation_locks.get(operation)
                or operation in self._running
            ):
                return
            self._running.append(operation)
            scope = await self.get_state(ScopeState)
            tenant, platform = scope.tenant_id, scope.platform_id
            needs_catalog = not scope.tenants or not scope.platforms
            identifier, revision = self._identifier, self.revision
            reason = self.analysis_reason
            initial = operation == "get_incident" and not self.records
            followups = False
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
            if operation == "analyze":
                result = await start_analysis(
                    tenant, platform, identifier, reason, request_id, revision
                )
            elif operation == "get_audit_timeline":
                timeline = await get_timeline(tenant, platform, identifier)
                result = None
            else:
                result = await detail_operation(
                    operation,
                    tenant,
                    platform,
                    identifier,
                    request_id,
                    revision,
                )
            async with self:
                scope = await self.get_state(ScopeState)
                if (
                    generation != self._generation
                    or (tenant, platform)
                    != (scope.tenant_id, scope.platform_id)
                    or self.incident_id != identifier
                ):
                    return
                if isinstance(result, WorkflowResponse):
                    self._accept_workflow(result, section)
                elif result is not None:
                    if not result.demo:
                        scope.tenant_id, scope.platform_id = (
                            result.tenant_id,
                            result.platform_id,
                        )
                        scope.tenants = scope.tenants or result.tenants
                        scope.platforms = scope.platforms or result.platforms
                        tenant, platform = result.tenant_id, result.platform_id
                    previous_audit = self.sections["audit"]
                    self._accept(result)
                    if not result.demo:
                        self.sections["audit"] = previous_audit
                else:
                    self.sections["audit"] = timeline
                self._scope = (tenant, platform)
                scope.selected_incident = identifier
                if initial:
                    self.logs_loading = True
                    self.operation_locks["logs"] = True
                    followups = True
                self.section_status[section] = "Service response confirmed"
                if operation == "get_incident":
                    for name in self.sections:
                        self.section_status[name] = (
                            "Service response confirmed"
                            if result is not None and name in result.sections
                            else "No data reported"
                        )
                if request_id:
                    self.errors["remediation"] = ""
                    self.lifecycle_message = (
                        "Investigating · awaiting backend status"
                        if operation == "analyze"
                        else "Action acknowledged · awaiting backend status"
                    )
                    followups = True
        except Exception as error:
            kind = error.kind if isinstance(error, ServiceError) else "api"
            try:
                raise ServiceError(kind) from None
            except ServiceError as e:
                logging.exception(f"Error: {e}")
            async with self:
                scope = await self.get_state(ScopeState)
                if (
                    generation == self._generation
                    and self.incident_id == identifier
                    and (tenant, platform)
                    == (scope.tenant_id, scope.platform_id)
                ):
                    self.errors[section] = self._error_message(kind)
                    self.lifecycle_message = ""
                    self.section_status[section] = ""
                    if (
                        request_id
                        or kind == "unauthorized"
                        or section == "remediation"
                    ):
                        self.capabilities = []
                    if kind == "unauthorized":
                        self.records = []
                        self.sections = {
                            key: DetailSection() for key in self.sections
                        }
        finally:
            async with self:
                if generation == self._generation:
                    self.operation_locks[operation] = False
                    if operation in self._running:
                        self._running.remove(operation)
                reload_current = (
                    generation == self._generation
                    and self.incident_id != identifier
                    and self.router.url.path.startswith("/incidents/")
                )
            if reload_current:
                yield DetailState.page_load
            elif followups:
                if initial:
                    yield DetailState.fetch_logs(generation, False)
                yield DetailState.reconcile(generation, bool(request_id))

    @rx.event(background=True)
    async def reconcile(self, generation: int, force_poll: bool = False):
        async with self:
            if generation != self._generation or "reconcile" in self._running:
                return
            self._running.append("reconcile")
            self.operation_locks["reconcile"] = True
            tenant, platform = self._scope
            identifier = self._identifier
            demo = self.demo
            for name in ("diagnosis", "history", "remediation", "audit"):
                self.section_status[name] = "Loading…"
        try:
            operations = [
                ("diagnosis", "get_incident_diagnosis"),
                ("history", "get_historical_incidents"),
                ("remediation", "get_remediation"),
                ("audit", "get_audit_timeline"),
            ]
            if demo:
                operations = []
            for section, operation in operations:
                async with self:
                    if not await self._matches(
                        generation, tenant, platform, identifier
                    ):
                        return
                try:
                    response = await detail_operation(
                        operation, tenant, platform, identifier
                    )
                    async with self:
                        if not await self._matches(
                            generation, tenant, platform, identifier
                        ):
                            return
                        if isinstance(response, WorkflowResponse):
                            self._accept_workflow(response, section)
                        else:
                            self._accept(response)
                        self.section_status[section] = (
                            "Service response confirmed"
                        )
                        self.errors[section] = ""
                except Exception as error:
                    logging.exception("Unexpected error")
                    kind = (
                        error.kind if isinstance(error, ServiceError) else "api"
                    )
                    async with self:
                        if not await self._matches(
                            generation, tenant, platform, identifier
                        ):
                            return
                        self.errors[section] = self._error_message(kind)
                        self.section_status[section] = ""
                        if section != "audit":
                            self.sections[section] = DetailSection()
                        if section == "remediation":
                            self.capabilities = []
                        if kind == "unauthorized":
                            self._invalidate()
                            self.errors["facts"] = self._error_message(kind)
                            return
        finally:
            async with self:
                valid = generation == self._generation
                if valid:
                    self.operation_locks["reconcile"] = False
                    if "reconcile" in self._running:
                        self._running.remove("reconcile")
            if valid:
                yield DetailState.poll(generation, force_poll)

    @rx.event(background=True)
    async def poll(self, generation: int, force: bool = False):
        async with self:
            if (
                generation != self._generation
                or self._polling
                or not self.records
            ):
                return
            active = {
                "QUEUED",
                "ANALYSIS_QUEUED",
                "SENDING",
                "SENDING_TO_AGENT",
                "ANALYZING",
                "INVESTIGATING",
                "REMEDIATING",
                "EXECUTING",
                "VALIDATING",
            }
            status = self.records[0].status
            if (
                not force
                and status not in active
                and status not in {"RESOLVED", "ESCALATED"}
            ):
                return
            self._polling = True
            tenant, platform = self._scope
            identifier = self._identifier
        current_section = "facts"
        try:
            interval, attempts = polling_settings()
            for attempt in range(attempts):
                if attempt:
                    await asyncio.sleep(interval)
                async with self:
                    if not await self._matches(
                        generation, tenant, platform, identifier
                    ):
                        return
                    previous = self.records[0].status if self.records else ""
                current_section = "facts"
                response = await detail_operation(
                    "get_incident", tenant, platform, identifier
                )
                async with self:
                    if not await self._matches(
                        generation, tenant, platform, identifier
                    ):
                        return
                    self._accept(response)
                    status = response.incident.status
                    self.lifecycle_message = (
                        "Investigating"
                        if status in active
                        else "Backend status confirmed"
                    )
                if status in {
                    "REMEDIATING",
                    "EXECUTING",
                    "VALIDATING",
                    "RESOLVED",
                    "ESCALATED",
                }:
                    current_section = "execution"
                    execution = await detail_operation(
                        "get_execution_status", tenant, platform, identifier
                    )
                    async with self:
                        if not await self._matches(
                            generation, tenant, platform, identifier
                        ):
                            return
                        if isinstance(execution, WorkflowResponse):
                            self._accept_workflow(execution, "execution")
                        else:
                            self._accept(execution)
                        terminal = self.sections[
                            "execution"
                        ].progress.upper() in {
                            "SUCCEEDED",
                            "FAILED",
                            "COMPLETED",
                            "SUCCESS",
                            "CANCELLED",
                            "ESCALATED",
                        }
                        self.section_status["execution"] = (
                            "Service response confirmed"
                        )
                    if terminal or status in {
                        "VALIDATING",
                        "RESOLVED",
                        "ESCALATED",
                    }:
                        current_section = "validation"
                        validation = await detail_operation(
                            "get_validation_status",
                            tenant,
                            platform,
                            identifier,
                        )
                        async with self:
                            if not await self._matches(
                                generation, tenant, platform, identifier
                            ):
                                return
                            if isinstance(validation, WorkflowResponse):
                                self._accept_workflow(validation, "validation")
                            else:
                                self._accept(validation)
                            self.section_status["validation"] = (
                                "Service response confirmed"
                            )
                async with self:
                    if not await self._matches(
                        generation, tenant, platform, identifier
                    ):
                        return
                    status = self.records[0].status
                    changed = status != previous
                    stable = status in {
                        "DIAGNOSED",
                        "REMEDIATION_PROPOSED",
                        "AWAITING_APPROVAL",
                        "RESOLVED",
                        "REJECTED",
                        "ESCALATED",
                    }
                if changed or (stable and force):
                    for section, operation in (
                        ("diagnosis", "get_incident_diagnosis"),
                        ("history", "get_historical_incidents"),
                        ("remediation", "get_remediation"),
                        ("audit", "get_audit_timeline"),
                    ):
                        async with self:
                            if not await self._matches(
                                generation, tenant, platform, identifier
                            ):
                                return
                        try:
                            extra = await detail_operation(
                                operation, tenant, platform, identifier
                            )
                            async with self:
                                if not await self._matches(
                                    generation, tenant, platform, identifier
                                ):
                                    return
                                if isinstance(extra, WorkflowResponse):
                                    self._accept_workflow(extra, section)
                                else:
                                    self._accept(extra)
                                self.errors[section] = ""
                        except ServiceError as error:
                            logging.exception("Unexpected error")
                            async with self:
                                if not await self._matches(
                                    generation, tenant, platform, identifier
                                ):
                                    return
                                self.errors[section] = self._error_message(
                                    error.kind
                                )
                            if error.kind in {"unauthorized", "empty"}:
                                raise
                if stable:
                    async with self:
                        if generation == self._generation:
                            self.lifecycle_message = "Backend handoff confirmed · recovery requires explicit validation"
                    return
            async with self:
                if generation == self._generation:
                    self.lifecycle_message = "Polling limit reached · refresh to reconcile. No success is assumed."
        except Exception as error:
            logging.exception("Unexpected error")
            kind = error.kind if isinstance(error, ServiceError) else "api"
            async with self:
                if await self._matches(
                    generation, tenant, platform, identifier
                ):
                    self.errors[current_section] = self._error_message(kind)
                    self.lifecycle_message = (
                        "Polling stopped · refresh to reconcile"
                    )
                    self.capabilities = []
                    if kind in {"unauthorized", "empty"}:
                        self._invalidate()
                        self.errors["facts"] = self._error_message(kind)
        finally:
            async with self:
                if generation == self._generation:
                    self._polling = False

    @rx.event
    def refresh_logs(self):
        if (
            self.logs_loading
            or self.logs_refreshing
            or not self.records
            or self.confirmation
        ):
            return
        self.logs_refreshing = True
        self.logs_error_kind = ""
        self.operation_locks["logs"] = True
        yield DetailState.fetch_logs(self._generation, True)

    @rx.event(background=True)
    async def fetch_logs(self, generation: int, refresh: bool):
        async with self:
            if (
                generation != self._generation
                or not self.operation_locks.get("logs")
                or "logs" in self._running
            ):
                return
            self._running.append("logs")
            tenant, platform = self._scope
            identifier = self._identifier
        try:
            result = await get_logs(tenant, platform, identifier, refresh)
            async with self:
                scope = await self.get_state(ScopeState)
                if (
                    generation != self._generation
                    or identifier != self.incident_id
                    or (tenant, platform)
                    != (scope.tenant_id, scope.platform_id)
                ):
                    return
                self.log_entries = result.entries
                self.logs_loaded = True
                self.logs_error_kind = ""
        except Exception as error:
            kind = error.kind if isinstance(error, ServiceError) else "api"
            try:
                raise ServiceError(kind) from None
            except ServiceError as e:
                logging.exception(f"Error: {e}")
            async with self:
                scope = await self.get_state(ScopeState)
                if (
                    generation == self._generation
                    and identifier == self.incident_id
                    and (tenant, platform)
                    == (scope.tenant_id, scope.platform_id)
                ):
                    self.logs_error_kind = kind
                    if kind in {"unauthorized", "empty"}:
                        self.log_entries = []
                        self.logs_loaded = kind == "empty"
        finally:
            async with self:
                if generation == self._generation:
                    self.logs_loading = False
                    self.logs_refreshing = False
                    self.operation_locks["logs"] = False
                    if "logs" in self._running:
                        self._running.remove("logs")
