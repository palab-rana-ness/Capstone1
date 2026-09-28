import reflex as rx
import asyncio
import json
import logging
import math
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener


class ServiceError(Exception):
    def __init__(self, kind: str):
        self.kind = kind
        super().__init__(kind)


def base_url() -> str:
    value = os.getenv("FASTAPI_BASE_URL", "").strip().rstrip("/")
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise ServiceError("unavailable")
    return value


def api_configured() -> bool:
    return bool(os.getenv("FASTAPI_BASE_URL", "").strip())


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_bytes(
    path: str,
    params: dict[str, str],
    method: str = "GET",
    payload: bytes = b"",
    idempotency_key: str = "",
) -> bytes:
    kind = "api"
    try:
        base = base_url()
        if method not in {"GET", "POST", "PUT"}:
            raise ServiceError("request_invalid")
        timeout = float(os.getenv("FASTAPI_TIMEOUT", "12"))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ServiceError("unavailable")
        query = urlencode(
            {key: value for key, value in params.items() if value}
        )
        url = f"{base}{path}"
        if query:
            url = f"{url}?{query}"
        headers = {"Accept": "application/json"}
        token = os.getenv("FASTAPI_BEARER_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if idempotency_key:
            if any(ord(c) < 32 for c in idempotency_key):
                raise ServiceError("request_invalid")
            headers["Idempotency-Key"] = idempotency_key
        if method in {"POST", "PUT"}:
            headers["Content-Type"] = "application/json"
        request = Request(
            url,
            headers=headers,
            method=method,
            data=(payload or b"{}") if method in {"POST", "PUT"} else None,
        )
        with build_opener(NoRedirect()).open(
            request, timeout=timeout
        ) as response:
            return response.read()
    except HTTPError as error:
        logging.exception("Unexpected error")
        kind = (
            "unauthorized"
            if error.code in {401, 403}
            else "empty"
            if error.code == 404
            else "unavailable"
            if error.code >= 500
            else {
                400: "request_invalid",
                409: "conflict",
                422: "validation",
            }.get(error.code, "api")
        )
    except (TimeoutError, socket.timeout):
        logging.exception("Unexpected error")
        kind = "timeout"
    except URLError as error:
        logging.exception("Unexpected error")
        kind = (
            "timeout"
            if isinstance(error.reason, (TimeoutError, socket.timeout))
            else "unavailable"
        )
    except ServiceError as error:
        logging.exception("Unexpected error")
        kind = error.kind
    except Exception:
        logging.exception("Unexpected error")
        kind = "api"
    logging.error("Request failed")
    raise ServiceError(kind) from None


def segment(value: str) -> str:
    if (
        not value.strip()
        or value in {".", ".."}
        or any(ord(c) < 32 for c in value)
    ):
        raise ServiceError("request_invalid")
    return quote(value, safe="")


def incident_path(identifier: str = "", suffix: str = "") -> str:
    if suffix not in {
        "",
        "/timeline",
        "/logs",
        "/logs/refresh",
        "/analyze",
        "/diagnosis",
        "/history",
        "/remediation",
        "/approve",
        "/reject",
        "/retry",
        "/execution",
        "/validation",
    }:
        raise ServiceError("request_invalid")
    if not identifier:
        if suffix:
            raise ServiceError("request_invalid")
        return "/api/v1/incidents"
    return f"/api/v1/incidents/{segment(identifier)}{suffix}"


async def json_request(
    path: str,
    params: dict[str, str],
    method: str = "GET",
    body: object = None,
    idempotency_key: str = "",
) -> object:
    try:
        payload = json.dumps(
            body if body is not None else {}, allow_nan=False
        ).encode()
    except Exception:
        logging.exception("Unexpected error")
        logging.error("Request encoding failed: %s", "request_invalid")
        payload = b""
    if not payload:
        raise ServiceError("request_invalid")
    if method == "GET" and not idempotency_key:
        raw = await asyncio.to_thread(request_bytes, path, params, method)
    else:
        raw = await asyncio.to_thread(
            request_bytes, path, params, method, payload, idempotency_key
        )
    try:
        return json.loads(raw, parse_constant=lambda _: invalid_json())
    except Exception:
        logging.exception("Unexpected error")
        logging.error("Response decoding failed: %s", "api")
    raise ServiceError("api") from None


def invalid_json():
    raise ServiceError("api")


async def catalog_json(kind: str) -> object:
    if kind not in {"tenants", "platforms"}:
        raise ServiceError("request_invalid")
    return await json_request(f"/api/v1/{kind}", {})


async def config_json(
    tenant: str,
    platform: str,
    method: str = "GET",
    body: object = None,
    idempotency_key: str = "",
    platform_config: bool = False,
) -> object:
    if platform_config:
        if method != "GET":
            raise ServiceError("request_invalid")
        path = f"/api/v1/platforms/{segment(platform)}/config"
    else:
        if method not in {"GET", "PUT"}:
            raise ServiceError("request_invalid")
        path = f"/api/v1/tenants/{segment(tenant)}/config"
    return await json_request(
        path,
        {"tenant_id": tenant, "platform_id": platform},
        method,
        body,
        idempotency_key,
    )


async def incident_json(
    tenant: str,
    platform: str,
    identifier: str = "",
    suffix: str = "",
    method: str = "GET",
    body: object = None,
    idempotency_key: str = "",
) -> object:
    expected = (
        "POST"
        if suffix
        in {"/logs/refresh", "/analyze", "/approve", "/reject", "/retry"}
        else "GET"
    )
    if method != expected:
        raise ServiceError("request_invalid")
    path = incident_path(identifier, suffix)
    if tenant and not identifier:
        path = f"/api/v1/tenants/{segment(tenant)}/incidents"
    return await json_request(
        path,
        {"tenant_id": tenant, "platform_id": platform},
        method,
        body,
        idempotency_key,
    )
