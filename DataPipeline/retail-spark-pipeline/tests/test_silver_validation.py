"""Silver validation tests: required fields + business rules (sections 26/28)."""

from src.silver.validation import add_validation_errors, split_valid_invalid


def test_products_required_field_violation(spark):
    rows = [
        {
            "product_id": "p1",
            "tenant_id": "tenant_001",
            "sku": "SKU1",
            "product_name": None,
            "supplier_id": "s1",
            "unit_price": 10.0,
            "cost_price": 5.0,
            "tax_rate": 18.0,
        }
    ]
    schema = (
        "product_id string, tenant_id string, sku string, product_name string, "
        "supplier_id string, unit_price double, cost_price double, tax_rate double"
    )
    df = spark.createDataFrame(rows, schema=schema)
    validated = add_validation_errors(df, "products")
    valid_df, invalid_df = split_valid_invalid(validated)
    assert valid_df.count() == 0
    assert invalid_df.count() == 1
    errors = invalid_df.collect()[0]["validation_errors"]
    assert "product_name is required" in errors


def test_products_negative_price_is_invalid(spark):
    rows = [
        {
            "product_id": "p1",
            "tenant_id": "tenant_001",
            "sku": "SKU1",
            "product_name": "Widget",
            "supplier_id": "s1",
            "unit_price": -10.0,
            "cost_price": 5.0,
            "tax_rate": 18.0,
        }
    ]
    df = spark.createDataFrame(rows)
    validated = add_validation_errors(df, "products")
    valid_df, invalid_df = split_valid_invalid(validated)
    assert invalid_df.count() == 1
    assert valid_df.count() == 0


def test_products_valid_record_passes(spark):
    rows = [
        {
            "product_id": "p1",
            "tenant_id": "tenant_001",
            "sku": "SKU1",
            "product_name": "Widget",
            "supplier_id": "s1",
            "unit_price": 100.0,
            "cost_price": 50.0,
            "tax_rate": 18.0,
        }
    ]
    df = spark.createDataFrame(rows)
    validated = add_validation_errors(df, "products")
    valid_df, invalid_df = split_valid_invalid(validated)
    assert valid_df.count() == 1
    assert invalid_df.count() == 0


def test_sales_items_quantity_must_be_positive(spark):
    rows = [
        {
            "order_id": "o1",
            "tenant_id": "tenant_001",
            "order_item_id": "oi1",
            "product_id": "p1",
            "quantity": 0,
            "unit_price": 10.0,
            "discount_amount": 0.0,
            "tax_amount": 0.0,
            "line_total": 10.0,
        }
    ]
    df = spark.createDataFrame(rows)
    validated = add_validation_errors(df, "sales_items")
    valid_df, invalid_df = split_valid_invalid(validated)
    assert invalid_df.count() == 1


def test_promotions_percentage_discount_over_100_is_invalid(spark):
    rows = [
        {
            "promotion_id": "pr1",
            "tenant_id": "tenant_001",
            "promotion_code": "P1",
            "start_date": "2026-01-01T00:00:00Z",
            "end_date": "2026-12-31T00:00:00Z",
            "discount_type": "PERCENTAGE",
            "discount_value": 150.0,
        }
    ]
    df = spark.createDataFrame(rows)
    validated = add_validation_errors(df, "promotions")
    valid_df, invalid_df = split_valid_invalid(validated)
    assert invalid_df.count() == 1


def test_suppliers_rating_out_of_range_is_invalid(spark):
    rows = [
        {
            "supplier_id": "s1",
            "tenant_id": "tenant_001",
            "supplier_code": "SUP1",
            "supplier_name": "Acme",
            "rating": 6.0,
        }
    ]
    df = spark.createDataFrame(rows)
    validated = add_validation_errors(df, "suppliers")
    valid_df, invalid_df = split_valid_invalid(validated)
    assert invalid_df.count() == 1
