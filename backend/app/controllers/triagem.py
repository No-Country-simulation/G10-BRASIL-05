from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.triagem import RequisicaoTriagem, RespostaTriagem
from app.services.triagem import TriagemService
from app.services.autenticacao import exigir_papeis


def processar_triagem(
    requisicao: RequisicaoTriagem,
    db: Session = Depends(get_db),
):
    """Endpoint principal de triagem: ingere documento em texto/JSON, classifica, extrai e roteia."""
    service = TriagemService(db)
    return service.processar_triagem(requisicao)
