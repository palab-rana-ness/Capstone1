from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
from app.middleware.tenant import validate_tenant_header
from app.data.store import data_store
from app.schemas.schemas import PromotionSchema
from app.utils.pagination import paginate_data, create_response_envelope, normalize_datetime

router = APIRouter(prefix="/api/v1/promotions", tags=["promotions"])


@router.get("")
async def list_promotions(
    tenant_id: str = Depends(validate_tenant_header),
    status_filter: str = Query(None, alias="status"),
    promotion_type: str = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    updated_since: datetime = Query(None)
):
    """List all promotions for the tenant with optional filtering."""
    
    promotions = data_store.get_tenant_promotions(tenant_id)
    
    # Filter by status if provided
    if status_filter:
        promotions = [p for p in promotions if p.status == status_filter]
    
    # Filter by promotion type if provided
    if promotion_type:
        promotions = [p for p in promotions if p.promotion_type == promotion_type]
    
    # Filter by updated_since if provided
    updated_since = normalize_datetime(updated_since)
    if updated_since:
        promotions = [p for p in promotions if p.updated_at >= updated_since]
    
    # Sort by created_at
    promotions = sorted(promotions, key=lambda x: x.created_at, reverse=True)
    
    return paginate_data(
        promotions,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="promotion_api",
        entity="promotion",
        schema_version="1.0"
    )


@router.get("/active")
async def get_active_promotions(
    tenant_id: str = Depends(validate_tenant_header),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all active promotions for the tenant."""
    
    promotions = [p for p in data_store.get_tenant_promotions(tenant_id) if p.status == "ACTIVE"]
    promotions = sorted(promotions, key=lambda x: x.created_at, reverse=True)
    
    return paginate_data(
        promotions,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="promotion_api",
        entity="promotion",
        schema_version="1.0"
    )


@router.get("/{promotion_id}")
async def get_promotion(
    promotion_id: str,
    tenant_id: str = Depends(validate_tenant_header)
):
    """Get a specific promotion."""
    
    promotion = data_store.get_promotion(promotion_id, tenant_id)
    
    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Promotion {promotion_id} was not found for tenant {tenant_id}"
                }
            }
        )
    
    return create_response_envelope(
        promotion,
        tenant_id=tenant_id,
        source_system="promotion_api",
        entity="promotion",
        schema_version="1.0"
    )
