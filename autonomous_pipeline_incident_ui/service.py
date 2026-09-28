import reflex as rx
import asyncio
import logging
import os
from autonomous_pipeline_incident_ui.http_client import (
    ServiceError,
    api_configured,
    incident_json,
    catalog_json,
    config_json,
)
from autonomous_pipeline_incident_ui.api_mapping import (
    mapped,
    normalize_list,
    normalize_detail,
    normalize_timeline,
    normalize_logs,
    dashboard_from_list,
    normalize_workflow,
    normalize_catalog,
    normalize_config,
    normalize_platform_config,
)
from autonomous_pipeline_incident_ui.models import (
    Catalog,
    DashboardResponse,
    IncidentsResponse,
    DetailResponse,
    ConfigurationValues,
    ConfigurationResponse,
    ConfigurationSavedResponse,
    WorkflowResponse,
    DetailSection,
    PlatformConfiguration,
)


DETAIL_OPERATIONS = {
    "get_incident": "",
    "get_incident_evidence": "/logs",
    "get_incident_diagnosis": "/diagnosis",
    "get_historical_incidents": "/history",
    "get_audit_timeline": "/timeline",
    "get_remediation": "/remediation",
    "request_approval": "",
    "analyze": "/analyze",
    "approve": "/approve",
    "reject": "/reject",
    "execute_retry": "/retry",
    "get_execution_status": "/execution",
    "get_execution_logs": "/execution",
    "get_validation_status": "/validation",
}
DETAIL_WRITES = {
    "request_approval",
    "analyze",
    "approve",
    "reject",
    "execute_retry",
}


def polling_settings() -> tuple[float, int]:
    import math

    try:
        interval = float(os.getenv("SENTINEL_POLL_INTERVAL", "3"))
        attempts = int(os.getenv("SENTINEL_POLL_MAX_ATTEMPTS", "40"))
        if (
            not math.isfinite(interval)
            or not 0.1 <= interval <= 60
            or not 1 <= attempts <= 300
        ):
            raise ValueError()
        return interval, attempts
    except (ValueError, OverflowError):
        logging.exception("Unexpected error")
        logging.error("Invalid polling configuration")
    raise ServiceError("configuration")


def current_user() -> str:
    value = os.getenv("SENTINEL_CURRENT_USER", "").strip()
    if not value or any(ord(c) < 32 for c in value):
        raise ServiceError("configuration")
    return value


async def start_analysis(
    tenant: str,
    platform: str,
    identifier: str,
    reason: str = "",
    request_id: str = "",
    revision: int = 0,
):
    requested_by = current_user()
    if _development_provider():
        return await detail_operation(
            "analyze", tenant, platform, identifier, request_id, revision
        )
    data = await incident_json(
        tenant,
        platform,
        identifier,
        "/analyze",
        "POST",
        {"requested_by": requested_by, "reason": reason},
        request_id,
    )
    return mapped(
        normalize_workflow, data, tenant, platform, identifier, "analyze"
    )


def _development_provider() -> bool:
    if api_configured():
        return False
    environment = os.getenv(
        "APP_ENV",
        "production"
        if os.getenv("REFLEX_ENV_MODE") == "prod"
        else "development",
    )
    provider = os.getenv(
        "OPS_PROVIDER", "mock" if environment == "development" else "api"
    )
    if provider == "mock" and environment != "development":
        raise ServiceError("unavailable")
    if provider not in {"mock", "api"}:
        raise ServiceError("unavailable")
    return provider == "mock"


async def get_timeline(tenant: str, platform: str, identifier: str):
    if _development_provider():
        return (
            await detail_operation(
                "get_audit_timeline", tenant, platform, identifier
            )
        ).sections["audit"]
    data = await incident_json(tenant, platform, identifier, "/timeline")
    return mapped(normalize_timeline, data, tenant, platform, identifier)


async def get_logs(
    tenant: str, platform: str, identifier: str, refresh: bool = False
):
    from autonomous_pipeline_incident_ui.models import LogsResponse

    if _development_provider():
        return LogsResponse()
    data = await incident_json(
        tenant,
        platform,
        identifier,
        "/logs/refresh" if refresh else "/logs",
        "POST" if refresh else "GET",
    )
    return mapped(normalize_logs, data, tenant, platform, identifier)


async def detail_operation(
    operation: str,
    tenant: str,
    platform: str,
    identifier: str,
    request_id: str = "",
    revision: int = 0,
) -> DetailResponse:
    try:
        if operation not in DETAIL_OPERATIONS:
            raise ServiceError("api")
        if _development_provider():
            from autonomous_pipeline_incident_ui.mock_provider import incident_detail

            result = await incident_detail(
                operation, tenant, platform, identifier, request_id, revision
            )
        else:
            if operation in {"request_approval", "analyze"}:
                raise ServiceError("request_invalid")
            suffix = DETAIL_OPERATIONS[operation]
            method = "POST" if operation in DETAIL_WRITES else "GET"
            if method == "POST" and not request_id:
                raise ServiceError("request_invalid")
            data = await incident_json(
                tenant,
                platform,
                identifier,
                suffix,
                method,
                {} if method == "POST" else None,
                request_id,
            )
            if operation == "get_incident":
                return mapped(
                    normalize_detail, data, tenant, platform, identifier
                )
            if operation == "get_audit_timeline":
                return WorkflowResponse(
                    section=mapped(
                        normalize_timeline, data, tenant, platform, identifier
                    )
                )
            if operation == "get_incident_evidence":
                logs = mapped(
                    normalize_logs, data, tenant, platform, identifier
                )
                return WorkflowResponse(
                    section=DetailSection(
                        logs=[row.message for row in logs.entries],
                        available=bool(logs.entries),
                    )
                )
            return mapped(
                normalize_workflow,
                data,
                tenant,
                platform,
                identifier,
                suffix.lstrip("/"),
            )
        if (result.tenant_id, result.platform_id, result.incident.id) != (
            tenant,
            platform,
            identifier,
        ):
            raise ServiceError("api")
        if (result.incident.tenant_id, result.incident.platform_id) != (
            tenant,
            platform,
        ):
            raise ServiceError("api")
        if set(result.sections) != {
            "evidence",
            "diagnosis",
            "history",
            "audit",
            "remediation",
            "execution",
            "validation",
        }:
            raise ServiceError("api")
        if result.approval_required and any(
            c.operation == "execute_retry" for c in result.capabilities
        ):
            raise ServiceError("api")
        return result
    except Exception as error:
        logging.exception("Unexpected error")
        kind = error.kind if isinstance(error, ServiceError) else "api"
        raise ServiceError(kind) from None


def _validate_configuration(
    result: ConfigurationResponse, tenant: str, platform: str
):
    if (result.tenant_id, result.platform_id) != (tenant, platform):
        raise ServiceError("api")
    if result.values.remediation_policy not in {p.id for p in result.policies}:
        raise ServiceError("api")
    if not set(result.values.allowed_actions).issubset(result.action_options):
        raise ServiceError("api")
    if len(set(result.values.allowed_actions)) != len(
        result.values.allowed_actions
    ):
        raise ServiceError("api")


async def get_tenant_config(
    tenant: str, platform: str
) -> ConfigurationResponse:
    try:
        if _development_provider():
            from autonomous_pipeline_incident_ui.mock_provider import configuration

            result = await configuration(tenant, platform)
        else:
            data = await config_json(tenant, platform)
            result = mapped(normalize_config, data, tenant, platform)
        _validate_configuration(result, tenant, platform)
        return result
    except Exception as error:
        kind = error.kind if isinstance(error, ServiceError) else "api"
        try:
            raise ServiceError(kind) from None
        except ServiceError as e:
            logging.exception("Unexpected error")
            logging.error(
                "%s",
                e.kind
                if e.kind
                in {
                    "api",
                    "configuration",
                    "request_invalid",
                    "unauthorized",
                    "empty",
                    "conflict",
                    "validation",
                    "unavailable",
                    "timeout",
                    "save_failed",
                    "policy_rejected",
                }
                else "api",
            )
            raise


async def save_configuration(
    tenant: str,
    platform: str,
    values: ConfigurationValues,
    request_id: str,
    revision: int,
) -> ConfigurationSavedResponse:
    try:
        values = ConfigurationValues.model_validate(values.model_dump())
        if not request_id or revision < 0:
            raise ServiceError("validation")
        if _development_provider():
            from autonomous_pipeline_incident_ui.mock_provider import configuration

            response = await configuration(
                tenant, platform, values, request_id, revision
            )
            result = ConfigurationSavedResponse.model_validate(
                response.model_dump()
            )
        else:
            data = await config_json(
                tenant,
                platform,
                "PUT",
                {"values": values.model_dump(), "revision": revision},
                request_id,
            )
            result = mapped(normalize_config, data, tenant, platform, True)
        _validate_configuration(result, tenant, platform)
        if result.request_id != request_id or result.revision <= revision:
            raise ServiceError("save_failed")
        return result
    except Exception as error:
        logging.exception("Unexpected error")
        kind = error.kind if isinstance(error, ServiceError) else "save_failed"
        raise ServiceError(kind) from None


async def get_incident(
    tenant: str, platform: str, identifier: str
) -> DetailResponse:
    return await detail_operation("get_incident", tenant, platform, identifier)


async def get_incident_evidence(
    tenant: str, platform: str, identifier: str
) -> DetailResponse:
    return await detail_operation(
        "get_incident_evidence", tenant, platform, identifier
    )


async def get_incident_diagnosis(
    tenant: str, platform: str, identifier: str
) -> DetailResponse:
    return await detail_operation(
        "get_incident_diagnosis", tenant, platform, identifier
    )


async def get_historical_incidents(
    tenant: str, platform: str, identifier: str
) -> DetailResponse:
    return await detail_operation(
        "get_historical_incidents", tenant, platform, identifier
    )


async def get_audit_timeline(tenant: str, platform: str, identifier: str):
    return await get_timeline(tenant, platform, identifier)


async def get_remediation(
    tenant: str, platform: str, identifier: str
) -> DetailResponse:
    return await detail_operation(
        "get_remediation", tenant, platform, identifier
    )


async def request_approval(
    tenant: str, platform: str, identifier: str, request_id: str, revision: int
) -> DetailResponse:
    return await detail_operation(
        "request_approval", tenant, platform, identifier, request_id, revision
    )


async def approve(
    tenant: str, platform: str, identifier: str, request_id: str, revision: int
) -> DetailResponse:
    return await detail_operation(
        "approve", tenant, platform, identifier, request_id, revision
    )


async def reject(
    tenant: str, platform: str, identifier: str, request_id: str, revision: int
) -> DetailResponse:
    return await detail_operation(
        "reject", tenant, platform, identifier, request_id, revision
    )


async def execute_retry(
    tenant: str, platform: str, identifier: str, request_id: str, revision: int
) -> DetailResponse:
    return await detail_operation(
        "execute_retry", tenant, platform, identifier, request_id, revision
    )


async def get_execution_status(
    tenant: str, platform: str, identifier: str
) -> DetailResponse:
    return await detail_operation(
        "get_execution_status", tenant, platform, identifier
    )


async def get_execution_logs(
    tenant: str, platform: str, identifier: str
) -> DetailResponse:
    return await detail_operation(
        "get_execution_logs", tenant, platform, identifier
    )


async def get_validation_status(
    tenant: str, platform: str, identifier: str
) -> DetailResponse:
    return await detail_operation(
        "get_validation_status", tenant, platform, identifier
    )


async def get_incidents(
    tenant: str, platform: str, new_detection: bool = False
) -> IncidentsResponse:
    try:
        if _development_provider():
            from autonomous_pipeline_incident_ui.mock_provider import incidents

            result = await incidents(tenant, platform, new_detection)
        else:
            data = await incident_json(tenant, platform)
            return mapped(normalize_list, data, tenant, platform)
        if result.tenant_id != tenant or result.platform_id != platform:
            raise ServiceError("api")
        if any(
            row.tenant_id != tenant or row.platform_id != platform
            for row in result.incidents
        ):
            raise ServiceError("api")
        if len({row.id for row in result.incidents}) != len(result.incidents):
            raise ServiceError("api")
        return result
    except Exception as error:
        logging.exception("Unexpected error")
        kind = error.kind if isinstance(error, ServiceError) else "api"
        raise ServiceError(kind) from None


async def load_catalog() -> Catalog:
    if _development_provider():
        from autonomous_pipeline_incident_ui.mock_provider import catalog

        return await catalog()
    tenants, platforms = await asyncio.gather(get_tenants(), get_platforms())
    return Catalog(tenants=tenants, platforms=platforms)


async def get_tenants():
    if _development_provider():
        return (await load_catalog()).tenants
    return mapped(normalize_catalog, await catalog_json("tenants"), "tenants")


async def get_platforms():
    if _development_provider():
        return (await load_catalog()).platforms
    return mapped(
        normalize_catalog, await catalog_json("platforms"), "platforms"
    )


async def get_platform_config(
    tenant: str, platform: str
) -> PlatformConfiguration:
    if _development_provider():
        return PlatformConfiguration(
            platform_id=platform, summary="Development platform configuration"
        )
    return mapped(
        normalize_platform_config,
        await config_json(tenant, platform, platform_config=True),
        tenant,
        platform,
    )


async def get_tenant_incidents(tenant: str, platform: str) -> IncidentsResponse:
    if not tenant:
        raise ServiceError("request_invalid")
    return await get_incidents(tenant, platform)


async def load_dashboard(tenant: str, platform: str) -> DashboardResponse:
    if not _development_provider():
        return dashboard_from_list(await get_incidents(tenant, platform))
    if _development_provider():
        from autonomous_pipeline_incident_ui.mock_provider import dashboard

        result = await dashboard(tenant, platform)
    if (
        result.tenant_id != tenant
        or result.platform_id != platform
        or len(result.metrics) != 7
    ):
        raise ServiceError("api")
    return result
