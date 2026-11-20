"""Formato padronizado do documento entregue pela ingestão aos demais nós do agente (SCRUM-56)."""

from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class FormatoDocumento(str, Enum):
    TEXTO = "TEXTO"
    JSON = "JSON"
    PDF = "PDF"
    IMAGEM = "IMAGEM"


class ImagemDocumento(BaseModel):
    """Imagem a ser enviada ao modelo multimodal (foto, digitalização ou página de PDF escaneado)."""

    model_config = ConfigDict(extra="forbid")

    mime_type: str = Field(..., pattern=r"^image/(png|jpeg|webp|gif|bmp|tiff)$")
    dados_base64: str = Field(..., min_length=1)


class DocumentoIngerido(BaseModel):
    """Conteúdo do documento pronto para a LLM: texto direto e/ou imagens para leitura multimodal."""

    model_config = ConfigDict(extra="forbid")

    formato: FormatoDocumento
    texto: str = ""
    imagens: List[ImagemDocumento] = Field(default_factory=list)

    @property
    def requer_ocr(self) -> bool:
        """Sem texto legível, mas com imagens: o conteúdo precisa ser lido por um modelo de visão."""
        return not self.texto.strip() and bool(self.imagens)
