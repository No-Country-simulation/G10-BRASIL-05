import json
import re
import unicodedata
from typing import Any, Dict, Optional

from pydantic import ValidationError

from app.agent.config import TERMOS_URGENCIA_CRITICA
from app.agent.llm import ClienteLLM, obter_cliente_llm
from app.agent.prompts.classificacao import (
    PROMPT_CLASSIFICACAO_SYSTEM,
    PROMPT_CLASSIFICACAO_USER,
)
from app.agent.state import GraphState
from app.config.logger import logger
from app.schemas.classificacao import (
    ClassificacaoDocumento,
    NivelPrioridade,
    TipoDocumento,
)

LIMITE_CARACTERES_PROMPT = 4000

# Score máximo do fallback: abaixo do CONFIDENCE_THRESHOLD para forçar revisão humana
SCORE_MAXIMO_FALLBACK = 0.70
SCORE_DOCUMENTO_NAO_IDENTIFICADO = 0.10

# Ordem importa: tipos mais específicos primeiro (um relatório de alta cita exames e medicamentos)
REGRAS_HEURISTICAS = [
    (TipoDocumento.RELATORIO_ALTA, ["relatorio de alta", "sumario de alta", "alta hospitalar"], "Clinica Medica"),
    (TipoDocumento.ATESTADO, ["atestado", "afastamento", "repouso", "dispensa"], "Clinica Geral"),
    (TipoDocumento.GUIA_TISS, ["guia", "tiss", "tuss", "autorizacao"], "Auditoria Medica"),
    (TipoDocumento.RECEITA, ["receita", "receituario", "prescricao", "uso oral", "posologia"], "Clinica Medica"),
    (TipoDocumento.LAUDO, ["laudo", "tomografia", "raio-x", "ressonancia", "ultrassom", "angiotomografia"], "Radiologia"),
]


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar com as palavras-chave."""
    sem_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acentos.lower()


def _contem_termo(texto_normalizado: str, termo: str) -> bool:
    return re.search(rf"\b{re.escape(termo)}\b", texto_normalizado) is not None


def _extrair_json(resposta: str) -> Dict[str, Any]:
    """Extrai o objeto JSON da resposta da LLM, aceitando blocos ```json."""
    inicio, fim = resposta.find("{"), resposta.rfind("}")
    if inicio == -1 or fim < inicio:
        raise ValueError("Resposta da LLM não contém um objeto JSON.")
    return json.loads(resposta[inicio : fim + 1])


def _classificar_com_llm(cliente_llm: ClienteLLM, texto: str) -> Optional[ClassificacaoDocumento]:
    """Plano B: classificação via LLM com saída validada pelo schema; None em caso de falha."""
    mensagens = [
        ("system", PROMPT_CLASSIFICACAO_SYSTEM),
        ("human", PROMPT_CLASSIFICACAO_USER.format(documento_texto=texto[:LIMITE_CARACTERES_PROMPT])),
    ]
    try:
        resposta = cliente_llm(mensagens)
        return ClassificacaoDocumento.model_validate(_extrair_json(resposta))
    except (ValueError, ValidationError) as erro:
        logger.warning(f"Resposta da LLM fora do schema de classificação: {erro}. Acionando Plano C (Fallback).")
    except Exception as erro:
        logger.warning(f"Falha ao executar LLM no nó de classificação: {erro}. Acionando Plano C (Fallback).")
    return None


def _classificar_deterministico(texto: str) -> Optional[ClassificacaoDocumento]:
    """Plano C: classificador heurístico por palavras-chave; None se nenhum tipo for reconhecido."""
    texto_normalizado = _normalizar(texto)
    is_emergencia = any(_contem_termo(texto_normalizado, termo) for termo in TERMOS_URGENCIA_CRITICA)

    for tipo, palavras_chave, especialidade in REGRAS_HEURISTICAS:
        acertos = sum(_contem_termo(texto_normalizado, palavra) for palavra in palavras_chave)
        if acertos:
            return ClassificacaoDocumento(
                tipo_documento=tipo,
                nivel_prioridade=NivelPrioridade.EMERGENCIA if is_emergencia else NivelPrioridade.ROTINA,
                especialidade=especialidade,
                score_confianca_classificacao=min(SCORE_MAXIMO_FALLBACK, 0.50 + 0.10 * acertos),
            )
    return None


def criar_node_classificacao(cliente_llm: Optional[ClienteLLM]):
    """Cria o nó de classificação com o cliente LLM informado (None usa apenas o fallback)."""

    def node_classificacao(state: GraphState) -> GraphState:
        """Nó 2: Classificação documental via LLM (Plano B) com fallback heurístico (Plano C) (SCRUM-57)."""
        texto = state.get("documento_texto") or ""

        classificacao = _classificar_com_llm(cliente_llm, texto) if cliente_llm else None
        metodo = "llm_generativa"
        if classificacao is None:
            classificacao = _classificar_deterministico(texto)
            metodo = "fallback_heuristico"

        if classificacao is None:
            return {
                **state,
                "classificacao": None,
                "tipo_documento": None,
                "especialidade": None,
                "nivel_prioridade": None,
                "score_confianca_classificacao": SCORE_DOCUMENTO_NAO_IDENTIFICADO,
                "erros": [*state.get("erros", []), "Tipo de documento não identificado na classificação."],
                "status": "classificado",
            }

        dados = classificacao.model_dump(mode="json")
        return {
            **state,
            "classificacao": {**dados, "metodo": metodo},
            "tipo_documento": dados["tipo_documento"],
            "especialidade": dados["especialidade"],
            "nivel_prioridade": dados["nivel_prioridade"],
            "score_confianca_classificacao": dados["score_confianca_classificacao"],
            "status": "classificado",
        }

    return node_classificacao


node_classificacao = criar_node_classificacao(obter_cliente_llm())
