import reflex as rx
import asyncio
import os
from datetime import datetime, timezone, timedelta
from faker import Faker
from autonomous_pipeline_incident_ui.models import (
    Catalog,
    DashboardResponse,
    Incident,
    IncidentRecord,
    IncidentsResponse,
    Metric,
    Pipeline,
    ScopeOption,
)


def _detail_capabilities(status: str, approval: bool):
    from autonomous_pipeline_incident_ui.models import ActionCapability

    if status == "DETECTED":
        return [ActionCapability(operation="analyze", label="Send to Agent")]
    if status == "AWAITING_APPROVAL":
        return [
            ActionCapability(
                operation="approve",
                label="Approve & Execute",
                confirmation="Approve this recommendation and execute one retry?",
            ),
            ActionCapability(
                operation="reject",
                label="Reject",
                confirmation="Reject this remediation recommendation? No retry will run.",
            ),
        ]
    if status in {"DIAGNOSED", "REMEDIATION_PROPOSED"}:
        if approval:
            return [
                ActionCapability(
                    operation="request_approval", label="Request Approval"
                )
            ]
        return [
            ActionCapability(
                operation="execute_retry",
                label="Execute Retry",
                confirmation="Execute one backend-authorized retry?",
            )
        ]
    return []


def _seed_detail(record: IncidentRecord):
    from autonomous_pipeline_incident_ui.models import DetailResponse, DetailSection, DetailEntry

    fake = Faker()
    fake.seed_instance(record.id)
    stamp = record.detected_at.isoformat()
    approval = record.status != "DIAGNOSED"
    sections = {
        "evidence": DetailSection(
            progress="Complete",
            summary="Pipeline degraded · downstream connection timed out",
            entries=[
                DetailEntry(label="Pipeline status", value="Failed"),
                DetailEntry(label="Failure rate", value="33.3% / last 3 runs"),
                DetailEntry(label="Latency", value="120 seconds"),
                DetailEntry(
                    label="Recent run",
                    value="Failed · connection timeout",
                    timestamp=stamp,
                ),
                DetailEntry(
                    label="Previous runs",
                    value="2 succeeded / 1 failed",
                    timestamp=stamp,
                ),
            ],
            logs=[
                f"{stamp} ERROR Connection timeout after 120 seconds",
                f"{stamp} WARN Pipeline halted; checkpoint retained",
            ],
        ),
        "diagnosis": DetailSection(
            progress="Complete",
            summary="Probable root cause: transient downstream connection timeout",
            confidence=94.0,
            available=True,
            confidence_supplied=True,
            severity=record.severity,
            entries=[
                DetailEntry(
                    label="Supporting evidence",
                    value="Timeout signature and retained checkpoint; no schema changes detected.",
                )
            ],
        ),
        "history": DetailSection(
            progress="Complete",
            summary="Historical search completed",
            entries=[
                DetailEntry(
                    label=f"HIST-{fake.random_int(min=100, max=999)} · 92.0% similarity",
                    value="Matching timeout signature · recovered after a single retry",
                    timestamp=(
                        record.detected_at - timedelta(days=3)
                    ).isoformat(),
                )
            ],
        ),
        "audit": DetailSection(
            progress="Current",
            entries=[
                DetailEntry(
                    label="Detection service",
                    value="Incident detected from failed pipeline run",
                    timestamp=stamp,
                ),
                DetailEntry(
                    label="Diagnosis service",
                    value="Diagnosis and historical search completed",
                    timestamp=stamp,
                ),
                DetailEntry(
                    label="Policy service",
                    value=f"Initial state: {record.status}",
                    timestamp=stamp,
                ),
            ],
        ),
        "remediation": DetailSection(
            progress="Recommendation ready",
            summary="Retry pipeline from retained checkpoint",
            entries=[
                DetailEntry(label="Action", value="Retry pipeline once"),
                DetailEntry(
                    label="Reason",
                    value="Transient failure; checkpoint permits safe recovery",
                ),
                DetailEntry(
                    label="Risk", value="Low · idempotent checkpoint replay"
                ),
                DetailEntry(
                    label="Execution policy",
                    value="Human approval required"
                    if approval
                    else "Backend-authorized manual retry",
                ),
            ],
        ),
        "execution": DetailSection(
            progress="Not started", summary="No execution result reported"
        ),
        "validation": DetailSection(
            progress="Not started", summary="Recovery has not been confirmed"
        ),
    }
    if record.status == "REMEDIATING":
        sections["execution"].progress = "Running"
    if record.status == "VALIDATING":
        sections["execution"].progress = "Succeeded"
        sections["validation"].progress = "Pending"
    if record.status in {"RESOLVED", "ESCALATED"}:
        record.recovery_confirmed = record.status == "RESOLVED"
        sections["validation"].recovery_confirmed = record.recovery_confirmed
        sections["validation"].outcome = record.status
        sections["validation"].progress = (
            "Confirmed" if record.status == "RESOLVED" else "Failed"
        )
    return DetailResponse(
        tenant_id=record.tenant_id,
        platform_id=record.platform_id,
        incident=record,
        sections=sections,
        capabilities=_detail_capabilities(record.status, approval),
        approval_required=approval,
        execution_policy="Human approval required; one retry only"
        if approval
        else "Manual retry permitted by backend",
        demo=True,
    )


def _persist_detail(
    operation: str, record: IncidentRecord, request_id: str, revision: int
):
    import sqlite3
    import logging
    from autonomous_pipeline_incident_ui.models import DetailResponse, DetailEntry
    from autonomous_pipeline_incident_ui.service import ServiceError, DETAIL_WRITES

    try:
        directory = rx.get_upload_dir()
        directory.mkdir(parents=True, exist_ok=True)
        # This isolated development database stores only synthetic fixture data.
        with sqlite3.connect(
            directory / ".incident-demo.sqlite3", timeout=10
        ) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS detail (scope TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS detail_requests (scope TEXT, request TEXT, PRIMARY KEY(scope, request))"
            )
            db.execute("BEGIN IMMEDIATE")
            scenario = os.getenv("OPS_DEMO_SCENARIO", "loaded")
            key = f"{scenario}:{record.tenant_id}:{record.platform_id}:{record.id}"
            row = db.execute(
                "SELECT payload FROM detail WHERE scope=?", (key,)
            ).fetchone()
            result = (
                DetailResponse.model_validate_json(row[0])
                if row
                else _seed_detail(record)
            )
            previous = result.incident.status
            event = ""
            stamp = datetime.now(timezone.utc).isoformat()
            duplicate = (
                request_id
                and db.execute(
                    "SELECT 1 FROM detail_requests WHERE scope=? AND request=?",
                    (key, request_id),
                ).fetchone()
            )
            if operation in DETAIL_WRITES and not duplicate:
                if scenario == "policy_rejected":
                    raise ServiceError("policy_rejected")
                if scenario == "action_failed":
                    raise ServiceError("action_failed")
                if (
                    not request_id
                    or revision != result.revision
                    or operation
                    not in {c.operation for c in result.capabilities}
                ):
                    raise ServiceError("policy_rejected")
                if operation == "analyze":
                    result.incident.status = "INVESTIGATING"
                    event = "Analysis queued by operator"
                elif operation == "request_approval":
                    result.incident.status = "AWAITING_APPROVAL"
                    event = "Approval requested; execution paused"
                elif operation == "reject":
                    result.incident.status = "REJECTED"
                    event = "Operator rejected recommendation; no execution performed"
                else:
                    result.incident.status = "REMEDIATING"
                    result.sections["execution"].progress = "Running"
                    result.sections[
                        "execution"
                    ].summary = "Retry accepted by execution service"
                    result.sections["execution"].logs.append(
                        f"{stamp} Retry started from checkpoint"
                    )
                    event = (
                        "Approval accepted and retry started"
                        if operation == "approve"
                        else "Authorized retry started"
                    )
                db.execute(
                    "INSERT INTO detail_requests VALUES (?, ?)",
                    (key, request_id),
                )
            elif operation == "get_incident" and previous == "INVESTIGATING":
                result.incident.status = "DIAGNOSED"
                event = "Analysis completed by development provider"
            elif (
                operation == "get_execution_status"
                and previous == "REMEDIATING"
            ):
                failed = (
                    scenario == "failed_retry" or record.severity == "CRITICAL"
                )
                result.incident.status = "ESCALATED" if failed else "VALIDATING"
                result.sections["execution"].progress = (
                    "Failed" if failed else "Succeeded"
                )
                result.sections["execution"].summary = (
                    "Retry failed; escalated to operations"
                    if failed
                    else "Retry completed; validation still required"
                )
                result.sections["execution"].logs.append(
                    f"{stamp} {'ERROR Retry failed: downstream unavailable' if failed else 'INFO Retry completed successfully'}"
                )
                result.sections["validation"].progress = (
                    "Failed" if failed else "Pending"
                )
                result.sections["validation"].summary = (
                    "Validation failed: retry did not recover the pipeline"
                    if failed
                    else "Waiting for independent recovery checks"
                )
                result.sections["validation"].outcome = (
                    "ESCALATED" if failed else ""
                )
                event = result.sections["execution"].summary
            elif (
                operation == "get_validation_status"
                and previous == "VALIDATING"
            ):
                failed = scenario == "validation_failed"
                result.incident.status = "ESCALATED" if failed else "RESOLVED"
                result.sections["validation"].progress = (
                    "Failed" if failed else "Confirmed"
                )
                result.sections["validation"].summary = (
                    "Validation failed: health checks remain degraded"
                    if failed
                    else "Recovery confirmed: run succeeded, health checks passed, no new failures"
                )
                result.incident.recovery_confirmed = not failed
                result.sections["validation"].recovery_confirmed = not failed
                result.sections["validation"].outcome = result.incident.status
                event = result.sections["validation"].summary
            if event:
                result.revision += 1
                result.sections["audit"].entries.append(
                    DetailEntry(label=operation, value=event, timestamp=stamp)
                )
            result.capabilities = _detail_capabilities(
                result.incident.status, result.approval_required
            )
            db.execute(
                "INSERT OR REPLACE INTO detail VALUES (?, ?)",
                (key, result.model_dump_json()),
            )
            return result
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise


async def incident_detail(
    operation: str,
    tenant: str,
    platform: str,
    identifier: str,
    request_id: str = "",
    revision: int = 0,
):
    from autonomous_pipeline_incident_ui.service import ServiceError

    result = await incidents(
        tenant, platform, identifier.startswith("INC-NEW-")
    )
    record = next((r for r in result.incidents if r.id == identifier), None)
    if record is None:
        snapshot = await dashboard(tenant, platform)
        item = next((r for r in snapshot.incidents if r.id == identifier), None)
        if item is None:
            raise ServiceError("empty")
        record = IncidentRecord(
            **item.model_dump(),
            tenant_id=tenant,
            platform_id=platform,
            detected_at=datetime.now(timezone.utc) - timedelta(minutes=4),
        )
    return await asyncio.to_thread(
        _persist_detail, operation, record, request_id, revision
    )


def _persist_configuration(
    tenant: str, platform: str, values, request_id: str, revision: int
):
    import hashlib
    import logging
    import sqlite3
    from autonomous_pipeline_incident_ui.models import (
        ConfigurationResponse,
        ConfigurationSavedResponse,
        ConfigurationValues,
    )
    from autonomous_pipeline_incident_ui.service import ServiceError

    try:
        directory = rx.get_upload_dir()
        directory.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(
            directory / ".configuration-demo.sqlite3", timeout=10
        ) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS configs (scope TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS config_requests (scope TEXT, request TEXT, fingerprint TEXT, payload TEXT, PRIMARY KEY(scope, request))"
            )
            db.execute("BEGIN IMMEDIATE")
            key = f"{tenant}:{platform}"
            row = db.execute(
                "SELECT payload FROM configs WHERE scope=?", (key,)
            ).fetchone()
            if row:
                result = ConfigurationResponse.model_validate_json(row[0])
            else:
                fake = Faker()
                fake.seed_instance(key)
                index = {
                    ("tenant-a", "synapse"): 0,
                    ("tenant-a", "tibco"): 1,
                    ("tenant-b", "synapse"): 2,
                    ("tenant-b", "tibco"): 3,
                }[(tenant, platform)]
                result = ConfigurationResponse(
                    tenant_id=tenant,
                    platform_id=platform,
                    revision=0,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                    can_edit=True,
                    values=ConfigurationValues(
                        monitoring_enabled=index != 3,
                        interval_seconds=[60, 30, 120, 300][index],
                        failure_threshold=index + 2,
                        latency_seconds=fake.random_element(
                            [60, 120, 180, 300]
                        ),
                        remediation_policy=[
                            "approval_required",
                            "manual",
                            "approval_required",
                            "disabled",
                        ][index],
                        allowed_actions=["Retry"]
                        if index % 2 == 0
                        else ["Restart", "Retry"],
                    ),
                    policies=[
                        ScopeOption(
                            id="approval_required",
                            label="Human approval required",
                        ),
                        ScopeOption(
                            id="manual", label="Manual remediation only"
                        ),
                        ScopeOption(
                            id="disabled", label="Remediation disabled"
                        ),
                    ],
                    action_options=["Retry", "Restart", "Rollback"],
                    demo=True,
                )
            if values is not None:
                fingerprint = hashlib.sha256(
                    f"{revision}:{values.model_dump_json()}".encode()
                ).hexdigest()
                prior = db.execute(
                    "SELECT fingerprint, payload FROM config_requests WHERE scope=? AND request=?",
                    (key, request_id),
                ).fetchone()
                if prior:
                    if prior[0] != fingerprint:
                        raise ServiceError("validation")
                    return ConfigurationSavedResponse.model_validate_json(
                        prior[1]
                    )
                scenario = os.getenv("OPS_DEMO_SCENARIO", "loaded")
                if scenario in {"validation", "policy_rejected"}:
                    raise ServiceError("validation")
                if scenario == "save_failed":
                    raise ServiceError("save_failed")
                if not result.can_edit:
                    raise ServiceError("unauthorized")
                if not request_id or revision != result.revision:
                    raise ServiceError("validation")
                if values.remediation_policy not in {
                    p.id for p in result.policies
                } or not set(values.allowed_actions).issubset(
                    result.action_options
                ):
                    raise ServiceError("validation")
                result.values = values.model_copy(deep=True)
                result.revision += 1
                result.updated_at = datetime.now(timezone.utc).isoformat()
                saved = ConfigurationSavedResponse(
                    **result.model_dump(), saved=True, request_id=request_id
                )
                db.execute(
                    "INSERT INTO config_requests VALUES (?, ?, ?, ?)",
                    (key, request_id, fingerprint, saved.model_dump_json()),
                )
                db.execute(
                    "INSERT OR REPLACE INTO configs VALUES (?, ?)",
                    (key, result.model_dump_json()),
                )
                return saved
            db.execute(
                "INSERT OR REPLACE INTO configs VALUES (?, ?)",
                (key, result.model_dump_json()),
            )
            return result
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise


async def configuration(
    tenant: str,
    platform: str,
    values=None,
    request_id: str = "",
    revision: int = 0,
):
    from autonomous_pipeline_incident_ui.service import ServiceError, _development_provider

    if not _development_provider():
        raise ServiceError("unavailable")
    await asyncio.sleep(0.4)
    if tenant not in {"tenant-a", "tenant-b"} or platform not in {
        "synapse",
        "tibco",
    }:
        raise ServiceError("unauthorized")
    scenario = os.getenv("OPS_DEMO_SCENARIO", "loaded")
    if scenario in {"timeout", "unauthorized", "unavailable", "api", "empty"}:
        raise ServiceError(scenario)
    return await asyncio.to_thread(
        _persist_configuration, tenant, platform, values, request_id, revision
    )


async def catalog() -> Catalog:
    await asyncio.sleep(0.25)
    return Catalog(
        tenants=[
            ScopeOption(id="tenant-a", label="Tenant A"),
            ScopeOption(id="tenant-b", label="Tenant B"),
        ],
        platforms=[
            ScopeOption(id="synapse", label="Synapse"),
            ScopeOption(id="tibco", label="TIBCO"),
        ],
    )


def _reconcile_snapshot(result: DashboardResponse | IncidentsResponse):
    import logging
    import sqlite3
    from autonomous_pipeline_incident_ui.models import DetailResponse

    try:
        path = rx.get_upload_dir() / ".incident-demo.sqlite3"
        if not path.exists():
            return result
        with sqlite3.connect(path, timeout=10) as db:
            if not db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='detail'"
            ).fetchone():
                return result
            scenario = os.getenv("OPS_DEMO_SCENARIO", "loaded")
            for record in result.incidents:
                key = f"{scenario}:{result.tenant_id}:{result.platform_id}:{record.id}"
                row = db.execute(
                    "SELECT payload FROM detail WHERE scope=?", (key,)
                ).fetchone()
                if row:
                    confirmed = DetailResponse.model_validate_json(row[0])
                    record.status = confirmed.incident.status
                    record.recovery_confirmed = (
                        confirmed.incident.recovery_confirmed
                    )
                    record.severity = confirmed.incident.severity
        return result
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise


async def incidents(
    tenant: str, platform: str, new_detection: bool = False
) -> IncidentsResponse:
    from autonomous_pipeline_incident_ui.service import ServiceError

    await asyncio.sleep(0.65)
    scenario = os.getenv("OPS_DEMO_SCENARIO", "loaded")
    if scenario in {"timeout", "unauthorized", "unavailable", "api"}:
        raise ServiceError(scenario)
    tenants = {"tenant-a": "Tenant A", "tenant-b": "Tenant B"}
    platforms = {"synapse": "Synapse", "tibco": "TIBCO"}
    if tenant not in tenants or platform not in platforms:
        raise ServiceError("unauthorized")
    fake = Faker()
    fake.seed_instance(f"incidents:{tenant}:{platform}")
    statuses = [
        "AWAITING_APPROVAL",
        "INVESTIGATING",
        "DETECTED",
        "DIAGNOSED",
        "REMEDIATION_PROPOSED",
        "REMEDIATING",
        "VALIDATING",
        "RESOLVED",
        "REJECTED",
        "ESCALATED",
    ]
    severities = ["HIGH", "CRITICAL", "MEDIUM", "LOW"]
    now = datetime.now(timezone.utc)
    records = []
    if scenario != "empty":
        for index, status in enumerate(statuses):
            primary = (
                tenant == "tenant-a" and platform == "synapse" and index == 0
            )
            records.append(
                IncidentRecord(
                    id="INC-001"
                    if primary
                    else f"INC-{fake.unique.random_int(min=110, max=9999)}",
                    pipeline="Orders Pipeline"
                    if primary
                    else f"{fake.bs().title()} pipeline",
                    tenant=tenants[tenant],
                    platform=platforms[platform],
                    tenant_id=tenant,
                    platform_id=platform,
                    severity=severities[index % len(severities)],
                    status=status,
                    recovery_confirmed=status == "RESOLVED",
                    detected=f"{index * 14 + 4} min ago",
                    detected_at=now - timedelta(minutes=index * 14 + 4),
                )
            )
        if new_detection or scenario == "new_detection":
            records.append(
                IncidentRecord(
                    id=f"INC-NEW-{tenant}-{platform}",
                    pipeline=f"{fake.bs().title()} pipeline",
                    tenant=tenants[tenant],
                    platform=platforms[platform],
                    tenant_id=tenant,
                    platform_id=platform,
                    severity="HIGH",
                    status="DETECTED",
                    detected="Just detected",
                    detected_at=now,
                )
            )
    result = IncidentsResponse(
        tenant_id=tenant,
        platform_id=platform,
        updated_at=now.strftime("%H:%M:%S UTC"),
        incidents=records,
        demo=True,
    )
    return await asyncio.to_thread(_reconcile_snapshot, result)


async def dashboard(tenant: str, platform: str) -> DashboardResponse:
    from autonomous_pipeline_incident_ui.service import ServiceError

    await asyncio.sleep(0.65)
    scenario = os.getenv("OPS_DEMO_SCENARIO", "loaded")
    if scenario in {"timeout", "unauthorized", "unavailable", "api"}:
        raise ServiceError(scenario)
    if tenant not in {"tenant-a", "tenant-b"} or platform not in {
        "synapse",
        "tibco",
    }:
        raise ServiceError("unauthorized")
    empty = scenario == "empty"
    primary = tenant == "tenant-a" and platform == "synapse"
    fake = Faker()
    fake.seed_instance(f"{tenant}:{platform}")
    names = [
        "Orders Pipeline",
        "Revenue reconciliation",
        "Inventory synchronization",
        "Warehouse refresh",
        "Reporting publication",
    ]
    if platform == "tibco":
        names = [
            "Order event listener",
            "Payment message bridge",
            "Fulfillment orchestration",
            "Partner event delivery",
            "Customer event stream",
        ]
    if tenant == "tenant-b":
        names = [f"Regional {name.lower()}" for name in names]
    health = (
        [72.0, 100.0, 98.0, 100.0, 96.0]
        if primary
        else [100.0, 98.0, 100.0, 99.0, 100.0]
    )
    incidents = []
    if not empty:
        statuses = (
            ["AWAITING_APPROVAL", "INVESTIGATING", "RESOLVED"]
            if primary
            else ["DETECTED", "RESOLVED"]
        )
        for index, status in enumerate(statuses):
            identifier = (
                "INC-001"
                if primary and index == 0
                else f"INC-{fake.unique.random_int(min=110, max=999)}"
            )
            incidents.append(
                Incident(
                    id=identifier,
                    pipeline=names[index],
                    tenant="Tenant A" if tenant == "tenant-a" else "Tenant B",
                    platform="Synapse" if platform == "synapse" else "TIBCO",
                    severity="HIGH" if primary and index == 0 else "MEDIUM",
                    status=status,
                    recovery_confirmed=status == "RESOLVED",
                    detected=f"{index * 14 + 4} min ago",
                )
            )
    values = (
        ["24", "2", "1", "1", "2", "16", "2"]
        if primary
        else ["16", "1", "0", "0", "0", "15", "0"]
    )
    if empty:
        values = ["0", "0", "0", "0", "0", "0", "0"]
    labels = [
        "Total incidents",
        "Open incidents",
        "Investigating",
        "Awaiting approval",
        "Remediating",
        "Resolved",
        "Failed/Escalated",
    ]
    notes = [
        "In reporting window",
        "Awaiting investigation",
        "Diagnosis in progress",
        "Human review needed",
        "Recovery in progress",
        "Recovery confirmed",
        "Requires operations review",
    ]
    result = DashboardResponse(
        tenant_id=tenant,
        platform_id=platform,
        updated_at=datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        window="Last 24 hours",
        metrics=[
            Metric(label=label, value=value, note=note)
            for label, value, note in zip(labels, values, notes)
        ],
        incidents=incidents,
        pipelines=[]
        if empty
        else [
            Pipeline(
                name=name,
                health=score,
                status="Degraded" if score < 90 else "Healthy",
                detail="Approval required · retry paused"
                if primary and index == 0
                else "Latest run completed",
            )
            for index, (name, score) in enumerate(zip(names, health))
        ],
        summary="One pipeline needs your attention."
        if primary
        else "Your pipelines are operating normally.",
        demo=True,
    )
    return await asyncio.to_thread(_reconcile_snapshot, result)
