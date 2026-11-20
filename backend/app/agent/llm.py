"""Adaptador do cliente LLM usado pelos nós do agente (SCRUM-57, SCRUM-96).

Os nós dependem apenas dos tipos `ClienteLLM` e `ClienteVisao`; o provedor concreto
(Gemini/OpenAI) fica isolado aqui e pode ser substituído por um cliente falso nos testes.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from app.config.settings import settings

MensagemLLM = Tuple[str, str]
ClienteLLM = Callable[[List[MensagemLLM]], str]
ClienteVisao = Callable[[str, List[Dict[str, str]]], str]

MODELO_PADRAO_GEMINI = "gemini-1.5-flash"
MODELO_PADRAO_OPENAI = "gpt-4o-mini"


def _criar_modelo_chat() -> Optional[Any]:
    """Instancia o modelo de chat do provedor configurado; None se não houver chave."""
    if settings.GOOGLE_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL or MODELO_PADRAO_GEMINI,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0,
        )
    if settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.LLM_MODEL or MODELO_PADRAO_OPENAI,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.0,
        )
    return None


def _conteudo_como_texto(conteudo: Any) -> str:
    return conteudo if isinstance(conteudo, str) else str(conteudo)


def obter_cliente_llm() -> Optional[ClienteLLM]:
    """Monta o cliente LLM de texto a partir das settings; retorna None se não houver chave configurada."""
    llm = _criar_modelo_chat()
    if llm is None:
        return None

    def invocar(mensagens: List[MensagemLLM]) -> str:
        return _conteudo_como_texto(llm.invoke(mensagens).content)

    return invocar


def obter_cliente_visao() -> Optional[ClienteVisao]:
    """Monta o cliente multimodal (instrução + imagens em base64); None sem chave configurada (SCRUM-96)."""
    llm = _criar_modelo_chat()
    if llm is None:
        return None

    from langchain_core.messages import HumanMessage

    def invocar(instrucao: str, imagens: List[Dict[str, str]]) -> str:
        partes = [{"type": "text", "text": instrucao}] + [
            {
                "type": "image_url",
                "image_url": {"url": f"data:{imagem['mime_type']};base64,{imagem['dados_base64']}"},
            }
            for imagem in imagens
        ]
        return _conteudo_como_texto(llm.invoke([HumanMessage(content=partes)]).content)

    return invocar
