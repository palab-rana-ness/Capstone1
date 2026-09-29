"""Application configuration loaded from environment variables.

No secrets are hard-coded here; everything is sourced from the environment
(optionally via a local .env file for development).
"""
from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Central configuration object for the service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Diagnosis Agent"
    environment: str = Field(default="development")

    # LLM configuration (Groq).
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    groq_temperature: float = Field(default=0.1)

    # Chroma configuration.
    chroma_persist_dir: str = Field(default="./data/chroma")
    chroma_collection_name: str = Field(default="incident_memory")

    # Retrieval configuration.
    similar_incidents_top_k: int = Field(default=5)

    # New Relic configuration (log retrieval agent).
    newrelic_api_key: str = Field(default="")
    newrelic_account_id: str = Field(default="")
    newrelic_graphql_endpoint: str = Field(default="https://api.newrelic.com/graphql")
    newrelic_log_lookback_minutes: int = Field(default=60)
    newrelic_log_limit: int = Field(default=200)

    log_level: str = Field(default="INFO")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
