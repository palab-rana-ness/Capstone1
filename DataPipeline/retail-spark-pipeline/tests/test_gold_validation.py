"""Gold validation tests (section 40) and pipeline failure-handling inputs (section 48 #20)."""

from src.quality.quality_checks import validate_gold_pricing


def test_negative_final_price_fails_validation(spark):
    df = spark.createDataFrame(
        [{"tenant_id": "tenant_001", "product_id": "p1", "final_price": -5.0, "gross_amount": 100.0, "discount_amount": 105.0}]
    )
    failures = validate_gold_pricing(df)
    assert any("final_price" in f for f in failures)
    assert any("discount_amount exceeds" in f for f in failures)


def test_duplicate_business_key_fails_validation(spark):
    df = spark.createDataFrame(
        [
            {"tenant_id": "tenant_001", "product_id": "p1", "final_price": 10.0, "gross_amount": 100.0, "discount_amount": 0.0},
            {"tenant_id": "tenant_001", "product_id": "p1", "final_price": 10.0, "gross_amount": 100.0, "discount_amount": 0.0},
        ]
    )
    failures = validate_gold_pricing(df)
    assert any("duplicate" in f for f in failures)


def test_valid_pricing_passes(spark):
    df = spark.createDataFrame(
        [{"tenant_id": "tenant_001", "product_id": "p1", "final_price": 80.0, "gross_amount": 100.0, "discount_amount": 20.0}]
    )
    failures = validate_gold_pricing(df)
    assert failures == []
