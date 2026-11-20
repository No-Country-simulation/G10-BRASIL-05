import re

from pydantic import ValidationError

from app.agent.state import GraphState
from app.config.logger import logger
from app.schemas.ingestao import DocumentoIngerido, FormatoDocumento


def _normalizar_formato(tipo_arquivo: str) -> FormatoDocumento:
    """Aceita o tipo informado em qualquer caixa; tipos desconhecidos são tratados como texto."""
    try:
        return FormatoDocumento((tipo_arquivo or "").strip().upper())
    except ValueError:
        return FormatoDocumento.TEXTO


def _higienizar_texto(texto: str) -> str:
    """Normaliza espaçamentos e quebras de linha múltiplas."""
    texto_limpo = re.sub(r"[ \t]+", " ", texto)
    return re.sub(r"\n{3,}", "\n\n", texto_limpo).strip()


def node_ingestao(state: GraphState) -> GraphState:
    """Nó 1: Padroniza texto, PDF e imagem no mesmo formato para os nós seguintes (SCRUM-56)."""
    erros = list(state.get("erros", []))

    try:
        documento = DocumentoIngerido(
            formato=_normalizar_formato(state.get("tipo_arquivo", "")),
            texto=_higienizar_texto(state.get("documento_texto") or ""),
            imagens=state.get("imagens_documento") or [],
        )
    except ValidationError as erro:
        logger.warning(f"Imagens do documento fora do formato esperado: {erro}. Seguindo só com o texto.")
        erros.append("Imagens do documento em formato inválido foram descartadas na ingestão.")
        documento = DocumentoIngerido(
            formato=_normalizar_formato(state.get("tipo_arquivo", "")),
            texto=_higienizar_texto(state.get("documento_texto") or ""),
        )

    if not documento.texto and not documento.imagens:
        erros.append("Texto do documento está vazio após higienização.")

    return {
        **state,
        "tipo_arquivo": documento.formato.value,
        "documento_texto": documento.texto,
        "imagens_documento": [imagem.model_dump() for imagem in documento.imagens],
        "requer_ocr": documento.requer_ocr,
        "erros": erros,
        "status": "ingestado",
    }
