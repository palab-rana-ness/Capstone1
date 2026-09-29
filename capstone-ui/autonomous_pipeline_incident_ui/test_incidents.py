import reflex as rx
import asyncio
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
from autonomous_pipeline_incident_ui.service import get_incidents, ServiceError


class IncidentServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        storage = patch.object(
            rx, "get_upload_dir", return_value=Path(directory.name)
        )
        storage.start()
        self.addCleanup(storage.stop)

    async def test_all_authorized_scopes(self):
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "OPS_PROVIDER": "mock",
                "OPS_DEMO_SCENARIO": "loaded",
            },
        ):
            for tenant in ("tenant-a", "tenant-b"):
                for platform in ("synapse", "tibco"):
                    result = await get_incidents(tenant, platform)
                    self.assertEqual(len(result.incidents), 10)
                    self.assertEqual(
                        len({row.status for row in result.incidents}), 10
                    )
                    self.assertEqual(
                        {row.severity for row in result.incidents},
                        {"HIGH", "MEDIUM", "LOW", "CRITICAL"},
                    )
                    self.assertTrue(
                        all(
                            (row.tenant_id, row.platform_id)
                            == (tenant, platform)
                            for row in result.incidents
                        )
                    )
                    if tenant == "tenant-a" and platform == "synapse":
                        self.assertEqual(result.incidents[0].id, "INC-001")
                        self.assertEqual(
                            result.incidents[0].status, "AWAITING_APPROVAL"
                        )

    async def test_new_detection_and_empty(self):
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "OPS_PROVIDER": "mock",
                "OPS_DEMO_SCENARIO": "loaded",
            },
        ):
            before = await get_incidents("tenant-a", "synapse")
            after = await get_incidents("tenant-a", "synapse", True)
            new_ids = {row.id for row in after.incidents} - {
                row.id for row in before.incidents
            }
            self.assertEqual(len(new_ids), 1)
            self.assertEqual(after.incidents[-1].status, "DETECTED")
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "OPS_PROVIDER": "mock",
                "OPS_DEMO_SCENARIO": "empty",
            },
        ):
            self.assertEqual(
                (await get_incidents("tenant-b", "tibco")).incidents, []
            )

    async def test_failures_and_echo_validation(self):
        for kind in ("timeout", "unauthorized", "unavailable", "api"):
            with patch.dict(
                "os.environ",
                {
                    "APP_ENV": "development",
                    "OPS_PROVIDER": "mock",
                    "OPS_DEMO_SCENARIO": kind,
                },
            ):
                with self.assertRaises(ServiceError) as failure:
                    await get_incidents("tenant-a", "synapse")
                self.assertEqual(failure.exception.kind, kind)
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "OPS_PROVIDER": "mock",
                "OPS_DEMO_SCENARIO": "loaded",
            },
        ):
            response = await get_incidents("tenant-b", "tibco")
            with patch(
                "app.mock_provider.incidents",
                new=AsyncMock(return_value=response),
            ):
                with self.assertRaises(ServiceError):
                    await get_incidents("tenant-a", "synapse")
            response.tenant_id = "tenant-a"
            response.platform_id = "synapse"
            with patch(
                "app.mock_provider.incidents",
                new=AsyncMock(return_value=response),
            ):
                with self.assertRaises(ServiceError):
                    await get_incidents("tenant-a", "synapse")

    async def test_mock_disabled_outside_development(self):
        with patch.dict(
            "os.environ", {"APP_ENV": "production", "OPS_PROVIDER": "mock"}
        ):
            with self.assertRaises(ServiceError):
                await get_incidents("tenant-a", "synapse", True)
