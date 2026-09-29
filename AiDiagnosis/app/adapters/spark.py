"""Spark adapter: the real, fully implemented adapter for this project."""
from __future__ import annotations

from app.adapters.base import FailurePattern, PipelineAdapter
from app.models.incident import Incident

_ALLOWED_ACTIONS: list[str] = [
    "retry_pipeline",
    "rerun_failed_stage",
    "increase_executor_memory",
    "increase_executor_cores",
    "increase_shuffle_partitions",
    "reduce_partition_size",
    "handle_data_skew",
    "fix_schema_mapping",
    "verify_source_connection",
    "verify_target_connection",
    "repair_input_path",
]

_FAILURE_PATTERNS: list[FailurePattern] = [
    FailurePattern(
        name="executor_out_of_memory",
        description="An executor ran out of heap space, typically during a wide "
        "transformation such as a join, groupBy, or aggregation.",
        indicators=["OutOfMemoryError", "Java heap space", "executor"],
    ),
    FailurePattern(
        name="driver_out_of_memory",
        description="The driver process ran out of memory, often from collecting "
        "too much data or broadcasting a large variable.",
        indicators=["driver", "OutOfMemoryError", "GC overhead limit exceeded"],
    ),
    FailurePattern(
        name="executor_lost",
        description="An executor was lost or killed, commonly due to memory "
        "pressure or node-level failures.",
        indicators=["ExecutorLostFailure", "executor lost", "killed"],
    ),
    FailurePattern(
        name="shuffle_fetch_failure",
        description="A shuffle block could not be fetched, usually because the "
        "producing executor died or the shuffle service is unreachable.",
        indicators=["FetchFailedException", "shuffle", "fetch failed"],
    ),
    FailurePattern(
        name="data_skew",
        description="A small number of partitions hold disproportionately more "
        "data, causing a handful of tasks to run far longer than the rest.",
        indicators=["skew", "long running task", "single task"],
    ),
    FailurePattern(
        name="excessive_shuffle",
        description="An unusually large volume of shuffle data is being read or "
        "written, increasing memory and I/O pressure.",
        indicators=["shuffle_read_mb", "shuffle_write_mb", "large shuffle"],
    ),
    FailurePattern(
        name="schema_mismatch",
        description="The data schema does not match what the pipeline expects.",
        indicators=["schema", "cannot resolve", "AnalysisException", "column"],
    ),
    FailurePattern(
        name="source_connection_failure",
        description="The pipeline could not connect to its source system.",
        indicators=["connection refused", "source", "timeout", "unreachable"],
    ),
    FailurePattern(
        name="target_connection_failure",
        description="The pipeline could not connect to its target/sink system.",
        indicators=["target", "sink", "write failed", "connection refused"],
    ),
    FailurePattern(
        name="permission_failure",
        description="The pipeline lacked permission to access a resource.",
        indicators=["AccessDenied", "permission", "403", "Forbidden"],
    ),
    FailurePattern(
        name="input_path_missing",
        description="An expected input path or file could not be found.",
        indicators=["Path does not exist", "FileNotFoundException", "no such file"],
    ),
]


class SparkAdapter(PipelineAdapter):
    """Adapter encapsulating Spark-specific diagnosis knowledge."""

    name = "spark"

    def normalize_incident(self, incident: Incident) -> Incident:
        normalized_logs = [line.strip() for line in incident.logs if line.strip()]
        return incident.model_copy(update={"logs": normalized_logs})

    def get_failure_patterns(self) -> list[FailurePattern]:
        return list(_FAILURE_PATTERNS)

    def get_allowed_remediation_actions(self) -> list[str]:
        return list(_ALLOWED_ACTIONS)

    def build_diagnosis_context(self, incident: Incident) -> str:
        patterns_text = "\n".join(
            f"- {p.name}: {p.description} (indicators: {', '.join(p.indicators)})"
            for p in self.get_failure_patterns()
        )
        details_text = "\n".join(f"- {k}: {v}" for k, v in incident.details.items())
        return (
            "Adapter: Spark\n"
            "Known Spark failure patterns:\n"
            f"{patterns_text}\n\n"
            "Incident execution details:\n"
            f"{details_text or '- (none provided)'}\n\n"
            "Allowed remediation actions for this adapter:\n"
            f"{', '.join(self.get_allowed_remediation_actions())}"
        )
