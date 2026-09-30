from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
from app.middleware.tenant import validate_tenant_header
from app.data.store import data_store
from app.schemas.schemas import ProductSchema
from app.utils.pagination import paginate_data, create_response_envelope, normalize_datetime

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("")
async def list_products(
    tenant_id: str = Depends(validate_tenant_header),
    category_id: str = Query(None),
    supplier_id: str = Query(None),
    status_filter: str = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    updated_since: datetime = Query(None)
):
    """List all products for the tenant with optional filtering."""
    
    products = data_store.get_tenant_products(tenant_id)
    
    # Filter by category if provided
    if category_id:
        products = [p for p in products if p.category_id == category_id]
    
    # Filter by supplier if provided
    if supplier_id:
        products = [p for p in products if p.supplier_id == supplier_id]
    
    # Filter by status if provided
    if status_filter:
        products = [p for p in products if p.status == status_filter]
    
    # Filter by updated_since if provided
    updated_since = normalize_datetime(updated_since)
    if updated_since:
        products = [p for p in products if p.updated_at >= updated_since]
    
    # Sort by created_at
    products = sorted(products, key=lambda x: x.created_at, reverse=True)
    
    return paginate_data(
        products,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="product_database",
        entity="product",
        schema_version="1.0"
    )


@router.get("/{product_id}")
async def get_product(
    product_id: str,
    tenant_id: str = Depends(validate_tenant_header)
):
    """Get a specific product."""
    
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
    
    return create_response_envelope(
        product,
        tenant_id=tenant_id,
        source_system="product_database",
        entity="product",
        schema_version="1.0"
    )


@router.get("/{product_id}/promotions")
async def get_product_promotions(
    product_id: str,
    tenant_id: str = Depends(validate_tenant_header)
):
    """Get all active promotions for a product."""
    
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
    
    promotions = data_store.get_promotions_for_product(product_id, tenant_id)
    
    return create_response_envelope(
        promotions,
        tenant_id=tenant_id,
        source_system="promotion_api",
        entity="promotion",
        schema_version="1.0",
        is_list=True
    )
