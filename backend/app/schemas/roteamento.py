from typing import Optional
from pydantic import BaseModel, Field


class NotificacaoAlerta(BaseModel):
    """Notificação gerada pelo agente para envio ao plantão médico ou canais de alerta."""
    canal: str = Field(..., example="Alerta_Plantao_Medico", description="Canal de destino do alerta")
    mensagem: str = Field(..., example="ALERTA URGENTE: Laudo critico detectado.", description="Texto da notificação")


class DecisaoRoteamento(BaseModel):
    """Decisão automatizada de roteamento do documento clínico no ecossistema hospitalar (SCRUM-52)."""
    destino_principal: str = Field(
        ...,
        example="Fila_Emergencia_Medica",
        description="Fila ou setor para onde o documento deve ser despachado",
    )
    requer_auditoria_humana: bool = Field(
        ...,
        example=False,
        description="Indica se há ambiguidade ou score abaixo do limiar que exige revisão médica",
    )
    justificativa_roteamento: str = Field(
        ...,
        example="Achado critico de alta gravidade detectado.",
        description="Explicação clínica detalhada da decisão de encaminhamento",
    )
    notificacao_gerada: Optional[NotificacaoAlerta] = Field(
        default=None,
        description="Alerta emitido caso haja urgência médica detectada",
    )
