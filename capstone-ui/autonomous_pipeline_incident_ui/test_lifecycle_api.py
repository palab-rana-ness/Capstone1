import reflex as rx
import json
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from faker import Faker
from autonomous_pipeline_incident_ui import service
from autonomous_pipeline_incident_ui.api_mapping import (
    mapped,
    normalize_workflow,
    normalize_timeline,
    normalize_list,
    APIIncident,
)
from autonomous_pipeline_incident_ui.http_client import ServiceError, incident_path, request_bytes
from autonomous_pipeline_incident_ui.models import ScopeOption, ActionCapability, DetailSection
from autonomous_pipeline_incident_ui.states.detail_state import DetailState


class LifecycleAPITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        environment = patch.dict(
            "os.environ",
            {
                "FASTAPI_BASE_URL": "https://example.test",
                "SENTINEL_CURRENT_USER": "test-operator",
            },
        )
        environment.start()
        self.addCleanup(environment.stop)
        fake = Faker()
        self.row = {
            "incident_id": "incident/one",
            "tenant_id": "tenant-a",
            "platform_id": "platform-a",
            "pipeline_name": fake.bs(),
            "severity": "HIGH",
            "status": "DETECTED",
            "detected_at": "2026-01-01T00:00:00Z",
        }

    async def test_analysis_body_identity_and_single_post(self):
        with patch(
            "app.http_client.request_bytes",
            return_value=b'{"data":{"status":"ANALYSIS_QUEUED","accepted":true}}',
        ) as transport:
            result = await service.start_analysis(
                "tenant-a",
                "platform-a",
                "incident/one",
                "Investigate lag",
                "key-1",
            )
            transport.assert_called_once()
            path, context, method, body, key = transport.call_args.args
            self.assertEqual(path, "/api/v1/incidents/incident%2Fone/analyze")
            self.assertEqual(method, "POST")
            self.assertEqual(
                json.loads(body),
                {"requested_by": "test-operator", "reason": "Investigate lag"},
            )
            self.assertEqual(key, "key-1")
            self.assertEqual(result.status, "ANALYSIS_QUEUED")
        with (
            patch.dict("os.environ", {"SENTINEL_CURRENT_USER": ""}),
            patch("app.http_client.request_bytes") as transport,
        ):
            with self.assertRaises(ServiceError) as error:
                await service.start_analysis(
                    "tenant-a", "platform-a", "incident/one"
                )
            self.assertEqual(error.exception.kind, "configuration")
            transport.assert_not_called()

    async def test_actions_and_read_routes_once(self):
        operations = {
            "approve": ("approve", "POST"),
            "reject": ("reject", "POST"),
            "execute_retry": ("retry", "POST"),
            "get_incident_diagnosis": ("diagnosis", "GET"),
            "get_historical_incidents": ("history", "GET"),
            "get_remediation": ("remediation", "GET"),
            "get_execution_status": ("execution", "GET"),
            "get_validation_status": ("validation", "GET"),
        }
        for operation, (suffix, method) in operations.items():
            with (
                self.subTest(operation=operation),
                patch(
                    "app.http_client.request_bytes",
                    return_value=b'{"status":"INVESTIGATING","accepted":true}',
                ) as transport,
            ):
                await service.detail_operation(
                    operation,
                    "tenant-a",
                    "platform-a",
                    "incident/one",
                    "key" if method == "POST" else "",
                )
                transport.assert_called_once()
                self.assertEqual(
                    transport.call_args.args[0],
                    f"/api/v1/incidents/incident%2Fone/{suffix}",
                )
                self.assertEqual(transport.call_args.args[2], method)
                if method == "POST":
                    self.assertEqual(transport.call_args.args[4], "key")
        with patch("app.http_client.request_bytes") as transport:
            with self.assertRaises(ServiceError):
                await service.request_approval(
                    "tenant-a", "platform-a", "one", "key", 0
                )
            transport.assert_not_called()

    async def test_catalog_and_tenant_routes(self):
        with patch(
            "app.http_client.request_bytes",
            side_effect=[
                b'{"tenants":[{"tenant_id":"tenant-a","name":"Workspace"}]}',
                b'{"data":{"platforms":[{"platform_id":"platform-a","name":"Platform"}]}}',
            ],
        ) as transport:
            catalog = await service.load_catalog()
            self.assertEqual(len(catalog.tenants), 1)
            self.assertEqual(
                {call.args[0] for call in transport.call_args_list},
                {"/api/v1/tenants", "/api/v1/platforms"},
            )
            self.assertEqual(transport.call_count, 2)
        with patch(
            "app.http_client.request_bytes",
            return_value=json.dumps([self.row]).encode(),
        ) as transport:
            await service.get_tenant_incidents("tenant-a", "platform-a")
            transport.assert_called_once_with(
                "/api/v1/tenants/tenant-a/incidents",
                {"tenant_id": "tenant-a", "platform_id": "platform-a"},
                "GET",
            )

    async def test_configuration_methods_and_echoes(self):
        config = {
            "tenant_id": "tenant-a",
            "platform_id": "platform-a",
            "values": {
                "monitoring_enabled": True,
                "interval_seconds": 60,
                "failure_threshold": 3,
                "latency_seconds": 120,
                "remediation_policy": "manual",
                "allowed_actions": ["Retry"],
            },
            "revision": 1,
            "updated_at": "2026-01-01",
            "can_edit": True,
            "policies": [{"id": "manual", "label": "Manual"}],
            "action_options": ["Retry"],
        }
        with patch(
            "app.http_client.request_bytes",
            return_value=json.dumps({"data": config}).encode(),
        ) as transport:
            result = await service.get_tenant_config("tenant-a", "platform-a")
            transport.assert_called_once()
            self.assertEqual(
                transport.call_args.args[0], "/api/v1/tenants/tenant-a/config"
            )
        saved = {
            **config,
            "revision": 2,
            "saved": True,
            "request_id": "save-key",
        }
        with patch(
            "app.http_client.request_bytes",
            return_value=json.dumps(saved).encode(),
        ) as transport:
            await service.save_configuration(
                "tenant-a", "platform-a", result.values, "save-key", 1
            )
            transport.assert_called_once()
            self.assertEqual(transport.call_args.args[2], "PUT")
            self.assertEqual(transport.call_args.args[4], "save-key")
        with patch(
            "app.http_client.request_bytes",
            return_value=b'{"platform_id":"platform-a","enabled":true}',
        ) as transport:
            await service.get_platform_config("tenant-a", "platform-a")
            self.assertEqual(
                transport.call_args.args[0],
                "/api/v1/platforms/platform-a/config",
            )
            transport.assert_called_once()
        with patch(
            "app.http_client.request_bytes",
            return_value=b'{"platform_id":"other","enabled":true}',
        ):
            with self.assertRaises(ServiceError):
                await service.get_platform_config("tenant-a", "platform-a")

    def test_chronology_and_malformed_scope(self):
        section = normalize_timeline(
            {
                "events": [
                    {"message": "later", "timestamp": "2026-01-01T10:00:00Z"},
                    {
                        "message": "earlier",
                        "timestamp": "2026-01-01T11:00:00+02:00",
                    },
                    {"message": "unknown", "timestamp": "bad"},
                    {"message": "unknown2"},
                ]
            },
            "tenant-a",
            "platform-a",
            "one",
        )
        self.assertEqual(
            [entry.value for entry in section.entries],
            ["earlier", "later", "unknown", "unknown2"],
        )
        for payload in (
            {},
            {"data": {"tenant_id": "other", "available": True}},
            {"available": "true"},
        ):
            with self.assertRaises(ServiceError):
                mapped(
                    normalize_workflow,
                    payload,
                    "tenant-a",
                    "platform-a",
                    "one",
                    "diagnosis",
                )
        with self.assertRaises(ServiceError):
            mapped(
                normalize_list,
                [{**self.row, "tenant_id": "other"}],
                "tenant-a",
                "platform-a",
            )
        for identifier in (".", ".."):
            with self.assertRaises(ServiceError):
                incident_path(identifier)

    def test_recovery_diagnosis_and_capabilities(self):
        diagnosis = normalize_workflow(
            {"status": "INVESTIGATING"}, "", "", "", "diagnosis"
        )
        self.assertFalse(diagnosis.section.available)
        self.assertFalse(diagnosis.section.confidence_supplied)
        validation = normalize_workflow(
            {"status": "RESOLVED", "recovery_confirmed": False},
            "",
            "",
            "",
            "validation",
        )
        self.assertNotEqual(validation.section.outcome, "RESOLVED")
        state = DetailState(_reflex_internal_init=True)
        state.records = [APIIncident.model_validate(self.row).record()]
        state._accept_workflow(validation, "validation")
        self.assertNotEqual(state.records[0].status, "RESOLVED")
        confirmed = normalize_workflow(
            {"status": "RESOLVED", "recovery_confirmed": True},
            "",
            "",
            "",
            "validation",
        )
        state._accept_workflow(confirmed, "validation")
        self.assertEqual(state.records[0].status, "RESOLVED")
        failed = normalize_workflow(
            {"status": "ESCALATED", "recovery_confirmed": False},
            "",
            "",
            "",
            "validation",
        )
        state._accept_workflow(failed, "validation")
        self.assertEqual(state.records[0].status, "ESCALATED")
        remediation = normalize_workflow(
            {"action": "Retry", "approval_required": True},
            "",
            "",
            "",
            "remediation",
        )
        self.assertEqual(remediation.capabilities, [])
        permitted = normalize_workflow(
            {"can_retry": True}, "", "", "", "remediation"
        )
        self.assertEqual(permitted.capabilities[0].operation, "execute_retry")

    async def test_action_and_poll_duplicate_guards(self):
        state = DetailState(_reflex_internal_init=True)
        state.capabilities = [
            ActionCapability(operation="analyze", label="Send to Agent")
        ]
        self.assertEqual(
            len(list(DetailState.choose_action.fn(state, "analyze"))), 1
        )
        self.assertEqual(
            list(DetailState.choose_action.fn(state, "analyze")), []
        )
        self.assertEqual(state.lifecycle_message, "Sending to Agent")
        proxy = MagicMock()
        proxy._generation = 2
        proxy._polling = True
        proxy.__aenter__ = AsyncMock(return_value=proxy)
        proxy.__aexit__ = AsyncMock(return_value=False)
        with patch(
            "app.states.detail_state.detail_operation", new_callable=AsyncMock
        ) as operation:
            self.assertIsNone(await DetailState.poll.fn(proxy, 2))
            operation.assert_not_called()
        state._polling = True
        state.sections["audit"] = DetailSection(summary="Old workspace")
        state._invalidate()
        self.assertFalse(state._polling)
        self.assertEqual(state.sections["audit"].summary, "")
        self.assertEqual(state.records, [])
        self.assertEqual(state.log_entries, [])

    async def test_scope_switch_clears_all_workspaces(self):
        from autonomous_pipeline_incident_ui.states.scope_state import ScopeState
        from autonomous_pipeline_incident_ui.states.dashboard_state import DashboardState
        from autonomous_pipeline_incident_ui.states.incident_state import IncidentState
        from autonomous_pipeline_incident_ui.states.config_state import ConfigState

        scope = ScopeState(_reflex_internal_init=True)
        scope.tenants = [
            ScopeOption(id="tenant-a", label="A"),
            ScopeOption(id="tenant-b", label="B"),
        ]
        scope.tenant_id = "tenant-a"
        scope.platform_id = "platform-a"
        states = {
            cls: cls(_reflex_internal_init=True)
            for cls in (DashboardState, IncidentState, DetailState, ConfigState)
        }
        states[IncidentState].raw_incidents = [
            APIIncident.model_validate(self.row).record()
        ]
        states[DetailState].records = [
            APIIncident.model_validate(self.row).record()
        ]
        states[DetailState]._polling = True
        with patch.object(
            ScopeState,
            "get_state",
            new=AsyncMock(side_effect=lambda cls: states[cls]),
        ):
            self.assertTrue(await scope._switch("tenant-b", "tenant"))
        self.assertEqual(states[IncidentState].raw_incidents, [])
        self.assertEqual(states[DetailState].records, [])
        self.assertFalse(states[DetailState]._polling)
        self.assertEqual(states[DashboardState].incidents, [])
        self.assertEqual(states[ConfigState].confirmed, [])

    def test_transport_headers(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"{}"
        opener = MagicMock()
        opener.open.return_value = response
        with patch("app.http_client.build_opener", return_value=opener):
            request_bytes(
                "/api/v1/incidents/one/approve", {}, "POST", b"{}", "key"
            )
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header("Idempotency-key"), "key")
        self.assertEqual(request.data, b"{}")
