"""Factory for a Groq chat LLM client via LangChain."""
from __future__ import annotations

from langchain_groq import ChatGroq

from app.config import get_settings


def build_chat_llm() -> ChatGroq:
    """Build a LangChain ChatGroq client from application settings."""
    settings = get_settings()
    return ChatGroq(
        model=settings.groq_model,
        temperature=settings.groq_temperature,
        api_key=settings.groq_api_key or "not-set",
    )
