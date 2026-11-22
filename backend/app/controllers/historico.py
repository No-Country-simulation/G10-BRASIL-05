import json
import logging
from typing import Any, Optional, Tuple
from fastapi import Depends, HTTPException, Query, status
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


def _extrair_revisao_doc(doc: Any, db: Optional[Session] = None) -> Optional[dict]:
    """Extrai informações da última revisão realizada por auditor humano."""
    revisao_info = None
    revisoes = getattr(doc, "revisoes", None)

    if not revisoes and hasattr(doc, "id"):
        sessao = db
        if not sessao:
            try:
                from sqlalchemy.orm import object_session
                sessao = object_session(doc)
            except Exception:
                sessao = None
        if sessao:
            try:
                from app.models.triagem import RevisaoModel
                revisoes = (
                    sessao.query(RevisaoModel)
                    .filter(RevisaoModel.documento_id == doc.id)
                    .order_by(RevisaoModel.id.asc())
                    .all()
                )
            except Exception:
                pass

    if revisoes:
        ult = None
        if isinstance(revisoes, list) and revisoes:
            decisoes_auditoria = [
                r for r in revisoes if getattr(r, "decisao", "").upper() != "INICIADA"
            ]
            ult = decisoes_auditoria[-1] if decisoes_auditoria else revisoes[-1]
        elif hasattr(revisoes, "__iter__"):
            lista = list(revisoes)
            if lista:
                decisoes_auditoria = [
                    r for r in lista if getattr(r, "decisao", "").upper() != "INICIADA"
                ]
                ult = decisoes_auditoria[-1] if decisoes_auditoria else lista[-1]

        if ult:
            revisor = getattr(ult, "revisor", None)
            if not revisor and getattr(ult, "revisor_id", None):
                sessao = db
                if not sessao:
                    try:
                        from sqlalchemy.orm import object_session
                        sessao = object_session(ult)
                    except Exception:
                        sessao = None
                if sessao:
                    try:
                        from app.models.users import UsuarioSistemaModel
                        revisor = sessao.query(UsuarioSistemaModel).filter_by(id=ult.revisor_id).first()
                    except Exception:
                        pass

            revisao_info = {
                "decisao": ult.decisao,
                "justificativa": ult.observacao or "",
                "revisado_em": (
                    ult.revisado_em.isoformat()
                    if hasattr(ult.revisado_em, "isoformat")
                    else str(ult.revisado_em)
                ),
                "revisor_nome": revisor.nome if revisor else "Auditor Clínico",
                "revisor_papel": revisor.papel if revisor else "",
                "revisor_registro": revisor.registro if revisor else "",
            }

    return revisao_info


def _formatar_doc_historico(doc: Any, db: Optional[Session] = None) -> dict:
    nome_paciente, cpf_paciente = _extrair_info_paciente(doc)
    revisao_info = _extrair_revisao_doc(doc, db=db)
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
        "canal_origem": getattr(doc, "canal_origem", None),
        "created_at": created_at,
        "revisao": revisao_info,
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
            documentos_formatados.append(_formatar_doc_historico(doc, db=db))
        except Exception as exc:
            logger.warning(
                "Falha ao formatar documento %s para o historico: %s",
                getattr(doc, "documento_id", "desconhecido"),
                exc,
            )
    return documentos_formatados


def obter_documento(
    documento_id: str,
    db: Session = Depends(get_db),
):
    """Retorna os detalhes completos de um documento do histórico."""
    repo = DatabaseRepository(db)
    doc = repo.buscar_por_documento_id(documento_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
    from app.controllers.triagem_jobs import _resultado_persistido
    res = _resultado_persistido(doc)
    if not res.get("revisao"):
        res["revisao"] = _extrair_revisao_doc(doc, db=db)
    return res


def desativar_alerta_documento(
    documento_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO", "ENFERMEIRO")),
):
    """Permite à equipe clínica desativar o alerta de emergência médica de um paciente."""
    repo = DatabaseRepository(db)
    doc = repo.buscar_por_documento_id(documento_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")

    doc.nivel_prioridade = "ROTINA"
    if doc.destino_principal == "Fila_Emergencia_Medica":
        doc.destino_principal = "Fluxo_Padrao"
        repo.vincular_destino(doc)

    db.commit()
    db.refresh(doc)
    return {
        "mensagem": "Alerta de emergência desativado com sucesso.",
        "documento_id": documento_id,
        "nivel_prioridade": doc.nivel_prioridade,
        "destino_principal": doc.destino_principal,
    }



