"""Gold-stage validation checks (section 40) and tenant-isolation guard (section 50)."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def validate_gold_pricing(df: DataFrame) -> list[str]:
    """Return a list of failure reasons; an empty list means Gold pricing passed."""
    failures = []

    if df.filter(F.col("tenant_id").isNull()).count() > 0:
        failures.append("tenant_id is null for one or more records")

    if df.filter(F.col("product_id").isNull()).count() > 0:
        failures.append("product_id is null for one or more records")

    duplicate_keys = df.groupBy("tenant_id", "product_id").count().filter(F.col("count") > 1).count()
    if duplicate_keys > 0:
        failures.append(f"{duplicate_keys} duplicate (tenant_id, product_id) business keys")

    if df.filter(F.col("final_price") < 0).count() > 0:
        failures.append("final_price is negative for one or more records")

    if df.filter(F.col("discount_amount") > F.col("gross_amount")).count() > 0:
        failures.append("discount_amount exceeds gross_amount for one or more records")

    return failures


def validate_no_cross_tenant_join(*dfs: DataFrame) -> bool:
    """Structural guard: every input DataFrame must carry tenant_id.

    Actual cross-tenant safety is enforced by always joining ON tenant_id AND
    <business_key> in the Gold transforms (see gold/enrichment.py, gold/pricing.py).
    """
    return all("tenant_id" in df.columns for df in dfs)
