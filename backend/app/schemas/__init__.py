"""Contratos DTO Pydantic v2 (Validação estrita de entrada e saída)."""

from app.schemas.requisicao_documento import RequisicaoDocumento
from app.schemas.classificacao import ClassificacaoDocumento, TipoDocumento, NivelPrioridade
from app.schemas.dados_extraidos import DadosExtraidos
from app.schemas.roteamento import DecisaoRoteamento, NotificacaoAlerta
from app.schemas.armazenamento import ArmazenamentoOCI

__all__ = [
    "RequisicaoDocumento",
    "ClassificacaoDocumento",
    "TipoDocumento",
    "NivelPrioridade",
    "DadosExtraidos",
    "DecisaoRoteamento",
    "NotificacaoAlerta",
    "ArmazenamentoOCI",
]
