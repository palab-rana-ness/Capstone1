import reflex as rx
import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from autonomous_pipeline_incident_ui.service import (
    detail_operation,
    get_incident,
    get_incidents,
    ServiceError,
)


class IncidentDetailTests(unittest.IsolatedAsyncioTestCase):
    async def test_recovery_and_persistent_audit(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(rx, "get_upload_dir", return_value=Path(directory)),
            patch.dict(
                os.environ,
                {
                    "APP_ENV": "development",
                    "OPS_PROVIDER": "mock",
                    "OPS_DEMO_SCENARIO": "loaded",
                },
            ),
        ):
            initial = await get_incident("tenant-a", "synapse", "INC-001")
            self.assertEqual(initial.incident.status, "AWAITING_APPROVAL")
            self.assertNotIn(
                "execute_retry", [c.operation for c in initial.capabilities]
            )
            with self.assertRaises(ServiceError):
                await detail_operation(
                    "execute_retry",
                    "tenant-a",
                    "synapse",
                    "INC-001",
                    "bypass",
                    initial.revision,
                )
            started = await detail_operation(
                "approve",
                "tenant-a",
                "synapse",
                "INC-001",
                "approve-1",
                initial.revision,
            )
            self.assertEqual(started.incident.status, "REMEDIATING")
            duplicate = await detail_operation(
                "approve",
                "tenant-a",
                "synapse",
                "INC-001",
                "approve-1",
                initial.revision,
            )
            self.assertEqual(
                len(duplicate.sections["audit"].entries),
                len(started.sections["audit"].entries),
            )
            early = await detail_operation(
                "get_validation_status", "tenant-a", "synapse", "INC-001"
            )
            self.assertNotEqual(
                early.sections["validation"].outcome, "RESOLVED"
            )
            executed = await detail_operation(
                "get_execution_status", "tenant-a", "synapse", "INC-001"
            )
            self.assertEqual(executed.incident.status, "VALIDATING")
            self.assertEqual(
                executed.sections["execution"].progress, "Succeeded"
            )
            resolved = await detail_operation(
                "get_validation_status", "tenant-a", "synapse", "INC-001"
            )
            self.assertEqual(resolved.incident.status, "RESOLVED")
            reloaded = await get_incident("tenant-a", "synapse", "INC-001")
            self.assertEqual(
                reloaded.sections["audit"], resolved.sections["audit"]
            )
            self.assertGreater(
                len(resolved.sections["audit"].entries),
                len(initial.sections["audit"].entries),
            )
            with self.assertRaises(ServiceError):
                await get_incident("tenant-b", "synapse", "INC-001")

    async def test_failed_retry_and_tibco(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(rx, "get_upload_dir", return_value=Path(directory)),
            patch.dict(
                os.environ,
                {
                    "APP_ENV": "development",
                    "OPS_PROVIDER": "mock",
                    "OPS_DEMO_SCENARIO": "failed_retry",
                },
            ),
        ):
            for tenant, platform in [
                ("tenant-a", "synapse"),
                ("tenant-b", "tibco"),
            ]:
                rows = await get_incidents(tenant, platform)
                identifier = rows.incidents[0].id
                initial = await get_incident(tenant, platform, identifier)
                await detail_operation(
                    "approve",
                    tenant,
                    platform,
                    identifier,
                    "start",
                    initial.revision,
                )
                failed = await detail_operation(
                    "get_execution_status", tenant, platform, identifier
                )
                self.assertEqual(failed.incident.status, "ESCALATED")
                self.assertEqual(
                    failed.sections["execution"].progress, "Failed"
                )
                validation = await detail_operation(
                    "get_validation_status", tenant, platform, identifier
                )
                self.assertEqual(
                    validation.sections["validation"].outcome, "ESCALATED"
                )
                self.assertNotEqual(
                    validation.sections["validation"].progress, "Confirmed"
                )
                self.assertTrue(validation.sections["audit"].entries)
                self.assertFalse(validation.capabilities)

    async def test_production_never_uses_mock(self):
        with patch.dict(
            os.environ, {"APP_ENV": "production", "OPS_PROVIDER": "mock"}
        ):
            with self.assertRaises(ServiceError):
                await get_incident("tenant-a", "synapse", "INC-001")


if __name__ == "__main__":
    unittest.main()
