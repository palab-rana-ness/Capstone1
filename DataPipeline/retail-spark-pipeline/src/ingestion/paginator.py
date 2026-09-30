"""Pagination helper -- walks a FastAPI list endpoint until has_more is False.

Never assumes an endpoint returns its full dataset in one response.
"""

from typing import Any, Iterator, Optional

from src.ingestion.api_client import RetailAPIClient


def paginate_all(
    client: RetailAPIClient,
    path: str,
    page_size: int,
    updated_since: Optional[str] = None,
    extra_params: Optional[dict[str, Any]] = None,
) -> Iterator[list[dict[str, Any]]]:
    """Yield successive pages (lists of records) from a paginated endpoint."""
    offset = 0
    while True:
        envelope = client.get_page(
            path=path,
            limit=page_size,
            offset=offset,
            updated_since=updated_since,
            extra_params=extra_params,
        )
        records = envelope.get("data", [])
        yield records

        has_more = envelope.get("pagination", {}).get("has_more", False)
        if not has_more or not records:
            break
        offset += page_size


def fetch_all_records(
    client: RetailAPIClient,
    path: str,
    page_size: int,
    updated_since: Optional[str] = None,
    extra_params: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Fetch every record across all pages of a list endpoint into one list."""
    records: list[dict[str, Any]] = []
    for page in paginate_all(client, path, page_size, updated_since, extra_params):
        records.extend(page)
    return records
