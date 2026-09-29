import unittest
from unittest.mock import patch

from autonomous_pipeline_incident_ui.api_mapping import (
    normalize_pipeline_run_start,
    normalize_pipeline_run_result,
    normalize_pipeline_diagnosis,
)
from autonomous_pipeline_incident_ui.http_client import ServiceError
from autonomous_pipeline_incident_ui.service import (
    start_pipeline_run,
    get_pipeline_run_result,
    diagnose_pipeline_run,
)


class PipelineRunFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        environment = patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "OPS_PROVIDER": "mock",
            },
        )
        environment.start()
        self.addCleanup(environment.stop)

    def test_pipeline_mapping_contracts(self):
        started = normalize_pipeline_run_start(
            {
                "data": {
                    "run_id": "run-1",
                    "status": "QUEUED",
                    "tenant_id": "tenant-a",
                    "platform_id": "synapse",
                    "pipeline_type": "Orders Pipeline",
                }
            },
            "tenant-a",
            "synapse",
            "Orders Pipeline",
        )
        self.assertEqual(started.run_id, "run-1")
        passed = normalize_pipeline_run_result(
            {"data": {"run_id": "run-1", "outcome": "SUCCESS"}},
            "tenant-a",
            "synapse",
            "run-1",
        )
        self.assertEqual(passed.outcome, "PASSED")
        diagnosis = normalize_pipeline_diagnosis(
            {
                "data": {
                    "run_id": "run-1",
                    "root_cause": "Downstream timeout",
                    "details": {"retryable": True},
                }
            },
            "tenant-a",
            "synapse",
            "run-1",
        )
        self.assertIn("Downstream timeout", diagnosis.diagnosis)

    async def test_failed_pipeline_then_diagnose(self):
        started = await start_pipeline_run(
            "tenant-a", "synapse", "Failing Pipeline"
        )
        result = await get_pipeline_run_result(
            "tenant-a", "synapse", started.run_id
        )
        self.assertEqual(result.outcome, "FAILED")
        diagnosis = await diagnose_pipeline_run(
            "tenant-a", "synapse", started.run_id, "Failing Pipeline"
        )
        self.assertTrue(bool(diagnosis.diagnosis))

    async def test_passed_pipeline_blocks_diagnose(self):
        started = await start_pipeline_run(
            "tenant-a", "synapse", "Orders Pipeline"
        )
        result = await get_pipeline_run_result(
            "tenant-a", "synapse", started.run_id
        )
        self.assertEqual(result.outcome, "PASSED")
        with self.assertRaises(ServiceError) as failure:
            await diagnose_pipeline_run(
                "tenant-a", "synapse", started.run_id, "Orders Pipeline"
            )
        self.assertEqual(failure.exception.kind, "request_invalid")


if __name__ == "__main__":
    unittest.main()
