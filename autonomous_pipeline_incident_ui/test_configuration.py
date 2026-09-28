import reflex as rx
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from pydantic import ValidationError
from autonomous_pipeline_incident_ui.models import ConfigurationResponse
from autonomous_pipeline_incident_ui.service import get_tenant_config, save_configuration, ServiceError


class ConfigurationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        storage = patch.object(
            rx, "get_upload_dir", return_value=Path(directory.name)
        )
        storage.start()
        self.addCleanup(storage.stop)
        environment = patch.dict(
            os.environ,
            {
                "APP_ENV": "development",
                "OPS_PROVIDER": "mock",
                "OPS_DEMO_SCENARIO": "loaded",
            },
        )
        environment.start()
        self.addCleanup(environment.stop)

    async def test_scoped_defaults_and_isolated_idempotent_save(self):
        snapshots = []
        for tenant in ("tenant-a", "tenant-b"):
            for platform in ("synapse", "tibco"):
                config = await get_tenant_config(tenant, platform)
                self.assertEqual(
                    (config.tenant_id, config.platform_id), (tenant, platform)
                )
                snapshots.append(config)
        self.assertEqual(len({c.values.interval_seconds for c in snapshots}), 4)
        original = snapshots[0]
        edited = original.values.model_copy(deep=True)
        edited.monitoring_enabled = not edited.monitoring_enabled
        saved = await save_configuration(
            "tenant-a", "synapse", edited, "save-1", original.revision
        )
        repeated = await save_configuration(
            "tenant-a", "synapse", edited, "save-1", original.revision
        )
        self.assertTrue(saved.saved)
        self.assertEqual(saved, repeated)
        self.assertEqual(saved.revision, original.revision + 1)
        self.assertEqual(
            (await get_tenant_config("tenant-a", "synapse")).values, edited
        )
        self.assertEqual(
            (await get_tenant_config("tenant-b", "tibco")).values,
            snapshots[-1].values,
        )
        with self.assertRaises(ServiceError):
            await save_configuration(
                "tenant-a",
                "synapse",
                original.values,
                "save-1",
                original.revision,
            )
        with self.assertRaises(ServiceError):
            await save_configuration(
                "tenant-a",
                "synapse",
                original.values,
                "save-2",
                original.revision,
            )

    async def test_error_states_and_no_false_save_success(self):
        original = await get_tenant_config("tenant-a", "synapse")
        for kind in ("timeout", "unauthorized", "unavailable", "api", "empty"):
            with patch.dict(os.environ, {"OPS_DEMO_SCENARIO": kind}):
                with self.assertRaises(ServiceError) as failure:
                    await get_tenant_config("tenant-a", "synapse")
                self.assertEqual(failure.exception.kind, kind)
        for kind in (
            "validation",
            "save_failed",
            "timeout",
            "unauthorized",
            "unavailable",
        ):
            with patch.dict(os.environ, {"OPS_DEMO_SCENARIO": kind}):
                with self.assertRaises(ServiceError) as failure:
                    await save_configuration(
                        "tenant-a",
                        "synapse",
                        original.values,
                        kind,
                        original.revision,
                    )
                self.assertEqual(failure.exception.kind, kind)
        self.assertEqual(
            (await get_tenant_config("tenant-a", "synapse")).revision,
            original.revision,
        )

    async def test_scope_and_backend_policy_authority(self):
        response = await get_tenant_config("tenant-b", "tibco")
        with patch(
            "app.mock_provider.configuration",
            new=AsyncMock(return_value=response),
        ):
            with self.assertRaises(ServiceError):
                await get_tenant_config("tenant-a", "synapse")
        with self.assertRaises(ServiceError):
            await get_tenant_config("unrecognized", "synapse")
        response.values.remediation_policy = "client-granted-permission"
        with self.assertRaises(ServiceError):
            await save_configuration(
                "tenant-b",
                "tibco",
                response.values,
                "bad-policy",
                response.revision,
            )
        response.values.interval_seconds = 0
        with self.assertRaises(ServiceError):
            await save_configuration(
                "tenant-b",
                "tibco",
                response.values,
                "bad-rule",
                response.revision,
            )

    async def test_api_response_contract(self):
        confirmed = await get_tenant_config("tenant-a", "synapse")
        incomplete = confirmed.model_dump()
        incomplete["values"].pop("monitoring_enabled")
        with self.assertRaises(ValidationError):
            ConfigurationResponse.model_validate(incomplete)
        with patch.dict(os.environ, {"OPS_PROVIDER": "api"}):
            with patch(
                "app.service.config_json",
                new=AsyncMock(return_value=confirmed.model_dump()),
            ):
                result = await get_tenant_config("tenant-a", "synapse")
                self.assertFalse(result.demo)
                with self.assertRaises(ServiceError):
                    await save_configuration(
                        "tenant-a",
                        "synapse",
                        confirmed.values,
                        "not-confirmed",
                        confirmed.revision,
                    )
        with patch.dict(
            os.environ, {"APP_ENV": "production", "OPS_PROVIDER": "mock"}
        ):
            with self.assertRaises(ServiceError):
                await get_tenant_config("tenant-a", "synapse")

    def test_all_page_components_construct(self):
        from autonomous_pipeline_incident_ui.app import index, incidents, incident_details, configuration

        for page in (index, incidents, incident_details, configuration):
            self.assertIsInstance(page(), rx.Component)


if __name__ == "__main__":
    unittest.main()
