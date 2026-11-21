from enum import Enum
from pydantic import BaseModel, Field

class TipoDocumento(str, Enum):
    RECEITA = "RECEITA"
    LAUDO = "LAUDO"
    GUIA_TISS = "GUIA_TISS"
    RELATORIO_ALTA = "RELATORIO_ALTA"
    ATESTADO = "ATESTADO"

class NivelPrioridade(str, Enum):
    ROTINA = "ROTINA"
    URGENTE = "URGENTE"
    EMERGENCIA = "EMERGENCIA"

class ClassificacaoDocumento(BaseModel):
    tipo_documento: TipoDocumento = Field(
        ..., 
        description="O tipo de documento clínico identificado."
    )
    nivel_prioridade: NivelPrioridade = Field(
        ..., 
        description="O nível de prioridade baseado na avaliação inicial."
    )
    especialidade: str = Field(
        ..., 
        max_length=100, 
        description="A especialidade médica relacionada ao documento."
    )
    score_confianca_classificacao: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="O nível de confiança da IA nesta classificação (de 0.0 a 1.0)."
    )