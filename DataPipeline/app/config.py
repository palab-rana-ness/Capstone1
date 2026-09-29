"""
Application configuration.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)


class Settings:
    """Application settings."""
    
    # Server
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database (for future use with real database)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # API
    API_TITLE: str = "Retail Mock Data Platform"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Multi-tenant mock FastAPI server for retail data"
    
    # Data
    SEED_DATA_ENABLED: bool = True
    RANDOM_SEED: int = 42  # For reproducible data generation

    # Intentional data-quality defects (for exercising downstream pipeline validation/quarantine).
    # Rate is capped at 10% regardless of the env value.
    DATA_ERROR_INJECTION_ENABLED: bool = os.getenv("DATA_ERROR_INJECTION_ENABLED", "True").lower() == "true"
    DATA_ERROR_RATE: float = min(float(os.getenv("DATA_ERROR_RATE", "0.08")), 0.10)

    # S3 location where retail-spark-pipeline writes its pipeline_status log records
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    
    # Pagination
    DEFAULT_LIMIT: int = 100
    MAX_LIMIT: int = 1000
    DEFAULT_OFFSET: int = 0
    
    # Tenants
    AVAILABLE_TENANTS = [
        "tenant_001",
        "tenant_002",
        "tenant_003"
    ]


settings = Settings()
