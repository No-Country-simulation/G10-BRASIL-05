"""Adaptador do cliente LLM usado pelos nós do agente (SCRUM-57).

Os nós dependem apenas do tipo `ClienteLLM`; o provedor concreto (OpenRouter/Gemini/OpenAI)
fica isolado aqui e pode ser substituído por um cliente falso nos testes.
"""

from typing import Any, Callable, List, Optional, Tuple

from app.config.logger import logger
from app.config.settings import settings

MensagemLLM = Tuple[str, str]
ClienteLLM = Callable[[List[MensagemLLM]], str]


class AdaptadorLLM:
    """Invólucro para clientes LLM compatível tanto como chamável quanto com .invoke()."""

    def __init__(self, raw_llm: Any):
        self._raw_llm = raw_llm

    def __call__(self, mensagens: List[MensagemLLM]) -> str:
        conteudo = self._raw_llm.invoke(mensagens).content
        return conteudo if isinstance(conteudo, str) else str(conteudo)

    def invoke(self, mensagens: List[MensagemLLM]) -> Any:
        return self._raw_llm.invoke(mensagens)


def obter_cliente_llm() -> Optional[AdaptadorLLM]:
    """Monta o cliente LLM a partir das settings; retorna None se não houver chave configurada."""
    raw_llm = None

    if settings.OPENROUTER_API_KEY:
        try:
            from langchain_openai import ChatOpenAI

            modelo = settings.OPENROUTER_MODEL or "google/gemma-3-27b-it"
            raw_llm = ChatOpenAI(
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

    elif settings.GOOGLE_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            raw_llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.0,
            )
        except Exception as e:
            logger.warning(f"Erro ao instanciar ChatGoogleGenerativeAI: {e}")

    elif settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI

            raw_llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=0.0,
            )
        except Exception as e:
            logger.warning(f"Erro ao instanciar ChatOpenAI: {e}")

    if raw_llm is None:
        return None

    return AdaptadorLLM(raw_llm)
