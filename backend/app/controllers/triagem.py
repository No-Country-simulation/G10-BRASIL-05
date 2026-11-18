from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.triagem import RequisicaoTriagem, RespostaTriagem
from app.services.triagem import TriagemService

router = APIRouter(prefix="/triagem", tags=["Triagem Clínica"])

@router.post("", response_model=RespostaTriagem, status_code=status.HTTP_200_OK)
def processar_triagem(
    requisicao: RequisicaoTriagem,
    db: Session = Depends(get_db),
):
    """Endpoint principal de triagem: ingere documento em texto/JSON, classifica, extrai e roteia."""
    service = TriagemService(db)
    return service.processar_triagem(requisicao)
