from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.triagem import DocumentoTriagemModel, TrilhaAuditoriaModel
from app.repositories.documentos import DocumentosRepository

class AuditoriaDatabaseRepository:
    """Lista a fila de revisão e registra decisões de auditoria."""

    def __init__(self, db: Session, documentos: DocumentosRepository):
        self.db = db
        self.documentos = documentos

    def listar_auditoria(self) -> List[DocumentoTriagemModel]:
        """Retorna documentos que aguardam revisão humana."""
        return (
            self.db.query(DocumentoTriagemModel)
            .filter(
                DocumentoTriagemModel.requer_auditoria_humana.is_(True),
                DocumentoTriagemModel.status_processamento == "em_auditoria",
            )
            .order_by(DocumentoTriagemModel.created_at.desc())
            .all()
        )

    def registrar_decisao(
        self,
        documento_id: str,
        decisao: str,
        auditor_nome: str,
        justificativa: str,
        dados_corrigidos: Optional[Dict[str, Any]] = None,
    ) -> Optional[DocumentoTriagemModel]:
        documento = self.documentos.buscar_por_documento_id(documento_id)
        if not documento:
            return None

        self.db.add(
            TrilhaAuditoriaModel(
                documento_id=documento_id,
                auditor_nome=auditor_nome,
                decisao=decisao,
                justificativa=justificativa,
                dados_anteriores=documento.dados_extraidos,
                dados_finais=dados_corrigidos or documento.dados_extraidos,
            )
        )
        documento.status_processamento = f"auditoria_{decisao}"
        documento.requer_auditoria_humana = False
        if dados_corrigidos:
            documento.dados_extraidos = dados_corrigidos

        self.db.flush()
        return documento
