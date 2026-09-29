"""Silver cleansing tests: dedup keeps latest record per business key (section 29)."""

from src.silver.cleansing import deduplicate, normalize_categoricals


def test_deduplicate_keeps_latest_by_updated_at(spark):
    rows = [
        {"tenant_id": "tenant_001", "product_id": "p1", "updated_at": "2026-09-01T00:00:00Z", "status": "active"},
        {"tenant_id": "tenant_001", "product_id": "p1", "updated_at": "2026-09-20T00:00:00Z", "status": "inactive"},
    ]
    df = spark.createDataFrame(rows)
    deduped_df, duplicate_count = deduplicate(df, "products")
    assert duplicate_count == 1
    result = deduped_df.collect()
    assert len(result) == 1
    assert result[0]["updated_at"] == "2026-09-20T00:00:00Z"


def test_deduplicate_no_duplicates_is_a_noop(spark):
    rows = [
        {"tenant_id": "tenant_001", "product_id": "p1", "updated_at": "2026-09-01T00:00:00Z"},
        {"tenant_id": "tenant_001", "product_id": "p2", "updated_at": "2026-09-01T00:00:00Z"},
    ]
    df = spark.createDataFrame(rows)
    deduped_df, duplicate_count = deduplicate(df, "products")
    assert duplicate_count == 0
    assert deduped_df.count() == 2


def test_normalize_categoricals_upper_trims(spark):
    rows = [{"status": " active "}]
    df = spark.createDataFrame(rows)
    result = normalize_categoricals(df, "products").collect()[0]
    assert result["status"] == "ACTIVE"
