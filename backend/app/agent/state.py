from typing import TypedDict, Optional, Dict, Any, List


class GraphState(TypedDict, total=False):
    """Estado tipado que transita entre todos os nós do fluxo clínico no LangGraph."""

    # Dados brutos de entrada
    documento_id: str
    tipo_arquivo: str
    documento_texto: str
    canal_origem: str

    # Classificação
    classificacao: Optional[Dict[str, Any]]
    tipo_documento: Optional[str]
    especialidade: Optional[str]
    nivel_prioridade: Optional[str]
    score_confianca_classificacao: Optional[float]

    # Extração de dados clínicos
    dados_extraidos: Optional[Dict[str, Any]]
    paciente: Optional[Dict[str, Any]]
    medico_solicitante: Optional[Dict[str, Any]]
    exame_realizado: Optional[str]
    diagnostico_principal: Optional[str]
    cid_sugerido: Optional[str]

    # Detecção de Urgência & Consistência
    is_urgente: bool
    motivo_urgencia: Optional[str]
    inconsistencias: List[str]

    # Decisão de Roteamento
    decisao_roteamento: Optional[Dict[str, Any]]
    destino_principal: Optional[str]
    requer_auditoria_humana: bool
    justificativa_roteamento: Optional[str]
    notificacao_gerada: Optional[Dict[str, Any]]

    # Armazenamento OCI
    armazenamento_oci: Optional[Dict[str, Any]]

    # Status geral e erros
    status: str
    erros: List[str]
