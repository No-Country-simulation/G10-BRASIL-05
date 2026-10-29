"""Adaptador do cliente LLM usado pelos nós do agente (SCRUM-57).

Os nós dependem apenas do tipo `ClienteLLM`; o provedor concreto (Gemini/OpenAI)
fica isolado aqui e pode ser substituído por um cliente falso nos testes.
"""

from typing import Callable, List, Optional, Tuple

from app.config.settings import settings

MensagemLLM = Tuple[str, str]
ClienteLLM = Callable[[List[MensagemLLM]], str]


def obter_cliente_llm() -> Optional[ClienteLLM]:
    """Monta o cliente LLM a partir das settings; retorna None se não houver chave configurada."""
    if settings.GOOGLE_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0,
        )
    elif settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY,
            temperature=0.0,
        )
    else:
        return None

    def invocar(mensagens: List[MensagemLLM]) -> str:
        conteudo = llm.invoke(mensagens).content
        return conteudo if isinstance(conteudo, str) else str(conteudo)

    return invocar
