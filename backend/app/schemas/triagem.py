from typing import Optional, Any, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.dados_extraidos import DadosExtraidos as DadosExtraidosClinicos


class RequisicaoTriagem(BaseModel):
    """Contrato de entrada para processamento de documento clínico."""
    documento_id: str = Field(..., json_schema_extra={"example": "DOC-CLIN-2026-8942"}, description="Identificador único do documento")
    tipo_arquivo: str = Field(..., json_schema_extra={"example": "PDF"}, description="Extensão ou tipo do arquivo (PDF, IMAGEM, TEXTO, JSON)")
    documento_texto: str = Field(..., description="Conteúdo textual bruto do documento extraído ou enviado diretamente")
    canal_origem: str = Field("Pronto_Socorro", json_schema_extra={"example": "Pronto_Socorro"}, description="Setor de origem do documento")


class ClassificacaoDocumento(BaseModel):
    """Diagnóstico de classificação e nível de prioridade clínica."""
    tipo_documento: str = Field(..., json_schema_extra={"example": "Laudo de Exame de Imagem"})
    especialidade: str = Field(..., json_schema_extra={"example": "Radiologia / Pneumologia"})
    nivel_prioridade: str = Field(..., json_schema_extra={"example": "Urgente"}, description="Rotina ou Urgente")
    score_confianca_classificacao: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.99})


class Paciente(BaseModel):
    nome: Optional[str] = Field(None, json_schema_extra={"example": "Carlos Eduardo Mendes"})
    idade: Optional[int] = Field(None, json_schema_extra={"example": 52})


class MedicoSolicitante(BaseModel):
    nome: Optional[str] = Field(None, json_schema_extra={"example": "Dra. Renata Silveira"})
    crm: Optional[str] = Field(None, json_schema_extra={"example": "145892-SP"})

    @field_validator("crm")
    @classmethod
    def normalizar_crm(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip().upper()
        return v


class DadosExtraidos(BaseModel):
    """Entidades clínicas essenciais extraídas do documento."""
    paciente: Paciente = Field(default_factory=Paciente)
    medico_solicitante: MedicoSolicitante = Field(default_factory=MedicoSolicitante)
    exame_realizado: Optional[str] = Field(None, json_schema_extra={"example": "Tomografia de Torax com contraste"})
    diagnostico_principal: Optional[str] = Field(None, json_schema_extra={"example": "Tromboembolismo Pulmonar Agudo (TEP)"})
    cid_sugerido: Optional[str] = Field(None, json_schema_extra={"example": "I26.9"})


class NotificacaoAlerta(BaseModel):
    canal: str = Field(..., json_schema_extra={"example": "Alerta_Plantao_Medico"})
    mensagem: str = Field(..., json_schema_extra={"example": "ALERTA URGENTE: Laudo critico detectado."})


class DecisaoRoteamento(BaseModel):
    """Decisão automatizada de roteamento do documento no hospital."""
    destino_principal: str = Field(..., json_schema_extra={"example": "Fila_Emergencia_Medica"})
    requer_auditoria_humana: bool = Field(..., json_schema_extra={"example": False})
    justificativa_roteamento: str = Field(..., json_schema_extra={"example": "Achado critico de alta gravidade detectado."})
    notificacao_gerada: Optional[NotificacaoAlerta] = None


class ArmazenamentoOCI(BaseModel):
    """Registro de persistência segregada no bucket OCI Always Free."""
    bucket: str = Field(..., json_schema_extra={"example": "mediflow-documentos-clinicos"})
    caminho_objeto: str = Field(..., json_schema_extra={"example": "processados/urgentes/DOC-CLIN-2026-8942.json"})
    status_backup: str = Field(..., json_schema_extra={"example": "sucesso"})


class RespostaTriagem(BaseModel):
    """Contrato oficial de saída da triagem clínica (alinhado ao mediflow.pdf)."""
    status: str = Field("processado", json_schema_extra={"example": "processado"})
    documento_id: str = Field(..., json_schema_extra={"example": "DOC-CLIN-2026-8942"})
    classificacao: ClassificacaoDocumento
    dados_extraidos: DadosExtraidos
    decisao_roteamento: DecisaoRoteamento
    armazenamento_oci: ArmazenamentoOCI


class DecisaoAuditoriaRequest(BaseModel):
    """Contrato para aprovação, correção ou rejeição no painel médico (Human-in-the-Loop)."""
    status_aprovacao: Literal["aprovado", "corrigido", "rejeitado"] = Field(
        ..., json_schema_extra={"example": "aprovado"}, description="aprovado, corrigido ou rejeitado"
    )
    auditor_nome: str = Field(..., json_schema_extra={"example": "Dr. Roberto Silva"})
    justificativa: str = Field(..., json_schema_extra={"example": "Dados conferidos e aprovados clinicamente."})
    dados_corrigidos: Optional[DadosExtraidosClinicos] = None

    @model_validator(mode="after")
    def validar_consistencia_decisao(self):
        if self.status_aprovacao == "corrigido":
            if self.dados_corrigidos is None:
                raise ValueError("dados_corrigidos é obrigatório para a decisão corrigido.")
            if not _contem_valor_clinico(self.dados_corrigidos.model_dump()):
                raise ValueError(
                    "dados_corrigidos deve conter ao menos um valor clínico preenchido."
                )
        elif self.dados_corrigidos is not None:
            raise ValueError("dados_corrigidos só pode ser informado para a decisão corrigido.")
        return self


def _contem_valor_clinico(valor: Any) -> bool:
    """Retorna se a estrutura contém ao menos um valor clínico não vazio."""
    if isinstance(valor, str):
        return bool(valor.strip())
    if isinstance(valor, dict):
        return any(_contem_valor_clinico(item) for item in valor.values())
    if isinstance(valor, list):
        return any(_contem_valor_clinico(item) for item in valor)
    return valor is not None


class BloqueioAuditoriaRequest(BaseModel):
    """Contrato para aquisição/liberação de lock distribuído via Redis para revisão médica."""
    auditor_nome: str = Field(..., json_schema_extra={"example": "Dr. Roberto Silva"})
    ttl_segundos: int = Field(300, ge=30, le=1800, json_schema_extra={"example": 300})

