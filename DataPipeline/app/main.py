from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.data.seed import init_seed_data
from app.data.store import data_store
from app.middleware.tenant import validate_tenant_header, tenant_context
from app.routers import suppliers, products, inventory, promotions, sales, customers, stores, pipeline_status
from datetime import datetime
import json


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print("Starting Retail Mock Data Service...")
    init_seed_data()
    print(f"Loaded {len(data_store.tenants)} tenants")
    print(f"Loaded {len(data_store.products)} products")
    print(f"Loaded {len(data_store.suppliers)} suppliers")
    print(f"Loaded {len(data_store.sales_orders)} sales orders")
    print("Service ready!")
    
    yield
    
    # Shutdown
    print("Shutting down Retail Mock Data Service...")


app = FastAPI(
    title="Retail Mock Data Platform",
    description="Multi-tenant mock FastAPI server simulating a retail data ecosystem",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "retail-mock-data-service",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# Tenants endpoint
@app.get("/api/v1/tenants", tags=["tenants"])
async def list_tenants(limit: int = 100, offset: int = 0):
    """List all tenants."""
    tenant_list = list(data_store.tenants.values())
    tenant_list = sorted(tenant_list, key=lambda x: x.created_at)
    
    paginated = tenant_list[offset:offset + limit]
    has_more = (offset + limit) < len(tenant_list)
    
    return {
        "data": paginated,
        "metadata": {
            "source_system": "tenant_management",
            "entity": "tenant",
            "schema_version": "1.0",
            "request_timestamp": datetime.utcnow().isoformat() + "Z",
            "record_count": len(paginated)
        },
        "pagination": {
            "record_count": len(paginated),
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    }


# Categories endpoint
@app.get("/api/v1/categories", tags=["products"])
async def list_categories(
    tenant_id: str = Depends(validate_tenant_header),
    limit: int = 100,
    offset: int = 0
):
    """List all categories for the tenant."""
    categories = data_store.get_tenant_categories(tenant_id)
    categories = sorted(categories, key=lambda x: x.created_at)
    
    paginated = categories[offset:offset + limit]
    has_more = (offset + limit) < len(categories)
    
    return {
        "data": paginated,
        "metadata": {
            "tenant_id": tenant_id,
            "source_system": "product_database",
            "entity": "category",
            "schema_version": "1.0",
            "request_timestamp": datetime.utcnow().isoformat() + "Z",
            "record_count": len(paginated)
        },
        "pagination": {
            "record_count": len(paginated),
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    }


# Include routers
app.include_router(suppliers.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(promotions.router)
app.include_router(sales.router)
app.include_router(customers.router)
app.include_router(stores.router)
app.include_router(pipeline_status.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return our pre-built error envelopes as-is instead of nesting under 'detail'."""
    content = exc.detail if isinstance(exc.detail, dict) and "error" in exc.detail else {
        "error": {"code": "HTTP_ERROR", "message": exc.detail}
    }
    return JSONResponse(status_code=exc.status_code, content=content)


# Error handler for JSON serialization
@app.exception_handler(TypeError)
async def type_error_handler(request, exc):
    """Handle type errors during serialization."""
    return {
        "error": {
            "code": "SERIALIZATION_ERROR",
            "message": str(exc)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
