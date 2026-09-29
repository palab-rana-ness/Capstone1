from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
from app.middleware.tenant import validate_tenant_header
from app.data.store import data_store
from app.schemas.schemas import StoreSchema
from app.utils.pagination import paginate_data, create_response_envelope, normalize_datetime

router = APIRouter(prefix="/api/v1/stores", tags=["stores"])


@router.get("")
async def list_stores(
    tenant_id: str = Depends(validate_tenant_header),
    store_type: str = Query(None),
    status_filter: str = Query(None, alias="status"),
    city: str = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    updated_since: datetime = Query(None)
):
    """List all stores for the tenant with optional filtering."""
    
    stores = data_store.get_tenant_stores(tenant_id)
    
    # Filter by store type if provided
    if store_type:
        stores = [s for s in stores if s.store_type == store_type]
    
    # Filter by status if provided
    if status_filter:
        stores = [s for s in stores if s.status == status_filter]
    
    # Filter by city if provided
    if city:
        stores = [s for s in stores if s.city.lower() == city.lower()]
    
    # Filter by updated_since if provided
    updated_since = normalize_datetime(updated_since)
    if updated_since:
        stores = [s for s in stores if s.updated_at >= updated_since]
    
    # Sort by created_at
    stores = sorted(stores, key=lambda x: x.created_at, reverse=True)
    
    return paginate_data(
        stores,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="sales_database",
        entity="store",
        schema_version="1.0"
    )


@router.get("/{store_id}")
async def get_store(
    store_id: str,
    tenant_id: str = Depends(validate_tenant_header)
):
    """Get a specific store."""
    
    store = data_store.get_store(store_id, tenant_id)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Store {store_id} was not found for tenant {tenant_id}"
                }
            }
        )
    
    return create_response_envelope(
        store,
        tenant_id=tenant_id,
        source_system="sales_database",
        entity="store",
        schema_version="1.0"
    )
