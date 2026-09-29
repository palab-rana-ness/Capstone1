"""Centralized configuration for the retail Spark pipeline.

Loads secrets/environment-specific values from environment variables (.env),
and static pipeline metadata (dataset/endpoint maps) from pipeline_config.yaml.
AWS credentials are never read or stored here -- Spark/boto3 resolve them via
the standard AWS credential provider chain (profile, env vars, or IAM role).
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = PROJECT_ROOT / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)

_PIPELINE_CONFIG_PATH = PROJECT_ROOT / "config" / "pipeline_config.yaml"


def _load_yaml_config() -> dict[str, Any]:
    with open(_PIPELINE_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass(frozen=True)
class Settings:
    # AWS
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))
    aws_profile: str = field(default_factory=lambda: os.getenv("AWS_PROFILE", "default"))
    s3_bucket: str = field(default_factory=lambda: os.getenv("S3_BUCKET", ""))

    # FastAPI source
    fastapi_base_url: str = field(default_factory=lambda: os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8000"))
    api_page_size: int = field(default_factory=lambda: int(os.getenv("API_PAGE_SIZE", "200")))
    api_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("API_TIMEOUT_SECONDS", "30")))

    # Pipeline identity
    pipeline_id: str = field(default_factory=lambda: os.getenv("PIPELINE_ID", "retail_data_pipeline"))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "dev"))
    service_version: str = field(default_factory=lambda: os.getenv("SERVICE_VERSION", "1.0.0"))

    # New Relic / OpenTelemetry (observability only, non-blocking)
    new_relic_license_key: str = field(default_factory=lambda: os.getenv("NEW_RELIC_LICENSE_KEY", ""))
    new_relic_region: str = field(default_factory=lambda: os.getenv("NEW_RELIC_REGION", "us"))
    new_relic_service_name: str = field(
        default_factory=lambda: os.getenv("NEW_RELIC_SERVICE_NAME", "retail-spark-pipeline")
    )
    new_relic_otlp_endpoint: str = field(default_factory=lambda: os.getenv("NEW_RELIC_OTLP_ENDPOINT", ""))
    silver_invalid_rate_threshold: float = field(
        default_factory=lambda: float(os.getenv("SILVER_INVALID_RATE_THRESHOLD", "0.10"))
    )

    # Spark
    spark_shuffle_partitions: int = field(default_factory=lambda: int(os.getenv("SPARK_SHUFFLE_PARTITIONS", "8")))
    spark_app_name: str = field(default_factory=lambda: os.getenv("SPARK_APP_NAME", "retail_data_pipeline"))

    # Static pipeline metadata loaded from YAML
    pipeline_config: dict[str, Any] = field(default_factory=_load_yaml_config)

    def s3_path(self, layer: str, dataset: str = "") -> str:
        """Build an s3a:// URI for a given layer (bronze/silver/gold/quarantine/logs)."""
        prefix = self.pipeline_config["s3_prefixes"][layer]
        parts = [f"s3a://{self.s3_bucket}", prefix]
        if dataset:
            parts.append(dataset)
        return "/".join(parts) + "/"

    @property
    def all_tenants(self) -> list[str]:
        return list(self.pipeline_config["tenants"])

    @property
    def primary_datasets(self) -> list[str]:
        return list(self.pipeline_config["datasets"]["primary"])

    @property
    def supporting_datasets(self) -> list[str]:
        return list(self.pipeline_config["datasets"]["supporting"])

    @property
    def all_datasets(self) -> list[str]:
        return self.primary_datasets + self.supporting_datasets

    def endpoint_for(self, dataset: str) -> dict[str, str]:
        return self.pipeline_config["source_endpoints"][dataset]


def get_settings() -> Settings:
    """Return a fresh Settings instance (re-reads env + yaml each call)."""
    return Settings()
