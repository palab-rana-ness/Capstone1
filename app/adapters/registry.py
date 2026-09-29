"""Adapter registry: resolves an adapter name to a PipelineAdapter instance.

This is the single place that knows about concrete adapter classes. The
LangGraph nodes call `get_adapter()` and only interact with the abstract
`PipelineAdapter` interface afterward.
"""
from __future__ import annotations

from app.adapters.base import PipelineAdapter
from app.adapters.spark import SparkAdapter
from app.adapters.synapse import SynapseAdapter


class UnknownAdapterError(ValueError):
    """Raised when an incident references an adapter that is not registered."""


_ADAPTERS: dict[str, PipelineAdapter] = {
    "spark": SparkAdapter(),
    "synapse": SynapseAdapter(),
}


def get_adapter(adapter_name: str) -> PipelineAdapter:
    """Resolve an adapter by name, case-insensitively."""
    key = adapter_name.strip().lower()
    adapter = _ADAPTERS.get(key)
    if adapter is None:
        raise UnknownAdapterError(
            f"No adapter registered for '{adapter_name}'. "
            f"Known adapters: {', '.join(sorted(_ADAPTERS))}"
        )
    return adapter


def list_adapters() -> list[str]:
    return sorted(_ADAPTERS)
