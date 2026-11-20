from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.repositories.database import DatabaseRepository, get_db
from app.services.autenticacao import exigir_papeis


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
