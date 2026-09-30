from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
from app.middleware.tenant import validate_tenant_header, tenant_context
from app.data.store import data_store
from app.schemas.schemas import SupplierSchema
from app.utils.pagination import paginate_data, create_response_envelope, normalize_datetime

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])


@router.get("")
async def list_suppliers(
    tenant_id: str = Depends(validate_tenant_header),
    status_filter: str = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    updated_since: datetime = Query(None)
):
    """List all suppliers for the tenant with optional filtering."""
    
    suppliers = data_store.get_tenant_suppliers(tenant_id)
    
    # Filter by status if provided
    if status_filter:
        suppliers = [s for s in suppliers if s.status == status_filter]
    
    # Filter by updated_since if provided
    updated_since = normalize_datetime(updated_since)
    if updated_since:
        suppliers = [s for s in suppliers if s.updated_at >= updated_since]
    
    # Sort by created_at
    suppliers = sorted(suppliers, key=lambda x: x.created_at, reverse=True)
    
    return paginate_data(
        suppliers,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="supplier_api",
        entity="supplier",
        schema_version="1.0"
    )


@router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: str,
    tenant_id: str = Depends(validate_tenant_header)
):
    """Get a specific supplier."""
    
    supplier = data_store.get_supplier(supplier_id, tenant_id)
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Supplier {supplier_id} was not found for tenant {tenant_id}"
                }
            }
        )
    
    return create_response_envelope(
        supplier,
        tenant_id=tenant_id,
        source_system="supplier_api",
        entity="supplier",
        schema_version="1.0"
    )
