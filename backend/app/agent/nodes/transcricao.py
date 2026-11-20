from typing import Optional

from app.agent.llm import ClienteVisao, obter_cliente_visao
from app.agent.prompts.transcricao import (
    PROMPT_TRANSCRICAO,
    RESPOSTA_SEM_TEXTO,
    VERSAO as VERSAO_PROMPT,
)
from app.agent.state import GraphState
from app.config.logger import logger


def criar_node_transcricao(cliente_visao: Optional[ClienteVisao]):
    """Cria o nó de OCR multimodal com o cliente de visão informado (None: OCR indisponível)."""

    def _registrar_falha(state: GraphState, mensagem: str) -> GraphState:
        return {**state, "erros": [*state.get("erros", []), mensagem], "status": "transcricao_pendente"}

    def node_transcricao(state: GraphState) -> GraphState:
        """Nó 1b: Transcreve imagens e PDFs escaneados com modelo multimodal (SCRUM-96)."""
        if not state.get("requer_ocr"):
            return state

        if cliente_visao is None:
            return _registrar_falha(state, "OCR indisponível: nenhum modelo multimodal configurado.")

        try:
            transcricao = cliente_visao(PROMPT_TRANSCRICAO, state.get("imagens_documento") or []).strip()
        except Exception as erro:
            logger.warning(f"Falha ao executar o modelo multimodal na transcrição: {erro}.")
            return _registrar_falha(state, "Falha na transcrição do documento escaneado.")

        if not transcricao or transcricao == RESPOSTA_SEM_TEXTO:
            return _registrar_falha(state, "Documento escaneado sem texto legível.")

        return {
            **state,
            "documento_texto": transcricao,
            "requer_ocr": False,
            "transcricao": {"metodo": "ocr_multimodal", "versao_prompt": VERSAO_PROMPT},
            "status": "transcrito",
        }

    return node_transcricao


node_transcricao = criar_node_transcricao(obter_cliente_visao())
