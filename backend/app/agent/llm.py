"""Módulo centralizado de instanciação de modelos LLM para o agente MediFlow."""

from typing import Optional, Any
from app.config.settings import settings
from app.config.logger import logger


def obter_cliente_llm() -> Optional[Any]:
    """Retorna cliente LLM configurado ou None se nenhuma chave estiver disponível."""
    if settings.OPENROUTER_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            modelo = settings.OPENROUTER_MODEL or "google/gemma-3-27b-it"
            return ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
                model=modelo,
                temperature=0.0,
                default_headers={
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "MediFlow Triagem Clinica",
                },
            )
        except Exception as e:
            logger.warning(f"Erro ao instanciar ChatOpenAI para OpenRouter: {e}")

    if settings.GOOGLE_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.0,
            )
        except Exception as e:
            logger.warning(f"Erro ao instanciar ChatGoogleGenerativeAI: {e}")

    if settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=0.0,
            )
        except Exception as e:
            logger.warning(f"Erro ao instanciar ChatOpenAI: {e}")

    return None
