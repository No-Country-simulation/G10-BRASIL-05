import json
from typing import Dict, Any
from app.agent.state import GraphState
from app.agent.config import TERMOS_URGENCIA_CRITICA
from app.config.settings import settings
from app.config.logger import logger
from app.agent.prompts.classificacao import (
    PROMPT_CLASSIFICACAO_SYSTEM,
    PROMPT_CLASSIFICACAO_USER,
)


def _classificar_deterministico(texto_lower: str) -> Dict[str, Any]:
    """Plano C: Classificador heurístico determinístico e resiliente."""
    is_urgente = any(termo in texto_lower for termo in TERMOS_URGENCIA_CRITICA)

    if any(k in texto_lower for k in ["tomografia", "laudo", "raio-x", "ressonancia", "ultrassom", "angiotomografia", "arteria pulmonar"]):
        tipo = "Laudo de Exame de Imagem"
        especialidade = "Radiologia / Pneumologia" if is_urgente or "pulmonar" in texto_lower else "Radiologia"
        prioridade = "Urgente" if is_urgente else "Rotina"
        score = 0.98 if ("laudo" in texto_lower or "tomografia" in texto_lower) else 0.85
    elif any(k in texto_lower for k in ["receita", "receituario", "prescricao", "uso oral", "posologia", "medicamento"]):
        tipo = "Receituario Medico"
        especialidade = "Clinica Medica"
        prioridade = "Rotina"
        score = 0.95
    elif any(k in texto_lower for k in ["atestado", "afastamento", "repouso", "dispensa"]):
        tipo = "Atestado Medico"
        especialidade = "Clinica Geral"
        prioridade = "Rotina"
        score = 0.92
    elif any(k in texto_lower for k in ["guia", "tiss", "autorizacao", "solicitacao"]):
        tipo = "Guia de Solicitacao"
        especialidade = "Auditoria Medica"
        prioridade = "Rotina"
        score = 0.90
    else:
        tipo = "Documento Nao Identificado"
        especialidade = "Indeterminada"
        prioridade = "Rotina"
        score = 0.45

    return {
        "tipo_documento": tipo,
        "especialidade": especialidade,
        "nivel_prioridade": prioridade,
        "score_confianca": score,
        "metodo": "fallback_heuristico",
    }


def node_classificacao(state: GraphState) -> GraphState:
    """Nó 2: Classificação documental via LLM (Plano B) com fallback resiliente (Plano C) (SCRUM-57)."""
    texto = state.get("documento_texto") or ""
    texto_lower = texto.lower()

    # Tenta classificação via LLM se houver chave configurada (Plano B)
    classificacao = None
    if settings.GOOGLE_API_KEY or settings.OPENAI_API_KEY:
        try:
            if settings.GOOGLE_API_KEY:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=0.0,
                )
            else:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0.0,
                )

            mensagens = [
                ("system", PROMPT_CLASSIFICACAO_SYSTEM),
                ("human", PROMPT_CLASSIFICACAO_USER.format(documento_texto=texto[:4000])),
            ]
            resposta = llm.invoke(mensagens)
            conteudo = resposta.content
            if isinstance(conteudo, str):
                conteudo_limpo = conteudo.strip().strip("```json").strip("```").strip()
                dados_json = json.loads(conteudo_limpo)
                classificacao = {
                    "tipo_documento": dados_json.get("tipo_documento", "Laudo de Exame de Imagem"),
                    "especialidade": dados_json.get("especialidade", "Radiologia"),
                    "nivel_prioridade": dados_json.get("nivel_prioridade", "Rotina"),
                    "score_confianca": float(dados_json.get("score_confianca", 0.90)),
                    "metodo": "llm_generativa",
                }
        except Exception as e:
            logger.warning(f"Falha ao executar LLM no nó de classificação: {e}. Acionando Plano C (Fallback).")
            classificacao = None

    # Se LLM não disponível ou falhou, usa Plano C (Deterministico)
    if not classificacao:
        classificacao = _classificar_deterministico(texto_lower)

    return {
        **state,
        "classificacao": classificacao,
        "tipo_documento": classificacao["tipo_documento"],
        "especialidade": classificacao["especialidade"],
        "nivel_prioridade": classificacao["nivel_prioridade"],
        "score_confianca_classificacao": classificacao["score_confianca"],
        "status": "classificado",
    }
