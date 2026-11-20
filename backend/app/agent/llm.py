"""Adaptador do cliente LLM usado pelos nós do agente (SCRUM-57).

Os nós dependem apenas do tipo `ClienteLLM`; o provedor concreto (OpenRouter/Gemini/OpenAI)
fica isolado aqui e pode ser substituído por um cliente falso nos testes.
"""

from typing import Any, Callable, List, Tuple

from app.config.settings import settings
from app.errors import DependencyUnavailableError

MensagemLLM = Tuple[str, str]
ClienteLLM = Callable[[List[MensagemLLM]], str]


class AdaptadorLLM:
    """Invólucro para clientes LLM compatível tanto como chamável quanto com .invoke()."""

    def __init__(self, raw_llm: Any):
        self._raw_llm = raw_llm

    def __call__(self, mensagens: List[MensagemLLM]) -> str:
        conteudo = self.invoke(mensagens).content
        return conteudo if isinstance(conteudo, str) else str(conteudo)

    def invoke(self, mensagens: List[MensagemLLM]) -> Any:
        try:
            return self._raw_llm.invoke(mensagens)
        except Exception as erro:
            raise DependencyUnavailableError("O serviço de IA está indisponível.") from erro


def obter_cliente_llm() -> AdaptadorLLM:
    """Cria o cliente OpenRouter e propaga erros de configuração ou conexão."""
    if not settings.OPENROUTER_API_KEY:
        raise DependencyUnavailableError("OPENROUTER_API_KEY não configurada; triagem indisponível.")

    try:
        from langchain_openai import ChatOpenAI

        cliente = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            model=settings.OPENROUTER_MODEL,
            api_key=settings.OPENROUTER_API_KEY,
            timeout=35.0,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "MediFlow Triagem Clinica",
            },
        )
        return AdaptadorLLM(cliente)
    except Exception as erro:
        raise DependencyUnavailableError("Não foi possível inicializar o cliente OpenRouter.") from erro
