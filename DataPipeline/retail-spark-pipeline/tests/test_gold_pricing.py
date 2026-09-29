"""Gold pricing calculation tests (sections 33-34, formulas documented in gold/pricing.py)."""

from datetime import date

from src.gold.pricing import build_gold_pricing


def _products_df(spark):
    return spark.createDataFrame(
        [
            {
                "tenant_id": "tenant_001",
                "product_id": "p1",
                "sku": "SKU1",
                "product_name": "Widget",
                "category_id": "c1",
                "category_name": "Cat",
                "brand": "Brand",
                "supplier_id": "s1",
                "unit_price": 100.0,
                "cost_price": 50.0,
                "currency": "INR",
                "tax_rate": 10.0,
            }
        ]
    )


def test_percentage_promotion_applies_correctly(spark):
    products = _products_df(spark)
    promotion_products = spark.createDataFrame(
        [{"tenant_id": "tenant_001", "promotion_id": "promo1", "product_id": "p1"}]
    )
    promotions = spark.createDataFrame(
        [
            {
                "tenant_id": "tenant_001",
                "promotion_id": "promo1",
                "status": "ACTIVE",
                "discount_type": "PERCENTAGE",
                "discount_value": 20.0,
                "maximum_discount": None,
                "start_date": "2026-01-01T00:00:00Z",
                "end_date": "2026-12-31T00:00:00Z",
                "promotion_type": "PRODUCT_DISCOUNT",
            }
        ],
        schema=(
            "tenant_id string, promotion_id string, status string, discount_type string, "
            "discount_value double, maximum_discount double, start_date string, end_date string, "
            "promotion_type string"
        ),
    )
    inventory = spark.createDataFrame([{"tenant_id": "tenant_001", "product_id": "p1", "quantity_available": 30}])
    sales_orders = spark.createDataFrame([{"tenant_id": "tenant_001", "order_id": "o1"}])
    sales_items = spark.createDataFrame(
        [
            {
                "tenant_id": "tenant_001",
                "order_id": "o1",
                "product_id": "p1",
                "quantity": 5,
                "unit_price": 100.0,
                "discount_amount": 0.0,
                "tax_amount": 0.0,
                "line_total": 500.0,
            }
        ]
    )

    result = build_gold_pricing(
        products,
        promotion_products,
        promotions,
        inventory,
        sales_orders,
        sales_items,
        "retail_data_pipeline",
        "run123",
        date(2026, 6, 1),
    ).collect()[0]

    assert result["promotion_applied"] is True
    assert float(result["final_price"]) == 80.0  # 100 - 20%
    assert float(result["net_price"]) == 88.0  # 80 * 1.10
    assert float(result["gross_amount"]) == 500.0  # 5 * 100
    assert float(result["discount_amount"]) == 100.0  # 5 * 20
    assert result["inventory_available"] == 30
    assert result["quantity_sold"] == 5


def test_no_active_promotion_means_full_price(spark):
    products = _products_df(spark)
    promotion_products = spark.createDataFrame([], "tenant_id string, promotion_id string, product_id string")
    promotions = spark.createDataFrame(
        [],
        "tenant_id string, promotion_id string, status string, discount_type string, "
        "discount_value double, maximum_discount double, start_date string, end_date string, promotion_type string",
    )
    inventory = spark.createDataFrame([], "tenant_id string, product_id string, quantity_available int")
    sales_orders = spark.createDataFrame([], "tenant_id string, order_id string")
    sales_items = spark.createDataFrame(
        [],
        "tenant_id string, order_id string, product_id string, quantity int, unit_price double, "
        "discount_amount double, tax_amount double, line_total double",
    )

    result = build_gold_pricing(
        products,
        promotion_products,
        promotions,
        inventory,
        sales_orders,
        sales_items,
        "retail_data_pipeline",
        "run123",
        date(2026, 6, 1),
    ).collect()[0]

    assert result["promotion_applied"] is False
    assert float(result["final_price"]) == 100.0
    assert float(result["discount_amount"]) == 0.0
    assert result["inventory_available"] == 0
    assert result["quantity_sold"] == 0
