"""Adaptador do cliente LLM usado pelos nós do agente (SCRUM-57).

Os nós dependem apenas do tipo `ClienteLLM`; o provedor concreto (OpenRouter/Gemini/OpenAI)
fica isolado aqui e pode ser substituído por um cliente falso nos testes.
Implementa contingência e alternância automática de chaves quando ocorre Rate Limit (HTTP 429).
"""

import logging
from typing import Any, Callable, List, Optional, Tuple

from app.config.settings import settings
from app.errors import DependencyUnavailableError

logger = logging.getLogger(__name__)

MensagemLLM = Tuple[str, str]
ClienteLLM = Callable[[List[MensagemLLM]], str]

# Índice global da chave atualmente ativa para evitar erros repetidos em cascata
_indice_chave_ativa: int = 0


def _eh_erro_429(erro: Exception) -> bool:
    """Verifica se a exceção representa um Rate Limit / Quota Exceeded (HTTP 429)."""
    codigo_status = getattr(erro, "status_code", None) or getattr(erro, "code", None)
    if codigo_status in (429, "429"):
        return True

    nome_classe = erro.__class__.__name__.lower()
    if "ratelimit" in nome_classe:
        return True

    msg = str(erro).lower()
    if "429" in msg or "rate limit" in msg or "rate_limit" in msg or "free-models-per-day" in msg:
        return True

    if erro.__cause__ and isinstance(erro.__cause__, Exception):
        return _eh_erro_429(erro.__cause__)

    return False


def _criar_cliente_openrouter(api_key: str) -> Any:
    """Instancia o ChatOpenAI apontando para o OpenRouter com a chave informada."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        model=settings.OPENROUTER_MODEL,
        api_key=api_key,
        timeout=35.0,
        default_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "MediFlow Triagem Clinica",
        },
    )


class AdaptadorLLM:
    """Invólucro para clientes LLM com alternância automática de chaves em caso de 429."""

    def __init__(self, raw_llm: Optional[Any] = None, chaves: Optional[List[str]] = None):
        self._raw_llm = raw_llm
        self._chaves = chaves or []

    def __call__(self, mensagens: List[MensagemLLM]) -> str:
        conteudo = self.invoke(mensagens).content
        return conteudo if isinstance(conteudo, str) else str(conteudo)

    def invoke(self, mensagens: List[MensagemLLM]) -> Any:
        global _indice_chave_ativa

        # Se não há chaves para rotação (ex: raw_llm falso injetado em testes)
        if not self._chaves:
            try:
                return self._raw_llm.invoke(mensagens)
            except Exception as erro:
                raise DependencyUnavailableError("O serviço de IA está indisponível.") from erro

        total_chaves = len(self._chaves)
        tentativas = 0
        ultimo_erro = None

        while tentativas < total_chaves:
            idx = _indice_chave_ativa % total_chaves
            chave_atual = self._chaves[idx]
            try:
                cliente = _criar_cliente_openrouter(chave_atual)
                self._raw_llm = cliente
                return cliente.invoke(mensagens)
            except Exception as erro:
                ultimo_erro = erro
                if _eh_erro_429(erro) and total_chaves > 1:
                    logger.warning(
                        "Rate limit (429) atingido na chave %d do OpenRouter (%s...). Alternando para a próxima chave...",
                        idx + 1,
                        chave_atual[:12] if len(chave_atual) >= 12 else "***",
                    )
                    _indice_chave_ativa = (_indice_chave_ativa + 1) % total_chaves
                    tentativas += 1
                    continue
                else:
                    raise DependencyUnavailableError("O serviço de IA está indisponível.") from erro

        logger.error("Todas as chaves do OpenRouter atingiram o limite de requisições (429).")
        raise DependencyUnavailableError(
            "O serviço de IA está indisponível: limite de requisições excedido em todas as chaves."
        ) from ultimo_erro


def obter_cliente_llm() -> AdaptadorLLM:
    """Cria o cliente OpenRouter e propaga erros de configuração ou conexão."""
    chaves = getattr(settings, "openrouter_api_keys", [])
    if not chaves:
        if settings.OPENROUTER_API_KEY:
            chaves = [settings.OPENROUTER_API_KEY]
        else:
            raise DependencyUnavailableError("OPENROUTER_API_KEY não configurada; triagem indisponível.")

    try:
        global _indice_chave_ativa
        chave_inicial = chaves[_indice_chave_ativa % len(chaves)]
        cliente = _criar_cliente_openrouter(chave_inicial)
        return AdaptadorLLM(raw_llm=cliente, chaves=chaves)
    except Exception as erro:
        raise DependencyUnavailableError("Não foi possível inicializar o cliente OpenRouter.") from erro
