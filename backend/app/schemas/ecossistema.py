from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict


class PacienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    cpf: Optional[str] = None
    idade: Optional[int] = None
    created_at: Optional[datetime] = None


class MedicoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    crm: str
    especialidade: Optional[str] = None
    uf: Optional[str] = None
    created_at: Optional[datetime] = None


class HospitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    cnpj: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    ativo: bool = True
    created_at: Optional[datetime] = None


class DocumentoHistoricoItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    documento_id: str
    tipo_documento: Optional[str] = None
    nivel_prioridade: Optional[str] = None
    status_processamento: Optional[str] = None
    score_confianca: Optional[float] = None
    destino_principal: Optional[str] = None
    created_at: Optional[datetime] = None
    dados_extraidos: Optional[Dict[str, Any]] = None


class PacienteHistoricoResponse(BaseModel):
    paciente: PacienteResponse
    total_documentos: int
    historico: List[DocumentoHistoricoItem]
