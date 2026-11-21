import json
import logging
from typing import Any, Optional, Tuple
from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.repositories.database import DatabaseRepository, get_db
from app.services.autenticacao import exigir_papeis

logger = logging.getLogger(__name__)


def _extrair_info_paciente(doc: Any) -> Tuple[Optional[str], Optional[str]]:
    """Extrai nome e CPF do paciente com resiliência a campos nulos ou corrompidos."""
    nome = None
    cpf = None

    # 1. Tentar via relacionamento ORM direto
    try:
        paciente_rel = getattr(doc, "paciente", None)
        if paciente_rel:
            nome = getattr(paciente_rel, "nome", None)
            cpf = getattr(paciente_rel, "cpf", None)
    except Exception:
        pass

    # 2. Tentar via dados_extraidos
    dados = getattr(doc, "dados_extraidos", None)
    if isinstance(dados, str):
        try:
            dados = json.loads(dados)
        except Exception:
            dados = {}

    if isinstance(dados, dict):
        paciente = dados.get("paciente")
        if isinstance(paciente, dict):
            nome = nome or paciente.get("nome")
            cpf = cpf or paciente.get("cpf")
        elif isinstance(paciente, str):
            nome = nome or paciente

    return nome, cpf


def _formatar_doc_historico(doc: Any) -> dict:
    nome_paciente, cpf_paciente = _extrair_info_paciente(doc)
    created_at = (
        doc.created_at.isoformat()
        if hasattr(doc.created_at, "isoformat")
        else (str(doc.created_at) if doc.created_at else None)
    )
    return {
        "documento_id": doc.documento_id,
        "tipo_documento": doc.tipo_documento,
        "nivel_prioridade": doc.nivel_prioridade,
        "score_confianca": doc.score_confianca,
        "destino_principal": doc.destino_principal,
        "status_processamento": doc.status_processamento,
        "requer_auditoria_humana": doc.requer_auditoria_humana,
        "paciente_nome": nome_paciente,
        "paciente_cpf": cpf_paciente,
        "created_at": created_at,
    }


def listar_documentos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retorna o histórico de documentos processados."""
    repo = DatabaseRepository(db)
    docs = repo.listar_todos(skip=skip, limit=limit)
    documentos_formatados = []
    for doc in docs:
        try:
            documentos_formatados.append(_formatar_doc_historico(doc))
        except Exception as exc:
            logger.warning(
                "Falha ao formatar documento %s para o historico: %s",
                getattr(doc, "documento_id", "desconhecido"),
                exc,
            )
    return documentos_formatados

