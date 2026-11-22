from typing import TypedDict, Optional, Dict, Any, List


class GraphState(TypedDict, total=False):
    """Estado tipado que transita entre todos os nós do fluxo clínico no LangGraph."""

    # Dados brutos de entrada
    documento_id: str
    tipo_arquivo: str
    documento_texto: str
    canal_origem: str
    referencia_fonte: Optional[str]

    # Elegibilidade e qualidade pré-classificação
    elegibilidade: Optional[str]
    confianca_elegibilidade: Optional[float]
    justificativa_elegibilidade: Optional[str]
    legibilidade_documento: Optional[str]
    avaliacao_escopo: Optional[Dict[str, Any]]
    qualidade_documento: Optional[Dict[str, Any]]

    # Evidências vinculadas aos valores extraídos
    evidencias_campos: Dict[str, Any]
    campos_bloqueados: List[str]
    validacao_schema: Optional[Dict[str, Any]]
    validacao_fonte: Optional[Dict[str, Any]]
    motivo_revisao: Optional[str]
    etapa_revisao: Optional[str]
    decisao_humana: Optional[Dict[str, Any]]
    mensagem_usuario: Optional[str]
    revisao_concluida: bool

    # Classificação
    classificacao: Optional[Dict[str, Any]]
    tipo_documento: Optional[str]
    especialidade: Optional[str]
    nivel_prioridade: Optional[str]
    score_confianca_classificacao: Optional[float]

    # Extração de dados clínicos
    identificacao_documento: Optional[Dict[str, Any]]
    identificacao_cadastral: Optional[Dict[str, Any]]
    etapa_atual: Optional[str]
    dados_extraidos: Optional[Dict[str, Any]]
    paciente: Optional[Dict[str, Any]]
    cpf_releitura_visual: bool
    cpf_validacao_falhou: bool
    medico_solicitante: Optional[Dict[str, Any]]
    exame_realizado: Optional[str]
    diagnostico_principal: Optional[str]
    cid_sugerido: Optional[str]
    medicamentos: List[Dict[str, Any]]

    # Detecção de Urgência & Consistência
    is_urgente: bool
    motivo_urgencia: Optional[str]
    inconsistencias: List[str]

    # Motor de Regras e Pontuação MediFlow (Excalidraw: 15/20/15/50 = 100)
    score_qualidade: Optional[float]
    score_cadastro: Optional[float]
    score_regulatorio: Optional[float]
    score_clinico: Optional[float]
    score_total: Optional[float]
    faixa_motor_regras: Optional[str]
    score_detalhes: Optional[Dict[str, Any]]

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
