from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
from app.middleware.tenant import validate_tenant_header
from app.data.store import data_store
from app.schemas.schemas import InventorySchema
from app.utils.pagination import paginate_data, create_response_envelope, normalize_datetime

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("")
async def list_inventory(
    tenant_id: str = Depends(validate_tenant_header),
    product_id: str = Query(None),
    location_id: str = Query(None),
    low_stock: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    updated_since: datetime = Query(None)
):
    """List all inventory for the tenant with optional filtering."""
    
    inventory = data_store.get_tenant_inventory(tenant_id)
    
    # Filter by product if provided
    if product_id:
        inventory = [inv for inv in inventory if inv.product_id == product_id]
    
    # Filter by location if provided
    if location_id:
        inventory = [inv for inv in inventory if inv.location_id == location_id]
    
    # Filter by low stock if requested
    if low_stock:
        inventory = [inv for inv in inventory if inv.quantity_available <= inv.reorder_level]
    
    # Filter by updated_since if provided
    updated_since = normalize_datetime(updated_since)
    if updated_since:
        inventory = [inv for inv in inventory if inv.updated_at >= updated_since]
    
    # Sort by updated_at
    inventory = sorted(inventory, key=lambda x: x.updated_at, reverse=True)
    
    return paginate_data(
        inventory,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="inventory_api",
        entity="inventory",
        schema_version="1.0"
    )


@router.get("/product/{product_id}")
async def get_inventory_by_product(
    product_id: str,
    tenant_id: str = Depends(validate_tenant_header),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all inventory records for a specific product."""
    
    # Verify product exists
    product = data_store.get_product(product_id, tenant_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Product {product_id} was not found for tenant {tenant_id}"
                }
            }
        )
    
    inventory = data_store.get_inventory_for_product(product_id, tenant_id)
    inventory = sorted(inventory, key=lambda x: x.updated_at, reverse=True)
    
    return paginate_data(
        inventory,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="inventory_api",
        entity="inventory",
        schema_version="1.0"
    )


@router.get("/location/{location_id}")
async def get_inventory_by_location(
    location_id: str,
    tenant_id: str = Depends(validate_tenant_header),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all inventory records for a specific location."""
    
    inventory = data_store.get_inventory_for_location(location_id, tenant_id)
    
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"No inventory found for location {location_id} in tenant {tenant_id}"
                }
            }
        )
    
    inventory = sorted(inventory, key=lambda x: x.updated_at, reverse=True)
    
    return paginate_data(
        inventory,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="inventory_api",
        entity="inventory",
        schema_version="1.0"
    )
