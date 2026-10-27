from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class RequisicaoTriagem(BaseModel):
    """Contrato de entrada para processamento de documento clínico."""
    documento_id: str = Field(..., example="DOC-CLIN-2026-8942", description="Identificador único do documento")
    tipo_arquivo: str = Field(..., example="PDF", description="Extensão ou tipo do arquivo (PDF, IMAGEM, TEXTO, JSON)")
    documento_texto: str = Field(..., description="Conteúdo textual bruto do documento extraído ou enviado diretamente")
    canal_origem: str = Field("Pronto_Socorro", example="Pronto_Socorro", description="Setor de origem do documento")


class ClassificacaoDocumento(BaseModel):
    """Diagnóstico de classificação e nível de prioridade clínica."""
    tipo_documento: str = Field(..., example="Laudo de Exame de Imagem")
    especialidade: str = Field(..., example="Radiologia / Pneumologia")
    nivel_prioridade: str = Field(..., example="Urgente", description="Rotina ou Urgente")
    score_confianca_classificacao: float = Field(..., ge=0.0, le=1.0, example=0.99)


class Paciente(BaseModel):
    nome: Optional[str] = Field(None, example="Carlos Eduardo Mendes")
    idade: Optional[int] = Field(None, example=52)


class MedicoSolicitante(BaseModel):
    nome: Optional[str] = Field(None, example="Dra. Renata Silveira")
    crm: Optional[str] = Field(None, example="145892-SP")

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
    exame_realizado: Optional[str] = Field(None, example="Tomografia de Torax com contraste")
    diagnostico_principal: Optional[str] = Field(None, example="Tromboembolismo Pulmonar Agudo (TEP)")
    cid_sugerido: Optional[str] = Field(None, example="I26.9")


class NotificacaoAlerta(BaseModel):
    canal: str = Field(..., example="Alerta_Plantao_Medico")
    mensagem: str = Field(..., example="ALERTA URGENTE: Laudo critico detectado.")


class DecisaoRoteamento(BaseModel):
    """Decisão automatizada de roteamento do documento no hospital."""
    destino_principal: str = Field(..., example="Fila_Emergencia_Medica")
    requer_auditoria_humana: bool = Field(..., example=False)
    justificativa_roteamento: str = Field(..., example="Achado critico de alta gravidade detectado.")
    notificacao_gerada: Optional[NotificacaoAlerta] = None


class ArmazenamentoOCI(BaseModel):
    """Registro de persistência segregada no bucket OCI Always Free."""
    bucket: str = Field(..., example="mediflow-documentos-clinicos")
    caminho_objeto: str = Field(..., example="processados/urgentes/DOC-CLIN-2026-8942.json")
    status_backup: str = Field(..., example="sucesso")


class RespostaTriagem(BaseModel):
    """Contrato oficial de saída da triagem clínica (alinhado ao mediflow.pdf)."""
    status: str = Field("processado", example="processado")
    documento_id: str = Field(..., example="DOC-CLIN-2026-8942")
    classificacao: ClassificacaoDocumento
    dados_extraidos: DadosExtraidos
    decisao_roteamento: DecisaoRoteamento
    armazenamento_oci: ArmazenamentoOCI


class DecisaoAuditoriaRequest(BaseModel):
    """Contrato para aprovação, correção ou rejeição no painel médico (Human-in-the-Loop)."""
    status_aprovacao: str = Field(..., example="aprovado", description="aprovado, corrigido ou rejeitado")
    auditor_nome: str = Field(..., example="Dr. Roberto Silva")
    justificativa: str = Field(..., example="Dados conferidos e aprovados clinicamente.")
    dados_corrigidos: Optional[Dict[str, Any]] = None
