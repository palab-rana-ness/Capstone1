from pydantic import BaseModel
from typing import TypeVar, Generic, Optional, Any
from datetime import datetime

T = TypeVar('T')


def normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Strip tzinfo so query datetimes can compare against naive UTC-stored timestamps."""
    if value is not None and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


class PaginationMetadata(BaseModel):
    record_count: int
    limit: int
    offset: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    metadata: dict[str, Any]
    pagination: PaginationMetadata


def paginate_data(
    items: list[T],
    limit: int = 100,
    offset: int = 0,
    tenant_id: str = None,
    source_system: str = None,
    entity: str = None,
    schema_version: str = "1.0"
) -> dict[str, Any]:
    """Paginate items and return with metadata."""
    
    from datetime import datetime
    
    # Validate pagination parameters
    limit = min(max(limit, 1), 1000)  # Between 1 and 1000
    offset = max(offset, 0)
    
    total_count = len(items)
    paginated_items = items[offset:offset + limit]
    has_more = (offset + limit) < total_count
    
    return {
        "data": paginated_items,
        "metadata": {
            "tenant_id": tenant_id,
            "source_system": source_system,
            "entity": entity,
            "schema_version": schema_version,
            "request_timestamp": datetime.utcnow().isoformat() + "Z",
            "record_count": len(paginated_items)
        },
        "pagination": {
            "record_count": len(paginated_items),
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    }


def create_response_envelope(
    data: Any,
    tenant_id: str,
    source_system: str,
    entity: str,
    schema_version: str = "1.0",
    is_list: bool = False
) -> dict[str, Any]:
    """Create a response envelope with metadata."""
    
    from datetime import datetime
    
    record_count = len(data) if is_list else 1
    
    return {
        "data": data,
        "metadata": {
            "tenant_id": tenant_id,
            "source_system": source_system,
            "entity": entity,
            "schema_version": schema_version,
            "request_timestamp": datetime.utcnow().isoformat() + "Z",
            "record_count": record_count
        }
    }
