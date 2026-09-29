"""Tenant isolation test for Gold enrichment (section 50).

A product in tenant_001 must never be joined with inventory belonging to
tenant_002, even when they share the same product_id.
"""

from src.gold.enrichment import enrich_with_inventory


def test_inventory_enrichment_never_crosses_tenants(spark):
    products = spark.createDataFrame([{"tenant_id": "tenant_001", "product_id": "prod_001", "name": "Widget"}])
    inventory = spark.createDataFrame([{"tenant_id": "tenant_002", "product_id": "prod_001", "quantity_available": 999}])

    result = enrich_with_inventory(products, inventory).collect()[0]

    assert result["tenant_id"] == "tenant_001"
    assert result["inventory_available"] == 0  # tenant_002's stock must NOT leak in
