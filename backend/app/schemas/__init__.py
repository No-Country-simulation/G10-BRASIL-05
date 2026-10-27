"""Contratos DTO Pydantic v2 (Validação estrita de entrada e saída)."""

from app.schemas.requisicao_documento import RequisicaoDocumento
from app.schemas.classificacao import ClassificacaoDocumento, TipoDocumento, NivelPrioridade
from app.schemas.roteamento import DecisaoRoteamento, NotificacaoAlerta
from app.schemas.armazenamento import ArmazenamentoOCI
from app.schemas.triagem import (
    RequisicaoTriagem,
    RespostaTriagem,
    DadosExtraidos,
    Paciente,
    MedicoSolicitante,
    DecisaoAuditoriaRequest,
    BloqueioAuditoriaRequest,
)

__all__ = [
    "RequisicaoDocumento",
    "ClassificacaoDocumento",
    "TipoDocumento",
    "NivelPrioridade",
    "DecisaoRoteamento",
    "NotificacaoAlerta",
    "ArmazenamentoOCI",
    "RequisicaoTriagem",
    "RespostaTriagem",
    "DadosExtraidos",
    "Paciente",
    "MedicoSolicitante",
    "DecisaoAuditoriaRequest",
    "BloqueioAuditoriaRequest",
]
