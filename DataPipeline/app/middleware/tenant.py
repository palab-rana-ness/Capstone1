from fastapi import Header, HTTPException, status
from app.data.store import data_store
from typing import Optional


class TenantContext:
    """Context to hold tenant information for the current request."""
    tenant_id: Optional[str] = None


tenant_context = TenantContext()


async def validate_tenant_header(
    x_tenant_id: Optional[str] = Header(
        None,
        alias="X-Tenant-ID",
        description="Tenant identifier, e.g. tenant_001, tenant_002, tenant_003"
    )
):
    """
    Dependency that validates the X-Tenant-ID header.

    Declared as a Header parameter (not a raw Request) so it shows up
    as a fillable field in Swagger UI / OpenAPI docs.

    Raises:
        HTTPException: If X-Tenant-ID is missing or invalid.
    """
    tenant_id = x_tenant_id

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "MISSING_TENANT_ID",
                    "message": "X-Tenant-ID header is required"
                }
            }
        )
    
    # Validate that tenant exists
    if tenant_id not in data_store.tenants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_TENANT_ID",
                    "message": f"Invalid tenant ID: {tenant_id}"
                }
            }
        )
    
    # Store in context
    tenant_context.tenant_id = tenant_id
    return tenant_id


def get_tenant_id() -> str:
    """Get the current tenant ID from context."""
    if not tenant_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "NO_TENANT_CONTEXT",
                    "message": "No tenant context available"
                }
            }
        )
    return tenant_context.tenant_id
