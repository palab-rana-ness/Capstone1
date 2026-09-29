import reflex as rx
import json
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
from faker import Faker
from autonomous_pipeline_incident_ui import service
from autonomous_pipeline_incident_ui.http_client import request_bytes, ServiceError, base_url
from autonomous_pipeline_incident_ui.api_mapping import (
    normalize_detail,
    normalize_timeline,
    normalize_logs,
    mapped,
)


class IncidentAPITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fake = Faker()
        self.row = {
            "incident_id": "INC /?#",
            "tenant_id": "tenant-a",
            "platform_id": "synapse",
            "pipeline_name": fake.bs(),
            "tenant_name": fake.company(),
            "severity": "HIGH",
            "status": "DETECTED",
            "created_at": "2026-01-01T00:00:00Z",
        }
        env = patch.dict(
            "os.environ",
            {
                "FASTAPI_BASE_URL": "https://example.test/",
                "APP_ENV": "development",
                "OPS_PROVIDER": "mock",
            },
        )
        env.start()
        self.addCleanup(env.stop)

    async def test_list_single_call_and_scope_discovery(self):
        for envelope in (
            [self.row],
            {"incidents": [self.row]},
            {"items": [self.row]},
            {"data": {"items": [self.row]}},
        ):
            with patch(
                "app.http_client.request_bytes",
                return_value=json.dumps(envelope).encode(),
            ) as transport:
                result = await service.get_incidents("", "")
                self.assertEqual(result.tenant_id, "tenant-a")
                self.assertEqual(
                    result.incidents[0].pipeline, self.row["pipeline_name"]
                )
                transport.assert_called_once_with(
                    "/api/v1/incidents",
                    {"tenant_id": "", "platform_id": ""},
                    "GET",
                )

    async def test_dashboard_single_list_call(self):
        with patch(
            "app.http_client.request_bytes",
            return_value=json.dumps([self.row]).encode(),
        ) as transport:
            result = await service.load_dashboard("tenant-a", "synapse")
            self.assertEqual(len(result.metrics), 7)
            self.assertEqual(result.metrics[0].value, "1")
            self.assertEqual(transport.call_count, 1)
            self.assertEqual(
                transport.call_args.args[0],
                "/api/v1/tenants/tenant-a/incidents",
            )

    async def test_detail_timeline_logs_paths(self):
        with patch(
            "app.http_client.request_bytes",
            return_value=json.dumps({"incident": self.row}).encode(),
        ) as transport:
            result = await service.get_incident(
                "tenant-a", "synapse", self.row["incident_id"]
            )
            self.assertEqual(result.sections["diagnosis"].entries, [])
            self.assertEqual(transport.call_count, 1)
            self.assertEqual(
                transport.call_args.args[0], "/api/v1/incidents/INC%20%2F%3F%23"
            )
        with patch(
            "app.http_client.request_bytes",
            return_value=b'{"timeline":[{"message":"Detected","timestamp":"2026-01-01"}]}',
        ) as transport:
            timeline = await service.get_timeline("tenant-a", "synapse", "one")
            self.assertEqual(timeline.entries[0].value, "Detected")
            self.assertEqual(
                transport.call_args.args[0], "/api/v1/incidents/one/timeline"
            )
        for refresh, suffix, method in [
            (False, "/logs", "GET"),
            (True, "/logs/refresh", "POST"),
        ]:
            with patch(
                "app.http_client.request_bytes",
                return_value=b'{"data":{"logs":[{"timestamp":"2026-01-01","level":"ERROR","source":"pipeline","message":"<script>text</script>","fields":{"retry":1}}]}}',
            ) as transport:
                logs = await service.get_logs(
                    "tenant-a", "synapse", "one", refresh
                )
                self.assertEqual(
                    json.loads(logs.entries[0].fields_json), {"retry": 1}
                )
                transport.assert_called_once_with(
                    f"/api/v1/incidents/one{suffix}",
                    {"tenant_id": "tenant-a", "platform_id": "synapse"},
                    method,
                    *([b"{}", ""] if refresh else []),
                )

    async def test_invalid_scope_required_fields_and_json(self):
        for changes in (
            {"tenant_id": "other"},
            {"platform_id": "other"},
            {"severity": "unknown"},
            {"status": "unknown"},
            {"incident_id": " "},
            {"created_at": "invalid"},
        ):
            with patch(
                "app.http_client.request_bytes",
                return_value=json.dumps([{**self.row, **changes}]).encode(),
            ):
                with self.assertRaises(ServiceError):
                    await service.get_incidents("tenant-a", "synapse")
        with patch("app.http_client.request_bytes", return_value=b"not json"):
            with self.assertRaises(ServiceError) as caught:
                await service.get_incidents("tenant-a", "synapse")
            self.assertEqual(caught.exception.kind, "api")
        with self.assertRaises(ServiceError):
            mapped(
                normalize_detail,
                self.row,
                "other",
                "synapse",
                self.row["incident_id"],
            )
        with self.assertRaises(ServiceError):
            mapped(
                normalize_logs,
                {"tenant_id": "other", "logs": []},
                "tenant-a",
                "synapse",
                "one",
            )

    def test_http_error_mapping_and_dynamic_settings(self):
        failures = [
            (HTTPError("private", 400, "private", {}, None), "request_invalid"),
            (HTTPError("private", 409, "private", {}, None), "conflict"),
            (HTTPError("private", 422, "private", {}, None), "validation"),
            (HTTPError("private", 500, "private", {}, None), "unavailable"),
            (HTTPError("private", 401, "private", {}, None), "unauthorized"),
            (HTTPError("private", 403, "private", {}, None), "unauthorized"),
            (HTTPError("private", 404, "private", {}, None), "empty"),
            (HTTPError("private", 503, "private", {}, None), "unavailable"),
            (TimeoutError(), "timeout"),
            (URLError("private"), "unavailable"),
        ]
        for error, kind in failures:
            opener = MagicMock()
            opener.open.side_effect = error
            with patch("app.http_client.build_opener", return_value=opener):
                with self.assertRaises(ServiceError) as caught:
                    request_bytes("/api/v1/incidents", {})
                self.assertEqual(caught.exception.kind, kind)
        self.assertEqual(base_url(), "https://example.test")
        with patch.dict("os.environ", {"FASTAPI_BASE_URL": "file:///tmp"}):
            with self.assertRaises(ServiceError):
                base_url()

    def test_immediate_log_and_section_guards(self):
        from autonomous_pipeline_incident_ui.states.detail_state import DetailState
        from autonomous_pipeline_incident_ui.api_mapping import APIIncident

        state = DetailState(_reflex_internal_init=True)
        state.records = [APIIncident.model_validate(self.row).record()]
        state._identifier = self.row["incident_id"]
        first = list(DetailState.refresh_logs.fn(state))
        second = list(DetailState.refresh_logs.fn(state))
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertTrue(state.operation_locks["logs"])
        self.assertEqual(
            list(DetailState.refresh_section.fn(state, "audit")), []
        )
