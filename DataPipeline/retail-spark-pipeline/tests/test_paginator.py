"""Pagination tests: fetch_all_records must walk every page (section 4/22)."""

from src.ingestion.paginator import fetch_all_records, paginate_all


class FakeClient:
    """Simulates a 3-page paginated endpoint."""

    def __init__(self):
        self.pages = [
            {"data": [{"id": 1}, {"id": 2}], "pagination": {"has_more": True}},
            {"data": [{"id": 3}, {"id": 4}], "pagination": {"has_more": True}},
            {"data": [{"id": 5}], "pagination": {"has_more": False}},
        ]
        self.calls = []

    def get_page(self, path, limit, offset, updated_since=None, extra_params=None):
        self.calls.append(offset)
        return self.pages[offset // limit]


def test_fetch_all_records_walks_every_page():
    client = FakeClient()
    records = fetch_all_records(client, "/api/v1/products", page_size=2)
    assert [r["id"] for r in records] == [1, 2, 3, 4, 5]
    assert client.calls == [0, 2, 4]


def test_paginate_all_stops_on_empty_page():
    class EmptyFirstPage:
        def get_page(self, path, limit, offset, updated_since=None, extra_params=None):
            return {"data": [], "pagination": {"has_more": True}}

    pages = list(paginate_all(EmptyFirstPage(), "/api/v1/products", page_size=10))
    assert pages == [[]]
