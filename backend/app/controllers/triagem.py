from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.schemas.triagem import (
    RequisicaoTriagem,
    RespostaTriagem,
    DecisaoAuditoriaRequest,
)
from app.repositories.database import get_db, DatabaseRepository
from app.services.triagem import TriagemService

router = APIRouter(prefix="/triagem", tags=["Triagem Clínica"])


@router.post("", response_model=RespostaTriagem, status_code=status.HTTP_200_OK)
def processar_triagem(
    requisicao: RequisicaoTriagem,
    db: Session = Depends(get_db),
):
    """Endpoint principal de triagem: ingere, classifica, extrai e roteia o documento clínico."""
    service = TriagemService(db)
    return service.processar_triagem(requisicao)


@router.get("/documentos", status_code=status.HTTP_200_OK)
def listar_documentos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retorna o histórico de documentos processados."""
    repo = DatabaseRepository(db)
    docs = repo.listar_todos(skip=skip, limit=limit)
    return [
        {
            "documento_id": doc.documento_id,
            "tipo_documento": doc.tipo_documento,
            "nivel_prioridade": doc.nivel_prioridade,
            "score_confianca": doc.score_confianca,
            "destino_principal": doc.destino_principal,
            "status_processamento": doc.status_processamento,
            "requer_auditoria_humana": doc.requer_auditoria_humana,
            "created_at": doc.created_at,
        }
        for doc in docs
    ]


@router.get("/auditoria", status_code=status.HTTP_200_OK)
def listar_fila_auditoria(db: Session = Depends(get_db)):
    """Lista os documentos encaminhados para a fila médica de Human-in-the-Loop."""
    repo = DatabaseRepository(db)
    docs = repo.listar_auditoria()
    return [
        {
            "documento_id": doc.documento_id,
            "tipo_documento": doc.tipo_documento,
            "score_confianca": doc.score_confianca,
            "dados_extraidos": doc.dados_extraidos,
            "justificativa_roteamento": doc.justificativa_roteamento,
            "caminho_objeto_oci": doc.caminho_objeto_oci,
            "created_at": doc.created_at,
        }
        for doc in docs
    ]


@router.post("/auditoria/{documento_id}/decisao", status_code=status.HTTP_200_OK)
def registrar_decisao_auditoria(
    documento_id: str,
    payload: DecisaoAuditoriaRequest,
    db: Session = Depends(get_db),
):
    """Permite ao médico/auditor aprovar, corrigir ou rejeitar uma triagem de baixa confiança."""
    service = TriagemService(db)
    doc_atualizado = service.registrar_decisao_medica(documento_id, payload)
    if not doc_atualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento {documento_id} não encontrado na fila de auditoria.",
        )
    return {
        "mensagem": "Decisão de auditoria registrada com sucesso.",
        "documento_id": documento_id,
        "novo_status": doc_atualizado.status_processamento,
    }
