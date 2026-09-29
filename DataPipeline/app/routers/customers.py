from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
from app.middleware.tenant import validate_tenant_header
from app.data.store import data_store
from app.schemas.schemas import CustomerSchema
from app.utils.pagination import paginate_data, create_response_envelope, normalize_datetime

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("")
async def list_customers(
    tenant_id: str = Depends(validate_tenant_header),
    segment: str = Query(None, alias="customer_segment"),
    city: str = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    updated_since: datetime = Query(None)
):
    """List all customers for the tenant with optional filtering."""
    
    customers = data_store.get_tenant_customers(tenant_id)
    
    # Filter by segment if provided
    if segment:
        customers = [c for c in customers if c.customer_segment == segment]
    
    # Filter by city if provided
    if city:
        customers = [c for c in customers if c.city.lower() == city.lower()]
    
    # Filter by updated_since if provided
    updated_since = normalize_datetime(updated_since)
    if updated_since:
        customers = [c for c in customers if c.updated_at >= updated_since]
    
    # Sort by created_at
    customers = sorted(customers, key=lambda x: x.created_at, reverse=True)
    
    return paginate_data(
        customers,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="sales_database",
        entity="customer",
        schema_version="1.0"
    )


@router.get("/{customer_id}")
async def get_customer(
    customer_id: str,
    tenant_id: str = Depends(validate_tenant_header)
):
    """Get a specific customer."""
    
    customer = data_store.get_customer(customer_id, tenant_id)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Customer {customer_id} was not found for tenant {tenant_id}"
                }
            }
        )
    
    return create_response_envelope(
        customer,
        tenant_id=tenant_id,
        source_system="sales_database",
        entity="customer",
        schema_version="1.0"
    )
