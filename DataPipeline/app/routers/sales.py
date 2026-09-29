from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
from app.middleware.tenant import validate_tenant_header
from app.data.store import data_store
from app.schemas.schemas import SalesOrderSchema, SalesOrderItemSchema, SalesTransactionSchema
from app.utils.pagination import paginate_data, create_response_envelope, normalize_datetime

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])


@router.get("/orders")
async def list_sales_orders(
    tenant_id: str = Depends(validate_tenant_header),
    store_id: str = Query(None),
    product_id: str = Query(None),
    order_status: str = Query(None, alias="status"),
    date_from: datetime = Query(None),
    date_to: datetime = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    updated_since: datetime = Query(None)
):
    """List all sales orders for the tenant with optional filtering."""
    
    orders = data_store.get_tenant_sales_orders(tenant_id)
    
    # Filter by store if provided
    if store_id:
        orders = [o for o in orders if o.store_id == store_id]
    
    # Filter by product if provided (search through order items)
    if product_id:
        order_ids_with_product = [
            item.order_id for item in data_store.sales_order_items
            if item.product_id == product_id and item.tenant_id == tenant_id
        ]
        orders = [o for o in orders if o.order_id in order_ids_with_product]
    
    # Filter by order status if provided
    if order_status:
        orders = [o for o in orders if o.order_status == order_status]
    
    # Filter by date range if provided
    date_from = normalize_datetime(date_from)
    date_to = normalize_datetime(date_to)
    if date_from:
        orders = [o for o in orders if o.order_date >= date_from]
    if date_to:
        orders = [o for o in orders if o.order_date <= date_to]
    
    # Filter by updated_since if provided
    updated_since = normalize_datetime(updated_since)
    if updated_since:
        orders = [o for o in orders if o.updated_at >= updated_since]
    
    # Sort by order date
    orders = sorted(orders, key=lambda x: x.order_date, reverse=True)
    
    return paginate_data(
        orders,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="sales_database",
        entity="sales_order",
        schema_version="1.0"
    )


@router.get("/orders/{order_id}")
async def get_sales_order(
    order_id: str,
    tenant_id: str = Depends(validate_tenant_header)
):
    """Get a specific sales order."""
    
    order = data_store.get_sales_order(order_id, tenant_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Sales order {order_id} was not found for tenant {tenant_id}"
                }
            }
        )
    
    return create_response_envelope(
        order,
        tenant_id=tenant_id,
        source_system="sales_database",
        entity="sales_order",
        schema_version="1.0"
    )


@router.get("/orders/{order_id}/items")
async def get_sales_order_items(
    order_id: str,
    tenant_id: str = Depends(validate_tenant_header)
):
    """Get all items for a specific sales order."""
    
    # Verify order exists
    order = data_store.get_sales_order(order_id, tenant_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Sales order {order_id} was not found for tenant {tenant_id}"
                }
            }
        )
    
    items = data_store.get_sales_order_items_for_order(order_id, tenant_id)
    
    return create_response_envelope(
        items,
        tenant_id=tenant_id,
        source_system="sales_database",
        entity="sales_order_item",
        schema_version="1.0",
        is_list=True
    )


@router.get("/transactions")
async def get_sales_transactions(
    tenant_id: str = Depends(validate_tenant_header),
    store_id: str = Query(None),
    date_from: datetime = Query(None),
    date_to: datetime = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    updated_since: datetime = Query(None)
):
    """Get sales transactions (orders with their items) for the tenant."""
    
    orders = data_store.get_tenant_sales_orders(tenant_id)
    
    # Filter by store if provided
    if store_id:
        orders = [o for o in orders if o.store_id == store_id]
    
    # Filter by date range if provided
    date_from = normalize_datetime(date_from)
    date_to = normalize_datetime(date_to)
    if date_from:
        orders = [o for o in orders if o.order_date >= date_from]
    if date_to:
        orders = [o for o in orders if o.order_date <= date_to]
    
    # Filter by updated_since if provided
    updated_since = normalize_datetime(updated_since)
    if updated_since:
        orders = [o for o in orders if o.updated_at >= updated_since]
    
    # Sort by order date
    orders = sorted(orders, key=lambda x: x.order_date, reverse=True)
    
    # Build transactions with items
    transactions = []
    for order in orders:
        items = data_store.get_sales_order_items_for_order(order.order_id, tenant_id)
        transaction = {
            "order_id": order.order_id,
            "tenant_id": order.tenant_id,
            "customer_id": order.customer_id,
            "store_id": order.store_id,
            "order_date": order.order_date,
            "order_status": order.order_status,
            "payment_method": order.payment_method,
            "currency": order.currency,
            "total_amount": order.total_amount,
            "discount_amount": order.discount_amount,
            "tax_amount": order.tax_amount,
            "net_amount": order.net_amount,
            "items": items,
            "created_at": order.created_at,
            "updated_at": order.updated_at
        }
        transactions.append(transaction)
    
    return paginate_data(
        transactions,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
        source_system="sales_database",
        entity="sales_transaction",
        schema_version="1.0"
    )
