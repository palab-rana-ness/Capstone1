"""Config loading tests (no Spark/Java required)."""

from src.config.config import get_settings


def test_settings_load_pipeline_config():
    settings = get_settings()
    assert settings.pipeline_id
    assert "tenant_001" in settings.all_tenants
    assert len(settings.all_tenants) == 3


def test_all_datasets_combines_primary_and_supporting():
    settings = get_settings()
    assert "products" in settings.primary_datasets
    assert "customers" in settings.supporting_datasets
    assert set(settings.primary_datasets) <= set(settings.all_datasets)
    assert set(settings.supporting_datasets) <= set(settings.all_datasets)


def test_s3_path_builds_expected_uri():
    settings = get_settings()
    path = settings.s3_path("bronze", "products")
    assert path.startswith("s3a://")
    assert path.endswith("bronze/products/")


def test_endpoint_for_products():
    settings = get_settings()
    endpoint = settings.endpoint_for("products")
    assert endpoint["path"] == "/api/v1/products"
    assert endpoint["source_system"] == "product_api"


def test_endpoint_for_sales_uses_transactions_endpoint():
    settings = get_settings()
    endpoint = settings.endpoint_for("sales")
    assert endpoint["path"] == "/api/v1/sales/transactions"
